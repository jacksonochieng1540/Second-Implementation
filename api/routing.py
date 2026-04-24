from django.urls import path
from .consumers import VehicleConsumer

websocket_urlpatterns = [
    path('ws/vehicle/', VehicleConsumer.as_asgi()),
]