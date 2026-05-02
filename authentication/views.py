from django.shortcuts import render
from django.contrib.auth import login
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import UserProfile
from .face_recognizer import face_recognizer
import logging
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_face(request):
    """Register a new face"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        face_image = request.data.get('face_image')
        
        if not all([username, password, face_image]):
            return Response({'error': 'All fields required'}, status=400)
        
        print(f"\n📝 Registering face for: {username}")
        
        # Register the face
        success, message = face_recognizer.register_face(username, face_image)
        
        if not success:
            return Response({'error': message}, status=400)
        
        # Create or get user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.com'}
        )
        
        if created:
            user.set_password(password)
            user.save()
            print(f"✅ Created user: {username}")
        else:
            user.set_password(password)
            user.save()
            print(f"✅ Updated password for: {username}")
        
        # Update profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.has_face_registered = True
        profile.save()
        
        return Response({
            'success': True,
            'message': message,
            'user_id': user.id
        }, status=200)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def face_login(request):
    """Authenticate face"""
    try:
        face_image = request.data.get('face_image')
        
        if not face_image:
            return Response({'error': 'Face image required'}, status=400)
        
        print(f"\n🔍 Authenticating face...")
        
        result, username, confidence = face_recognizer.authenticate_face(face_image)
        
        if result == 'RECOGNIZED':
            user = User.objects.get(username=username)
            login(request, user)
            
            return Response({
                'success': True,
                'message': f'Welcome {username}!',
                'user': username,
                'confidence': confidence
            }, status=200)
        
        elif result == 'NO_FACE':
            return Response({
                'success': False,
                'message': 'No face detected',
                'result': 'NO_FACE'
            }, status=200)
        
        else:  # NOT_RECOGNIZED
            return Response({
                'success': False,
                'message': 'Face not recognized - Unauthorized',
                'result': 'NOT_RECOGNIZED'
            }, status=401)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return Response({'error': str(e)}, status=500)


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})