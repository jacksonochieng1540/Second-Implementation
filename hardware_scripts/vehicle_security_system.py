#!/usr/bin/env python3
"""
Complete Vehicle Security System for Raspberry Pi
Implements: Face Recognition, GPS Tracking, Relay Control, GSM Alerts
"""

import requests
import time
import json
import base64
import cv2
import numpy as np
import RPi.GPIO as GPIO
import serial
import gpsd
import hashlib
from datetime import datetime
import threading
import queue
import logging

# ============= CONFIGURATION =============
API_BASE_URL = "http://your-server-ip:8000"  # Replace with your cloud server IP
API_KEY = "your-hardware-api-key-2024"
RELAY_PIN = 17  # GPIO pin for engine relay
CAMERA_DEVICE = 0  # USB camera device
GPS_UPDATE_INTERVAL = 3  # seconds
COMMAND_POLL_INTERVAL = 2  # seconds
INTRUDER_CHECK_INTERVAL = 10  # seconds
GSM_PORT = '/dev/ttyUSB0'  # USB GSM module
OWNER_PHONE = '+254700000000'  # Replace with owner's phone number

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= HARDWARE SETUP =============
class VehicleHardware:
    def __init__(self):
        self.engine_locked = True
        self.current_location = None
        self.setup_gpio()
        self.setup_gps()
        self.setup_gsm()
        self.setup_camera()
        
    def setup_gpio(self):
        """Setup GPIO for relay control"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(RELAY_PIN, GPIO.OUT)
            GPIO.output(RELAY_PIN, GPIO.LOW)  # Engine locked by default
            logger.info("✓ GPIO configured - Engine LOCKED")
        except Exception as e:
            logger.error(f"GPIO setup error: {e}")
    
    def setup_gps(self):
        """Setup GPS module"""
        try:
            gpsd.connect()
            logger.info("✓ GPS module connected")
        except Exception as e:
            logger.warning(f"GPS not available: {e}")
    
    def setup_gsm(self):
        """Setup GSM module for SMS"""
        self.gsm_available = False
        try:
            self.gsm = serial.Serial(GSM_PORT, 9600, timeout=1)
            time.sleep(2)
            self.gsm.write(b'AT\r\n')
            if b'OK' in self.gsm.read(100):
                self.gsm_available = True
                logger.info("✓ GSM module connected")
            else:
                logger.warning("GSM module not responding")
        except Exception as e:
            logger.warning(f"GSM not available: {e}")
    
    def setup_camera(self):
        """Setup camera for face recognition"""
        try:
            self.camera = cv2.VideoCapture(CAMERA_DEVICE)
            if self.camera.isOpened():
                logger.info("✓ Camera initialized")
            else:
                logger.warning("Camera not available")
                self.camera = None
        except Exception as e:
            logger.warning(f"Camera error: {e}")
            self.camera = None
    
    def lock_engine(self):
        """Lock the engine (immobilize vehicle)"""
        try:
            GPIO.output(RELAY_PIN, GPIO.LOW)
            self.engine_locked = True
            logger.info("🔒 Engine LOCKED - Vehicle immobilized")
            return True
        except Exception as e:
            logger.error(f"Lock engine error: {e}")
            return False
    
    def unlock_engine(self):
        """Unlock the engine (allow vehicle operation)"""
        try:
            GPIO.output(RELAY_PIN, GPIO.HIGH)
            self.engine_locked = False
            logger.info("🔓 Engine UNLOCKED - Vehicle operational")
            return True
        except Exception as e:
            logger.error(f"Unlock engine error: {e}")
            return False
    
    def get_gps_location(self):
        """Get current GPS coordinates"""
        try:
            packet = gpsd.get_current()
            if packet.mode >= 2:  # 2D or 3D fix
                location = {
                    'latitude': packet.lat,
                    'longitude': packet.lon,
                    'speed': packet.hspeed * 3.6,  # Convert to km/h
                    'heading': packet.track,
                    'altitude': packet.alt,
                    'satellites': packet.sats,
                    'timestamp': datetime.now().isoformat()
                }
                self.current_location = location
                return location
        except Exception as e:
            logger.debug(f"GPS error: {e}")
        
        return self.current_location
    
    def capture_face(self):
        """Capture face image for authentication"""
        if self.camera is None:
            return None
        
        try:
            ret, frame = self.camera.read()
            if ret:
                # Detect face using OpenCV
                face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
                
                if len(faces) > 0:
                    # Get the largest face
                    (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
                    face_roi = frame[y:y+h, x:x+w]
                    
                    # Encode to base64
                    _, buffer = cv2.imencode('.jpg', face_roi)
                    return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            logger.error(f"Face capture error: {e}")
        
        return None
    
    def send_sms(self, message):
        """Send SMS alert via GSM"""
        if not self.gsm_available:
            logger.info(f"[SIMULATED SMS] {message}")
            return True
        
        try:
            self.gsm.write(b'AT+CMGF=1\r\n')
            time.sleep(0.5)
            self.gsm.write(f'AT+CMGS="{OWNER_PHONE}"\r\n'.encode())
            time.sleep(0.5)
            self.gsm.write(f'{message}\x1A'.encode())
            logger.info(f"SMS sent: {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"SMS error: {e}")
            return False
    
    def cleanup(self):
        """Cleanup hardware resources"""
        try:
            self.lock_engine()  # Lock engine on shutdown
            if self.camera:
                self.camera.release()
            GPIO.cleanup()
            logger.info("Hardware cleanup complete")
        except:
            pass

# ============= CLOUD COMMUNICATION =============
class CloudCommunicator:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    
    def send_location(self, location):
        """Send GPS location to cloud"""
        try:
            response = requests.post(
                f"{self.api_url}/hardware/location/",
                headers=self.headers,
                json=location,
                timeout=5
            )
            if response.status_code == 200:
                logger.debug(f"Location sent: {location['latitude']:.4f}, {location['longitude']:.4f}")
                return True
        except Exception as e:
            logger.error(f"Send location error: {e}")
        return False
    
    def get_command(self):
        """Get pending command from cloud"""
        try:
            response = requests.get(
                f"{self.api_url}/hardware/get-command/",
                headers=self.headers,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('command') != 'NONE':
                    return data
        except Exception as e:
            logger.error(f"Get command error: {e}")
        return None
    
    def mark_command_executed(self, command_id):
        """Mark command as executed"""
        try:
            response = requests.post(
                f"{self.api_url}/hardware/mark-executed/",
                headers=self.headers,
                json={'command_id': command_id},
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Mark executed error: {e}")
        return False
    
    def authenticate_face(self, face_image):
        """Authenticate face via cloud"""
        try:
            response = requests.post(
                f"{self.api_url}/api/face-auth/",
                headers=self.headers,
                json={'face_image': f"data:image/jpeg;base64,{face_image}"},
                timeout=5
            )
            if response.status_code == 200:
                return response.json().get('success', False)
        except Exception as e:
            logger.error(f"Face auth error: {e}")
        return False
    
    def send_alert(self, title, description, severity='HIGH', location=None):
        """Send alert to cloud"""
        try:
            alert_data = {
                'title': title,
                'description': description,
                'severity': severity,
                'location': location or self.current_location
            }
            response = requests.post(
                f"{self.api_url}/api/alerts/create/",
                headers=self.headers,
                json=alert_data,
                timeout=5
            )
            return response.status_code == 201
        except Exception as e:
            logger.error(f"Send alert error: {e}")
        return False

# ============= MAIN SYSTEM =============
class VehicleSecuritySystem:
    def __init__(self):
        self.hardware = VehicleHardware()
        self.cloud = CloudCommunicator(API_BASE_URL, API_KEY)
        self.running = True
        self.command_queue = queue.Queue()
        
    def run(self):
        """Main system loop"""
        logger.info("=" * 50)
        logger.info("🚗 VEHICLE SECURITY SYSTEM STARTED")
        logger.info(f"Cloud Server: {API_BASE_URL}")
        logger.info(f"Relay Pin: GPIO{RELAY_PIN}")
        logger.info("=" * 50)
        
        # Start background threads
        self.start_threads()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.running = False
            self.hardware.cleanup()
    
    def start_threads(self):
        """Start all background threads"""
        threads = [
            threading.Thread(target=self.gps_loop, daemon=True),
            threading.Thread(target=self.command_loop, daemon=True),
            threading.Thread(target=self.intruder_detection_loop, daemon=True),
        ]
        for thread in threads:
            thread.start()
    
    def gps_loop(self):
        """Continuous GPS tracking loop"""
        while self.running:
            location = self.hardware.get_gps_location()
            if location:
                self.cloud.send_location(location)
            time.sleep(GPS_UPDATE_INTERVAL)
    
    def command_loop(self):
        """Poll for remote commands"""
        while self.running:
            command_data = self.cloud.get_command()
            if command_data:
                command = command_data.get('command')
                command_id = command_data.get('command_id')
                
                if command == 'UNLOCK':
                    success = self.hardware.unlock_engine()
                    if success:
                        self.cloud.mark_command_executed(command_id)
                        self.send_alert_sms("VEHICLE UNLOCKED", "Your vehicle has been unlocked remotely")
                elif command == 'LOCK':
                    success = self.hardware.lock_engine()
                    if success:
                        self.cloud.mark_command_executed(command_id)
                        self.send_alert_sms("VEHICLE LOCKED", "Your vehicle has been locked remotely")
            
            time.sleep(COMMAND_POLL_INTERVAL)
    
    def intruder_detection_loop(self):
        """Check for unauthorized access attempts"""
        last_alert_time = 0
        consecutive_failures = 0
        
        while self.running:
            if self.hardware.engine_locked:  # Only check when locked
                face_image = self.hardware.capture_face()
                
                if face_image:
                    is_authorized = self.cloud.authenticate_face(face_image)
                    
                    if is_authorized:
                        logger.info("✅ Authorized user detected - Unlocking engine")
                        self.hardware.unlock_engine()
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        logger.warning(f"⚠️ Unauthorized access attempt #{consecutive_failures}")
                        
                        # Send alert on every 3rd failure
                        if consecutive_failures >= 3:
                            current_time = time.time()
                            if current_time - last_alert_time > 60:  #  1 alert per minute
                                self.handle_intruder_alert()
                                last_alert_time = current_time
                                consecutive_failures = 0
            
            time.sleep(INTRUDER_CHECK_INTERVAL)
    
    def handle_intruder_alert(self):
        """Handle unauthorized access attempt"""
        location = self.hardware.current_location
        
        # Create alert in cloud
        self.cloud.send_alert(
            title="UNAUTHORIZED ACCESS ATTEMPT",
            description=f"An unauthorized person attempted to access your vehicle at {location}",
            severity="HIGH",
            location=location
        )
        
        # Send SMS alert
        sms_message = f"ALERT! Unauthorized access attempt on your vehicle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.hardware.send_sms(sms_message)
        
        # Also send via HTTP API fallback
        self.send_http_alert(sms_message)
    
    def send_alert_sms(self, title, message):
        """Send SMS alert for system events"""
        sms_message = f"{title}: {message} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.hardware.send_sms(sms_message)
    
    def send_http_alert(self, message):
        """Fallback HTTP alert using SMS gateway API"""
        try:
            # You can integrate with Twilio, MessageBird, or other SMS APIs
            # Example with a generic SMS gateway:
            response = requests.post(
                "https://api.smsgateway.com/send",
                json={
                    "to": OWNER_PHONE,
                    "message": message,
                    "api_key": "your-sms-gateway-api-key"
                },
                timeout=5
            )
            logger.info(f"HTTP SMS sent: {response.status_code}")
        except:
            pass


if __name__ == "__main__":
    system = VehicleSecuritySystem()
    system.run()