from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.manage_scraper),
    path('render', views.render_scraper)
]
