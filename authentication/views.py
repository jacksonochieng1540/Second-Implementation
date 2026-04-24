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

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_face(request):
    """Register a new face for a user"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        face_image = request.data.get('face_image')
        
        if not all([username, password, face_image]):
            return Response({'error': 'Username, password, and face image required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        print(f"Registering face for user: {username}")
        
        # Register the face
        success, message = face_recognizer.register_face(username, face_image)
        
        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create or get user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.com'}
        )
        
        if created:
            user.set_password(password)
            user.save()
        
        # Update profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.has_face_registered = True
        profile.save()
        
        return Response({
            'success': True,
            'message': message,
            'user_id': user.id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Face registration error: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def face_login(request):
    """Authenticate user via face recognition"""
    try:
        face_image = request.data.get('face_image')
        
        if not face_image:
            return Response({'error': 'Face image required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        print("Authenticating face...")
        
        # Authenticate face
        username, message = face_recognizer.authenticate_face(face_image)
        
        if username:
            try:
                user = User.objects.get(username=username)
                login(request, user)
                
                print(f"✅ Face authenticated: {username}")
                
                return Response({
                    'success': True,
                    'message': f'Welcome {username}!',
                    'user': username
                }, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                pass
        
        return Response({
            'success': False,
            'message': 'Face not recognized. Please register first.'
        }, status=status.HTTP_401_UNAUTHORIZED)
        
    except Exception as e:
        logger.error(f"Face login error: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)