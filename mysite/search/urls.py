from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.search_start),
    path('search/', views.search_target),
    path('news/<int:news_id>', views.show_news)
]
