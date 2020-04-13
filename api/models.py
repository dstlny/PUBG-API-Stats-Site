from django.db import models


class Map(models.Model):
    name = models.CharField(max_length=64)
    reference = models.CharField(max_length=64)

    def __str__(self):
        return "{} ({})".format(self.name, self.reference)

class Match(models.Model):
    api_id = models.CharField(max_length=255)
    created = models.DateTimeField()
    api_url = models.CharField(max_length=255)
    mode = models.CharField(max_length=255, blank=True, null=True)
    map = models.ForeignKey('Map', on_delete=models.CASCADE)
    is_custom_match = models.IntegerField(blank=True, null=True)
    # full_match = models.BooleanField(default=False)

    def __str__(self):
        return "{} - {}".format(self.api_id, self.map.name)
        
class MatchParticipant(models.Model):
    match = models.ForeignKey('Match', on_delete=models.CASCADE)
    participant = models.ForeignKey('Participant', on_delete=models.CASCADE)

    def __str__(self):
        return "{} - {}".format(self.match.api_id, self.participant.player_name)

class Participant(models.Model):
    api_id = models.CharField(max_length=255)
    player_name = models.CharField(max_length=255)
    damage = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    kills = models.IntegerField(blank=True, null=True)
    placement = models.IntegerField(blank=True, null=True)
    player = models.ForeignKey('Player', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "{} - {}".format(self.api_id, self.player_name)

class Player(models.Model):
    api_id = models.CharField(max_length=255)
    # name = models.CharField(max_length=30)
    platform_url = models.CharField(max_length=255, blank=True, null=True)
    api_url = models.CharField(max_length=255)

    def __str__(self):
        return self.api_id

class PlayerSeasonStats(models.Model):
    mode = models.CharField(max_length=255, blank=True, null=True)
    assists = models.IntegerField(blank=True, null=True)
    boosts = models.IntegerField(blank=True, null=True)
    knocks = models.IntegerField(blank=True, null=True)
    daily_kills = models.IntegerField(blank=True, null=True)
    damage_dealt = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    days = models.IntegerField(blank=True, null=True)
    daily_wins = models.IntegerField(blank=True, null=True)
    headshot_kills = models.IntegerField(blank=True, null=True)
    heals = models.IntegerField(blank=True, null=True)
    kill_points = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    kills = models.IntegerField(blank=True, null=True)
    longest_kill = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    longest_time_survived = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    losses = models.IntegerField(blank=True, null=True)
    max_kill_streaks = models.IntegerField(blank=True, null=True)
    most_survival_time = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    rank_points = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    rank_points_title = models.CharField(max_length=255, blank=True, null=True)
    revives = models.IntegerField(blank=True, null=True)
    ride_distance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    road_kills = models.IntegerField(blank=True, null=True)
    round_most_kills = models.IntegerField(blank=True, null=True)
    rounds_played = models.IntegerField(blank=True, null=True)
    suicides = models.IntegerField(blank=True, null=True)
    swim_distance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    team_kills = models.IntegerField(blank=True, null=True)
    time_survived = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    top_10s = models.IntegerField(blank=True, null=True)
    vehicle_destroys = models.IntegerField(blank=True, null=True)
    walk_distance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    weapons_acquired = models.IntegerField(blank=True, null=True)
    weekly_kills = models.IntegerField(blank=True, null=True)
    weekly_wins = models.IntegerField(blank=True, null=True)
    win_points = models.IntegerField(blank=True, null=True)
    wins = models.IntegerField(blank=True, null=True)
    player = models.ForeignKey('Player', on_delete=models.CASCADE, blank=True, null=True)
    season = models.ForeignKey('Season', on_delete=models.CASCADE)

    def __str__(self):
        return "{} - {}".format(self.player.name, self.season.api_id)

class Roster(models.Model):
    api_id = models.CharField(max_length=255)
    placement = models.IntegerField(blank=True, null=True)
    match = models.ForeignKey('Match', on_delete=models.CASCADE)
    participants = models.ManyToManyField('Participant', through='Rosterparticipant')

    def __str__(self):
        return f"{self.api_id} - {self.match.api_id}"

class RosterParticipant(models.Model):
    participant = models.ForeignKey('Participant', on_delete=models.CASCADE)
    roster = models.ForeignKey('Roster', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.participant.player_name} - {self.roster.api_id}"

class Season(models.Model):
    api_id = models.CharField(max_length=255)
    is_current = models.IntegerField(blank=True, null=True)
    is_off_season = models.IntegerField(blank=True, null=True)
    api_url = models.CharField(max_length=255)
    platform = models.CharField(max_length=255)
    
    def __str__(self):
        return "{} - {} - {}".format(self.api_id, self.platform, 'Current' if self.is_current else 'Not current')

class Telemetry(models.Model):
    api_id = models.CharField(max_length=255)
    api_url = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    match = models.ForeignKey('Match', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.api_id} - {self.match.api_id}"

class TelemetryEvent(models.Model):
    event_type = models.CharField(max_length=255)
    timestamp = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    telemetry = models.ForeignKey('Telemetry', on_delete=models.CASCADE)
    player =  models.ForeignKey('Player', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"{self.timestamp} - {self.event_type} - {self.description}"

class ItemTypeLookup(models.Model):
    name = models.CharField(max_length=255)
    reference = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name}"