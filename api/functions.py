import django
django.setup()


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

session = requests.Session()

class RangeDict(dict):
	''' 
	  An implementation of dict which allows you to use range as a key  
	'''

	def __getitem__(self, item):
		if type(item) != range:
			return ''.join([self[key] for key in self if item in key])
		else:
			return super().__getitem__(item)

def get_season_rank(rank):

	rank = range(rank)

	return RangeDict({
		range(-20, 1): 'Unranked',
		range(1, 200): 'Beginner V', 
		range(200, 400): 'Beginner IV', 
		range(400, 600): 'Beginner III',
		range(600, 800): 'Beginner II', 
		range(800, 1000): 'Beginner I',
		range(1000, 1200): 'Novice V',
		range(1200, 1400): 'Novice IV',
		range(1400, 1600): 'Novice III',
		range(1600, 1800): 'Novice II', 
		range(1800, 2000): 'Novice I', 
		range(2000, 2200): 'Experienced V', 
		range(2200, 2400): 'Experienced IV', 
		range(2400, 2600): 'Experienced III', 
		range(2600, 2800): 'Experienced II', 
		range(2800, 3000): 'Experienced I', 
		range(3000, 3200): 'Skilled V', 
		range(3200, 3400): 'Skilled IV', 
		range(3400, 3600): 'Skilled III', 
		range(3600, 3800): 'Skilled II', 
		range(3800, 4000): 'Skilled I', 
		range(4000, 4200): 'Specialist V', 
		range(4200, 4400): 'Specialist IV', 
		range(4400, 4600): 'Specialist III', 
		range(4600, 4800): 'Specialist II', 
		range(4800, 5000): 'Specialist I', 
		range(5000, 6000): 'Expert',
		range(6000, 9999): 'Survivor'
	}).get(rank)

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
	return perspective.lower() if 'all' not in perspective.lower() else None

def correct_mode(mode):
	return mode.lower() if 'all' not in mode.lower() else None

def get_map_name(map_codename):
	return api_settings.MAP_BINDING.get(map_codename)

def make_request(url):

	if 'season' in url:
		time.sleep(6)

	return json.loads(session.get(url, headers=api_settings.API_HEADER).content)

def parse_player_object(platform_url, player_response):

	if 'errors' not in player_response:

		match_queryset = Match.objects.only('api_id')
		player_queryset = Player.objects.only('api_id')

		player_id = player_response['data'][0]['id']
		player = player_queryset.filter(api_id=player_id)

		if not player.exists():
			player = Player(
				api_id=player_id,
				platform_url=platform_url,
				api_url=build_player_account_id_url(platform_url, player_id)
			)
			player.save()

		matches = [
			make_request(build_match_url(platform_url, match['id'])) for match in player_response['data'][0]['relationships']['matches']['data']
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
		return None

def parse_player_matches(match_json_list, player_id):

	match_queryset = Map.objects.only('reference')
	player_queryset = Player.objects.only('api_id')

	for match in match_json_list:

		if 'data' in match and 'attributes' in match['data']:

			start_time = time.time()

			match_id = match['data']['id']
			match_date = datetime.strptime(match['data']['attributes']['createdAt'].replace('Z', ''), "%Y-%m-%dT%H:%M:%S")

			match_date = make_aware(match_date)

			match_map =  get_map_name(match['data']['attributes']['mapName'])
			match_map_reference = match['data']['attributes']['mapName']
			match_mode = correct_mode(match['data']['attributes']['gameMode'])
			match_custom = match['data']['attributes']['isCustomMatch']
			match_shard = match['data']['attributes']['shardId']
			platform_url = build_url(match_shard)

			match_url = match['data']['links']['self']
			match_url = match_url.replace('playbattlegrounds', 'pubg')

			map = match_queryset.filter(reference__iexact=match_map_reference)

			if not map.exists():
				map = Map(
					name=match_map,
					reference=match_map_reference
				)
				map.save()
			else:
				map = map.first()

			this_match = Match(
				api_id=get_player_match_id(player_id, match_id),
				created=match_date,
				map=map,
				mode=match_mode,
				api_url=match_url,
				is_custom_match=match_custom
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
				match=this_match,
				api_id=roster_id
			)
			roster.save()

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
				participant_player_object = get_object_or_none(player_queryset, api_id=participant_player_api_id)
	
				if not participant_player_object:
					participant_player_object = Player(
						api_id=participant_player_api_id,
						platform_url=platform_url,
						api_url=build_player_account_id_url(platform_url, participant_player_api_id)
					)
					participant_player_object.save()

				participant_object = Participant(
					api_id=participant_api_id,
					kills=participant_kills,
					player_name=participant_name,
					placement=participant_placement,
					damage=participant_damage,
					player=participant_player_object  
				)
				participant_object.save()
				
				roster_participant = RosterParticipant(
					roster=roster,
					participant=participant_object
				)
				roster_participant.save()
			

			seconds_taken = "{:0.4f}".format(time.time() - start_time)
			print(
				f"--- parsing {match_id} took {seconds_taken}(s) ---"
			)

def get_player_matches(platform_url, player_response, perspective, game_mode):
	player_id, player_matches = parse_player_object(platform_url, player_response)
	parse_player_matches(player_matches, player_id)

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

def retrieve_player_season_stats(player_id, platform):

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
					rank_points_title=get_season_rank(round(rankPoints)),
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
					player=current_player,
					season=current_season
				).save()

