from django.urls import path

from . import views

urlpatterns = [
    path('status', views.status, name='status'),
    path('search', views.search, name='search'),
    path('retrieve_matches', views.retrieve_matches, name='retrieve_matches'),
    path('retrieve_season_stats', views.retrieve_season_stats, name='retrieve_season_stats'),
]