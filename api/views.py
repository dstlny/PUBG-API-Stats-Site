from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpRequest

import collections

from api.settings import API_HEADER
from api.functions import (
	build_url, build_lifetime_url, make_request, correct_perspective, correct_mode,
	build_player_url, get_player_matches, retrieve_player_season_stats, populate_seasons, build_player_account_id_url,
	make_request, build_match_url, get_match_telemetry_from_match, get_match_data, create_leaderboard_for_match, get_player_match_id,
	chunk_matches, parse_player_matches, parse_chunked_player_matches
)

from api.models import *

import time
from datetime import datetime
from datetime import timedelta
from django.utils import timezone

## try import orjson, fallback to normal json module upon failure
try:
	import orjson as json
except:
	import json

from django.core.cache import cache
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.request import Request
from django.shortcuts import redirect
from dateutil.parser import parse
import ast
from django.db.models import Q

import multiprocessing

from django.utils.timesince import timesince

import threading
import logging

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

	perspective = body.get('perspective', None)
	game_mode = body.get('game_mode', None)
	platform = body.get('platform', None)

	player_platform_url_cache_key = '{}_{}_platform_url'.format(player_name, platform)
	player_player_url_cache_key = '{}_{}_player_url'.format(player_name, platform)
	player_player_response_cache_key = '{}_{}_player_response'.format(player_name, platform)

	cached_platform_url = cache.get(player_platform_url_cache_key, None)

	if not cached_platform_url:
		platform_url = build_url(platform)
		cache.set(player_platform_url_cache_key, platform_url, 60)
	else:
		platform_url = cached_platform_url

	cached_player_url = cache.get(player_player_url_cache_key, None)

	if not cached_player_url:
		player_url = build_player_url(base_url=platform_url, player_name=player_name)
		cache.set(player_player_url_cache_key, player_url, 60)
	else:
		player_url = cached_player_url

	cached_player_response = cache.get(player_player_response_cache_key, None)

	if not cached_player_response or 'data' not in cached_player_response:
		player_response = make_request(player_url)

		if 'data' not in player_response:
			potential_current_player = Participant.objects.filter(player_name=player_name)
			if potential_current_player.exists():
				potential_current_player = potential_current_player.first()
				player_url = potential_current_player.player.api_url
				player_response = make_request(player_url)
				
		cache.set(player_player_response_cache_key, player_response, 120)
	else:
		player_response = cached_player_response

	ajax_data = {}

	player_data_length = 0

	if 'data' in player_response:

		api_ids = list(set(Match.objects.values_list('api_id', flat=True).distinct()))

		if isinstance(player_response['data'], list):
			player_id = player_response['data'][0]['id']
			player_data_length = (len(player_response['data'][0]['relationships']['matches']['data']), [match['id'] for match in player_response['data'][0]['relationships']['matches']['data'] if get_player_match_id(player_id, match['id']) not in api_ids]) 
		else:
			player_id = player_response['data']['id']
			player_data_length = (len(player_response['data']['relationships']['matches']['data']), [match['id'] for match in player_response['data']['relationships']['matches']['data'] if get_player_match_id(player_id, match['id']) not in api_ids]) 

		if player_data_length[0] > 0:

			ajax_data['player_id'] = player_id
			ajax_data['player_name']  = player_name

			length_of_matches = len(player_data_length[1])

			if length_of_matches > 0:

				player_currently_processing_cache_key = '{}_{}_current_processing'.format(player_id, platform)
				currently_processing = cache.get(player_currently_processing_cache_key, None)

				if not currently_processing:
					cache.set(player_currently_processing_cache_key, True, 60)
					ajax_data['currently_processing'] = True
					thread = threading.Thread(target=get_player_matches,  kwargs={
						'platform_url': platform_url,
						'player_response': player_response
					})
					thread.daemon = True
					thread.start()
				else:
					ajax_data['currently_processing'] = False

			else:
				message = "No new matches to process for this user."
				ajax_data['message'] = message
				ajax_data['no_new_matches'] = True

		else:
			error = "Sorry, looks like this player has not played any matches in the last 14 days."
			ajax_data['error'] = error

	else:
		error = "Sorry, looks like this player does not exist."
		ajax_data['error'] = error

	return Response(ajax_data)

