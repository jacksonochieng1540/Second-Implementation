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
from django.contrib.auth.models import User  # Add this import

@api_view(['POST'])
@permission_classes([AllowAny])  # CHANGE THIS: from IsAuthenticated to AllowAny
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
    """Face authentication endpoint - REAL face matching"""
    from authentication.face_utils import face_auth as face_authenticator
    
    face_image = request.data.get('face_image')
    
    if not face_image:
        return Response({'error': 'Face image required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract face hash
    face_hash = face_authenticator.extract_face_hash(face_image)
    
    if face_hash is None:
        return Response({
            'success': False,
            'message': 'No face detected. Please look at the camera.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Find matching user
    username = face_authenticator.authenticate_face(face_hash)
    
    if username:
        from django.contrib.auth.models import User
        from .models import VehicleCommand, EventLog
        
        try:
            user = User.objects.get(username=username)
            
            # Create UNLOCK command
            command = VehicleCommand.objects.create(command='UNLOCK', user=user)
            
            EventLog.objects.create(
                user=user,
                event_type='FACE_AUTH',
                description=f"Face authentication successful for {user.username}"
            )
            
            print(f"✅ Face recognized: {username} - UNLOCK command created")
            
            return Response({
                'success': True,
                'message': f'Welcome {username}! Engine unlocking...',
                'user': username
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            pass
    
    # Create alert for unauthorized access
    from alerts.models import Alert
    Alert.objects.create(
        title='Unauthorized Face Access Attempt',
        description='An unrecognized face attempted to access the vehicle',
        severity='HIGH'
    )
    
    print(f"❌ Unauthorized face detected - Alert created")
    
    return Response({
        'success': False,
        'message': 'Face not recognized - Access denied'
    }, status=status.HTTP_401_UNAUTHORIZED)

    
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
        
        # Send SMS notification (with error handling)
        try:
            from alerts.sms_handler import gsm_handler
            owner_phone = '+254700000000'  # Get from user profile
            gsm_handler.send_sms(owner_phone, f"VEHICLE ALERT: {title}")
        except Exception as e:
            print(f"SMS error: {e}")
        
        return Response({'id': alert.id, 'message': 'Alert created'}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)