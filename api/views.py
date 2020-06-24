from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpRequest

import collections

from api.functions import (
	build_url, build_lifetime_url, make_request, correct_perspective, correct_mode,
	build_player_url, get_player_matches, retrieve_player_season_stats, build_player_account_id_url,
	make_request, build_match_url, get_match_telemetry_from_match, get_match_data, create_leaderboard_for_match, get_player_match_id,
	chunk_matches, parse_player_matches, parse_chunked_player_matches, player_placement_format
)

from api.models import *

import time
from datetime import datetime
from datetime import timedelta
from django.utils import timezone

import json as old_json
import orjson as json

from django.core.cache import cache
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.request import Request
from django.shortcuts import redirect
from dateutil.parser import parse
import ast
from django.db.models import Q

from django.utils.timesince import timesince

import threading
import logging

import api.settings as api_settings

logger = logging.getLogger('django')

@api_view(['GET'])
def status(request):
	return Response({
		'status': 'OK'
	})

@api_view(['POST'])
def search(request):
	
	start_time = time.time()

	body = request.data

	player_name = body.get('player_name', None)
	platform = body.get('platform', None)

	player_response_cache_key = api_settings.PLAYER_RESPONSE_CACHE_KEY.format(player_name, platform)

	cached_player_response = cache.get(player_response_cache_key, None)

	if cached_player_response and 'data' in cached_player_response:
		return Response(cached_player_response)

	player_request_cache_key = api_settings.PLAYER_REQUEST_CACHE_KEY.format(player_name, platform)
	player_platform_url_cache_key = api_settings.PLAYER_PLATFORM_URL_CACHE_KEY.format(player_name, platform)
	player_player_url_cache_key =  api_settings.PLAYER_URL_CACHE_KEY.format(player_name, platform)

	cached_platform_url = cache.get(player_platform_url_cache_key, None)
	cached_player_request = cache.get(player_request_cache_key, None)

	if not cached_platform_url:
		platform_url = build_url(platform)
		cache.set(player_platform_url_cache_key, platform_url, 60*30)
	else:
		platform_url = cached_platform_url

	cached_player_url = cache.get(player_player_url_cache_key, None)

	if not cached_player_url:
		player_url = build_player_url(base_url=platform_url, player_name=player_name)
		cache.set(player_player_url_cache_key, player_url, 60*30)
	else:
		player_url = cached_player_url

	if not cached_player_request or 'data' not in cached_player_request:
		player_request = make_request(player_url)

		if 'data' not in player_request:
			potential_current_player = Participant.objects.filter(player_name=player_name)
			if potential_current_player.exists():
				potential_current_player = potential_current_player.first()
				player_url = potential_current_player.player.api_url
				player_request = make_request(player_url)
				
		cache.set(cached_player_request, player_request, 120)
	else:
		player_request = cached_player_request

	ajax_data = {}

	player_data_length = 0

	if 'data' in player_request:

		api_ids = list(set(Match.objects.values_list('api_id', flat=True).distinct()))

		if isinstance(player_request['data'], list):
			player_id = player_request['data'][0]['id']
			player_data_length = (len(player_request['data'][0]['relationships']['matches']['data']), [match['id'] for match in player_request['data'][0]['relationships']['matches']['data'] if get_player_match_id(player_id, match['id']) not in api_ids]) 
		else:
			player_id = player_request['data']['id']
			player_data_length = (len(player_request['data']['relationships']['matches']['data']), [match['id'] for match in player_request['data']['relationships']['matches']['data'] if get_player_match_id(player_id, match['id']) not in api_ids]) 

		if player_data_length[0] > 0:

			ajax_data['player_id'] = player_id
			ajax_data['player_name']  = player_name

			length_of_matches = len(player_data_length[1])

			if length_of_matches > 0:

				player_currently_processing_cache_key = api_settings.PLAYER_CURRENTLY_PROCESSING_CACHE_KEY.format(player_id, platform)
				currently_processing = cache.get(player_currently_processing_cache_key, None)

				if not currently_processing:
					cache.set(player_currently_processing_cache_key, True, 60)
					ajax_data['currently_processing'] = True
					thread = threading.Thread(target=get_player_matches,  kwargs={
						'platform_url': platform_url,
						'player_response': player_request
					})
					thread.daemon = True
					thread.start()
				else:
					ajax_data['currently_processing'] = False

			else:
				ajax_data['message'] =  "No new matches to process for this user."
				ajax_data['no_new_matches'] = True
				if cached_player_url:
					cache.touch(player_player_url_cache_key, 120)
				if cached_platform_url:
					cache.touch(player_platform_url_cache_key, 120)
				if cached_player_request:
					cache.touch(player_request_cache_key, 120)

		else:
			ajax_data['error'] = "Sorry, looks like this player has not played any matches in the last 14 days."

	else:
		ajax_data['error'] = "Sorry, looks like this player does not exist."

	cache.set(player_response_cache_key, ajax_data, 120)
	return Response(ajax_data)

