#!/usr/bin/env python3
"""
Complete Vehicle Security System for Raspberry Pi
Works with web dashboard - Controls relay via GPIO27
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

# ============= CONFIGURATION - CHANGE THESE =============
API_BASE_URL = "http://10.251.159.57:8000"  # YOUR LAPTOP IP ADDRESS
API_KEY = "mysecurekey123"  # Must match Django settings
RELAY_PIN = 27  # GPIO27 (Physical pin 13) - the pin that worked in your test
CAMERA_DEVICE = 0
GPS_UPDATE_INTERVAL = 3
COMMAND_POLL_INTERVAL = 2
INTRUDER_CHECK_INTERVAL = 10
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
        return self.current_location
    
    def capture_face(self):
        if self.camera is None:
            return None
        try:
            ret, frame = self.camera.read()
            if ret:
                face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
                if len(faces) > 0:
                    (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
                    face_roi = frame[y:y+h, x:x+w]
                    _, buffer = cv2.imencode('.jpg', face_roi)
                    return base64.b64encode(buffer).decode('utf-8')
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
                return response.json().get('success', False)
        except:
            pass
        return False
    
    def send_alert(self, title, description, severity='HIGH'):
        try:
            requests.post(
                f"{self.api_url}/api/alerts/create/",
                headers=self.headers,
                json={'title': title, 'description': description, 'severity': severity},
                timeout=5
            )
        except:
            pass

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
        consecutive = 0
        while self.running:
            if self.hardware.engine_locked:
                face = self.hardware.capture_face()
                if face:
                    if self.cloud.authenticate_face(face):
                        logger.info("✅ Authorized face detected - UNLOCKING")
                        self.hardware.unlock_engine()
                        consecutive = 0
                    else:
                        consecutive += 1
                        logger.warning(f"⚠️ Unauthorized attempt #{consecutive}")
                        if consecutive >= 3:
                            self.cloud.send_alert(
                                "UNAUTHORIZED ACCESS",
                                "Unknown person attempted to access vehicle",
                                "HIGH"
                            )
                            self.hardware.send_sms("🚨 ALERT! Unauthorized access attempt!")
                            consecutive = 0
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