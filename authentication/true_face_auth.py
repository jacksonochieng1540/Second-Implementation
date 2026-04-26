"""
True Face Authentication - Only registered faces can unlock
Stores face encodings and compares them
"""

import face_recognition
import cv2
import numpy as np
import base64
import json
import os
from pathlib import Path
from datetime import datetime

class TrueFaceAuth:
    def __init__(self):
        self.faces_dir = Path('registered_faces')
        self.faces_dir.mkdir(exist_ok=True)
        self.encodings_file = self.faces_dir / 'face_encodings.json'
        self.load_encodings()
        print("="*50)
        print("🔐 TRUE FACE AUTHENTICATION SYSTEM")
        print(f"   Registered users: {len(self.known_names)}")
        print("="*50)
    
    def load_encodings(self):
        """Load registered face encodings"""
        self.known_encodings = []
        self.known_names = []
        
        if self.encodings_file.exists():
            try:
                with open(self.encodings_file, 'r') as f:
                    data = json.load(f)
                    self.known_encodings = [np.array(enc) for enc in data['encodings']]
                    self.known_names = data['names']
                print(f"✅ Loaded {len(self.known_names)} registered faces")
            except Exception as e:
                print(f"⚠️ Error loading: {e}")
    
    def save_encodings(self):
        """Save face encodings to file"""
        data = {
            'encodings': [enc.tolist() for enc in self.known_encodings],
            'names': self.known_names,
            'created_at': datetime.now().isoformat()
        }
        with open(self.encodings_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💾 Saved {len(self.known_names)} face encodings")
    
    def extract_face_encoding(self, image_base64):
        """
        Extract 128-point face encoding from image
        This is the UNIQUE mathematical representation of a face
        """
        try:
            # Decode base64 image
            if ',' in image_base64:
                image_data = base64.b64decode(image_base64.split(',')[1])
            else:
                image_data = base64.b64decode(image_base64)
            
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None, "Invalid image"
            
            # Convert to RGB (face_recognition uses RGB)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(rgb_img)
            
            if len(face_locations) == 0:
                return None, "No face detected. Please look at camera."
            
            # Get face encoding (128-dimensional vector - UNIQUE PER FACE)
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
            
            if len(face_encodings) == 0:
                return None, "Could not extract face features"
            
            print(f"📸 Face encoding extracted (128 points)")
            return face_encodings[0], "Face detected"
            
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def register_face(self, username, image_base64):
        """
        Register a new face - stores the UNIQUE face encoding
        Only this specific face will be recognized later
        """
        face_encoding, message = self.extract_face_encoding(image_base64)
        
        if face_encoding is None:
            return False, message
        
        # Remove existing registration for this user (if any)
        if username in self.known_names:
            idx = self.known_names.index(username)
            del self.known_encodings[idx]
            del self.known_names[idx]
        
        # Add new face encoding
        self.known_encodings.append(face_encoding)
        self.known_names.append(username)
        self.save_encodings()
        
        print(f"✅ Face REGISTERED for: {username}")
        print(f"   This face will now be recognized for unlocking")
        
        return True, f"Face registered for {username}"
    
    def authenticate_face(self, image_base64, tolerance=0.6):
        """
        Authenticate a face - compares with registered faces
        Returns: (username, confidence, message) or (None, 0, message)
        """
        face_encoding, message = self.extract_face_encoding(image_base64)
        
        if face_encoding is None:
            return None, 0, message
        
        if len(self.known_encodings) == 0:
            return None, 0, "No registered faces. Please register first."
        
        # COMPARE with all registered faces
        # This is the key step - it compares the 128-point vectors
        matches = face_recognition.compare_faces(
            self.known_encodings, 
            face_encoding, 
            tolerance=tolerance
        )
        
        # Calculate face distances (lower = more similar)
        face_distances = face_recognition.face_distance(
            self.known_encodings, 
            face_encoding
        )
        
        # Print comparison results
        print("\n🔍 FACE COMPARISON RESULTS:")
        print("-" * 40)
        for i, (name, match, distance) in enumerate(zip(self.known_names, matches, face_distances)):
            confidence = (1 - distance) * 100
            status = "✅ MATCH" if match else "❌ NO MATCH"
            print(f"   {status}: {name} (confidence: {confidence:.1f}%)")
        print("-" * 40)
        
        # Find the best match
        if True in matches:
            # Get the index of the matching face
            match_index = matches.index(True)
            username = self.known_names[match_index]
            confidence = (1 - face_distances[match_index]) * 100
            
            print(f"\n✅✅✅ AUTHENTICATED: {username} with {confidence:.1f}% confidence")
            return username, confidence, f"Welcome {username}! ({confidence:.1f}%)"
        
        # No match found
        if len(face_distances) > 0:
            closest_index = np.argmin(face_distances)
            closest_name = self.known_names[closest_index]
            closest_confidence = (1 - face_distances[closest_index]) * 100
            print(f"\n❌ ACCESS DENIED: Face not recognized")
            print(f"   Closest match was {closest_name} ({closest_confidence:.1f}%)")
            return None, closest_confidence, f"Face not recognized (closest: {closest_name})"
        
        return None, 0, "Face not recognized"
    
    def delete_user(self, username):
        """Delete a registered user"""
        if username in self.known_names:
            idx = self.known_names.index(username)
            del self.known_encodings[idx]
            del self.known_names[idx]
            self.save_encodings()
            return True
        return False
    
    def get_all_users(self):
        """Get all registered users"""
        return self.known_names.copy()

# Create global instance
face_auth = TrueFaceAuth()