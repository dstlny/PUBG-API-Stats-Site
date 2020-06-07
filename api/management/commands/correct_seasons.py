# django
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

# api app
from api.models import *

# other things
from datetime import timedelta
import os
from django.db.models import Count

from api.functions import make_request, build_url, get_object_or_none, get_platform
import api.settings as api_settings
import json

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

		all_platform_urls = [
			build_url('xbox'),
			build_url('steam'),
			build_url('psn'),
			build_url('kakao'),
			build_url('stadia'),
			build_url('tournament')
		]

		current_seasons = Season.objects.all()

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



			