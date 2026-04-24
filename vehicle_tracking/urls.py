from django.urls import path
from . import views

urlpatterns = [
    path('latest-location/', views.get_latest_location, name='latest_location'),
    path('location-history/', views.get_location_history, name='location_history'),
]