def get_match_telemetry_from_match(match_json, match):

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
				parse_match_telemetry(
					url=url,
					asset_id=asset_id,
					telemetry_data=telemetry_data,
					match=match,
					date_created=date_created,
					account_id=match.api_id.split('_')[0]
				)

def parse_match_telemetry(url, asset_id, telemetry_data, date_created, match, account_id):

	telemetry_check = Telemetry.objects.filter(match=match, api_id=asset_id)
	this_player = get_object_or_404(Player, api_id=account_id)

	save = True

	if not telemetry_check.exists():

		match_kills = 0
		dead = False
		won_match = False

		match_telemet = Telemetry(
			api_id=asset_id,
			api_url=url,
			created_at=date_created,
			match=match
		)

		if save:
	 		match_telemet.save()

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
			'LogMatchStart'
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

		for log_event in log_player_events:
			
			event_type = log_event['_T']
			event_timestamp = log_event['_D']

			if event_timestamp:
				event_timestamp = parse(event_timestamp)

			if event_type == 'LogPlayerKill':

				victim_name = log_event['victim']['name']
				victim_id = log_event['victim']['accountId']

				if victim_id == account_id:
					victim_name = 'You'
					dead = True

				killer_name = log_event['killer']['name']
				killer_id = log_event['killer']['accountId']
				
				if killer_id == account_id:
					killer_name = 'You'
					match_kills += 1
					dead = False

				kill_location = log_event['damageReason']
				
				if kill_location not in ['None', 'NonSpecific']:
					kill_location = kill_location.title()
				else:
					kill_location = None

				kill_cause = log_event['damageCauserName']
				kill_cause = get_object_or_404(ItemTypeLookup, reference=kill_cause)
				kill_cause = kill_cause.name

				if kill_location:
					event_description = f'<b>{killer_name}</b> killed <b>{victim_name}</b> with a {kill_location} from a <b>{kill_cause}</b>'
				else:
					event_description = f'<b>{killer_name}</b> killed <b>{victim_name}</b> with a <b>{kill_cause}</b>'

				telemetry_event = TelemetryEvent(
					event_type=event_type,
					timestamp=event_timestamp,
					description=event_description,
					telemetry=match_telemet,
					player=this_player
				)
				
				if save:
					telemetry_event.save()

				if match_kills:
					
					if dead:
						event_description = f'<b>You</b> died with <b>{match_kills} kill(s)</b>'
					else:
						event_description = f'<b>You</b> now have <b>{match_kills} kill(s)</b>'

					telemetry_event = TelemetryEvent(
						event_type=event_type,
						timestamp=event_timestamp,
						description=event_description,
						telemetry=match_telemet,
						player=this_player
					)

					if save:
						telemetry_event.save()

			if event_type == 'LogItemUse':

				item_id = log_event['item']['itemId']
				item_used = get_object_or_404(ItemTypeLookup, reference=item_id)
				item_used = item_used.name

				event_description = f'<b>You</b> used a <b>{item_used}</b>'

				telemetry_event = TelemetryEvent(
					event_type=event_type,
					timestamp=event_timestamp,
					description=event_description,
					telemetry=match_telemet,
					player=this_player
				)

				if save:
					telemetry_event.save()

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
					event_description = f'<b>You</b> did not win this match. Better luck next time!'

				telemetry_event = TelemetryEvent(
					event_type=event_type,
					timestamp=event_timestamp,
					description=event_description,
					telemetry=match_telemet,
					player=this_player
				)

				if save:
					telemetry_event.save()

			if event_type == 'LogMatchStart':

				event_description = 'Match started'

				telemetry_event = TelemetryEvent(
					event_type=event_type,
					timestamp=event_timestamp,
					description=event_description,
					telemetry=match_telemet,
					player=this_player
				)

				if save:
					telemetry_event.save()

		event_description = match_kills
		event_type = 'LogTotalMatchKills'

		telemetry_event = TelemetryEvent(
			event_type=event_type,
			timestamp=event_timestamp,
			description=event_description,
			telemetry=match_telemet,
			player=this_player
		)

		if save:
			telemetry_event.save()
