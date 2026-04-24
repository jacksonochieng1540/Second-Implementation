from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from .models import UserProfile
import base64
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class FaceAuthenticationBackend(ModelBackend):
    def authenticate(self, request, face_image=None, **kwargs):
        if not face_image:
            return None
            
        try:
            # Decode base64 image
            image_data = base64.b64decode(face_image.split(',')[1])
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Load OpenCV's face detector
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            # Detect faces
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
            
            if len(faces) > 0:
                # For development, return or create test user
                test_user, created = User.objects.get_or_create(
                    username='testuser',
                    defaults={
                        'email': 'test@example.com'
                    }
                )
                if created:
                    test_user.set_password('testpass123')
                    test_user.save()
                    print(f"Created test user: {test_user.username}")
                
                print(f"Authenticated as: {test_user.username}")
                return test_user
            else:
                print("No face detected")
            
        except Exception as e:
            logger.error(f"Face authentication error: {e}")
            print(f"Auth error: {e}")
            
        return None
        
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None