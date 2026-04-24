"""
Face Authentication Engine using face_recognition library
Stores unique face encodings and compares them for authentication
"""

import face_recognition
import cv2
import numpy as np
import base64
import pickle
import os
import json
from pathlib import Path
from datetime import datetime

class FaceAuthenticationEngine:
    def __init__(self):
        self.faces_dir = Path('registered_faces')
        self.faces_dir.mkdir(exist_ok=True)
        self.encodings_file = self.faces_dir / 'face_encodings.json'
        self.load_encodings()
        print(f"🔐 Face Authentication Engine initialized")
        print(f"   Registered users: {len(self.known_face_encodings)}")
    
    def load_encodings(self):
        """Load saved face encodings from file"""
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
    
    def get_face_encoding_from_base64(self, image_base64):
        """
        Extract face encoding from base64 image
        Returns: face_encoding (128-dim array) or None if no face detected
        """
        try:
            # Remove data URL prefix if present
            if ',' in image_base64:
                image_data = base64.b64decode(image_base64.split(',')[1])
            else:
                image_data = base64.b64decode(image_base64)
            
            # Convert to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None, "Invalid image data"
            
            # Convert BGR to RGB (face_recognition uses RGB)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(rgb_img)
            
            if len(face_locations) == 0:
                return None, "No face detected. Please look directly at the camera."
            
            # Get face encodings (128-dimensional vector)
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
            
            if len(face_encodings) == 0:
                return None, "Could not encode face. Please ensure good lighting."
            
            # Return the first face encoding
            return face_encodings[0], f"Face detected (found {len(face_locations)} face(s))"
            
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def register_face(self, username, image_base64):
        """
        Register a new face for a user
        Returns: (success, message)
        """
        face_encoding, message = self.get_face_encoding_from_base64(image_base64)
        
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
        
        # Remove old encodings for this user (if updating)
        indices_to_remove = [i for i, name in enumerate(self.known_face_names) if name == username]
        for idx in reversed(indices_to_remove):
            del self.known_face_encodings[idx]
            del self.known_face_names[idx]
        
        # Add new encoding
        self.known_face_encodings.append(face_encoding)
        self.known_face_names.append(username)
        
        # Save to file
        self.save_encodings()
        
        # Also save a reference image
        self.save_reference_image(username, image_base64)
        
        return True, f"Face registered successfully for {username}!"
    
    def save_reference_image(self, username, image_base64):
        """Save a reference image for the user"""
        try:
            if ',' in image_base64:
                image_data = base64.b64decode(image_base64.split(',')[1])
            else:
                image_data = base64.b64decode(image_base64)
            
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            img_dir = self.faces_dir / 'images'
            img_dir.mkdir(exist_ok=True)
            
            img_file = img_dir / f'{username}.jpg'
            cv2.imwrite(str(img_file), img)
            print(f"   Saved reference image for {username}")
        except Exception as e:
            print(f"   Could not save reference image: {e}")
    
    def authenticate_face(self, image_base64, tolerance=0.6):
        """
        Authenticate a face against registered users
        Returns: (username, confidence, message) or (None, 0, message)
        """
        face_encoding, message = self.get_face_encoding_from_base64(image_base64)
        
        if face_encoding is None:
            return None, 0, message
        
        if len(self.known_face_encodings) == 0:
            return None, 0, "No registered faces. Please register first."
        
        # Compare with known faces
        matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=tolerance)
        
        # Calculate face distances (lower = better match)
        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
        
        # Print debug info
        print("\n🔍 Face Match Results:")
        for i, (name, match, distance) in enumerate(zip(self.known_face_names, matches, face_distances)):
            confidence = (1 - distance) * 100
            print(f"   {name}: match={match}, distance={distance:.4f}, confidence={confidence:.1f}%")
        
        # Find best match
        best_match_index = None
        best_distance = 1.0
        
        for i, is_match in enumerate(matches):
            distance = face_distances[i]
            if is_match and distance < best_distance:
                best_distance = distance
                best_match_index = i
        
        if best_match_index is not None:
            username = self.known_face_names[best_match_index]
            confidence = (1 - best_distance) * 100
            print(f"\n✅ AUTHENTICATED: {username} with {confidence:.1f}% confidence")
            return username, confidence, f"Welcome back {username}!"
        
        # Find closest match for feedback
        if len(face_distances) > 0:
            min_distance_index = np.argmin(face_distances)
            min_distance = face_distances[min_distance_index]
            min_confidence = (1 - min_distance) * 100
            closest_user = self.known_face_names[min_distance_index]
            print(f"\n❌ AUTHENTICATION FAILED")
            print(f"   Closest match: {closest_user} with {min_confidence:.1f}% (need >40%)")
            return None, min_confidence, f"Face not recognized. Closest match was {closest_user} ({min_confidence:.1f}%)"
        
        return None, 0, "Face not recognized. Please try again."
    
    def get_all_users(self):
        """Get list of all registered users"""
        return list(set(self.known_face_names))
    
    def delete_user(self, username):
        """Delete a registered user"""
        if username in self.known_face_names:
            indices_to_remove = [i for i, name in enumerate(self.known_face_names) if name == username]
            for idx in reversed(indices_to_remove):
                del self.known_face_encodings[idx]
                del self.known_face_names[idx]
            self.save_encodings()
            print(f"✅ Deleted user: {username}")
            
            # Delete reference image
            img_file = self.faces_dir / 'images' / f'{username}.jpg'
            if img_file.exists():
                img_file.unlink()
            
            return True
        return False

# Create global instance
face_auth_engine = FaceAuthenticationEngine()
