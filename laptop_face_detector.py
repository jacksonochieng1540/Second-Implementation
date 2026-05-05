#!/usr/bin/env python3
"""
LAPTOP FACE DETECTOR - Uses laptop's built-in webcam
Sends intruder alerts to Raspberry Pi
"""

import cv2
import requests
import base64
import time

# ============= CONFIGURATION =============
PI_API_URL = "http://10.251.159.168:5000"  # Raspberry Pi IP
DJANGO_URL = "http://127.0.0.1:8000"
API_KEY = "mysecurekey123"

print("="*60)
print("LAPTOP FACE DETECTOR - Using built-in webcam")
print("="*60)

# Open laptop webcam
print("Opening laptop webcam...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Cannot open laptop webcam at index 0")
    print("Trying index 1...")
    cap = cv2.VideoCapture(1)
    
if not cap.isOpened():
    print("❌ Cannot open laptop webcam!")
    exit()

print("✅ Laptop webcam opened successfully!")

def authenticate_face(face_b64):
    """Authenticate face with Django"""
    try:
        response = requests.post(
            f"{DJANGO_URL}/api/face-auth/",
            json={'face_image': f"data:image/jpeg;base64,{face_b64}"},
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Auth error: {e}")
        return False

def send_intruder_alert_to_pi():
    """Tell Raspberry Pi to send intruder SMS"""
    try:
        response = requests.post(
            f"{PI_API_URL}/intruder-alert",
            headers={'X-API-KEY': API_KEY},
            timeout=3
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Cannot reach Pi: {e}")
        return False

print("\n👀 Watching for intruders with laptop webcam...")
print("Make sure you're looking at the camera!")
print("Press Ctrl+C to stop\n")

last_alert = 0
frame_count = 0

try:
    while True:
        ret, frame = cap.read()
        if ret:
            frame_count += 1
            
            # Detect faces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.02, 3, minSize=(80, 80))
            
            if len(faces) > 0:
                print(f"\n[{frame_count}] 📸 Face detected!")
                
                # Get the largest face
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                face_roi = frame[y:y+h, x:x+w]
                _, buffer = cv2.imencode('.jpg', face_roi)
                face_b64 = base64.b64encode(buffer).decode()
                
                # Authenticate with Django
                print("   Checking authorization with Django...")
                is_authorized = authenticate_face(face_b64)
                
                if is_authorized:
                    print("✅✅✅ AUTHORIZED FACE DETECTED! ✅✅✅")
                else:
                    print("🚨🚨🚨 UNAUTHORIZED FACE DETECTED! 🚨🚨🚨")
                    
                    # Rate limit to 1 SMS per 30 seconds
                    current_time = time.time()
                    if current_time - last_alert > 30:
                        print("📱 Sending intruder alert to Raspberry Pi...")
                        if send_intruder_alert_to_pi():
                            print("✅✅✅ Pi will send SMS to your phone! ✅✅✅")
                            last_alert = current_time
                        else:
                            print("❌ Could not reach Pi - make sure pi_sms_receiver.py is running")
                    else:
                        remaining = 30 - (current_time - last_alert)
                        print(f"⏰ Rate limited - next SMS in {remaining:.0f}s")
                
                # Wait before next detection
                time.sleep(2)
            else:
                # No face - show progress dot
                if frame_count % 30 == 0:
                    print(".", end="", flush=True)
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\nShutting down...")
    cap.release()
    print("✅ Done")
