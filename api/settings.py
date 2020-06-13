API_TOKEN = ''

API_HEADER = {
    "accept": "application/vnd.api+json",
    "Accept-Encoding": "gzip",
    "Authorization": "Bearer {}".format(API_TOKEN)
}

PLAYER_FILTER = 'players?filter[playerNames]='
PLAYER_ACCOUNT_FILTER = 'players/$accountId'
MATCH_FILTER = 'matches/$matchID'
LIFETIME_FILTER = 'players/$accountId/seasons/lifetime'
SEASON_FILTER = 'players/$accountId/seasons/$seasonID'
LIST_TOURNAMENTS_FILTER = 'tournaments/'
TOURNAMENTS_FILTER = 'tournaments/$tourneyID'
SEASON_LIST_URL = 'seasons'

BASE_API_URL = 'https://api.pubg.com/'
PC_SHARD = "shards/steam/"
STADIA_SHARD = "shards/stadia/"
XBOX_SHARD = "shards/xbox/"
PLAYSTATION_SHARD = "shards/psn/"
KAKAO_SHARD = "shards/kakao/"
TOURNAMENT_SHARD = "shards/tournament/"

MAP_BINDING = {
    "Baltic_Main": "Erangel",
    "Erangel_Main": "Erangel",
    "DihorOtok_Main": "Vikendi",
    "Desert_Main": "Miramar",
    "Range_Main": "Camp Jackal",
    "Savage_Main": "Sanhok",
    "Summerland_Main": "Karakin"
}

PLAYER_PLATFORM_URL_CACHE_KEY = '{}_{}_platform_url'
PLAYER_URL_CACHE_KEY = '{}_{}_player_url'
PLAYER_RESPONSE_CACHE_KEY = '{}_{}_player_response'
PLAYER_CURRENTLY_PROCESSING_CACHE_KEY = '{}_{}_current_processing'
PLAYER_MATCH_DATA_CACHE_KEY = '{}_match_data'
PLAYER_RANKED_SEASON_STATS_CACHE_KEY = 'ranked_{}_season_data'
PLAYER_SEASON_STATS_CACHE_KEY = '{}_season_data'
MATCH_ROSTER_CACHE_KEY = '{}_roster'