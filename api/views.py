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
import base64
from django.core.files.base import ContentFile
import os

# Import the working face recognizer
from authentication.face_recognizer import face_recognizer

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
    """Face authentication"""
    from authentication.face_recognizer import face_recognizer
    from .models import VehicleCommand
    from alerts.models import Alert
    import base64
    from django.core.files.base import ContentFile
    import os
    
    face_image = request.data.get('face_image')
    
    if not face_image:
        return Response({'error': 'Face image required'}, status=400)
    
    print("\n" + "="*50)
    print("🔐 FACE AUTHENTICATION")
    print("="*50)
    
    result, username, confidence = face_recognizer.authenticate_face(face_image)
    
    if result == 'RECOGNIZED':
        user = User.objects.get(username=username)
        command = VehicleCommand.objects.create(command='UNLOCK', user=user)
        print(f"✅ RECOGNIZED: {username} - UNLOCK #{command.id}")
        
        return Response({
            'success': True,
            'message': f'Welcome {username}! Engine unlocking...',
            'user': username
        }, status=200)
    
    elif result == 'NO_FACE':
        print("📷 NO_FACE - No face detected")
        return Response({
            'success': False,
            'message': 'No face detected'
        }, status=200)
    
    else:  # NOT_RECOGNIZED - UNAUTHORIZED ACCESS
        print("🚫 NOT_RECOGNIZED - Unauthorized access - Creating alert with image")
        
        # Create alert
        alert = Alert.objects.create(
            title='UNAUTHORIZED ACCESS ATTEMPT',
            description='An unrecognized face attempted to access the vehicle',
            severity='HIGH'
        )
        
        # Save the intruder image
        try:
            # Remove data URL prefix if present
            if ',' in face_image:
                image_data = base64.b64decode(face_image.split(',')[1])
            else:
                image_data = base64.b64decode(face_image)
            
            # Ensure media/alerts directory exists
            os.makedirs('media/alerts', exist_ok=True)
            
            # Save the image
            filename = f'intruder_{alert.id}.jpg'
            alert.image.save(filename, ContentFile(image_data))
            print(f"📸 Intruder image saved for alert {alert.id}")
            
        except Exception as e:
            print(f"Failed to save image: {e}")
        
        return Response({ 
            'success': False,
            'message': 'Face not recognized - Access denied. Alert created.',
            'alert_id': alert.id
        }, status=401)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_alert(request):
    """Create alert from hardware with intruder image"""
    import base64
    from django.core.files.base import ContentFile
    import os
    
    try:
        title = request.data.get('title', 'Security Alert')
        description = request.data.get('description', '')
        severity = request.data.get('severity', 'MEDIUM')
        location = request.data.get('location', {})
        face_image = request.data.get('face_image')  # Base64 encoded intruder face
        
        print(f"\n📝 Creating alert: {title}")
        print(f"   Severity: {severity}")
        print(f"   Face image provided: {bool(face_image)}")
        
        if face_image:
            print(f"   Image data length: {len(face_image)} chars")
            print(f"   Image starts with: {face_image[:50]}...")
        
        alert = Alert.objects.create(
            title=title,
            description=description,
            severity=severity,
            location_lat=location.get('latitude'),
            location_lng=location.get('longitude')
        )
        
        # Save the intruder image if provided
        image_saved = False
        image_path = None
        
        if face_image:
            try:
                # Remove data URL prefix if present
                if ',' in face_image:
                    image_data = base64.b64decode(face_image.split(',')[1])
                else:
                    image_data = base64.b64decode(face_image)
                
                # Ensure media/alerts directory exists
                os.makedirs('media/alerts', exist_ok=True)
                
                # Save the image
                filename = f'intruder_{alert.id}.jpg'
                full_path = os.path.join('media/alerts', filename)
                
                with open(full_path, 'wb') as f:
                    f.write(image_data)
                
                # Also save via Django's ImageField
                alert.image.save(filename, ContentFile(image_data))
                image_saved = True
                image_path = full_path
                
                print(f"📸 Intruder image saved for alert {alert.id}")
                print(f"   Path: {full_path}")
                print(f"   Size: {len(image_data)} bytes")
                
            except Exception as img_error:
                print(f"❌ Failed to save image: {img_error}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️ No face image provided in request")
        
        # Send SMS notification (optional, handle gracefully)
        try:
            from alerts.sms_handler import gsm_handler
            owner_phone = '+254792333250'
            gsm_handler.send_sms(owner_phone, f"🚨 ALERT: {title}")
        except Exception as e:
            print(f"SMS error: {e}")
        
        return Response({
            'id': alert.id,
            'message': 'Alert created',
            'image_saved': image_saved,
            'image_path': image_path
        }, status=201)
        
    except Exception as e:
        print(f"❌ Create alert error: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)