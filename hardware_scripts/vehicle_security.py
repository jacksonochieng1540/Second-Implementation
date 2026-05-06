#!/usr/bin/env python3
"""
Complete Vehicle Security System for Raspberry Pi
Works with web dashboard - Controls relay via GPIO27
Includes intruder image capture and alert
REAL GSM SMS using pigpio software serial
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
import pigpio
import subprocess

# ============= CONFIGURATION - CHANGE THESE =============
API_BASE_URL = "http://10.251.159.57:8000"  # YOUR LAPTOP IP ADDRESS
API_KEY = "mysecurekey123"  # Must match Django settings
RELAY_PIN = 27  # GPIO27 (Physical pin 13)
CAMERA_DEVICE = 0
GPS_UPDATE_INTERVAL = 3
COMMAND_POLL_INTERVAL = 2
INTRUDER_CHECK_INTERVAL = 5  # Check every 5 seconds
OWNER_PHONE = "+254792333250"  # YOUR PHONE NUMBER

# GSM Software Serial Pins (using pigpio)
GSM_TX_PIN = 18  # GPIO18 (Physical pin 12) - Connect to SIM800L RX
GSM_RX_PIN = 17  # GPIO17 (Physical pin 11) - Connect to SIM800L TX
GSM_BAUD = 9600

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============= GSM SOFTWARE SERIAL CLASS =============
class GSMSoftwareSerial:
    """Real GSM communication using pigpio software serial"""
    
    def __init__(self, tx_pin=18, rx_pin=17, baud=9600):
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.baud = baud
        self.pi = None
        self.is_connected = False
        self.connect()
    
    def connect(self):
        """Connect to pigpio daemon and initialize software serial"""
        try:
            # Start pigpio daemon if not running
            subprocess.run(['sudo', 'killall', 'pigpiod'], stderr=subprocess.DEVNULL)
            time.sleep(1)
            
            subprocess.run(['sudo', 'pigpiod'], stderr=subprocess.DEVNULL)
            time.sleep(2)
            
            self.pi = pigpio.pi()
            if not self.pi.connected:
                logger.error("❌ pigpio not running")
                return False
            
            # Setup pins
            self.pi.set_mode(self.tx_pin, pigpio.OUTPUT)
            self.pi.set_mode(self.rx_pin, pigpio.INPUT)
            self.pi.bb_serial_read_open(self.rx_pin, self.baud, 8)
            
            # Test GSM module
            response = self.send_command("AT\r")
            
            if b'OK' in response:
                self.is_connected = True
                logger.info(f"✅ REAL GSM connected (TX=GPIO{self.tx_pin}, RX=GPIO{self.rx_pin})")
                
                # Set SMS text mode
                self.send_command("AT+CMGF=1\r")
                time.sleep(0.5)
                
                logger.info("✅ GSM ready for SMS")
                return True
            
            self.is_connected = False
            logger.warning("⚠️ GSM not responding - SMS will be simulated")
            return False
            
        except Exception as e:
            logger.warning(f"GSM connection error: {e}")
            self.is_connected = False
            return False
    
    def send_byte(self, byte):
        """Send a single byte via software serial"""
        if not self.pi:
            return
        bits = []
        bit_duration = int(1e6 / self.baud)
        
        # Start bit (low)
        bits.append(pigpio.pulse(0, 1 << self.tx_pin, bit_duration))
        
        # Data bits (LSB first)
        for i in range(8):
            if (byte >> i) & 1:
                bits.append(pigpio.pulse(1 << self.tx_pin, 0, bit_duration))
            else:
                bits.append(pigpio.pulse(0, 1 << self.tx_pin, bit_duration))
        
        # Stop bit (high)
        bits.append(pigpio.pulse(1 << self.tx_pin, 0, bit_duration))
        
        self.pi.wave_clear()
        self.pi.wave_add_generic(bits)
        wid = self.pi.wave_create()
        self.pi.wave_send_once(wid)
        while self.pi.wave_tx_busy():
            time.sleep(0.001)
        self.pi.wave_delete(wid)
    
    def send_command(self, cmd, timeout=1):
        """Send a command and return response"""
        if not self.pi:
            return b''
        
        # Clear buffer
        self.pi.bb_serial_read(self.rx_pin)
        
        # Send command
        for byte in cmd.encode():
            self.send_byte(byte)
        time.sleep(0.5)
        
        # Read response
        count, data = self.pi.bb_serial_read(self.rx_pin)
        return data
    
    def send_sms(self, phone_number, message):
        """Send REAL SMS via GSM module"""
        if not self.is_connected:
            logger.info(f"[SIMULATED SMS] To: {phone_number}")
            logger.info(f"[SIMULATED SMS] Message: {message}")
            return True
        
        try:
            logger.info(f"📱 Sending REAL SMS to {phone_number}...")
            
            # Set SMS text mode
            self.send_command("AT+CMGF=1\r")
            time.sleep(0.5)
            
            # Send SMS command with phone number
            cmd = f'AT+CMGS="{phone_number}"\r'
            for byte in cmd.encode():
                self.send_byte(byte)
            time.sleep(1)
            
            # Send message content
            for byte in message.encode('utf-8'):
                self.send_byte(byte)
            
            # Send Ctrl+Z (0x1A) to indicate end of message
            self.send_byte(26)
            time.sleep(4)
            
            # Read response
            count, data = self.pi.bb_serial_read(self.rx_pin)
            
            if b'+CMGS' in data or b'OK' in data:
                logger.info(f"✅✅✅ REAL SMS SENT SUCCESSFULLY! ✅✅✅")
                logger.info(f"   Message: {message}")
                return True
            else:
                logger.warning(f"⚠️ SMS may not have sent. Response: {data[:100]}")
                return False
                
        except Exception as e:
            logger.error(f"SMS error: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        if self.pi:
            self.pi.bb_serial_read_close(self.rx_pin)
            self.pi.stop()


# ============= HARDWARE SETUP =============
class VehicleHardware:
    def __init__(self):
        self.engine_locked = True
        self.current_location = None
        self.camera = None
        self.sim_angle = 0  # For simulated GPS
        self.gsm = None
        
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
        """Setup REAL GSM using software serial"""
        try:
            self.gsm = GSMSoftwareSerial(tx_pin=GSM_TX_PIN, rx_pin=GSM_RX_PIN, baud=GSM_BAUD)
            if not self.gsm.is_connected:
                logger.warning("GSM not found - SMS will be simulated")
        except Exception as e:
            logger.warning(f"GSM error: {e}")
            self.gsm = None
    
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
            # SMS #1: Engine LOCKED (already working)
            self.send_sms("ENGINE LOCKED - Vehicle immobilized")
            return True
        except Exception as e:
            logger.error(f"Lock error: {e}")
            return False
    
    def unlock_engine(self):
        try:
            GPIO.output(RELAY_PIN, GPIO.HIGH)
            self.engine_locked = False
            logger.info("🔓 ENGINE UNLOCKED - Relay ON")
            # SMS #2: Engine UNLOCKED (ADD THIS)
            self.send_sms("ENGINE UNLOCKED - Vehicle operational")
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
        """Send REAL SMS via GSM module (or simulated if unavailable)"""
        if self.gsm and self.gsm.is_connected:
            return self.gsm.send_sms(OWNER_PHONE, message)
        else:
            logger.info(f"[SIMULATED SMS] To: {OWNER_PHONE}")
            logger.info(f"[SIMULATED SMS] Message: {message}")
            return True
    
    def send_intruder_sms_alert(self):
        """SMS #3: Send intruder SMS alert"""
        message = "INTRUSION DETECTED! Check web app for more details!"
        logger.info(f"🚨🚨🚨 SENDING INTRUDER SMS: {message} 🚨🚨🚨")
        return self.send_sms(message)
    
    def cleanup(self):
        try:
            self.lock_engine()
            if self.camera:
                self.camera.release()
            if self.gsm:
                self.gsm.cleanup()
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
            else:
                # If unauthorized (401), still return False to trigger SMS
                if response.status_code == 401:
                    logger.info("Face not authorized by server")
                    return False, None
        except Exception as e:
            logger.error(f"Face auth error: {e}")
        return False, None
    
    def send_intruder_alert(self, face_image):
        """Send intruder alert with captured face image"""
        try:
            if not face_image:
                logger.error("❌ No face image to send")
                return False
            
            logger.info(f"📸 Preparing to send intruder alert")
            
            # Ensure the image has data URL prefix
            if not face_image.startswith('data:image'):
                face_image_with_prefix = f"data:image/jpeg;base64,{face_image}"
            else:
                face_image_with_prefix = face_image
            
            alert_data = {
                'title': 'UNAUTHORIZED ACCESS ATTEMPT',
                'description': f'Unknown person attempted to access vehicle at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'severity': 'HIGH',
                'face_image': face_image_with_prefix
            }
            
            logger.info(f"📤 Sending POST to {self.api_url}/api/alerts/create/")
            
            response = requests.post(
                f"{self.api_url}/api/alerts/create/",
                headers=self.headers,
                json=alert_data,
                timeout=15
            )
            
            if response.status_code == 201:
                result = response.json()
                logger.info(f"✅ Alert {result.get('id')} created")
                return True
            else:
                logger.error(f"❌ Alert failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Send intruder alert error: {e}")
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
                    if self.hardware.unlock_engine():  # This will send UNLOCK SMS
                        self.cloud.mark_executed(command_id)
                        logger.info(f"✅ Command {command_id} marked as executed")
                elif command == 'LOCK':
                    logger.info("🔒 Executing LOCK...")
                    if self.hardware.lock_engine():  # This will send LOCK SMS
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
        """Check for unauthorized access and send intruder SMS"""
        last_alert_time = 0
        
        while self.running:
            # Always check for intruders regardless of engine state
            face_image = self.hardware.capture_face()
            
            if face_image:
                logger.info(f"📸 Face captured, length: {len(face_image)} bytes")
                
                # Authenticate face with cloud
                is_authorized, result = self.cloud.authenticate_face(face_image)
                
                if is_authorized:
                    logger.info("✅ Authorized face detected")
                    if self.hardware.engine_locked:
                        logger.info("🔓 Authorized user - UNLOCKING engine")
                        self.hardware.unlock_engine()  # This will send UNLOCK SMS
                else:
                    logger.warning("⚠️ Unauthorized face detected - Sending alert")
                    
                    # Send alert with image and SMS (rate limited to once per 30 seconds)
                    current_time = time.time()
                    if current_time - last_alert_time > 30:
                        logger.info("📸 Sending intruder alert with captured image...")
                        self.cloud.send_intruder_alert(face_image)
                        
                        # SMS #3: Send intruder SMS
                        self.hardware.send_intruder_sms_alert()
                        
                        last_alert_time = current_time
            time.sleep(INTRUDER_CHECK_INTERVAL)
    
    def run(self):
        logger.info("=" * 60)
        logger.info("🚗 VEHICLE SECURITY SYSTEM STARTED")
        logger.info(f"Cloud Server: {API_BASE_URL}")
        logger.info(f"Relay Pin: GPIO{RELAY_PIN}")
        logger.info(f"GSM: GPIO{GSM_TX_PIN} (TX), GPIO{GSM_RX_PIN} (RX)")
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
        logger.info("📱 REAL SMS alerts active for:")
        logger.info("   - SMS #1: ENGINE LOCKED (immobilized)")
        logger.info("   - SMS #2: ENGINE UNLOCKED (operational)")
        logger.info("   - SMS #3: INTRUSION DETECTED (unauthorized face)")
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