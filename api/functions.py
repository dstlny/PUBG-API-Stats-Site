import django
django.setup()

import sys


## my files
import api.settings as api_settings
from api.models import *

## external libs
import json as old_json
import orjson as json

import requests

## py libs
import time
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.shortcuts import _get_queryset
from django.utils.timezone import make_aware
from os import path
from dateutil.parser import parse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

from django.core.cache import cache

session = requests.Session()

import logging

logger = logging.getLogger('django')

def build_url(platform):
	if 'steam' in platform.strip().lower():
		return "{}{}".format(
			api_settings.BASE_API_URL,
			api_settings.PC_SHARD
		)
	elif 'xbox' in platform.strip().lower():
		return "{}{}".format(
			api_settings.BASE_API_URL,
			api_settings.XBOX_SHARD
		)
	elif "psn" in platform.strip().lower():
		return "{}{}".format(
			api_settings.BASE_API_URL,
			api_settings.PLAYSTATION_SHARD
		)
	elif "kakao" in platform.strip().lower():
		return "{}{}".format(
			api_settings.BASE_API_URL,
			api_settings.KAKAO_SHARD
		)
	elif "tour" in platform.strip().lower():
		return "{}{}".format(
			api_settings.BASE_API_URL,
			api_settings.TOURNAMENT_SHARD
		)

def get_platform(url):
	if 'steam' in url.strip().lower():
		return 'steam'
	elif 'xbox' in url.strip().lower():
		return 'xbox'
	elif "psn" in url.strip().lower():
		return 'psn'
	elif "kakao" in url.strip().lower():
		return 'kakao'
	elif "tour" in url.strip().lower():
		return 'tour'

def build_player_url(base_url, player_name):
	return "{}{}{}".format(
		base_url,
		api_settings.PLAYER_FILTER,
		player_name
	)

def build_player_account_id_url(base_url, player_id):
	return "{}{}".format(
		base_url,
		api_settings.PLAYER_ACCOUNT_FILTER
	).replace('$accountId', player_id)

def build_season_url(base_url, season_id, player_id):
	return "{}{}".format(
		base_url,
		api_settings.SEASON_FILTER,
	).replace('$accountId', player_id).replace('$seasonID', season_id) 

def build_lifetime_url(base_url, player_id):
	return "{}{}".format(
		base_url,
		api_settings.LIFETIME_FILTER
	).replace('$accountId', player_id)

def build_tournament_url(tournament_id):
	return "{}{}".format(
		api_settings.BASE_API_URL,
		api_settings.TOURNAMENTS_FILTER
	).replace('$tourneyID', tournament_id)

def build_match_url(base_url, platform):
	return "{}{}".format(
		base_url,
		api_settings.MATCH_FILTER
	).replace('$matchID', platform)

def correct_perspective(perspective):
	return perspective.lower() if perspective and 'all' not in perspective.lower() else None

def correct_mode(mode):
	return mode.lower() if mode and 'all' not in mode.lower() else None

def get_map_name(map_codename):
	return api_settings.MAP_BINDING.get(map_codename)

def make_request(url):

	if 'season' in url:
		time.sleep(6)

	try:
		response = json.loads(session.get(url, headers=api_settings.API_HEADER).content)
	except:
		time.sleep(2)
		logger.info(f'For some reason, requesting {url} failed with the following error: {sys.exc_info()[1]}.')
		make_request(url)
	
	return response

def parse_player_object(platform_url, player_response):

	if 'errors' not in player_response:

		match_queryset = Match.objects.only('api_id')
		player_queryset = Player.objects.only('api_id')

		if isinstance(player_response['data'], list):
			player_id = player_response['data'][0]['id']
		else:
			player_id = player_response['data']['id']

		if not player_queryset.filter(api_id__iexact=player_id).exists():
			player = Player(
				api_id=player_id,
				platform_url=platform_url,
				api_url=build_player_account_id_url(platform_url, player_id)
			)
			player.save()

		if isinstance(player_response['data'], list):
			matches = [
				make_request(build_match_url(platform_url, match['id'])) for match in player_response['data'][0]['relationships']['matches']['data']
				if not match_queryset.filter(api_id=get_player_match_id(player_id, match['id'])).exists()
			]
		else:
			matches = [
				make_request(build_match_url(platform_url, match['id'])) for match in player_response['data']['relationships']['matches']['data']
				if not match_queryset.filter(api_id=get_player_match_id(player_id, match['id'])).exists()
			]

		return player_id, matches
	else:

		return None, None