@api_view(['POST'])
def retrieve_matches(request):

	body = request.data
	player_id = body.get('player_id', None)
	player_match_data_cache = api_settings.PLAYER_MATCH_DATA_CACHE_KEY.format(player_id)

	cached_ajax_data = cache.get(player_match_data_cache, None)

	if cached_ajax_data:
		return Response(cached_ajax_data)

	ajax_data = {}

	current_player = Player.objects.filter(api_id=player_id).first()
		
	if current_player:

		match_data = get_match_data(player_id, current_player.id)

		if match_data.exists():
			
			match_ids = match_data.values_list('match_id', flat=True).distinct()			

			ajax_data = {
				'data':[
					{	
						'id': roster.match.id,
						'map': roster.match.map.name if roster.match.map else None,
						'mode': f'{roster.match.mode.upper()}<br>' + '<span class="badge badge-success">Ranked</span>' if roster.match.match_type and 'comp' in roster.match.match_type  else f'{roster.match.mode.upper()}<br><span class="badge badge-secondary">Not Ranked</span>',
						'raw_mode': f'{roster.match.mode.upper()}',
						'date_created': datetime.strftime(roster.match.created, '%d/%m/%Y %H:%M:%S'),
						'time_since': timesince(roster.match.created),
						'team_details': ''.join([f"{x.player_name}: {x.kills} kill(s) | {x.damage} damage<br>" for x in roster.participants.all()]),
						'team_details_object': [
							{
								'kills': x.kills,
								'player_name': x.player_name,
								'damage': x.damage
							} for x in roster.participants.all()
						],
						'team_placement': player_placement_format(roster.match.total_teams, roster.placement),
						'actions': f'<a href="/match_detail/{roster.match.api_id}/" class="btn btn-link btn-sm active" role="button">View Match</a>',
						'btn_link': f"/match_detail/{roster.match.api_id}/"
					} for roster in match_data
				],
				'api_id': current_player.api_id,
				'match_ids': match_ids
			}
			
			cache.set(player_match_data_cache, ajax_data, 60)

		else:

			message = "It would seem no TPP/FPP (SOLO, DUO, SQUAD) matches exist for this user for the last 14 days."

			ajax_data = {
				'error': message,
				'api_id': current_player.api_id
			}

		return Response(ajax_data)

