import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from vehicle_tracking.models import VehicleLocation

class VehicleTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'vehicle_tracking'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        print(f"WebSocket connected: {self.channel_name}")
        
        # Send latest location on connect
        latest_location = await self.get_latest_location()
        if latest_location:
            await self.send(text_data=json.dumps({
                'type': 'LOCATION_UPDATE',
                'data': latest_location
            }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print(f"WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        print(f"Received WebSocket message: {data}")
        
        if data.get('type') == 'GET_HISTORY':
            history = await self.get_location_history()
            await self.send(text_data=json.dumps({
                'type': 'LOCATION_HISTORY',
                'data': history
            }))
    
    async def location_update(self, event):
        """Send location update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'LOCATION_UPDATE',
            'data': event['data']
        }))
    
    async def command_update(self, event):
        """Send command update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'COMMAND_UPDATE',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def get_latest_location(self):
        try:
            location = VehicleLocation.objects.latest('timestamp')
            return {
                'latitude': float(location.latitude),
                'longitude': float(location.longitude),
                'speed': location.speed,
                'heading': location.heading,
                'timestamp': location.timestamp.isoformat()
            }
        except VehicleLocation.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_location_history(self):
        locations = VehicleLocation.objects.order_by('-timestamp')[:30]
        return [{
            'latitude': float(loc.latitude),
            'longitude': float(loc.longitude),
            'speed': loc.speed,
            'heading': loc.heading,
            'timestamp': loc.timestamp.isoformat()
        } for loc in locations]