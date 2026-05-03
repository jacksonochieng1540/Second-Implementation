"""
Face Recognition Module - STRICT matching (no false positives)
"""

import face_recognition
import cv2
import numpy as np
import base64
import pickle
from pathlib import Path

class FaceRecognizer:
    def __init__(self):
        self.encodings_file = Path('encodings.pickle')
        self.known_face_encodings = []
        self.known_face_names = []
        self.load_encodings()
        print("="*50)
        print("🔐 STRICT FACE RECOGNITION SYSTEM")
        print(f"   Authorized users: {len(self.known_face_names)}")
        if self.known_face_names:
            print(f"   ONLY these faces can unlock: {', '.join(self.known_face_names)}")
        print("="*50)
    
    def load_encodings(self):
        if self.encodings_file.exists():
            try:
                with open(self.encodings_file, "rb") as f:
                    data = pickle.loads(f.read())
                    self.known_face_encodings = data["encodings"]
                    self.known_face_names = data["names"]
                print(f"✅ Loaded {len(self.known_face_names)} authorized face(s)")
            except Exception as e:
                print(f"⚠️ Error: {e}")
    
    def get_face_encoding(self, image_base64):
        try:
            if ',' in image_base64:
                image_data = base64.b64decode(image_base64.split(',')[1])
            else:
                image_data = base64.b64decode(image_base64)
            
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return None
            
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb)
            if len(face_locations) == 0:
                return None
            
            face_encodings = face_recognition.face_encodings(rgb, face_locations)
            if len(face_encodings) == 0:
                return None
            
            return face_encodings[0]
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def register_face(self, username, image_base64):
        print(f"\n📝 Registering: {username}")
        face_encoding = self.get_face_encoding(image_base64)
        if face_encoding is None:
            return False, "No face detected"
        
        # Remove old entries
        indices = [i for i, name in enumerate(self.known_face_names) if name == username]
        for idx in reversed(indices):
            del self.known_face_encodings[idx]
            del self.known_face_names[idx]
        
        self.known_face_encodings.append(face_encoding)
        self.known_face_names.append(username)
        
        data = {"encodings": self.known_face_encodings, "names": self.known_face_names}
        with open(self.encodings_file, "wb") as f:
            f.write(pickle.dumps(data))
        
        print(f"✅ Registered: {username}")
        return True, f"Registered {username}"
    
    def authenticate_face(self, image_base64, tolerance=0.5):
        """
        STRICT authentication - ONLY returns match if distance is very low
        Returns: (username, confidence, message) or (None, 0, message)
        """
        print(f"\n🔍 STRICT AUTHENTICATION")
        print("-" * 40)
        
        face_encoding = self.get_face_encoding(image_base64)
        if face_encoding is None:
            print("📷 NO_FACE")
            return None, 0, "NO_FACE"
        
        if len(self.known_face_encodings) == 0:
            print("📷 NOT_RECOGNIZED - No authorized users")
            return None, 0, "NOT_RECOGNIZED - No registered faces"
        
        # Calculate distances to all known faces
        distances = []
        for known_encoding in self.known_face_encodings:
            distance = np.linalg.norm(known_encoding - face_encoding)
            distances.append(distance)
        
        # Find best match
        best_idx = np.argmin(distances)
        best_distance = distances[best_idx]
        best_name = self.known_face_names[best_idx]
        confidence = (1 - min(best_distance, 1.0)) * 100
        
        print(f"\n   Best match: {best_name}")
        print(f"   Distance: {best_distance:.4f}")
        print(f"   Confidence: {confidence:.1f}%")
        print(f"   Required: distance < {tolerance} to authorize")
        
        # Print all comparisons for debugging
        print("\n   All comparisons:")
        for i, (name, dist) in enumerate(zip(self.known_face_names, distances)):
            conf = (1 - min(dist, 1.0)) * 100
            match_status = "✅" if dist < tolerance else "❌"
            print(f"   {match_status} {name}: distance={dist:.4f}, confidence={conf:.1f}%")
        
        # STRICT CHECK - ONLY authorize if distance is very small
        if best_distance < tolerance:
            print(f"\n✅✅✅ AUTHORIZED: {best_name} ({confidence:.1f}% confidence)")
            return best_name, confidence, f"Welcome back {best_name}!"
        else:
            print(f"\n❌ DENIED: Face does not match any authorized user")
            print(f"   (Closest match was {best_name} but distance {best_distance:.4f} > {tolerance})")
            return None, confidence, f"NOT_RECOGNIZED (closest: {best_name})"

# Create instance
face_recognizer = FaceRecognizer()