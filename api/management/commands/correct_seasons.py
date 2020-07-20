# django
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

# api app
from api.models import *

# other things
from datetime import timedelta
import os
from django.db.models import Count

from api.functions import make_request, build_url, get_object_or_none, get_platform, build_leaderboard_url
import api.settings as api_settings
import json

import time

class Command(BaseCommand):
	help = 'Re-populates the seasons within the Database with the correct information.'

	def add_arguments(self, parser):
         parser.add_argument(
            '--save',
            action='store_true',
            help='Save season',
        )

	def handle(self, *args, **options):

		save = options.pop('save')

		game_modes = [
			'solo',
			'solo-fpp',
			'duo',
			'duo-fpp',
			'squad',
			'squad-fpp'
		]

		region_shards = api_settings.PLATFORM_REGIONS

		current_seasons = Season.objects.all()
		
		all_platform_urls = [
			build_url('steam'),
			build_url('kakao'),
		]


		failed = {


		}

		for platform_url in all_platform_urls:
			platform = get_platform(platform_url)
			platform_shards = region_shards.get(platform, None)

			platform_seasons = current_seasons.filter(platform=platform)

			if platform_shards:

				for season in platform_seasons:
		
					for platform_shard in platform_shards:

						failed[platform_shard] = {

						}

						season_id = season.api_id

						new_url = platform_url.replace(platform, platform_shard)

						for game_mode in game_modes:

							if platform_shard in failed and season_id in failed[platform_shard] and 'error' in failed[platform_shard][season_id] and failed[platform_shard][season_id]['error']: continue

							print(season, ' x ', platform_shard, ' x ', game_mode)

							leaderboard_url = build_leaderboard_url(
								base_url=new_url,
								season_id=season_id,
								game_mode=game_mode
							)

							api_request = make_request(leaderboard_url)

							if api_request and 'errors' not in api_request:

								season.requires_region_shard = False
								season.save()

								failed[platform_shard][season_id] = { 'error': None }

							else:

								season.requires_region_shard = True
								season.save()

								if platform_shard in failed:

									if season_id not in failed[platform_shard]:

										if 'Not Found' in api_request['errors'][0]['title']:

											failed[platform_shard][season_id] = {
												'error': 'Not Found'
											}

										else:

											failed[platform_shard][season_id] = {
												'error': 'Missing Data'
											}

		all_platform_urls = [
			build_url('xbox'),
			build_url('steam'),
			build_url('psn'),
			build_url('kakao'),
			build_url('stadia'),
			build_url('tournament')
		]

		for platform_url in all_platform_urls:
			url = "{}{}".format(platform_url, 'seasons')
			request = make_request(url)
			platform = get_platform(url)

			if not request.get('errors'):
				for season in request.get('data'):
					api_id = season.get('id')
					current_season = current_seasons.filter(api_id=api_id, platform=platform)

					attributes = season.get('attributes')
					is_current = attributes.get('isCurrentSeason')
					is_off_season = attributes.get('isOffseason')

					if current_season.exists():
						current_season = current_season.first()
						
						if current_season.is_current != is_current:
							current_season.is_current = is_current
						
						if current_season.is_off_season != is_off_season:
							current_season.is_off_season = is_off_season

						if save:
							current_season.save()

					else:

						Season.objects.get_or_create(
							api_id=api_id,
							is_current=is_current,
							is_off_season=is_off_season,
							api_url=url,
							platform=platform
						)

			else:

				print(url, ' failed for some reason')
										
					


			