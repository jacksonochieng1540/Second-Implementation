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
from django.views.decorators.csrf import csrf_exempt
import base64
from django.core.files.base import ContentFile
import os

# Import the working face recognizer
from authentication.face_recognizer import face_recognizer

@api_view(['POST'])
@permission_classes([AllowAny])
def send_command(request):
    """Send LOCK or UNLOCK command to Raspberry Pi"""
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
    
    # Broadcast via WebSocket for real-time dashboard update
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
    
    print(f"📡 Command created: {command} (ID: {vehicle_command.id})")
    
    serializer = VehicleCommandSerializer(vehicle_command)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def face_auth(request):
    """Face authentication - ONLY registered user can unlock engine"""
    from authentication.face_recognizer import face_recognizer
    from .models import VehicleCommand, EventLog
    from alerts.models import Alert
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    face_image = request.data.get('face_image')
    
    if not face_image:
        return Response({'error': 'Face image required'}, status=400)
    
    print("\n" + "🔐"*25)
    print("FACE AUTHENTICATION FOR ENGINE UNLOCK")
    print("🔐"*25)
    
    # This will ONLY return username if face MATCHES a registered face
    username, confidence, message = face_recognizer.authenticate_face(face_image)
    
    if username:
        try:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@example.com'}
            )
            if created:
                user.set_password(f'{username}pass123')
                user.save()
                print(f"✅ Auto-created user: {username}")
            
            # Create UNLOCK command
            command = VehicleCommand.objects.create(command='UNLOCK', user=user)
            
            # Log event
            EventLog.objects.create(
                user=user,
                event_type='FACE_AUTH',
                description=f"Face authentication successful for {user.username}"
            )
            
            print(f"\n✅✅✅ AUTHENTICATED: {username} ({confidence:.1f}% confidence) ✅✅✅")
            print(f"UNLOCK command #{command.id} created")
            
            # Broadcast via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'vehicle_tracking',
                {
                    'type': 'command_update',
                    'data': {
                        'command': 'UNLOCK',
                        'status': 'pending',
                        'user': username,
                        'timestamp': command.timestamp.isoformat()
                    }
                }
            )
            
            return Response({
                'success': True,
                'message': f'Welcome {username}! Engine unlocking...',
                'user': username,
                'confidence': confidence
            }, status=200)
            
        except Exception as e:
            print(f"❌ User error: {e}")
    
    # CREATE ALERT FOR INTRUDER WITH IMAGE
    print(f"\n❌❌❌ ACCESS DENIED: {message} ❌❌❌")
    
    alert = Alert.objects.create(
        title='UNAUTHORIZED ACCESS ATTEMPT',
        description=f'An unrecognized person attempted to access the vehicle. {message}',
        severity='HIGH'
    )
    
    # Save the intruder face image
    try:
        if ',' in face_image:
            image_data = base64.b64decode(face_image.split(',')[1])
        else:
            image_data = base64.b64decode(face_image)
        
        os.makedirs('media/alerts', exist_ok=True)
        filename = f'intruder_{alert.id}.jpg'
        alert.image.save(filename, ContentFile(image_data))
        print(f"📸 Intruder image saved for alert {alert.id}")
    except Exception as img_error:
        print(f"Failed to save image: {img_error}")
    
    return Response({
        'success': False,
        'message': 'Access denied - Face not recognized. Alert created.',
        'alert_id': alert.id
    }, status=401)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_alert(request):
    """Create alert from hardware with intruder image"""
    try:
        title = request.data.get('title', 'Security Alert')
        description = request.data.get('description', '')
        severity = request.data.get('severity', 'MEDIUM')
        location = request.data.get('location', {})
        face_image = request.data.get('face_image')
        
        alert = Alert.objects.create(
            title=title,
            description=description,
            severity=severity,
            location_lat=location.get('latitude'),
            location_lng=location.get('longitude')
        )
        
        if face_image:
            try:
                if ',' in face_image:
                    image_data = base64.b64decode(face_image.split(',')[1])
                else:
                    image_data = base64.b64decode(face_image)
                
                os.makedirs('media/alerts', exist_ok=True)
                filename = f'intruder_{alert.id}.jpg'
                alert.image.save(filename, ContentFile(image_data))
                print(f"📸 Image saved for alert {alert.id}")
            except Exception as img_error:
                print(f"Failed to save image: {img_error}")
        
        try:
            from alerts.sms_handler import gsm_handler
            owner_phone = '+254792333250'
            gsm_handler.send_sms(owner_phone, f"🚨 ALERT: {title}")
        except Exception as e:
            print(f"SMS error: {e}")
        
        return Response({'id': alert.id, 'message': 'Alert created'}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)