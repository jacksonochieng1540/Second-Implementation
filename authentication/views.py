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
    """TRAIN the system with a new face"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        face_image = request.data.get('face_image')
        
        if not all([username, password, face_image]):
            return Response({'error': 'All fields required'}, status=400)
        
        # Train the system with this face
        success, message = face_recognizer.train_new_face(username, face_image)
        
        if not success:
            return Response({'error': message}, status=400)
        
        # Create user account
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.com'}
        )
        
        if created:
            user.set_password(password)
            user.save()
        
        return Response({
            'success': True,
            'message': message,
            'user_id': user.id
        }, status=200)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def face_login(request):
    """RECOGNIZE face - compares with trained faces"""
    try:
        face_image = request.data.get('face_image')
        
        if not face_image:
            return Response({'error': 'Face image required'}, status=400)
        
        # Recognize the face
        result, username, confidence = face_recognizer.recognize_face(face_image)
        
        if result == 'RECOGNIZED':
            user = User.objects.get(username=username)
            login(request, user)
            
            return Response({
                'success': True,
                'message': f'Welcome {username}! Face recognized.',
                'user': username,
                'confidence': confidence
            }, status=200)
        
        elif result == 'NO_FACE':
            return Response({
                'success': False,
                'message': 'No face detected. Please look at the camera.',
                'result': 'NO_FACE'
            }, status=200)
        
        else:  # UNREGISTERED
            return Response({
                'success': False,
                'message': 'Face not recognized. Unregistered user detected.',
                'result': 'UNREGISTERED'
            }, status=401)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)