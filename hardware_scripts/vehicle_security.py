#!/usr/bin/env python3
"""
Complete Vehicle Security System for Raspberry Pi
Works with web dashboard - Controls relay via GPIO27
REAL GSM SMS using pigpio software serial
WITH GPS LOCATION IN INTRUDER SMS
ADDED: API server to receive intruder alerts from web app
"""

import requests
import time
import json
import base64
import cv2
import numpy as np
import RPi.GPIO as GPIO
import gpsd
from datetime import datetime
import threading
import logging
import math
import pigpio
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler


API_BASE_URL = "http://10.251.159.57:8000"
API_KEY = "mysecurekey123"
RELAY_PIN = 27
CAMERA_DEVICE = 0
GPS_UPDATE_INTERVAL = 3
COMMAND_POLL_INTERVAL = 2
INTRUDER_CHECK_INTERVAL = 5
OWNER_PHONE = "+254792333250"


GSM_TX_PIN = 18
GSM_RX_PIN = 17
GSM_BAUD = 9600


API_PORT = 5000
API_SECRET = "mysecurekey123"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GSMSoftwareSerial:
    def __init__(self, tx_pin=18, rx_pin=17, baud=9600):
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.baud = baud
        self.pi = None
        self.is_connected = False
        self.connect()
    
    def connect(self):
        try:
            subprocess.run(['sudo', 'killall', 'pigpiod'], stderr=subprocess.DEVNULL)
            time.sleep(1)
            subprocess.run(['sudo', 'pigpiod'], stderr=subprocess.DEVNULL)
            time.sleep(2)
            
            self.pi = pigpio.pi()
            if not self.pi.connected:
                logger.error("pigpio not running")
                return False
            
            self.pi.set_mode(self.tx_pin, pigpio.OUTPUT)
            self.pi.set_mode(self.rx_pin, pigpio.INPUT)
            self.pi.bb_serial_read_open(self.rx_pin, self.baud, 8)
            
            response = self.send_command("AT\r")
            if b'OK' in response:
                self.is_connected = True
                logger.info("GSM connected")
                self.send_command("AT+CMGF=1\r")
                time.sleep(0.5)
                return True
            return False
        except Exception as e:
            logger.warning(f"GSM error: {e}")
            return False
    
    def send_byte(self, byte):
        if not self.pi:
            return
        bits = []
        bit_duration = int(1e6 / self.baud)
        bits.append(pigpio.pulse(0, 1 << self.tx_pin, bit_duration))
        for i in range(8):
            if (byte >> i) & 1:
                bits.append(pigpio.pulse(1 << self.tx_pin, 0, bit_duration))
            else:
                bits.append(pigpio.pulse(0, 1 << self.tx_pin, bit_duration))
        bits.append(pigpio.pulse(1 << self.tx_pin, 0, bit_duration))
        
        self.pi.wave_clear()
        self.pi.wave_add_generic(bits)
        wid = self.pi.wave_create()
        self.pi.wave_send_once(wid)
        while self.pi.wave_tx_busy():
            time.sleep(0.001)
        self.pi.wave_delete(wid)
    
    def send_command(self, cmd):
        if not self.pi:
            return b''
        self.pi.bb_serial_read(self.rx_pin)
        for byte in cmd.encode():
            self.send_byte(byte)
        time.sleep(0.5)
        count, data = self.pi.bb_serial_read(self.rx_pin)
        return data
    
    def send_sms(self, phone_number, message):
        if not self.is_connected:
            logger.info(f"[SIMULATED] {message[:50]}")
            return True
        try:
            logger.info(f"📱 Sending SMS...")
            self.send_command("AT+CMGF=1\r")
            time.sleep(0.5)
            cmd = f'AT+CMGS="{phone_number}"\r'
            for byte in cmd.encode():
                self.send_byte(byte)
            time.sleep(1)
            for byte in message.encode('utf-8'):
                self.send_byte(byte)
            self.send_byte(26)
            time.sleep(4)
            count, data = self.pi.bb_serial_read(self.rx_pin)
            if b'+CMGS' in data or b'OK' in data:
                logger.info("✅ SMS sent!")
                return True
            return False
        except Exception as e:
            logger.error(f"SMS error: {e}")
            return False
    
    def cleanup(self):
        if self.pi:
            self.pi.bb_serial_read_close(self.rx_pin)
            self.pi.stop()



