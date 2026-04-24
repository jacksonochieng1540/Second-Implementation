import cv2
import numpy as np
import base64
import hashlib
import pickle
import os
from pathlib import Path

class FaceAuthenticator:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.faces_dir = Path('registered_faces')
        self.faces_dir.mkdir(exist_ok=True)
        self.bypass_mode = True  # SET TO False for real face detection
        print(f"FaceAuthenticator initialized. Bypass mode: {self.bypass_mode}")
    
    def extract_face_hash(self, face_image_base64):
        """Extract face hash from base64 image"""
        
        # BYPASS MODE - Always return a fixed hash for testing
        if self.bypass_mode:
            print("BYPASS MODE: Using test hash")
            return "test_hash_12345"
        
        try:
            print(f"Processing face image...")
            
            # Decode base64 image
            if ',' in face_image_base64:
                image_data = base64.b64decode(face_image_base64.split(',')[1])
            else:
                image_data = base64.b64decode(face_image_base64)
            
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                print("Failed to decode image")
                return None
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Try multiple detection attempts
            detection_attempts = [
                (1.05, 3, (30, 30)),
                (1.1, 5, (40, 40)),
                (1.2, 3, (50, 50)),
                (1.01, 2, (20, 20))
            ]
            
            faces = []
            for scale_factor, min_neighbors, min_size in detection_attempts:
                faces = self.face_cascade.detectMultiScale(
                    gray, 
                    scaleFactor=scale_factor, 
                    minNeighbors=min_neighbors, 
                    minSize=min_size
                )
                if len(faces) > 0:
                    print(f"Face found with params: scale={scale_factor}")
                    break
            
            if len(faces) == 0:
                print("No face detected")
                return None
            
            # Get the largest face
            (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
            face_roi = gray[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, (100, 100))
            
            # Generate a hash
            face_hash = hashlib.sha256(face_roi.tobytes()).hexdigest()
            print(f"Face hash generated")
            
            return face_hash
            
        except Exception as e:
            print(f"Face extraction error: {e}")
            return None
    
    def register_face(self, username, face_hash):
        """Register a face for a user"""
        user_file = self.faces_dir / f'{username}.pkl'
        with open(user_file, 'wb') as f:
            pickle.dump({
                'username': username,
                'face_hash': face_hash,
            }, f)
        print(f"✅ Face registered for: {username}")
        return True
    
    def authenticate_face(self, face_hash):
        """Check if face hash matches any registered user"""
        if not face_hash:
            return None
        
        # BYPASS MODE - Always return the first registered user
        if self.bypass_mode:
            registered_files = list(self.faces_dir.glob('*.pkl'))
            if registered_files:
                with open(registered_files[0], 'rb') as f:
                    data = pickle.load(f)
                    print(f"BYPASS MODE: Authenticated as {data['username']}")
                    return data['username']
            return None
        
        for user_file in self.faces_dir.glob('*.pkl'):
            with open(user_file, 'rb') as f:
                data = pickle.load(f)
                if data['face_hash'] == face_hash:
                    print(f"✅ Face matched: {data['username']}")
                    return data['username']
        
        print("❌ No matching face found")
        return None
    
    def get_all_users(self):
        """Get all registered users"""
        users = []
        for user_file in self.faces_dir.glob('*.pkl'):
            with open(user_file, 'rb') as f:
                data = pickle.load(f)
                users.append(data['username'])
        return users

# Create global instance
face_auth = FaceAuthenticator()
print("Face authenticator ready!")