def get_player_match_id(player_id, match_id):
	return "{}_{}".format(player_id, match_id)  

def get_object_or_none(klass, *args, **kwargs):
	queryset = _get_queryset(klass)
	try:
		return queryset.get(*args, **kwargs)
	except queryset.model.DoesNotExist:
		logger.info(f'Tried to get {klass} object with kwargs {kwargs}, however returned None.')
		return None

def get_match_data(player_api_id, player_id, game_mode, perspective):

	kwargs = {}

	if game_mode and perspective:
		mode_fiter = "{}-{}".format(game_mode, perspective)
		kwargs['match__mode__iexact'] = mode_fiter
	elif game_mode:
		mode_fiter = game_mode
		kwargs['match__mode__icontains'] = mode_fiter
	elif perspective:
		mode_fiter = perspective
		kwargs['match__mode__icontains'] = mode_fiter
	else:
		all_game_modes = list(set(Match.objects.values_list('mode', flat=True).distinct()))
		kwargs['match__mode__in'] = all_game_modes

	fourteen_days_in_past = timezone.now() - timedelta(days=15)
	
	kwargs['participants__player_id'] = player_id
	kwargs['match__api_id__icontains'] = player_api_id
	kwargs['match__created__gte'] = fourteen_days_in_past

	roster_data = Roster.objects.filter(**kwargs)\
	.select_related('match')\
	.prefetch_related('participants')

	return roster_data

def chunk_matches(matches, chunk):
	return [matches[i:i + chunk] for i in range(0, len(matches), chunk)]

def parse_chunked_player_matches(chunk, player_id, platform_url):
	parse_player_matches(chunk, player_id, platform_url)
	platform = get_platform(platform_url)
	player_currently_processing_cache_key = '{}_{}_current_processing'.format(player_id, platform)
	cache.set(player_currently_processing_cache_key, False, 60)
	
