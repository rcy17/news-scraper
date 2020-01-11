from django.urls import path, include
from . import views


urlpatterns = [
    path('<int:team_id>', views.show_team),
    path('rank/<str:rank_key>', views.show_rank),
]
