# django
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

# api app
from api.models import *

# other things
from datetime import timedelta
import os
from django.db.models import Count

class Command(BaseCommand):
    help = 'Deletes data older than 14 days.'

    def handle(self, *args, **options):

        fourteen_days_ago = timezone.now() - timedelta(days=14)
        old_matches = Match.objects.filter(created__lt=fourteen_days_ago)

        logs_path = os.path.realpath('.../logs/deletion_log.log')

        log_file = open(logs_path, 'a+')

        log_file.write(f'########################## COMMAND BEING RAN AT {timezone.now().strftime("%b %d %Y @ %H:%M:%S")} | {old_matches.count()} OBJECTS TO BE DELETED ##########################\n')

        for match in old_matches:

            days_old = timezone.now() - match.created
            created = match.created.strftime("%b %d %Y @ %H:%M:%S")
            data = f"~~~~ Match was created on {created} and is {days_old.days} days old ~~~~~\n"
            log_file.write(data)
            match.delete()

        log_file.close()

        purge_dupes()

def purge_dupes():

	duplicates = Match.objects.values(
    	'api_id'
    ).annotate(
		api_id_count=Count('api_id')
	).filter(api_id_count__gt=1)

	matches = Match.objects.all()

	for duplicate in duplicates:
		api_id = duplicate['api_id']
		dupes_match = matches.filter(api_id__iexact=api_id)
		
		earliest = dupes_match.earliest('id')
		print('deleting earliest...')
		earliest.delete()




       
