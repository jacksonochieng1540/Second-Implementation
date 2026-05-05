cat > /home/raspberrypi/SmartVehicleProject/vehicle_security_complete.py << 'EOF'
#!/usr/bin/env python3
"""
COMPLETE VEHICLE SECURITY SYSTEM - RASPBERRY PI
Handles: Engine LOCK/UNLOCK SMS + Intruder SMS via API
"""

import requests
import time
import base64
import cv2
import numpy as np
import RPi.GPIO as GPIO
import pigpio
import subprocess
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============= CONFIGURATION =============
API_BASE_URL = "http://10.251.159.57:8000"  # Django server IP
API_KEY = "mysecurekey123"
RELAY_PIN = 27
CAMERA_DEVICE = 0
OWNER_PHONE = "+254792333250"

# GSM Pins
GSM_TX_PIN = 18
GSM_RX_PIN = 17
GSM_BAUD = 9600

# Intruder API config
INTRUDER_API_PORT = 5000
INTRUDER_API_KEY = "mysecurekey123"

# Get actual Pi IP for display
import socket
def get_pi_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "YOUR_PI_IP"

PI_IP = get_pi_ip()

print("="*60)
print("COMPLETE VEHICLE SECURITY - RASPBERRY PI")
print("="*60)
print(f"📡 Pi IP Address: {PI_IP}")
print("="*60)

# ============= GSM MODULE =============
class GSM:
    def __init__(self):
        self.pi = None
        self.connected = False
        self.connect()
    
    def connect(self):
        try:
            subprocess.run(['sudo', 'killall', 'pigpiod'], stderr=subprocess.DEVNULL)
            time.sleep(1)
            subprocess.run(['sudo', 'pigpiod'], stderr=subprocess.DEVNULL)
            time.sleep(2)
            
            self.pi = pigpio.pi()
            if not self.pi.connected:
                return False
            
            self.pi.set_mode(GSM_TX_PIN, pigpio.OUTPUT)
            self.pi.set_mode(GSM_RX_PIN, pigpio.INPUT)
            self.pi.bb_serial_read_open(GSM_RX_PIN, GSM_BAUD, 8)
            
            response = self.send_cmd("AT")
            if "OK" in response:
                self.connected = True
                print("✅ GSM CONNECTED!")
                self.send_cmd("AT+CMGF=1")
                time.sleep(0.5)
                return True
            return False
        except Exception as e:
            print(f"GSM error: {e}")
            return False
    
    def send_byte(self, byte):
        bits = []
        bit_duration = int(1e6 / GSM_BAUD)
        bits.append(pigpio.pulse(0, 1 << GSM_TX_PIN, bit_duration))
        for i in range(8):
            if (byte >> i) & 1:
                bits.append(pigpio.pulse(1 << GSM_TX_PIN, 0, bit_duration))
            else:
                bits.append(pigpio.pulse(0, 1 << GSM_TX_PIN, bit_duration))
        bits.append(pigpio.pulse(1 << GSM_TX_PIN, 0, bit_duration))
        
        self.pi.wave_clear()
        self.pi.wave_add_generic(bits)
        wid = self.pi.wave_create()
        self.pi.wave_send_once(wid)
        while self.pi.wave_tx_busy():
            time.sleep(0.001)
        self.pi.wave_delete(wid)
        time.sleep(0.05)
    
    def send_cmd(self, cmd):
        self.pi.bb_serial_read(GSM_RX_PIN)
        for char in cmd + "\r":
            self.send_byte(ord(char))
        time.sleep(0.5)
        count, data = self.pi.bb_serial_read(GSM_RX_PIN)
        return data.decode('utf-8', errors='ignore') if count > 0 else ""
    
    def send_sms(self, message):
        if not self.connected:
            print("❌ GSM not connected")
            return False
        try:
            print(f"📱 Sending SMS: {message[:50]}...")
            self.send_cmd("AT+CMGF=1")
            time.sleep(0.5)
            cmd = f'AT+CMGS="{OWNER_PHONE}"'
            self.send_cmd(cmd)
            time.sleep(1)
            for char in message:
                self.send_byte(ord(char))
            self.send_byte(26)
            time.sleep(4)
            count, data = self.pi.bb_serial_read(GSM_RX_PIN)
            response = data.decode('utf-8', errors='ignore') if count > 0 else ""
            if "+CMGS" in response or "OK" in response:
                print("✅ SMS SENT SUCCESSFULLY!")
                return True
            else:
                print(f"⚠️ SMS response: {response[:100]}")
                return False
        except Exception as e:
            print(f"SMS error: {e}")
            return False
    
    def cleanup(self):
        if self.pi:
            self.pi.bb_serial_read_close(GSM_RX_PIN)
            self.pi.stop()

