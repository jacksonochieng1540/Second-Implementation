from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import VehicleCommand, EventLog
from .serializers import VehicleCommandSerializer
from vehicle_tracking.models import VehicleLocation
from alerts.models import Alert
from django.contrib.auth.models import User

# Import the correct face recognizer
from authentication.true_face_recognizer import face_recognizer

@api_view(['POST'])
@permission_classes([AllowAny])
def send_command(request):
    command = request.data.get('command')
    
    if command not in ['LOCK', 'UNLOCK']:
        return Response({'error': 'Invalid command'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get or create a test user for unauthenticated requests
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        test_user.set_password('testpass123')
        test_user.save()
    
    # Use test_user if no authenticated user
    user = request.user if request.user.is_authenticated else test_user
    
    vehicle_command = VehicleCommand.objects.create(
        command=command,
        user=user
    )
    
    # Log event
    EventLog.objects.create(
        user=user,
        event_type='COMMAND_SENT',
        description=f"User {user.username} sent {command} command"
    )
    
    # Broadcast via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'vehicle_tracking',
        {
            'type': 'command_update',
            'data': {
                'command': command,
                'status': 'pending',
                'user': user.username,
                'timestamp': vehicle_command.timestamp.isoformat()
            }
        }
    )
    
    serializer = VehicleCommandSerializer(vehicle_command)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def face_auth(request):
    """Face authentication - ONLY registered user can unlock engine"""
    
    face_image = request.data.get('face_image')
    
    if not face_image:
        return Response({'error': 'Face image required'}, status=400)
    
    print("\n" + "🔐"*25)
    print("FACE AUTHENTICATION FOR ENGINE UNLOCK")
    print("🔐"*25)
    
    # This will ONLY return username if face MATCHES a registered face
    username, message = face_recognizer.authenticate_face(face_image)
    
    if username:
        try:
            user = User.objects.get(username=username)
            
            # Create UNLOCK command
            command = VehicleCommand.objects.create(command='UNLOCK', user=user)
            
            print(f"\n✅✅✅ AUTHENTICATED: {username} ✅✅✅")
            print(f"UNLOCK command #{command.id} created")
            
            return Response({
                'success': True,
                'message': f'Welcome {username}! Engine unlocking...',
                'user': username
            }, status=200)
            
        except User.DoesNotExist:
            print(f"User {username} not found in database")
    
    print(f"\n❌❌❌ ACCESS DENIED: {message} ❌❌❌")
    
    # Create alert for unauthorized access
    Alert.objects.create(
        title='UNAUTHORIZED ACCESS ATTEMPT',
        description=f'An unrecognized person attempted to access the vehicle. {message}',
        severity='HIGH'
    )
    
    return Response({
        'success': False,
        'message': 'Access denied - Face not recognized'
    }, status=401)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_alert(request):
    """Create alert from hardware"""
    try:
        title = request.data.get('title')
        description = request.data.get('description')
        severity = request.data.get('severity', 'MEDIUM')
        location = request.data.get('location', {})
        
        alert = Alert.objects.create(
            title=title,
            description=description,
            severity=severity,
            location_lat=location.get('latitude'),
            location_lng=location.get('longitude')
        )
        
        # Send SMS notification
        try:
            from alerts.sms_handler import gsm_handler
            owner_phone = '+254700000000'
            gsm_handler.send_sms(owner_phone, f"VEHICLE ALERT: {title}")
        except Exception as e:
            print(f"SMS error: {e}")
        
        return Response({'id': alert.id, 'message': 'Alert created'}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)