def parse_player_matches(match_json_list, player_id, platform_url):

	map_queryset = Map.objects.only('reference')
	player_queryset = Player.objects.only('api_id')


	json_length = len(match_json_list)
	message = f'{json_length} matches to parse for {player_id}'
	logger.info(message)

	match_count = 0

	total_time_taken = 0

	for match in match_json_list:

		match_count += 1

		match_id = match['data']['id']

		try:

			start_time = time.time()

			match_date = datetime.strptime(match['data']['attributes']['createdAt'].replace('Z', ''), "%Y-%m-%dT%H:%M:%S")

			match_date = make_aware(match_date)

			match_map =  get_map_name(match['data']['attributes']['mapName'])
			match_map_reference = match['data']['attributes']['mapName']
			match_mode = correct_mode(match['data']['attributes']['gameMode'])
			match_custom = match['data']['attributes']['isCustomMatch']
			match_shard = match['data']['attributes']['shardId']
			match_type = match['data']['attributes']['matchType']

			match_url = match['data']['links']['self']
			match_url = match_url.replace('playbattlegrounds', 'pubg')

			match_map = map_queryset.filter(reference__iexact=match_map_reference)

			if not match_map.exists():
				match_map = Map(
					name=match_map,
					reference=match_map_reference
				)
				match_map.save()
				map_id = match_map.id
			else:
				map_id = match_map.first().id

			this_match = Match(
				api_id=get_player_match_id(player_id, match_id),
				created=match_date,
				map_id=map_id,
				mode=match_mode,
				api_url=match_url,
				is_custom_match=match_custom,
				match_type=match_type
			)
			this_match.save()

			current_player_parsed = [
				x for x in match['included']
				if x['type'] == 'participant'
				and 'attributes' in x
				and 'stats' in x['attributes']
				and x['attributes']['stats']['playerId'] == player_id
			]
			this_participant_api_id = current_player_parsed[0]['id']

			team_roster = [
				x for x in match['included']
				if x['type'] == 'roster'
				and 'relationships' in x
				and 'participants' in x['relationships']
				and any(
					z['id'] == this_participant_api_id for z in x['relationships']['participants']['data']
				)
			]
			roster_id = team_roster[0]['id']
			roster_placement = team_roster[0]['attributes']['stats']['rank']

			roster = Roster(
				placement=roster_placement,
				match_id=this_match.id,
				api_id=roster_id
			)
			roster.save()

			roster_id = roster.id

			roster_participant_ids = [
				x['id'] for x in team_roster[0]['relationships']['participants']['data']
			]

			roster_participants = [
				x for x in match['included']
				if x['type'] == 'participant'
				and x['id'] in roster_participant_ids
			]

			for participant in roster_participants:

				participant_api_id = participant['id']
				participant_kills = participant['attributes']['stats'].get('kills', None)
				participant_damage = participant['attributes']['stats'].get('damageDealt', None)
				participant_placement = participant['attributes']['stats'].get('winPlace', None)
				participant_name = participant['attributes']['stats'].get('name', None)
				participant_player_api_id =  participant['attributes']['stats'].get('playerId', None)
				knocks = participant['attributes']['stats'].get('DBNOs', None)
				ride_distance = participant['attributes']['stats'].get('rideDistance', None)
				swim_distance = participant['attributes']['stats'].get('swimDistance', None)
				walk_distance = participant['attributes']['stats'].get('walkDistance', None)

				if 'ai' in participant_player_api_id:
					participant_is_ai = True
				else:
					participant_is_ai = False

				this_player = player_queryset.filter(api_id=participant_player_api_id)

				if not this_player.exists():
					participant_player_object = Player(
						api_id=participant_player_api_id,
						platform_url=platform_url,
						api_url=build_player_account_id_url(platform_url, player_id)
					)
					participant_player_object.save()
				else:
					participant_player_object = this_player.first()

				participant_player_object_id = participant_player_object.id

				participant_object = Participant(
					api_id=participant_api_id,
					kills=participant_kills,
					player_name=participant_name,
					placement=participant_placement,
					damage=participant_damage,
					player_id=participant_player_object_id,
					is_ai=participant_is_ai,
					knocks=knocks,
					ride_distance=ride_distance,
					swim_distance=swim_distance,
					walk_distance=walk_distance,
				)
				participant_object.save()

				particpant_id = participant_object.id
				
				roster_participant = RosterParticipant(
					roster_id=roster_id,
					participant_id=particpant_id
				)
				roster_participant.save()
			
			seconds_taken = "{:0.4f}".format(time.time() - start_time)
			total_time_taken += time.time() - start_time
			message =  f"[{match_count}/{json_length}] ({match_id}) took {seconds_taken}(s)"
			logger.info(message)

		except:
			logger.info(f'Threw the following error when trying to parse a match ({match_id}). {sys.exc_info()[1]}')

	total_time_taken = "{:0.4f}".format(total_time_taken)
	message =  f"Took a total of {total_time_taken}(s)"
	logger.info(message)

def get_player_matches(platform_url, player_response):
	player_id, player_matches = parse_player_object(platform_url, player_response)
	parse_player_matches(player_matches, player_id, platform_url)
	platform = get_platform(platform_url)
	player_currently_processing_cache_key = '{}_{}_current_processing'.format(player_id, platform)
	cache.set(player_currently_processing_cache_key, False, 60)

def populate_seasons():
	platforms = [
		'steam',
		'xbox',
		'psn'
	]

	for platform in platforms:
		url = build_url(platform)
		url = "{}{}".format(url, 'seasons')
		request = make_request(url)

		for season in request.get('data'):
			api_id = season.get('id')
			attributes = season.get('attributes')
			is_current_season = attributes.get('isCurrentSeason')
			is_off_season = attributes.get('isOffseason')

			Season.objects.get_or_create(
				api_id=api_id,
				is_current=is_current_season,
				is_off_season=is_off_season,
				api_url=url,
				platform=platform
			)

