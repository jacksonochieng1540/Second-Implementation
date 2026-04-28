#!/usr/bin/env python3
"""
Train face recognition model from dataset folder
Run: python train_face_model.py
"""

import face_recognition
import cv2
import pickle
import os
from pathlib import Path

def train_model():
    print("[INFO] Starting face recognition training...")
    
    # Path to dataset
    dataset_path = Path("dataset")
    
    if not dataset_path.exists():
        print("❌ Dataset folder not found!")
        print("   Create 'dataset/yourname/photo1.jpg' folders")
        return
    
    # Get all images
    image_paths = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG']:
        image_paths.extend(list(dataset_path.rglob(ext)))
    
    if len(image_paths) == 0:
        print("❌ No images found in dataset folder!")
        return
    
    known_encodings = []
    known_names = []
    
    print(f"[INFO] Processing {len(image_paths)} images...")
    
    for i, image_path in enumerate(image_paths):
        print(f"   {i+1}/{len(image_paths)}: {image_path.name}")
        
        # Get person name from folder name
        name = image_path.parent.name
        
        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        
        # Convert to RGB
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect face
        face_locations = face_recognition.face_locations(rgb)
        
        if len(face_locations) == 0:
            print(f"      ⚠️ No face detected, skipping")
            continue
        
        # Get face encoding
        face_encodings = face_recognition.face_encodings(rgb, face_locations)
        
        for encoding in face_encodings:
            known_encodings.append(encoding)
            known_names.append(name)
            print(f"      ✅ Encoded 1 face")
    
    if len(known_encodings) == 0:
        print("❌ No faces were encoded!")
        return
    
    # Save encodings
    data = {"encodings": known_encodings, "names": known_names}
    with open("encodings.pickle", "wb") as f:
        f.write(pickle.dumps(data))
    
    print(f"\n✅ Training complete!")
    print(f"   Total faces: {len(known_encodings)}")
    print(f"   Users: {', '.join(set(known_names))}")
    print(f"   Saved to: encodings.pickle")

if __name__ == "__main__":
    train_model()
