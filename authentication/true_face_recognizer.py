"""
True Face Recognition Module - Stores unique face encodings for authentication
"""

import face_recognition
import cv2
import numpy as np
import base64
import json
import pickle
from pathlib import Path
from datetime import datetime

class TrueFaceRecognizer:
    def __init__(self):
        self.faces_dir = Path('registered_faces')
        self.faces_dir.mkdir(exist_ok=True)
        self.encodings_file = self.faces_dir / 'face_encodings.json'
        self.load_encodings()
        print(f"🔐 True Face Recognizer initialized")
        print(f"   Registered users: {len(self.known_face_encodings)}")
    
    def load_encodings(self):
        """Load saved face encodings"""
        self.known_face_encodings = []
        self.known_face_names = []
        
        if self.encodings_file.exists():
            try:
                with open(self.encodings_file, 'r') as f:
                    data = json.load(f)
                    self.known_face_encodings = [np.array(enc) for enc in data['encodings']]
                    self.known_face_names = data['names']
                print(f"   Loaded {len(self.known_face_names)} registered faces")
            except Exception as e:
                print(f"   Error loading encodings: {e}")
    
    def save_encodings(self):
        """Save face encodings to file"""
        data = {
            'encodings': [enc.tolist() for enc in self.known_face_encodings],
            'names': self.known_face_names,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.encodings_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"   Saved {len(self.known_face_names)} face encodings")
    
    def get_face_encoding(self, image_base64):
        """Extract face encoding from base64 image"""
        try:
            # Remove data URL prefix if present
            if ',' in image_base64:
                image_data = base64.b64decode(image_base64.split(',')[1])
            else:
                image_data = base64.b64decode(image_base64)
            
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None, "Invalid image"
            
            # Convert BGR to RGB (face_recognition uses RGB)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(rgb_img)
            
            if len(face_locations) == 0:
                return None, "No face detected"
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
            
            if len(face_encodings) == 0:
                return None, "Could not encode face"
            
            return face_encodings[0], f"Face detected ({len(face_locations)} face(s))"
            
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def register_face(self, username, image_base64):
        """Register a face - stores UNIQUE face encoding"""
        face_encoding, message = self.get_face_encoding(image_base64)
        
        if face_encoding is None:
            return False, message
        
        # Check if this face already matches an existing user
        if len(self.known_face_encodings) > 0:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
            if True in matches:
                match_index = matches.index(True)
                existing_user = self.known_face_names[match_index]
                if existing_user != username:
                    return False, f"This face already belongs to user: {existing_user}"
        
        # Remove old encodings for this user
        indices_to_remove = [i for i, name in enumerate(self.known_face_names) if name == username]
        for idx in reversed(indices_to_remove):
            del self.known_face_encodings[idx]
            del self.known_face_names[idx]
        
        # Add new encoding
        self.known_face_encodings.append(face_encoding)
        self.known_face_names.append(username)
        self.save_encodings()
        
        return True, f"Face registered for {username}"
    
    def authenticate_face(self, image_base64, tolerance=0.6):
        """Authenticate face - returns username if match found"""
        face_encoding, message = self.get_face_encoding(image_base64)
        
        if face_encoding is None:
            return None, message
        
        if len(self.known_face_encodings) == 0:
            return None, "No registered faces"
        
        # Compare with known faces
        matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance)
        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
        
        print("\n🔍 Face Comparison Results:")
        for i, (name, match, distance) in enumerate(zip(self.known_face_names, matches, face_distances)):
            confidence = (1 - distance) * 100
            print(f"   {name}: match={match}, confidence={confidence:.1f}%")
        
        # Find best match
        if True in matches:
            best_idx = matches.index(True)
            username = self.known_face_names[best_idx]
            confidence = (1 - face_distances[best_idx]) * 100
            print(f"\n✅ AUTHENTICATED: {username} ({confidence:.1f}%)")
            return username, f"Welcome back {username}! ({confidence:.1f}% confidence)"
        
        # No match - provide closest match info
        if len(face_distances) > 0:
            best_idx = np.argmin(face_distances)
            best_name = self.known_face_names[best_idx]
            best_confidence = (1 - face_distances[best_idx]) * 100
            return None, f"Face not recognized. Closest match: {best_name} ({best_confidence:.1f}%)"
        
        return None, "Face not recognized"
    
    def get_all_users(self):
        """Get all registered users"""
        return list(self.known_face_names)

# Create global instance
face_recognizer = TrueFaceRecognizer()