# ============= HARDWARE =============
class VehicleHardware:
    def __init__(self):
        self.gsm = None
        self.camera = None
        self.engine_locked = True
        self.last_sms_time = 0
        
        self.setup_gpio()
        self.setup_gsm()
        self.setup_camera()
    
    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RELAY_PIN, GPIO.OUT)
        GPIO.output(RELAY_PIN, GPIO.LOW)
        print("✓ GPIO ready - Engine LOCKED")
    
    def setup_gsm(self):
        self.gsm = GSM()
        if self.gsm.connected:
            time.sleep(2)
            self.gsm.send_sms("VEHICLE SECURITY ONLINE - Pi ACTIVE")
    
    def setup_camera(self):
        try:
            self.camera = cv2.VideoCapture(CAMERA_DEVICE)
            if self.camera.isOpened():
                print("✓ Camera ready")
                ret, frame = self.camera.read()
                if ret:
                    print("✓ Camera test OK")
            else:
                print("⚠️ Camera not available (intruder detection will be from web app)")
                self.camera = None
        except Exception as e:
            print(f"Camera error: {e}")
            self.camera = None
    
    def send_engine_sms(self, message):
        """Send engine LOCK/UNLOCK SMS"""
        current_time = time.time()
        if current_time - self.last_sms_time < 10:
            return False
        self.last_sms_time = current_time
        
        if self.gsm and self.gsm.connected:
            return self.gsm.send_sms(message)
        return False
    
    def send_intruder_sms(self, message):
        """Send intruder SMS (called from API)"""
        if self.gsm and self.gsm.connected:
            return self.gsm.send_sms(message)
        return False
    
    def lock_engine(self):
        GPIO.output(RELAY_PIN, GPIO.LOW)
        self.engine_locked = True
        print("🔒 ENGINE LOCKED")
        self.send_engine_sms("ENGINE LOCKED - Vehicle immobilized")
    
    def unlock_engine(self):
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        self.engine_locked = False
        print("🔓 ENGINE UNLOCKED")
        self.send_engine_sms("ENGINE UNLOCKED - Vehicle operational")
    
    def capture_face(self):
        if not self.camera:
            return None
        try:
            ret, frame = self.camera.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces = face_cascade.detectMultiScale(gray, 1.02, 3, minSize=(60, 60))
                if len(faces) > 0:
                    x, y, w, h = faces[0]
                    face_roi = frame[y:y+h, x:x+w]
                    _, buffer = cv2.imencode('.jpg', face_roi)
                    return base64.b64encode(buffer).decode()
            return None
        except:
            return None
    
    def cleanup(self):
        if self.camera:
            self.camera.release()
        if self.gsm:
            self.gsm.cleanup()
        GPIO.cleanup()

