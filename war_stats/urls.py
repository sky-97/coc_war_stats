from django.urls import path
from .views import get_war_stats, war_stats

urlpatterns = [
    path('war-stats/<str:clan_tag>/', get_war_stats, name='get_war_stats'),
    path('war-stats/', war_stats, name='war_stats'),
]
