import face_recognition
import cv2
import numpy as np
import base64
import json
from pathlib import Path
from .true_face_recognizer import face_recognizer as face_matcher

class RealFaceMatcher:
    def __init__(self):
        self.faces_dir = Path('registered_faces')
        self.faces_dir.mkdir(exist_ok=True)
        self.encodings_file = self.faces_dir / 'encodings.json'
        self.load_encodings()
    
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
                print(f"Loaded {len(self.known_face_names)} registered faces")
            except:
                print("No existing face data found")
    
    def save_encodings(self):
        """Save face encodings to file"""
        data = {
            'encodings': [enc.tolist() for enc in self.known_face_encodings],
            'names': self.known_face_names
        }
        with open(self.encodings_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_face_encoding(self, image_base64):
        """Extract face encoding from image"""
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
            
            # Find face locations
            face_locations = face_recognition.face_locations(rgb_img)
            
            if len(face_locations) == 0:
                return None, "No face detected"
            
            # Get face encoding
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
            
            if len(face_encodings) == 0:
                return None, "Could not encode face"
            
            return face_encodings[0], "Face detected"
            
        except Exception as e:
            return None, str(e)
    
    def register_face(self, username, image_base64):
        """Register a face - stores the unique encoding"""
        face_encoding, message = self.get_face_encoding(image_base64)
        
        if face_encoding is None:
            return False, message
        
        # Check if face already exists
        if len(self.known_face_encodings) > 0:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            if True in matches:
                idx = matches.index(True)
                existing_user = self.known_face_names[idx]
                return False, f"This face already belongs to {existing_user}"
        
        # Add new face
        self.known_face_encodings.append(face_encoding)
        self.known_face_names.append(username)
        self.save_encodings()
        
        print(f"✅ Registered: {username}")
        return True, f"Face registered for {username}"
    
    def authenticate_face(self, image_base64):
        """Authenticate - checks if this face matches any registered face"""
        face_encoding, message = self.get_face_encoding(image_base64)
        
        if face_encoding is None:
            return None, message
        
        if len(self.known_face_encodings) == 0:
            return None, "No registered users"
        
        # Compare with known faces
        matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
        
        # Calculate face distances (lower = better match)
        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
        
        # Print debug info
        print("\n--- Face Match Results ---")
        for i, (name, match, distance) in enumerate(zip(self.known_face_names, matches, face_distances)):
            confidence = (1 - distance) * 100
            print(f"{name}: match={match}, confidence={confidence:.1f}%")
        
        # Find best match
        if True in matches:
            best_match_idx = matches.index(True)
            username = self.known_face_names[best_match_idx]
            confidence = (1 - face_distances[best_match_idx]) * 100
            print(f"\n✅ MATCH: {username} ({confidence:.1f}% confidence)")
            return username, f"Welcome back {username}!"
        
        # If no match, find closest for feedback
        if len(face_distances) > 0:
            best_idx = np.argmin(face_distances)
            best_name = self.known_face_names[best_idx]
            best_confidence = (1 - face_distances[best_idx]) * 100
            print(f"\n❌ NO MATCH. Closest was {best_name} ({best_confidence:.1f}%)")
            return None, f"Face not recognized. Closest match was {best_name} ({best_confidence:.1f}%)"
        
        return None, "Face not recognized"

# Create global instance
face_matcher = RealFaceMatcher()