# ============= CLOUD COMMANDS =============
class CloudComm:
    def __init__(self):
        self.headers = {'X-API-KEY': API_KEY, 'Content-Type': 'application/json'}
    
    def get_command(self):
        try:
            r = requests.get(f"{API_BASE_URL}/hardware/get-command/", headers={'X-API-KEY': API_KEY}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get('command') != 'NONE':
                    print(f"📡 Command received: {data.get('command')}")
                    return data
        except Exception as e:
            pass
        return None
    
    def mark_executed(self, cmd_id):
        try:
            requests.post(f"{API_BASE_URL}/hardware/mark-executed/", headers=self.headers, json={'command_id': cmd_id}, timeout=5)
        except:
            pass

# ============= INTRUDER API SERVER =============
class IntruderAPI:
    def __init__(self, hardware):
        self.hardware = hardware
        self.server = None
    
    def start(self):
        handler = self.create_handler()
        self.server = HTTPServer(('0.0.0.0', INTRUDER_API_PORT), handler)
        print(f"\n🌐 Intruder API listening on port {INTRUDER_API_PORT}")
        print(f"📍 POST http://{PI_IP}:{INTRUDER_API_PORT}/intruder-alert")
        print(f"🔑 API Key: {INTRUDER_API_KEY}")
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
    
    def create_handler(self):
        hardware = self.hardware
        
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == '/intruder-alert':
                    api_key = self.headers.get('X-API-KEY')
                    if api_key != INTRUDER_API_KEY:
                        self.send_response(401)
                        self.end_headers()
                        self.wfile.write(b'Invalid API key')
                        return
                    
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length)
                    
                    try:
                        data = json.loads(post_data)
                        print("\n" + "="*50)
                        print("🚨 INTRUDER ALERT RECEIVED FROM WEB APP!")
                        print(f"   Alert ID: {data.get('alert_id', 'unknown')}")
                        print("="*50)
                        
                        # Send intruder SMS
                        success = hardware.send_intruder_sms("INTRUSION DETECTED! Check web app for more details!")
                        
                        if success:
                            print("✅✅✅ INTRUDER SMS SENT! ✅✅✅")
                            self.send_response(200)
                            self.end_headers()
                            self.wfile.write(b'{"status": "sms_sent"}')
                        else:
                            print("❌ Failed to send SMS")
                            self.send_response(500)
                            self.end_headers()
                            self.wfile.write(b'{"status": "failed"}')
                    except Exception as e:
                        print(f"Error: {e}")
                        self.send_response(500)
                        self.end_headers()
                        self.wfile.write(b'{"status": "error"}')
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_GET(self):
                if self.path == '/health':
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'{"status": "ok"}')
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass
        
        return Handler

# ============= MAIN SYSTEM =============
class VehicleSecuritySystem:
    def __init__(self):
        self.hardware = VehicleHardware()
        self.cloud = CloudComm()
        self.running = True
    
    def command_loop(self):
        while self.running:
            cmd = self.cloud.get_command()
            if cmd:
                if cmd.get('command') == 'UNLOCK':
                    self.hardware.unlock_engine()
                    self.cloud.mark_executed(cmd.get('command_id'))
                elif cmd.get('command') == 'LOCK':
                    self.hardware.lock_engine()
                    self.cloud.mark_executed(cmd.get('command_id'))
            time.sleep(2)
    
    def run(self):
        print("\n✅ SYSTEM RUNNING")
        print("="*50)
        print("📱 SMS WILL BE SENT FOR:")
        print("   1. ENGINE LOCKED (via cloud command)")
        print("   2. ENGINE UNLOCKED (via cloud command)")
        print("   3. INTRUDER DETECTED (via web app alert)")
        print("="*50)
        
        # Start command loop
        threading.Thread(target=self.command_loop, daemon=True).start()
        
        # Start intruder API server
        intruder_api = IntruderAPI(self.hardware)
        intruder_api.start()
        
        print("\n✅ ALL SYSTEMS GO!")
        print("Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()
    
    def cleanup(self):
        self.running = False
        self.hardware.cleanup()
        print("\nShutdown complete")

if __name__ == "__main__":
    VehicleSecuritySystem().run()