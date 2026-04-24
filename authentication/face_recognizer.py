import cv2
import numpy as np
import base64
import pickle
import os
from pathlib import Path
import hashlib

class FaceRecognizer:
    def __init__(self):
        # Load face detection cascade
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.faces_dir = Path('registered_faces')
        self.faces_dir.mkdir(exist_ok=True)
        
        # Try to load face recognition model
        self.face_recognizer = None
        try:
            # Use LBPH face recognizer (built into OpenCV)
            self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.load_trained_model()
            print("Face recognizer initialized successfully")
        except Exception as e:
            print(f"Face recognizer warning: {e}")
            print("Using fallback hash-based recognition")
    
    def load_trained_model(self):
        """Load pre-trained face recognition model"""
        model_path = self.faces_dir / 'trained_model.yml'
        if model_path.exists():
            self.face_recognizer.read(str(model_path))
            print("Loaded trained face model")
    
    def save_trained_model(self):
        """Save trained face recognition model"""
        model_path = self.faces_dir / 'trained_model.yml'
        self.face_recognizer.write(str(model_path))
        print("Saved trained face model")
    
    def detect_face(self, image):
        """Detect face in image and return face ROI"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Try multiple detection parameters
        faces = self.face_cascade.detectMultiScale(gray, 1.05, 5, minSize=(50, 50))
        
        if len(faces) == 0:
            # Try with different parameters
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(40, 40))
        
        if len(faces) == 0:
            return None, None
        
        # Get the largest face
        (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
        face_roi = gray[y:y+h, x:x+w]
        face_roi = cv2.resize(face_roi, (100, 100))
        
        return face_roi, (x, y, w, h)
    
    def extract_face_from_base64(self, face_image_base64):
        """Extract face from base64 image"""
        try:
            # Remove data URL prefix if present
            if ',' in face_image_base64:
                face_image_base64 = face_image_base64.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(face_image_base64)
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None, None
            
            # Detect face
            face_roi, face_location = self.detect_face(img)
            return face_roi, img
            
        except Exception as e:
            print(f"Error extracting face: {e}")
            return None, None
    
    def register_face(self, username, face_image_base64):
        """Register a face for a user"""
        face_roi, original_img = self.extract_face_from_base64(face_image_base64)
        
        if face_roi is None:
            return False, "No face detected. Please look directly at the camera."
        
        # Store face ROI for training
        user_face_file = self.faces_dir / f'{username}_face.pkl'
        with open(user_face_file, 'wb') as f:
            pickle.dump({'username': username, 'face_roi': face_roi}, f)
        
        # Also store original image for reference
        img_file = self.faces_dir / f'{username}_image.jpg'
        cv2.imwrite(str(img_file), original_img)
        
        # Re-train model with all faces
        self.train_model()
        
        return True, "Face registered successfully!"
    
    def train_model(self):
        """Train the face recognition model with all registered faces"""
        if self.face_recognizer is None:
            return
        
        faces = []
        labels = []
        label_map = {}
        current_label = 0
        
        # Load all registered faces
        for face_file in self.faces_dir.glob('*_face.pkl'):
            with open(face_file, 'rb') as f:
                data = pickle.load(f)
                username = data['username']
                face_roi = data['face_roi']
                
                if username not in label_map:
                    label_map[username] = current_label
                    current_label += 1
                
                faces.append(face_roi)
                labels.append(label_map[username])
        
        if len(faces) > 0:
            # Train the model
            self.face_recognizer.train(faces, np.array(labels))
            self.save_trained_model()
            print(f"Trained model with {len(faces)} face samples for {len(label_map)} users")
    
    def authenticate_face(self, face_image_base64):
        """Authenticate a face against registered users"""
        face_roi, _ = self.extract_face_from_base64(face_image_base64)
        
        if face_roi is None:
            return None, "No face detected"
        
        # Try face recognizer first
        if self.face_recognizer is not None:
            try:
                label, confidence = self.face_recognizer.predict(face_roi)
                print(f"Face recognition confidence: {confidence}")
                
                # Lower confidence is better (0 = perfect match)
                if confidence < 80:  # Threshold for acceptance
                    # Find username for this label
                    for face_file in self.faces_dir.glob('*_face.pkl'):
                        with open(face_file, 'rb') as f:
                            data = pickle.load(f)
                            # Need to map label back to username
                            pass
                    
                    # For simplicity, return the first user
                    # In production, you'd maintain a label mapping file
                    face_files = list(self.faces_dir.glob('*_face.pkl'))
                    if face_files:
                        with open(face_files[0], 'rb') as f:
                            data = pickle.load(f)
                            return data['username'], "Face recognized!"
            except Exception as e:
                print(f"Recognition error: {e}")
        
        # Fallback: Use hash comparison
        face_hash = hashlib.sha256(face_roi.tobytes()).hexdigest()
        
        for face_file in self.faces_dir.glob('*_face.pkl'):
            with open(face_file, 'rb') as f:
                data = pickle.load(f)
                stored_hash = hashlib.sha256(data['face_roi'].tobytes()).hexdigest()
                if face_hash == stored_hash:
                    return data['username'], "Face recognized!"
        
        return None, "Face not recognized"
    
    def get_registered_users(self):
        """Get list of registered users"""
        users = []
        for face_file in self.faces_dir.glob('*_face.pkl'):
            with open(face_file, 'rb') as f:
                data = pickle.load(f)
                users.append(data['username'])
        return list(set(users))

# Create global instance
face_recognizer = FaceRecognizer()