@api_view(['POST'])
def retrieve_matches(request):

	request_again = False
	redo_cache = False

	body = request.data
	
	player_id = body.get('player_id', None)
	perspective = body.get('perspective', None)
	game_mode = body.get('game_mode', None)
	times_requested = body.get('times_requested', None)
	seen_match_ids = body.get('seen_match_ids', None)

	player_cache_key = '{}_match_data'.format(player_id)

	if times_requested:
		times_requested = int(times_requested)

	ajax_data = {}

	cached_ajax_data = cache.get(player_cache_key, None)

	current_player = Player.objects.filter(api_id=player_id).first()

	if cached_ajax_data:

		cached_perspective = cached_ajax_data.get('perspective', None)
		cached_game_mode = cached_ajax_data.get('game_mode', None)
		cached_data = cached_ajax_data.get('data', None)
		cached_match_ids = cached_ajax_data.get('match_ids', None)

		game_mode = correct_mode(game_mode)
		perspective = correct_perspective(perspective)

		if cached_perspective and correct_perspective(cached_perspective) != perspective:
			cached_perspective = perspective
			request_again = True

		if cached_game_mode and correct_mode(cached_game_mode) != game_mode:
			cached_game_mode = game_mode
			request_again = True

		match_data = get_match_data(player_id, current_player.id, cached_game_mode, cached_perspective)

		match_ids = list(set(match_data.values_list('match_id', flat=True)))

		## this is the first time this user has requested, but the data is cached
		if times_requested == 0:
			## thus, server the match_ids
			cached_match_ids = match_ids
			include = True
		else:
			## this means they've requeted more than one time
			difference = len(cached_match_ids) > 0 and cached_match_ids != match_ids

			if difference:
				include = True
				## find the difference
				cached_match_ids = list(set(cached_match_ids) - set(match_ids))
			else:
				include = False

		if cached_match_ids:
			if include:
				match_data = match_data.filter(match_id__in=cached_match_ids)
			else:
				match_data = match_data.exclude(match_id__in=cached_match_ids)

		if seen_match_ids:
			cached_match_ids = list(set(cached_match_ids) - set(seen_match_ids))
			include = False

		if len(cached_data) < match_data.count():
			request_again = True
		else:
			request_again = False

		if cached_game_mode and cached_perspective:
			mode_fiter = "{}-{}".format(cached_game_mode, cached_perspective)
			match_data.filter(match__mode__iexact=mode_fiter)
		elif cached_game_mode:
			match_data.filter(match__mode__icontains=cached_game_mode)
		elif cached_perspective:
			match_data.filter(match__mode__icontains=cached_perspective)

		if request_again:

			cached_match_ids = cached_match_ids + list(set(match_data.values_list('match_id', flat=True)))
			cached_match_ids = list(set(cached_match_ids))

			new_ajax_data = cached_ajax_data

			data = [
				{
					'id': roster.match.id,
					'map': roster.match.map.name if roster.match.map else None,
					'mode': roster.match.mode.upper(),
					'custom_match': roster.match.match_type.title() if roster.match.match_type else 'Normal',
					'date_created': datetime.strftime(roster.match.created, '%d/%m/%Y %H:%M:%S'),
					'team_details': ''.join([f"{x.player_name}: {x.kills} kill(s) | {x.damage} damage<br>" for x in roster.participants.all()]),
					'team_placement': roster.placement,
					'actions': f'<a href="/match_detail/{roster.match.api_id}/" class="btn btn-link btn-sm active" role="button">View Match</a>'
				} for roster in match_data
			]

			new_ajax_data['data'] = data
			new_ajax_data['match_ids'] = cached_match_ids

			cache.set(player_cache_key, new_ajax_data, 60)

			if request_again and new_ajax_data:
				return Response(new_ajax_data)

		else:
			return Response(cached_ajax_data)

	else:
		request_again = True

	if request_again:
		redo_cache = True

	if request_again:

		if player_id and perspective and game_mode:

			game_mode = correct_mode(game_mode)
			perspective = correct_perspective(perspective)

			match_data = get_match_data(player_id, current_player.id, game_mode, perspective)

			if match_data.exists():
				
				match_ids = match_data.values_list('match_id', flat=True).distinct()

				ajax_data = {
					'perspective': perspective,
					'game_mode': game_mode,
					'data':[
						{	
							'id': roster.match.id,
							'map': roster.match.map.name if roster.match.map else None,
							'mode': roster.match.mode.upper(),
							'custom_match': roster.match.match_type.title() if roster.match.match_type else 'Normal',
							'date_created': datetime.strftime(roster.match.created, '%d/%m/%Y %H:%M:%S'),
							'team_details': ''.join([f"{x.player_name}: {x.kills} kill(s) | {x.damage} damage<br>" for x in roster.participants.all()]),
							'team_placement': roster.placement,
							'actions': f'<a href="/match_detail/{roster.match.api_id}/" class="btn btn-link btn-sm active" role="button">View Match</a>'
						} for roster in match_data
					],
					'api_id': current_player.api_id,
					'match_ids': match_ids
				}

				if cache.has_key(player_cache_key) and redo_cache:
					cache.delete(player_cache_key)

				if redo_cache:
					cache.set(player_cache_key, ajax_data, 60)

			else:

				if game_mode and perspective:
					message = "It would seem no {} {} matches exist for this user for the last 14 days.".format(game_mode.upper(), perspective)
				elif game_mode:
					message = "It would seem no TPP/FPP {} matches exist for this user for the last 14 days.".format(game_mode.upper())
				elif perspective:
					message = "It would seem no {} (SOLO, DUO, SQUAD) matches exist for this user for the last 14 days.".format(perspective.upper())
				else:
					message = "It would seem no TPP/FPP (SOLO, DUO, SQUAD) matches exist for this user for the last 14 days."

				ajax_data = {
					'error': message,
					'api_id': current_player.api_id
				}

	else:

		ajax_data = cached_ajax_data
		
	return Response(ajax_data)

