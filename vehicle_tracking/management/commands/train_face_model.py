"""
Management command to train face recognition model from dataset folder
Usage: python manage.py train_face_model
"""

import os
from django.core.management.base import BaseCommand
from imutils import paths
import face_recognition  
import pickle
from pathlib import Path
import cv2 

class Command(BaseCommand):
    help = 'Train face recognition model from dataset folder'
    
    def handle(self, *args, **options):
        self.stdout.write("[INFO] Starting face recognition training...")
        
        # Path to dataset folder
        dataset_path = Path("dataset")
        
        if not dataset_path.exists():
            self.stdout.write(self.style.ERROR("❌ Dataset folder not found!"))
            self.stdout.write("   Create 'dataset' folder with subfolders for each person")
            return
        
        imagePaths = list(paths.list_images(str(dataset_path)))
        
        if len(imagePaths) == 0:
            self.stdout.write(self.style.ERROR("❌ No images found in dataset folder!"))
            return
        
        knownEncodings = []
        knownNames = []
        
        self.stdout.write(f"[INFO] Processing {len(imagePaths)} images...")
        
        for i, imagePath in enumerate(imagePaths):
            self.stdout.write(f"   Processing {i+1}/{len(imagePaths)}")
            name = imagePath.split(os.path.sep)[-2]
            
            image = cv2.imread(imagePath)
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            boxes = face_recognition.face_locations(rgb, model="hog")
            encodings = face_recognition.face_encodings(rgb, boxes)
            
            for encoding in encodings:
                knownEncodings.append(encoding)
                knownNames.append(name)
        
        data = {"encodings": knownEncodings, "names": knownNames}
        
        with open("encodings.pickle", "wb") as f:
            f.write(pickle.dumps(data))
        
        self.stdout.write(self.style.SUCCESS(f"✅ Training complete!"))
        self.stdout.write(f"   Total faces encoded: {len(knownEncodings)}")
        self.stdout.write(f"   Unique users: {len(set(knownNames))}")
        self.stdout.write(f"   Model saved to: encodings.pickle")