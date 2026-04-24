import serial
import time
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class GSMHandler:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        """Initialize GSM module"""
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.use_simulated = True  # Set to False for real GSM
        
    def connect(self):
        """Connect to GSM module"""
        try:
            if not self.use_simulated:
                self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
                time.sleep(2)
                self.serial_connection.write(b'AT\r\n')
                response = self.serial_connection.read(100)
                if b'OK' in response:
                    logger.info("GSM module connected")
                    return True
        except Exception as e:
            logger.error(f"GSM connection error: {e}")
        
        # Use simulated mode for development
        logger.info("Using simulated SMS mode")
        return True
    
    def send_sms(self, phone_number, message):
        """Send SMS alert"""
        try:
            if self.use_simulated:
                # Simulate SMS sending
                logger.info(f"[SIMULATED SMS] To: {phone_number}")
                logger.info(f"[SIMULATED SMS] Message: {message}")
                
                # Also send via HTTP API (Twilio/MessageBird alternative)
                self.send_via_http_api(phone_number, message)
                return True
            else:
                # Real GSM SMS
                self.serial_connection.write(b'AT+CMGF=1\r\n')
                time.sleep(0.5)
                self.serial_connection.write(f'AT+CMGS="{phone_number}"\r\n'.encode())
                time.sleep(0.5)
                self.serial_connection.write(f'{message}\x1A'.encode())
                time.sleep(1)
                return True
        except Exception as e:
            logger.error(f"SMS sending error: {e}")
            return False
    
    def send_via_http_api(self, phone_number, message):
        """Fallback to HTTP API (Twilio, etc.)"""
        # You can integrate with Twilio, MessageBird, or other SMS gateways
        api_key = getattr(settings, 'SMS_API_KEY', None)
        if api_key:
            # Example with a generic SMS API
            try:
                response = requests.post(
                    'https://api.sms-gateway.com/send',
                    json={
                        'to': phone_number,
                        'message': message,
                        'api_key': api_key
                    },
                    timeout=5
                )
                return response.status_code == 200
            except:
                pass
        return False

# Global instance
gsm_handler = GSMHandler()