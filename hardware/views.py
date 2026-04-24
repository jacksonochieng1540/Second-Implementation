from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils import timezone
from api.models import VehicleCommand, EventLog
from vehicle_tracking.models import VehicleLocation
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def verify_hardware_api_key(request):
    api_key = request.headers.get('X-API-KEY')
    return api_key == settings.HARDWARE_API_KEY

@api_view(['GET'])
@permission_classes([AllowAny])
def get_command(request):
    if not verify_hardware_api_key(request):
        return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
    
    
    command = VehicleCommand.objects.filter(executed=False).first()
    
    if command:
        return Response({
            'command_id': command.id,
            'command': command.command,
            'timestamp': command.timestamp.isoformat()
        })
    else:
        return Response({'command': 'NONE'})

@api_view(['POST'])
@permission_classes([AllowAny])
def mark_executed(request):
    if not verify_hardware_api_key(request):
        return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
    
    command_id = request.data.get('command_id')
    
    try:
        command = VehicleCommand.objects.get(id=command_id)
        command.executed = True
        command.executed_at = timezone.now()
        command.save()
        
        
        EventLog.objects.create(
            user=command.user,
            event_type='COMMAND_EXECUTED',
            description=f"Command {command.command} executed by hardware"
        )
        
        # Broadcast via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'vehicle_tracking',
            {
                'type': 'command_update',
                'data': {
                    'command': command.command,
                    'status': 'executed',
                    'executed_at': command.executed_at.isoformat()
                }
            }
        )
        
        return Response({'status': 'success'})
    except VehicleCommand.DoesNotExist:
        return Response({'error': 'Command not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def send_location(request):
    if not verify_hardware_api_key(request):
        return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
    
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    speed = request.data.get('speed', 0)
    heading = request.data.get('heading', 0)
    
    if not all([latitude, longitude]):
        return Response({'error': 'Latitude and longitude required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Save location
    location = VehicleLocation.objects.create(
        latitude=latitude,
        longitude=longitude,
        speed=speed,
        heading=heading
    )
    
    # Log event periodically (not every update to avoid spam)
    import random
    if random.random() < 0.1:  # 10% of updates
        EventLog.objects.create(
            event_type='LOCATION_UPDATE',
            description=f"Vehicle location updated: {latitude}, {longitude}"
        )
    
    # Broadcast via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'vehicle_tracking',
        {
            'type': 'location_update',
            'data': {
                'latitude': float(latitude),
                'longitude': float(longitude),
                'speed': speed,
                'heading': heading,
                'timestamp': location.timestamp.isoformat()
            }
        }
    )
    
    return Response({'status': 'success', 'location_id': location.id})