@api_view(['GET', 'POST'])
def retrieve_season_stats(request):

	body = request.data

	player_id = body.get('player_id', None)

	platform = body.get('platform', None)

	player = get_object_or_404(Player, api_id=player_id)

	player_cache_key = '{}_season_data'.format(player_id)
	cached_ajax_data = cache.get(player_cache_key, None)

	if not cached_ajax_data:
		retrieve_player_season_stats(player_id,  platform)

		season_stats_queryset = PlayerSeasonStats.objects.only(
			'player',
			'season',
			'mode'
		).select_related('season')

		season_stats = season_stats_queryset.filter(
			player=player,
			season__is_current=True,
			season__platform=platform,
		)

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
			} for x in season_stats
		]

		cache.set(player_cache_key, ajax_data, 60*20)

	else:
		ajax_data = cached_ajax_data

	return Response(ajax_data)

@api_view(['GET'])
def get_match_rosters(request, match_id):

	match = get_object_or_404(Match, id=match_id)
	match_id = match.api_id
	account_id = match_id.split('_')[0]
	match_url = match.api_url

	if not match_url or match_id not in match_url:
		current_player = get_object_or_404(Player, api_id__iexact=account_id)
		match_id = match_id = match.api_id.split('_')[1]
		platform_url = current_player.platform_url
		match_url = build_match_url(platform_url, match_id)
	
	match_json = make_request(match_url)

	match_roster_cache = f'{match_id}_roster'

	rosters = cache.get(match_roster_cache, None)

	if not rosters:

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
							'x_cord': x.x_cord,
							'y_cord': x.y_cord
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
		
		return Response(telemetry_data)