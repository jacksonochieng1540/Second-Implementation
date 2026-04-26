"""
COMPLETE WORKING FACE RECOGNITION
Registration and Authentication working
"""

import face_recognition
import cv2
import numpy as np
import base64
import json
from pathlib import Path

class FaceRecognizer:
    def __init__(self):
        self.encodings_file = Path('face_encodings.json')
        self.known_face_encodings = []
        self.known_face_names = []
        self.load_data()
        print("="*50)
        print("🔐 FACE RECOGNITION READY")
        print(f"   Registered: {len(self.known_face_names)} user(s)")
        print("="*50)
    
    def load_data(self):
        """Load registered faces"""
        if self.encodings_file.exists():
            try:
                with open(self.encodings_file, 'r') as f:
                    data = json.load(f)
                    self.known_face_encodings = [np.array(enc) for enc in data['encodings']]
                    self.known_face_names = data['names']
            except:
                pass
    
    def save_data(self):
        """Save registered faces"""
        data = {
            'encodings': [enc.tolist() for enc in self.known_face_encodings],
            'names': self.known_face_names
        }
        with open(self.encodings_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_encoding(self, image_base64):
        """Extract face encoding from image"""
        try:
            # Decode image
            if ',' in image_base64:
                image_data = base64.b64decode(image_base64.split(',')[1])
            else:
                image_data = base64.b64decode(image_base64)
            
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None
            
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb)
            
            if len(locations) == 0:
                return None
            
            encodings = face_recognition.face_encodings(rgb, locations)
            
            if len(encodings) == 0:
                return None
            
            return encodings[0]
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    # This is the method called by register_face in views.py
    def register_face(self, username, image_base64):
        """Register a new face"""
        print(f"\n📝 Registering: {username}")
        
        encoding = self.get_encoding(image_base64)
        
        if encoding is None:
            return False, "No face detected. Please look at the camera."
        
        # Remove old entry if exists
        for i, name in enumerate(self.known_face_names):
            if name == username:
                del self.known_face_encodings[i]
                del self.known_face_names[i]
        
        # Add new face
        self.known_face_encodings.append(encoding)
        self.known_face_names.append(username)
        self.save_data()
        
        print(f"✅ Registered: {username}")
        return True, f"Face registered for {username}"
    
    # This is the method called by face_auth in api/views.py
    def authenticate_face(self, image_base64, tolerance=0.6):
        """Authenticate a face"""
        print(f"\n🔍 Authenticating...")
        
        encoding = self.get_encoding(image_base64)
        
        # NO FACE
        if encoding is None:
            print("📷 NO_FACE")
            return 'NO_FACE', None, None
        
        # NO REGISTERED FACES
        if len(self.known_face_encodings) == 0:
            print("📷 NOT_RECOGNIZED - No registered faces")
            return 'NOT_RECOGNIZED', None, None
        
        # COMPARE
        matches = face_recognition.compare_faces(self.known_face_encodings, encoding, tolerance)
        distances = face_recognition.face_distance(self.known_face_encodings, encoding)
        
        print("   Results:")
        for i, (name, match, dist) in enumerate(zip(self.known_face_names, matches, distances)):
            conf = (1 - dist) * 100
            status = "✅" if match else "❌"
            print(f"   {status} {name}: {conf:.1f}%")
        
        # CHECK MATCH
        if True in matches:
            idx = matches.index(True)
            username = self.known_face_names[idx]
            confidence = (1 - distances[idx]) * 100
            print(f"\n✅ RECOGNIZED: {username}")
            return 'RECOGNIZED', username, confidence
        
        print(f"\n❌ NOT_RECOGNIZED - Unauthorized face")
        return 'NOT_RECOGNIZED', None, None

# Create the instance
face_recognizer = FaceRecognizer()