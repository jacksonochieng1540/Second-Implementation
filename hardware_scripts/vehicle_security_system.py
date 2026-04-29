#!/usr/bin/env python3
"""
Complete Vehicle Security System for Raspberry Pi
Works with web dashboard - Controls relay via GPIO27
Includes intruder image capture and alert
"""

import requests
import time
import json
import base64
import cv2
import numpy as np
import RPi.GPIO as GPIO
import gpsd
import serial
from datetime import datetime
import threading
import logging
import math

# ============= CONFIGURATION - CHANGE THESE =============
API_BASE_URL = "http://10.251.159.57:8000"  # YOUR LAPTOP IP ADDRESS
API_KEY = "mysecurekey123"  # Must match Django settings
RELAY_PIN = 27  # GPIO27 (Physical pin 13)
CAMERA_DEVICE = 0
GPS_UPDATE_INTERVAL = 3
COMMAND_POLL_INTERVAL = 2
INTRUDER_CHECK_INTERVAL = 5  # Check every 5 seconds
GSM_PORT = '/dev/ttyUSB0'
OWNER_PHONE = "+254792333250"  # YOUR PHONE NUMBER

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
        self.gsm_available = False
        self.camera = None
        self.sim_angle = 0  # For simulated GPS
        
        self.setup_gpio()
        self.setup_gps()
        self.setup_gsm()
        self.setup_camera()
        
    def setup_gpio(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(RELAY_PIN, GPIO.OUT)
            GPIO.output(RELAY_PIN, GPIO.LOW)
            logger.info(f"✓ GPIO configured - Engine LOCKED (Pin GPIO{RELAY_PIN})")
        except Exception as e:
            logger.error(f"GPIO error: {e}")
    
    def setup_gps(self):
        try:
            gpsd.connect()
            logger.info("✓ GPS module connected")
        except Exception as e:
            logger.warning(f"GPS not available: {e}")
    
    def setup_gsm(self):
        try:
            for port in ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0']:
                try:
                    self.gsm = serial.Serial(port, 9600, timeout=1)
                    time.sleep(2)
                    self.gsm.write(b'AT\r\n')
                    if b'OK' in self.gsm.read(100):
                        self.gsm_available = True
                        logger.info(f"✓ GSM connected on {port}")
                        break
                    self.gsm.close()
                except:
                    continue
            if not self.gsm_available:
                logger.warning("GSM not found - SMS simulated")
        except Exception as e:
            logger.warning(f"GSM error: {e}")
    
    def setup_camera(self):
        try:
            self.camera = cv2.VideoCapture(CAMERA_DEVICE)
            if self.camera.isOpened():
                logger.info("✓ USB Camera ready")
            else:
                logger.warning("Camera not available")
                self.camera = None
        except Exception as e:
            logger.warning(f"Camera error: {e}")
            self.camera = None
    
    def lock_engine(self):
        try:
            GPIO.output(RELAY_PIN, GPIO.LOW)
            self.engine_locked = True
            logger.info("🔒 ENGINE LOCKED - Relay OFF")
            self.send_sms("VEHICLE LOCKED")
            return True
        except Exception as e:
            logger.error(f"Lock error: {e}")
            return False
    
    def unlock_engine(self):
        try:
            GPIO.output(RELAY_PIN, GPIO.HIGH)
            self.engine_locked = False
            logger.info("🔓 ENGINE UNLOCKED - Relay ON")
            self.send_sms("VEHICLE UNLOCKED")
            return True
        except Exception as e:
            logger.error(f"Unlock error: {e}")
            return False
    
    def get_gps_location(self):
        # Try real GPS first
        try:
            packet = gpsd.get_current()
            if packet.mode >= 2:
                return {
                    'latitude': packet.lat,
                    'longitude': packet.lon,
                    'speed': packet.hspeed * 3.6,
                    'heading': packet.track,
                    'timestamp': datetime.now().isoformat()
                }
        except:
            pass
        
        # Simulated GPS (circular movement)
        self.sim_angle += 0.03
        center_lat = -1.2864  # Nairobi
        center_lng = 36.8172
        radius = 0.008
        
        return {
            'latitude': center_lat + radius * math.sin(self.sim_angle),
            'longitude': center_lng + radius * math.cos(self.sim_angle),
            'speed': 40 + 20 * math.sin(self.sim_angle),
            'heading': (self.sim_angle * 57.3) % 360,
            'timestamp': datetime.now().isoformat()
        }
    
    def capture_face(self):
        if self.camera is None:
            logger.warning("Camera not available")
            return None
        try:
            ret, frame = self.camera.read()
            if ret:
                logger.info(f"📷 Frame captured: {frame.shape}")
                face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
                logger.info(f"👤 Faces detected: {len(faces)}")
                if len(faces) > 0:
                    (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
                    face_roi = frame[y:y+h, x:x+w]
                    _, buffer = cv2.imencode('.jpg', face_roi)
                    b64_data = base64.b64encode(buffer).decode('utf-8')
                    logger.info(f"📸 Face captured, base64 length: {len(b64_data)}")
                    return b64_data
                else:
                    logger.info("No faces detected in frame")
            else:
                logger.warning("Failed to read frame")
        except Exception as e:
            logger.error(f"Face capture error: {e}")
        return None
    
    def send_sms(self, message):
        if self.gsm_available:
            try:
                self.gsm.write(b'AT+CMGF=1\r\n')
                time.sleep(0.5)
                self.gsm.write(f'AT+CMGS="{OWNER_PHONE}"\r\n'.encode())
                time.sleep(0.5)
                self.gsm.write(f'{message}\x1A'.encode())
                logger.info(f"SMS sent: {message}")
            except:
                logger.info(f"[SIMULATED SMS] {message}")
        else:
            logger.info(f"[SIMULATED SMS] {message}")
        return True
    
    def cleanup(self):
        try:
            self.lock_engine()
            if self.camera:
                self.camera.release()
            GPIO.cleanup()
        except:
            pass

# ============= CLOUD COMMUNICATION =============
class CloudCommunicator:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    
    def send_location(self, location):
        if not location:
            return False
        try:
            response = requests.post(
                f"{self.api_url}/hardware/location/",
                headers=self.headers,
                json=location,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def get_command(self):
        try:
            response = requests.get(
                f"{self.api_url}/hardware/get-command/",
                headers={'X-API-KEY': self.api_key},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('command') != 'NONE':
                    logger.info(f"📡 Command received: {data.get('command')} (ID: {data.get('command_id')})")
                    return data
        except Exception as e:
            logger.debug(f"Command poll error: {e}")
        return None
    
    def mark_executed(self, command_id):
        try:
            response = requests.post(
                f"{self.api_url}/hardware/mark-executed/",
                headers=self.headers,
                json={'command_id': command_id},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def authenticate_face(self, face_image):
        try:
            response = requests.post(
                f"{self.api_url}/api/face-auth/",
                headers={'Content-Type': 'application/json'},
                json={'face_image': f"data:image/jpeg;base64,{face_image}"},
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False), result
        except:
            pass
        return False, None
    
    def send_intruder_alert(self, face_image):
        """Send intruder alert with captured face image"""
        try:
            if not face_image:
                logger.error("❌ No face image to send")
                return False
            
            logger.info(f"📸 Preparing to send intruder alert")
            logger.info(f"   Image length: {len(face_image)} characters")
            logger.info(f"   Image starts with: {face_image[:50]}...")
            
            # Ensure the image has data URL prefix
            if not face_image.startswith('data:image'):
                face_image_with_prefix = f"data:image/jpeg;base64,{face_image}"
                logger.info(f"   Added data URL prefix")
            else:
                face_image_with_prefix = face_image
            
            alert_data = {
                'title': 'UNAUTHORIZED ACCESS ATTEMPT',
                'description': f'Unknown person attempted to access vehicle at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'severity': 'HIGH',
                'face_image': face_image_with_prefix
            }
            
            logger.info(f"📤 Sending POST to {self.api_url}/api/alerts/create/")
            logger.info(f"   Alert data size: {len(str(alert_data))} bytes")
            
            response = requests.post(
                f"{self.api_url}/api/alerts/create/",
                headers=self.headers,
                json=alert_data,
                timeout=15
            )
            
            logger.info(f"📥 Response status: {response.status_code}")
            logger.info(f"   Response body: {response.text[:200]}")
            
            if response.status_code == 201:
                result = response.json()
                logger.info(f"✅ Alert {result.get('id')} created, image saved: {result.get('image_saved')}")
                return True
            else:
                logger.error(f"❌ Alert failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Send intruder alert error: {e}")
            import traceback
            traceback.print_exc()
            return False

# ============= MAIN SYSTEM =============
class VehicleSecuritySystem:
    def __init__(self):
        self.hardware = VehicleHardware()
        self.cloud = CloudCommunicator(API_BASE_URL, API_KEY)
        self.running = True
        
    def command_loop(self):
        while self.running:
            command_data = self.cloud.get_command()
            if command_data:
                command = command_data.get('command')
                command_id = command_data.get('command_id')
                
                if command == 'UNLOCK':
                    logger.info("🔓 Executing UNLOCK...")
                    if self.hardware.unlock_engine():
                        self.cloud.mark_executed(command_id)
                        logger.info(f"✅ Command {command_id} marked as executed")
                elif command == 'LOCK':
                    logger.info("🔒 Executing LOCK...")
                    if self.hardware.lock_engine():
                        self.cloud.mark_executed(command_id)
                        logger.info(f"✅ Command {command_id} marked as executed")
            
            time.sleep(COMMAND_POLL_INTERVAL)
    
    def gps_loop(self):
        while self.running:
            location = self.hardware.get_gps_location()
            if location:
                self.cloud.send_location(location)
            time.sleep(GPS_UPDATE_INTERVAL)
    
    def intruder_loop(self):
        """Check for unauthorized access and capture intruder images"""
        last_alert_time = 0
        
        while self.running:
            if self.hardware.engine_locked:
                face_image = self.hardware.capture_face()
                
                if face_image:
                    logger.info(f"📸 Face captured, length: {len(face_image)} bytes")
                    
                    # Authenticate face with cloud
                    is_authorized, result = self.cloud.authenticate_face(face_image)
                    
                    if is_authorized:
                        logger.info("✅ Authorized face detected - UNLOCKING")
                        self.hardware.unlock_engine()
                    else:
                        logger.warning("⚠️ Unauthorized face detected - Sending alert with image")
                        
                        # Send alert with image (rate limited to once per 30 seconds)
                        current_time = time.time()
                        if current_time - last_alert_time > 30:
                            logger.info("📸 Sending intruder alert with captured image...")
                            self.cloud.send_intruder_alert(face_image)
                            self.hardware.send_sms("🚨 ALERT! Unauthorized access attempt on your vehicle!")
                            last_alert_time = current_time
            time.sleep(INTRUDER_CHECK_INTERVAL)
    
    def run(self):
        logger.info("=" * 60)
        logger.info("🚗 VEHICLE SECURITY SYSTEM STARTED")
        logger.info(f"Cloud Server: {API_BASE_URL}")
        logger.info(f"Relay Pin: GPIO{RELAY_PIN}")
        logger.info("=" * 60)
        
        # Start threads
        threads = [
            threading.Thread(target=self.gps_loop, daemon=True),
            threading.Thread(target=self.command_loop, daemon=True),
            threading.Thread(target=self.intruder_loop, daemon=True),
        ]
        for t in threads:
            t.start()
        
        logger.info("✅ All systems operational")
        logger.info("📡 Waiting for commands from cloud...")
        logger.info("👤 Intruder detection active - unauthorized faces will be captured")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()
    
    def cleanup(self):
        self.running = False
        self.hardware.cleanup()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    # Test cloud connection
    try:
        test = requests.get(f"{API_BASE_URL}/api/face-auth/", timeout=3)
        logger.info(f"✅ Cloud server reachable at {API_BASE_URL}")
    except Exception as e:
        logger.warning(f"⚠️ Cannot reach cloud server at {API_BASE_URL}: {e}")
    
    system = VehicleSecuritySystem()
    system.run()