def retrieve_player_season_stats(player_id, platform, ranked=None):

	platform_url = build_url(platform)

	current_season = get_object_or_none(Season, is_current=True, platform=platform.lower())
	current_player = get_object_or_404(Player, api_id=player_id, platform_url=platform_url)

	player_season_stats_queryset = PlayerSeasonStats.objects.only('player', 'season', 'mode')

	if current_season:
		season_url = build_season_url(
			base_url=platform_url,
			season_id=current_season.api_id,
			player_id=player_id
		)

		season_request = make_request(season_url)

		player_id = current_player.id
		season_id = current_season.id

		if season_request:
			attributes = season_request.get('data').get('attributes')
			game_mode_stats = attributes.get('gameModeStats')

			## we should really only save the details that we do not have
			game_modes = [
				game_mode for game_mode in game_mode_stats if not(player_season_stats_queryset.filter(
					player=current_player,
					season=current_season,
					mode=game_mode
				).exists())
			]

			for game_mode in game_modes:
				stats =  game_mode_stats.get(game_mode)
				assists = stats.get('assists', None)
				boosts = stats.get('boosts', None)
				dBNOs = stats.get('dBNOs', None)
				dailyKills = stats.get('dailyKills', None)
				dailyWins = stats.get('dailyWins', None)
				damageDealt = stats.get('damageDealt', None)
				days = stats.get('days', None)
				headshotKills = stats.get('headshotKills', None)
				heals = stats.get('heals', None)
				killPoints = stats.get('killPoints', None)
				kills = stats.get('kills', None)
				longestKill = stats.get('longestKill', None)
				longestTimeSurvived = stats.get('longestTimeSurvived', None)
				losses = stats.get('losses', None)
				maxKillStreaks = stats.get('maxKillStreaks', None)
				mostSurvivalTime = stats.get('mostSurvivalTime', None)
				rankPoints = stats.get('rankPoints', None)
				rankPointsTitle = stats.get('rankPointsTitle', None)
				revives = stats.get('revives', None)
				rideDistance = stats.get('rideDistance', None)
				roadKills = stats.get('roadKills', None)
				roundMostKills = stats.get('roundMostKills', None)
				roundsPlayed = stats.get('roundsPlayed', None)
				suicides = stats.get('suicides', None)
				swimDistance = stats.get('swimDistance', None)
				teamKills = stats.get('teamKills', None)
				timeSurvived = stats.get('timeSurvived', None)
				top10s = stats.get('top10s', None)
				vehicleDestroys = stats.get('vehicleDestroys', None)
				walkDistance = stats.get('walkDistance', None)
				weaponsAcquired = stats.get('weaponsAcquired', None)
				weeklyKills = stats.get('weeklyKills', None)
				weeklyWins = stats.get('weeklyWins', None)
				winPoints = stats.get('winPoints', None)
				wins = stats.get('wins', None)

				PlayerSeasonStats(
					mode=game_mode,
					assists=assists,
					boosts=boosts,
					knocks=dBNOs,
					daily_kills=dailyKills,
					damage_dealt=damageDealt,
					days=days,
					daily_wins=dailyWins,
					headshot_kills=headshotKills,
					heals=heals,
					kill_points=killPoints,
					kills=kills,
					longest_kill=longestKill,
					longest_time_survived=longestTimeSurvived,
					losses=losses,
					max_kill_streaks=maxKillStreaks,
					most_survival_time=mostSurvivalTime,
					rank_points=rankPoints,
					rank_points_title=rankPointsTitle,
					revives=revives,
					ride_distance=rideDistance,
					road_kills=roadKills,
					round_most_kills=roundMostKills,
					rounds_played=roundsPlayed,
					suicides=suicides,
					swim_distance=swimDistance,
					team_kills=teamKills,
					time_survived=timeSurvived,
					top_10s=top10s,
					vehicle_destroys=vehicleDestroys,
					walk_distance=walkDistance,
					weapons_acquired=weaponsAcquired,
					weekly_kills=weeklyKills,
					weekly_wins=weeklyWins,
					win_points=winPoints,
					wins=wins,
					player_id=player_id,
					season_id=season_id
				).save()