@api_view(['GET', 'POST'])
def retrieve_season_stats(request):

	body = request.data

	player_id = body.get('player_id', None)
	ranked = body.get('ranked', None)

	if ranked == 'true':
		is_ranked = True
	else:
		is_ranked = False

	if is_ranked:
		season_stats_cache_key = api_settings.PLAYER_RANKED_SEASON_STATS_CACHE_KEY.format(player_id)
	else:
		season_stats_cache_key = api_settings.PLAYER_SEASON_STATS_CACHE_KEY.format(player_id)

	cached_ajax_data = cache.get(season_stats_cache_key, None)

	if cached_ajax_data:
		return Response(cached_ajax_data)

	platform = body.get('platform', None)

	player = get_object_or_404(Player, api_id=player_id)

	retrieve_player_season_stats(player_id,  platform, is_ranked)

	all_game_modes = list(set(PlayerSeasonStats.objects.filter(mode__icontains='squad').values_list('mode', flat=True)))

	season_stats_queryset = PlayerSeasonStats.objects.filter(
		player=player,
		season__is_current=True,
		season__platform=platform,
		is_ranked=is_ranked
	).select_related('season')

	modes_not_added = []

	if is_ranked:

		ajax_data = [
			{
				f"ranked_{x.mode.lower().replace('-', '_')}_season_stats": correct_mode(x.mode.replace('_', ' ')).upper(),
				f"ranked_{x.mode.lower().replace('-', '_')}_season_matches": "{} {}".format(x.rounds_played, 'Matches Played'),
				f"ranked_{x.mode.lower().replace('-', '_')}_season_kills__text": 'Kills',
				f"ranked_{x.mode.lower().replace('-', '_')}_season_kills__figure": x.kills,
				f"ranked_{x.mode.lower().replace('-', '_')}_season_damage__text": 'Damage Dealt',
				f"ranked_{x.mode.lower().replace('-', '_')}_season_damage__figure": str(x.damage_dealt),
				f"ranked_{x.mode.lower().replace('-', '_')}_season_longest_kill__text": 'Longest Kill',
				f"ranked_{x.mode.lower().replace('-', '_')}_season_longest_kill__figure": str(x.longest_kill),
				f"ranked_{x.mode.lower().replace('-', '_')}_season_headshots__text": 'Headshot kills',
				f"ranked_{x.mode.lower().replace('-', '_')}_season_headshots__figure": x.headshot_kills
			} for x in season_stats_queryset
		]

	else:

		ajax_data = [
			{
				f"{x.mode.lower().replace('-', '_')}_season_stats": correct_mode(x.mode.replace('_', ' ')).upper(),
				f"{x.mode.lower().replace('-', '_')}_season_matches": "{} {}".format(x.rounds_played, 'Matches Played'),
				f"{x.mode.lower().replace('-', '_')}_season_kills__text": 'Kills',
				f"{x.mode.lower().replace('-', '_')}_season_kills__figure": x.kills,
				f"{x.mode.lower().replace('-', '_')}_season_damage__text": 'Damage Dealt',
				f"{x.mode.lower().replace('-', '_')}_season_damage__figure": str(x.damage_dealt),
				f"{x.mode.lower().replace('-', '_')}_season_longest_kill__text": 'Longest Kill',
				f"{x.mode.lower().replace('-', '_')}_season_longest_kill__figure": str(x.longest_kill),
				f"{x.mode.lower().replace('-', '_')}_season_headshots__text": 'Headshot kills',
				f"{x.mode.lower().replace('-', '_')}_season_headshots__figure": x.headshot_kills
			} for x in season_stats_queryset
		]

	
	if len(ajax_data) < 6:
		modes_not_added = []
		for x in all_game_modes:
			for y in ajax_data:
				if is_ranked:
					dict_key = f"ranked_{x.lower().replace('-', '_')}_season_stats"
				else:
					dict_key = f"{x.lower().replace('-', '_')}_season_stats"
					
				if dict_key not in y:
					modes_not_added.append(x)

		if ranked:
			ajax_data += [
				{
					'container' :f"ranked_{x.lower().replace('-', '_')}_season_stats_container",
					'text': f"No ranked data available for {correct_mode(x.replace('_', ' ')).upper()}"
				} for x in modes_not_added
			]
		else:
			ajax_data += [
				{
					'container' :f"{x.lower().replace('-', '_')}_season_stats_container",
					'text':  f"No data available for {correct_mode(x.replace('_', ' ')).upper()}"
				} for x in modes_not_added
			]
			

	cache.set(season_stats_cache_key, ajax_data, 60*20)

	return Response(ajax_data)

@api_view(['GET'])
def get_match_rosters(request, match_id):

	match = get_object_or_404(Match, id=match_id)
	match_id = match.api_id
	account_id = match_id.split('_')[0]
	match_url = match.api_url

	if not match_url or match_id not in match_url:
		current_player = get_object_or_404(Player, api_id__iexact=account_id)
		match_id = match.api_id.split('_')[1]
		platform_url = current_player.platform_url
		match_url = build_match_url(platform_url, match_id)
	
	match_roster_cache = api_settings.MATCH_ROSTER_CACHE_KEY.format(match_id)
	rosters = cache.get(match_roster_cache, None)

	if rosters:
		return Response(rosters)

	match_json = make_request(match_url)

	telemetry = get_match_telemetry_from_match(
		match_json=match_json,
		match=match,
		return_early=True
	)

	rosters = create_leaderboard_for_match(
		match_json=telemetry,
		telemetry=None,
		save=False
	)

	cache.set(match_roster_cache, rosters, 60*60)

	return Response(rosters)

