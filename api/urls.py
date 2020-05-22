from django.urls import path, re_path

from . import views

urlpatterns = [
    path('status', views.status, name='status'),
    path('search', views.search, name='search'),
    path('retrieve_matches', views.retrieve_matches, name='retrieve_matches'),
    path('retrieve_season_stats', views.retrieve_season_stats, name='retrieve_season_stats'),
    re_path(r'match_detail/(?P<match_id>.+)/$', views.match_detail, name='match_detail'),
    path('match_rosters/<int:match_id>/', views.get_match_rosters, name='match_rosters')
]