def get_match_telemetry_from_match(match_json, match, return_early=False):

	assets = [
		x for x in match_json['included']
		if x['type'] == 'asset'
	]

	for asset in assets:
		asset_id = asset.get('id', None)
		asset_attributes = asset.get('attributes', None)
		if asset_attributes:
			url = asset_attributes.get('URL', None)
			date_created = asset_attributes.get('createdAt', None)
			date_created = datetime.strptime(date_created.replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
			date_created = make_aware(date_created)
			if url:
				telemetry_data = make_request(url)

				if return_early:
					return telemetry_data
				else:
					parse_match_telemetry(
						url=url,
						asset_id=asset_id,
						telemetry_data=telemetry_data,
						match=match,
						date_created=date_created,
						account_id=match.api_id.split('_')[0],
					)

def create_leaderboard_for_match(match_json, telemetry, save=True):

	game_results_on_finished = [
		x for x in match_json
		if x['_T'] == 'LogMatchEnd'
	]

	telemetry_events = []

	game_results_on_finished_results = [
		x['gameResultOnFinished']['results'] for x in game_results_on_finished	
	][0]

	characters = [
		x['characters'] for x in game_results_on_finished	
	][0]

	victim_game_results = [
		x['victimGameResult'] for x in match_json
		if x['_T'] == 'LogPlayerKill'
	]

	log_player_take_damage_events = [
		x for x in match_json
		if x['_T'] == 'LogPlayerTakeDamage'
	]

	for x in game_results_on_finished_results:
		victim_game_results.append(x)
	
	teams = {}
	players = {}

	team_ids = []

	## build a list of rosters and their team members
	ais = 0
	non_ais = 0

	for character_entry in characters:

		character = character_entry.get('character')

		if character:

			team_id = character.get('teamId')
			team_ranking = character.get('ranking')
			player_name = character.get('name')
			player_acount_id = character.get('accountId')

			if 'ai' in player_acount_id:
				ais += 1
				is_ai = True
			else:
				non_ais += 1
				is_ai = False

			if team_id not in teams:

				team_ids.append(team_id)

				teams[team_id] = {
					'team_id': team_id,
					'roster_rank': team_ranking,
					'participant_objects':[
						{
							'player_name': player_name,
							'player_account_id': player_acount_id,
							'player_kills': 0,
							'damage_dealt': 0,
							'is_ai': is_ai
						}
					]
				}

			else:

				participant_details = {
					'player_name': player_name,
					'player_account_id': player_acount_id,
					'player_kills': 0,
					'damage_dealt': 0,
					'is_ai': is_ai
				}

				teams[team_id]['participant_objects'].append(participant_details)

	## this has kills for the team who are first place 
	for victim_game_result in victim_game_results:
		team_id = victim_game_result['teamId']
		kills = victim_game_result['stats']['killCount']
		account_id = victim_game_result['accountId']

		for participant in teams[team_id]['participant_objects']:

			if participant['player_account_id'] == account_id:
				if 'ai' in account_id:
					participant['is_ai'] = True
				else:
					participant['is_ai'] = False
					
				participant['player_kills'] = kills

	for log_player_take_damage_event in log_player_take_damage_events:
		attacker = log_player_take_damage_event['attacker']

		if attacker:
			team_id = attacker['teamId']
			account_id = attacker['accountId']
			damage_dealt = log_player_take_damage_event['damage']

			for participant in teams[team_id]['participant_objects']:
				if participant['player_account_id'] == account_id:
					participant['damage_dealt'] += damage_dealt

	rosters = []

	for team_id in team_ids:
		team = teams[team_id]
		participant_objects = ''

		for x in team['participant_objects']:
			if not x['is_ai']:
				participant_objects += f"<i class=\"fas fa-user\"></i> {x['player_name']}: {x['player_kills']} kill(s) | {round(x['damage_dealt'], 2)} damage<br>"
			else:
				participant_objects += f"<i class=\"fas fa-robot\"></i> {x['player_name']}: {x['player_kills']} kill(s) | {round(x['damage_dealt'], 2)} damage<br>"

		team['participant_objects'] = participant_objects
		rosters.append(team)

	if save:

		TelemetryRoster(
			json=rosters,
			telemetry=telemetry
		).save()
		
		telemetry_events.append(
			TelemetryEvent(
				event_type='AICount',
				telemetry=telemetry,
				description=ais,
				timestamp=None,
				player=None,
				x_cord=None,
				y_cord=None
			)
		)
		telemetry_events.append(
			TelemetryEvent(
				event_type='PlayerCount',
				telemetry=telemetry,
				description=non_ais,
				timestamp=None,
				player=None,
				x_cord=None,
				y_cord=None
			)
		)
		TelemetryEvent.objects.bulk_create(telemetry_events)

	else:
		return rosters

def parse_match_telemetry(url, asset_id, telemetry_data, date_created, match, account_id):

	match_id = match.id

	telemetry_check = Telemetry.objects.filter(match_id=match_id, api_id=asset_id)
	this_player = get_object_or_404(Player, api_id=account_id)
	player_name = Participant.objects.filter(player=this_player).latest('id').player_name
	kill_causes = ItemTypeLookup.objects.only('name', 'reference')

	telemetry_events = []

	save = True

	player_id = this_player.id

	append = telemetry_events.append

	if not telemetry_check.exists():

		match_kills = 0
		dead = False
		won_match = False

		match_telemet = Telemetry(
			api_id=asset_id,
			api_url=url,
			created_at=date_created,
			match_id=match_id
		)

		if save:
	 		match_telemet.save()
		
		create_leaderboard_for_match(
			match_json=telemetry_data,
			telemetry=match_telemet
		)

		telem_id = match_telemet.id

		heal_item_ids = [
			'Item_Boost_PainKiller_C',
			'Item_Heal_FirstAid_C',
			'Item_Boost_EnergyDrink_C',
			'Item_Heal_Bandage_C',
			'Item_Heal_MedKit_C'
		]

		telem_to_capture = [
			'LogItemUse',
			'LogPlayerKill',
			'LogMatchEnd',
			'LogMatchStart',
		]

		log_player_events = [
			x for x in telemetry_data
			if x['_T'] in telem_to_capture
			and (
					( 
						'killer' in x
						and x['killer']
						and 'accountId' in x['killer']
						and x['killer']['accountId'] == account_id
					)
				or
					(
						'victim' in x
						and x['victim']
						and 'accountId' in x['victim']
						and x['victim']['accountId'] == account_id
					)
				or
					(
						'item' in x
						and x['item']['itemId'] in heal_item_ids
						and 'character' in x
						and x['character']['accountId'] == account_id
					)
				or not (
						( 
							'killer' in x
						)
					or
						(
							'victim' in x
						)
					or
						(
							'item' in x
						)
				)
			)
		]

		del telemetry_data

		if 'ai' in account_id:
			is_player_ai = True
		else:
			is_player_ai = False

		ais = 0

		for log_event in log_player_events:
			
			event_type = log_event['_T']
			event_timestamp = log_event['_D']

			if event_timestamp:
				event_timestamp = parse(event_timestamp)
				
			if event_type == 'LogPlayerKill':

				victim_name = log_event['victim']['name']
				victim_id = log_event['victim']['accountId']

				if victim_id == account_id:
					dead = True

				if 'ai' in victim_id:
					is_victim_ai = True
				else:
					is_victim_ai = False

				killer = log_event.get('killer')

				if killer:

					killer_name = log_event['killer']['name']
					killer_id = log_event['killer']['accountId']
					killer_x = log_event['killer']['location']['x']
					killer_y = log_event['killer']['location']['y']

					victim_x = None
					victim_y = None
					
					if killer_id == account_id:
						match_kills += 1
						dead = False

					if 'ai' in killer_id:
						is_killer_ai = True
					else:
						is_killer_ai = False

				else:

					victim_x = log_event['victim']['location']['x']
					victim_y = log_event['victim']['location']['y']
					killer_x = victim_x
					killer_y = victim_y

					damage_type = log_event.get('damageTypeCategory')

					if damage_type:
						killer_name = log_event['damageTypeCategory']

				kill_location = log_event['damageReason']
				
				if kill_location not in ['None', 'NonSpecific']:
					kill_location = kill_location.title()
				else:
					kill_location = None

				kill_cause = log_event['damageCauserName']
				kill_cause = kill_causes.filter(reference=kill_cause)
				kill_cause = kill_cause.first()
				kill_cause = kill_cause.name

				if kill_cause in ['Redzone', 'Bluezone']:
					if is_victim_ai:
						event_description = f'<i class="fas fa-robot"></i> <b>{victim_name}</b> died inside the <b>{kill_cause}</b>'
					else:
						event_description = f'<i class="fas fa-user"></i> <b>{victim_name}</b> died inside the <b>{kill_cause}</b>'
				else:
					if is_killer_ai:
						if is_victim_ai:
							event_description = f'<i class="fas fa-robot"></i> <b>{killer_name}</b> killed <i class="fas fa-robot"></i><b>{victim_name}</b> with a <b>{kill_cause}</b>'
						else:
							event_description = f'<i class="fas fa-robot"></i> <b>{killer_name}</b> killed <i class="fas fa-user"></i> <b>{victim_name}</b> with a <b>{kill_cause}</b>'
					else:
						if is_victim_ai:
							event_description = f'<i class="fas fa-user"></i> <b>{killer_name}</b> killed <i class="fas fa-robot"></i><b>{victim_name}</b> with a <b>{kill_cause}</b>'
						else:
							event_description = f'<i class="fas fa-user"></i> <b>{killer_name}</b> killed <i class="fas fa-user"></i> <b>{victim_name}</b> with a <b>{kill_cause}</b>'

				append(TelemetryEvent(
					event_type=event_type,
					timestamp=event_timestamp,
					description=event_description,
					telemetry_id=telem_id,
					player_id=player_id,
					x_cord=killer_x,
					y_cord=killer_y
				))
				
				if match_kills:
					
					if dead:
						if is_player_ai:
							event_description = f'<i class="fas fa-robot"></i> <b>{player_name}</b> died with <b>{match_kills} kill(s)</b>'
						else:
							event_description = f'<i class="fas fa-user"></i> <b>{player_name}</b> died with <b>{match_kills} kill(s)</b>'
					else:
						if is_player_ai:
							event_description = f'<i class="fas fa-robot"></i> <b>{player_name}</b> now has <b>{match_kills} kill(s)</b>'
						else:
							event_description = f'<i class="fas fa-user"></i> <b>{player_name}</b> now has <b>{match_kills} kill(s)</b>'

					append(TelemetryEvent(
						event_type=event_type,
						timestamp=event_timestamp,
						description=event_description,
						telemetry_id=telem_id,
						player_id=player_id
					))

			if event_type == 'LogItemUse':

				item_id = log_event['item']['itemId']
				item_used = kill_causes.filter(reference=item_id)
				item_used = item_used.first()
				item_used = item_used.name

				if is_player_ai:
					event_description = f'<i class="fas fa-robot"></i> <b>{player_name}</b> used a <b>{item_used}</b>'
				else:
					event_description = f'<i class="fas fa-user"></i> <b>{player_name}</b> used a <b>{item_used}</b>'

				if item_id in ['Item_Boost_PainKiller_C', 'Item_Boost_EnergyDrink_C']:
					event_type = 'LogItemUseBoost'
				else:
					event_type = 'LogItemUseMed'

				append(TelemetryEvent(
					event_type=event_type,
					timestamp=event_timestamp,
					description=event_description,
					telemetry_id=telem_id,
					player_id=player_id
				))

			if event_type == 'LogMatchEnd':

				game_results = log_event['gameResultOnFinished']

				if game_results:

					won_match = any(
						x['accountId'] == account_id
						for x in game_results['results']
					)

				if won_match:
					event_description = f'<b>Winner Winner Chicken Dinner!</b>'
				else:
					if is_player_ai:
						event_description = f'<i class="fas fa-robot"></i> <b>{player_name}</b> did not win this match. Better luck next time!'
					else:
						event_description = f'<i class="fas fa-user"></i> <b>{player_name}</b> did not win this match. Better luck next time!'

				append(TelemetryEvent(
					event_type=event_type,
					timestamp=event_timestamp,
					description=event_description,
					telemetry_id=telem_id,
					player_id=player_id
				))

			if event_type == 'LogMatchStart':

				event_description = 'Match started'

				append(TelemetryEvent(
					event_type=event_type,
					timestamp=event_timestamp,
					description=event_description,
					telemetry_id=telem_id,
					player_id=player_id
				))

		event_description = match_kills
		event_type = 'LogTotalMatchKills'

		append(TelemetryEvent(
			event_type=event_type,
			timestamp=event_timestamp,
			description=event_description,
			telemetry_id=telem_id,
			player_id=player_id
		))

		TelemetryEvent.objects.bulk_create(telemetry_events)