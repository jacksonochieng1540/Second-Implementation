from django.shortcuts import render
from django.contrib.auth import login, authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import UserProfile
from .face_utils import face_auth
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_face(request):
    """Register a new face for a user - REAL face recognition"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        face_image = request.data.get('face_image')
        
        if not all([username, password, face_image]):
            return Response({'error': 'Username, password, and face image required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Extract face hash
        face_hash = face_auth.extract_face_hash(face_image)
        
        if face_hash is None:
            return Response({'error': 'No face detected. Please look at the camera and try again.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Check if face already registered to another user
        existing_user = face_auth.authenticate_face(face_hash)
        if existing_user and existing_user != username:
            return Response({'error': f'This face is already registered to user: {existing_user}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Create or get user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.com'}
        )
        
        if created:
            user.set_password(password)
            user.save()
            logger.info(f"New user created: {username}")
        else:
            if not user.check_password(password):
                return Response({'error': 'Invalid password for existing user'}, 
                              status=status.HTTP_401_UNAUTHORIZED)
        
        # Register the face
        face_auth.register_face(username, face_hash)
        
        # Update user profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.has_face_registered = True
        profile.save()
        
        return Response({
            'success': True,
            'message': f'Face registered successfully for user: {username}',
            'user_id': user.id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Face registration error: {e}")
        return Response({'error': str(e)}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def face_login(request):
    """Authenticate user via face recognition - REAL face matching"""
    try:
        face_image = request.data.get('face_image')
        
        if not face_image:
            return Response({'error': 'Face image required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Extract face hash from the image
        face_hash = face_auth.extract_face_hash(face_image)
        
        if face_hash is None:
            return Response({
                'success': False,
                'message': 'No face detected. Please look at the camera.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find matching user
        username = face_auth.authenticate_face(face_hash)
        
        if username:
            try:
                user = User.objects.get(username=username)
                login(request, user)
                
                # Auto unlock engine
                from api.models import VehicleCommand
                command = VehicleCommand.objects.create(
                    command='UNLOCK',
                    user=user
                )
                
                logger.info(f"✅ Face authenticated: {username} - UNLOCK command created")
                
                return Response({
                    'success': True,
                    'message': f'Welcome {username}! Engine unlocking...',
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
        return Response({'error': str(e)}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)