@api_view(['GET'])
def match_detail(request, match_id):

	match_detail_cache_key = api_settings.MATCH_DETAIL_CACHE_KEY.format(match_id)
	match_detail_response = cache.get(match_detail_cache_key, None)

	if match_detail_response:
		return 	Response(match_detail_response)

	matches = Match.objects.only('api_id')
	match_exists =  matches.filter(api_id__iexact=match_id)
	telemetry_objects = Telemetry.objects.filter(match__in=matches)

	split = match_id.split('_')
	account_id = split[0]
	match_id = split[1]

	if match_exists.exists():
		current_player = get_object_or_404(Player, api_id=account_id)
		player_name = Participant.objects.filter(player=current_player).latest('id').player_name

		match = match_exists.first()
		telemetry_exists = telemetry_objects.filter(match=match)

		if not telemetry_exists.exists():

			match_url = match.api_url

			if not match_url or match_id not in match_url:
				platform_url = current_player.platform_url
				match_url = build_match_url(platform_url, match_id)

			match_json = make_request(match_url)
			match_type = match_json['data']['attributes']['matchType']

			get_match_telemetry_from_match(
				match_json=match_json,
				match=match,
				return_early=False
			)

			telemetry = telemetry_objects.filter(match=match)
			telemetry = telemetry.first()
		else:
			telemetry = telemetry_exists.first()

		telemetry_events = TelemetryEvent.objects.filter(telemetry=telemetry)

		log_match_start = get_object_or_404(telemetry_events, event_type__iexact='LogMatchStart')
		total_match_kills = get_object_or_404(telemetry_events, event_type__iexact='LogTotalMatchKills')
		log_match_end = get_object_or_404(telemetry_events, event_type__iexact='LogMatchEnd')
		roster_telem = get_object_or_404(TelemetryRoster, telemetry=telemetry)
		roster_participant = RosterParticipant.objects.filter(roster__match=match, participant__player=current_player).first()

		log_match_start_timestamp = parse(log_match_start.timestamp)
		log_match_start_timestamp = str(log_match_start_timestamp)
		
		if '+' in log_match_start_timestamp:
			log_match_start_timestamp = str(log_match_start_timestamp).split('+')[0]

		log_match_start_timestamp = str(log_match_start_timestamp).split('.')[0]
		log_match_end_timestamp = parse(log_match_end.timestamp)

		log_match_end_timestamp = str(log_match_end_timestamp)
		
		if '+' in log_match_end_timestamp:
			log_match_end_timestamp = str(log_match_end_timestamp).split('+')[0]

		log_match_end_timestamp = str(log_match_end_timestamp).split('.')[0]

		FMT = '%Y-%m-%d %H:%M:%S'
		
		elapased_time = datetime.strptime(log_match_end_timestamp, FMT) - datetime.strptime(log_match_start_timestamp, FMT)

		heals_items_used = telemetry_events.filter(event_type__iexact='LogItemUseMed').count()
		boost_items_used = telemetry_events.filter(event_type__iexact='LogItemUseBoost').count()

		ai_events = telemetry_events.filter(event_type__iexact='AICount')
		player_events = telemetry_events.filter(event_type__iexact='PlayerCount')

		ais = False
		ai_count = 0
		player_count = 0
		ai_percentage = 0.00
		
		if ai_events.exists():
			ai_count = int(ai_events.first().description)
			ais = True

		if player_events.exists():
			player_count = int(player_events.first().description)

		total_count = ai_count + player_count
		ai_percentage = round((ai_count / total_count) * 100)
		player_percentage =  round((player_count / total_count) * 100)

		telemetry_excluding_some_events = telemetry_events.exclude(Q(event_type__iexact='LogTotalMatchKills') | Q(event_type__iexact='Roster') | Q(timestamp__isnull=True))

		match_map_url = match.map.image_url
		map_name = match.map.name

		telemetry_data = {
			'telemetry_data':{
				'match_data':{
					'match_id': match_id,
					'match_elapsed_time': f'{elapased_time} minutes',
					'match_map_name': map_name,
					'map_image': match_map_url,
					'time_since': timesince(match.created),
					'events': [
						{
							'timestamp': datetime.strftime(parse(x.timestamp), '%H:%M:%S'),
							'event': x.description,
							'killer_x_cord': x.killer_x_cord,
							'killer_y_cord': x.killer_y_cord,
							'victim_x_cord': x.victim_x_cord,
							'victim_y_cord': x.victim_y_cord
						} for x in telemetry_excluding_some_events
					],
					'player_breakdown':{
						'ais': ais,
						'ai_count': ai_count,
						'ai_percentage': ai_percentage,
						'player_count': player_count,
						'player_percentage': player_percentage,
						'total_count': total_count,
						'rosters': roster_telem.json,
					}
				},
				'player_data':{
					'player_kills': total_match_kills.description,
					'player_damage': roster_participant.participant.damage,
					'knocks': roster_participant.participant.knocks,
					'player_name': player_name,
					'boost_items_used': boost_items_used,
					'heals_items_used': heals_items_used,
				}
			}
		}

		cache.set(match_detail_cache_key, telemetry_data, 60*10)

		return Response(telemetry_data)