class VehicleHardware:
    def __init__(self):
        self.engine_locked = True
        self.camera = None
        self.sim_angle = 0
        self.gsm = None
        self.current_gps_lat = -1.2864
        self.current_gps_lon = 36.8172
        
        self.setup_gpio()
        self.setup_gps()
        self.setup_gsm()
        self.setup_camera()
    
    def setup_gpio(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(RELAY_PIN, GPIO.OUT)
            GPIO.output(RELAY_PIN, GPIO.LOW)
            logger.info("✓ GPIO ready - Engine LOCKED")
        except Exception as e:
            logger.error(f"GPIO error: {e}")
    
    def setup_gps(self):
        try:
            gpsd.connect()
            logger.info("✓ GPS connected")
        except Exception as e:
            logger.warning(f"GPS not available: {e}")
    
    def setup_gsm(self):
        try:
            self.gsm = GSMSoftwareSerial()
        except Exception as e:
            logger.warning(f"GSM error: {e}")
            self.gsm = None
    
    def setup_camera(self):
        try:
            self.camera = cv2.VideoCapture(CAMERA_DEVICE)
            if self.camera.isOpened():
                logger.info("✓ Camera ready")
            else:
                self.camera = None
        except Exception as e:
            logger.warning(f"Camera error: {e}")
            self.camera = None
    
    def lock_engine(self):
        GPIO.output(RELAY_PIN, GPIO.LOW)
        self.engine_locked = True
        logger.info(" ENGINE LOCKED")
        self.send_sms("ENGINE LOCKED - Vehicle immobilized")
    
    def unlock_engine(self):
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        self.engine_locked = False
        logger.info(" ENGINE UNLOCKED")
        self.send_sms("ENGINE UNLOCKED - Vehicle operational")
    
    def get_gps_location(self):
        try:
            packet = gpsd.get_current()
            if packet.mode >= 2:
                self.current_gps_lat = packet.lat
                self.current_gps_lon = packet.lon
                return {
                    'latitude': packet.lat,
                    'longitude': packet.lon,
                    'speed': packet.hspeed * 3.6,
                    'heading': packet.track,
                    'timestamp': datetime.now().isoformat()
                }
        except:
            pass
        
        self.sim_angle += 0.03
        center_lat = -1.2864
        center_lng = 36.8172
        radius = 0.008
        self.current_gps_lat = center_lat + radius * math.sin(self.sim_angle)
        self.current_gps_lon = center_lng + radius * math.cos(self.sim_angle)
        
        return {
            'latitude': self.current_gps_lat,
            'longitude': self.current_gps_lon,
            'speed': 40 + 20 * math.sin(self.sim_angle),
            'heading': (self.sim_angle * 57.3) % 360,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_gps_location_string(self):
        lat = abs(self.current_gps_lat)
        lon = abs(self.current_gps_lon)
        lat_dir = 'N' if self.current_gps_lat >= 0 else 'S'
        lon_dir = 'E' if self.current_gps_lon >= 0 else 'W'
        return f"\n📍 Location: https://www.google.com/maps?q={lat:.6f},{lon:.6f}\n   Coordinates: {lat:.6f}°{lat_dir}, {lon:.6f}°{lon_dir}"
    
    def send_sms(self, message):
        if self.gsm and self.gsm.is_connected:
            return self.gsm.send_sms(OWNER_PHONE, message)
        else:
            logger.info(f"[SIMULATED] {message}")
            return True
    
    def send_intruder_sms(self):
        """Send intruder SMS with GPS location"""
        gps_str = self.get_gps_location_string()
        message = f"INTRUSION DETECTED! Check web app for more details!{gps_str}"
        logger.info(" SENDING INTRUDER SMS WITH GPS LOCATION")
        return self.send_sms(message)
    
    def cleanup(self):
        if self.camera:
            self.camera.release()
        if self.gsm:
            self.gsm.cleanup()
        GPIO.cleanup()



class CloudComm:
    def __init__(self):
        self.headers = {'X-API-KEY': API_KEY, 'Content-Type': 'application/json'}
    
    def get_command(self):
        try:
            r = requests.get(f"{API_BASE_URL}/hardware/get-command/", headers={'X-API-KEY': API_KEY}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get('command') != 'NONE':
                    return data
        except:
            pass
        return None
    
    def mark_executed(self, cmd_id):
        try:
            requests.post(f"{API_BASE_URL}/hardware/mark-executed/", headers=self.headers, json={'command_id': cmd_id}, timeout=5)
        except:
            pass



class IntruderHandler(BaseHTTPRequestHandler):
    hardware = None
    
    def do_POST(self):
        if self.path == '/intruder-alert':
            api_key = self.headers.get('X-API-KEY')
            if api_key != API_SECRET:
                self.send_response(401)
                self.end_headers()
                return
            
            print("\n" + "#"*50)
            print(" INTRUDER ALERT FROM WEB APP!")
            print("#"*50)
            
            if IntruderHandler.hardware:
                IntruderHandler.hardware.send_intruder_sms()
                print(" Intruder SMS with GPS location sent!")
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "sent"}')
    
    def log_message(self, format, *args):
        pass



class VehicleSecuritySystem:
    def __init__(self):
        self.hardware = VehicleHardware()
        self.cloud = CloudComm()
        self.running = True
        IntruderHandler.hardware = self.hardware
    
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
    
    def gps_loop(self):
        while self.running:
            location = self.hardware.get_gps_location()
            if location:
                try:
                    requests.post(
                        f"{API_BASE_URL}/hardware/location/",
                        headers={'X-API-KEY': API_KEY, 'Content-Type': 'application/json'},
                        json=location,
                        timeout=3
                    )
                    logger.info(f"📍 Location: {location['latitude']:.6f}, {location['longitude']:.6f}")
                except:
                    pass
            time.sleep(3)
    
    def run(self):
        logger.info("="*60)
        logger.info("VEHICLE SECURITY - WITH GPS LOCATION IN INTRUDER SMS")
        logger.info("="*60)
        
     
        threading.Thread(target=self.command_loop, daemon=True).start()
        threading.Thread(target=self.gps_loop, daemon=True).start()
        
        
        server = HTTPServer(('0.0.0.0', API_PORT), IntruderHandler)
        logger.info(f" API server on port {API_PORT}")
        logger.info(f" POST http://10.251.159.168:{API_PORT}/intruder-alert")
        
        logger.info(" ALL SYSTEMS GO")
        logger.info(" SMS WILL BE SENT FOR:")
        logger.info("   1. ENGINE LOCKED")
        logger.info("   2. ENGINE UNLOCKED")
        logger.info("   3. INTRUDER DETECTED (with GPS location)")
        logger.info("\nPress Ctrl+C to stop\n")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.cleanup()
            server.shutdown()
    
    def cleanup(self):
        self.running = False
        self.hardware.cleanup()

if __name__ == "__main__":
    VehicleSecuritySystem().run()
