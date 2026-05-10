from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import VehicleCommand, EventLog
from .serializers import VehicleCommandSerializer
from alerts.models import Alert
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import base64
from django.core.files.base import ContentFile
import os
import requests

from authentication.face_recognizer import face_recognizer



PI_API_URL = "http://10.251.159.168:5000"  
PI_API_KEY = "mysecurekey123"


@api_view(['POST'])
@permission_classes([AllowAny])
def send_command(request):
    """Send LOCK or UNLOCK command to Raspberry Pi"""
    command = request.data.get('command')
    
    if command not in ['LOCK', 'UNLOCK']:
        return Response({'error': 'Invalid command'}, status=status.HTTP_400_BAD_REQUEST)
    
    
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        test_user.set_password('testpass123')
        test_user.save()
    
    user = request.user if request.user.is_authenticated else test_user
    
    vehicle_command = VehicleCommand.objects.create(
        command=command,
        user=user
    )
    

    EventLog.objects.create(
        user=user,
        event_type='COMMAND_SENT',
        description=f"User {user.username} sent {command} command"
    )
    
   
    try:
        response = requests.post(
            f"{PI_API_URL}/command",
            headers={'X-API-KEY': PI_API_KEY, 'Content-Type': 'application/json'},
            json={'command': command},
            timeout=2
        )
        if response.status_code == 200:
            print(f"{command} command sent to Raspberry Pi")
        else:
            print(f" Pi responded: {response.status_code}")
    except Exception as e:
        print(f" Could not send to Pi: {e}")
    
    print(f" Command created: {command} (ID: {vehicle_command.id})")
    
    serializer = VehicleCommandSerializer(vehicle_command)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def face_auth(request):
    """Face authentication - sends UNLOCK to Pi when authorized, INTRUDER alert when not"""
    
    face_image = request.data.get('face_image')
    
    if not face_image:
        return Response({'error': 'Face image required'}, status=400)
    
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
                print(f"Auto-created user: {username}")
            

            command = VehicleCommand.objects.create(command='UNLOCK', user=user)
            

            EventLog.objects.create(
                user=user,
                event_type='FACE_AUTH',
                description=f"Face authentication successful for {user.username}"
            )
            
            print(f"\n AUTHENTICATED: {username} ({confidence:.1f}% confidence) ")
            print(f"UNLOCK command #{command.id} created")
            
            
            try:
                print(f"\n📡 Sending UNLOCK command to Raspberry Pi at {PI_API_URL}...")
                response = requests.post(
                    f"{PI_API_URL}/command",
                    headers={'X-API-KEY': PI_API_KEY, 'Content-Type': 'application/json'},
                    json={'command': 'UNLOCK'},
                    timeout=2
                )
                if response.status_code == 200:
                    print(" UNLOCK command sent to Pi - Relay will activate!")
                else:
                    print(f" Pi responded: {response.status_code}")
            except Exception as e:
                print(f"Could not send UNLOCK to Pi: {e}")
            
            return Response({
                'success': True,
                'message': f'Welcome {username}! Engine unlocking...',
                'user': username,
                'confidence': confidence
            }, status=200)
            
        except Exception as e:
            print(f" User error: {e}")
    
  
    print(f"\n ACCESS DENIED: {message} ")
    print(" INTRUDER DETECTED - Sending alert to Raspberry Pi for SMS ")
    
    
    alert = Alert.objects.create(
        title='UNAUTHORIZED ACCESS ATTEMPT',
        description=f'An unrecognized person attempted to access the vehicle. {message}',
        severity='HIGH'
    )
    

    image_saved = False
    try:
        if ',' in face_image:
            image_data = base64.b64decode(face_image.split(',')[1])
        else:
            image_data = base64.b64decode(face_image)
        
        os.makedirs('media/alerts', exist_ok=True)
        filename = f'intruder_{alert.id}.jpg'
        alert.image.save(filename, ContentFile(image_data))
        image_saved = True
        print(f"Intruder image saved for alert {alert.id}")
    except Exception as img_error:
        print(f"Failed to save image: {img_error}")
    
   
    pi_alert_sent = False
    try:
        print(f"\n Sending intruder alert to Raspberry Pi at {PI_API_URL}/intruder-alert...")
        
        response = requests.post(
            f"{PI_API_URL}/intruder-alert",
            headers={
                'X-API-KEY': PI_API_KEY,
                'Content-Type': 'application/json'
            },
            json={
                'alert_type': 'intruder',
                'alert_id': alert.id
            },
            timeout=5
        )
        
        if response.status_code == 200:
            pi_alert_sent = True
            print(" Intruder alert sent to Raspberry Pi! ")
            print("📱 Raspberry Pi will send SMS with GPS location to your phone!")
        else:
            print(f"Raspberry Pi returned error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f" Cannot connect to Raspberry Pi at {PI_API_URL}")
        print("   Make sure the Pi server is running on Raspberry Pi")
        print("   SSH to Pi and run: python3 pi_server.py")
    except Exception as e:
        print(f" Error sending to Raspberry Pi: {e}")
    
    return Response({
        'success': False,
        'message': 'Access denied - Face not recognized. Alert sent to Raspberry Pi for SMS.',
        'alert_id': alert.id,
        'image_saved': image_saved,
        'pi_alert_sent': pi_alert_sent
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
                print(f" Image saved for alert {alert.id}")
            except Exception as img_error:
                print(f"Failed to save image: {img_error}")
        
        return Response({
            'id': alert.id, 
            'message': 'Alert created',
            'image_saved': bool(face_image)
        }, status=201)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)
