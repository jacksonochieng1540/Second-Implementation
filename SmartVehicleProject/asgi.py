import os
import django
from django.core.asgi import get_asgi_application

# Initialize Django BEFORE importing other modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartVehicleProject.settings')
django.setup()

# Now import other modules after Django is initialized
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from api.consumers import VehicleTrackingConsumer

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/vehicle/", VehicleTrackingConsumer.as_asgi()),
        ])
    ),
})