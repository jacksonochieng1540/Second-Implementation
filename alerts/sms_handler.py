"""
GSM SMS Handler - Real GSM Module on /dev/ttyS0
"""

import serial
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class GSMHandler:
    def __init__(self, port='/dev/ttyS0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.use_simulated = False
        self.connect_gsm()
    
    def connect_gsm(self):
        """Connect to GSM module on /dev/ttyS0"""
        try:
            logger.info(f"🔌 Connecting to GSM on {self.port}...")
            
            # Open serial connection
            self.serial_connection = serial.Serial(
                self.port, 
                self.baudrate, 
                timeout=2,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            time.sleep(1)
            
            # Test AT command
            self.serial_connection.write(b'AT\r\n')
            time.sleep(0.5)
            response = self.serial_connection.read(100)
            
            if b'OK' in response:
                self.use_simulated = False
                logger.info(f"✅ GSM module connected on {self.port}")
                
                # Initialize GSM
                self.init_gsm()
                return True
            else:
                logger.warning(f"GSM not responding on {self.port}")
                self.serial_connection.close()
                self.serial_connection = None
                self.use_simulated = True
                return False
                
        except Exception as e:
            logger.error(f"GSM connection error: {e}")
            self.use_simulated = True
            return False
    
    def init_gsm(self):
        """Initialize GSM module"""
        try:
            # Set SMS text mode
            self.serial_connection.write(b'AT+CMGF=1\r\n')
            time.sleep(0.5)
            
            # Set character set
            self.serial_connection.write(b'AT+CSCS="GSM"\r\n')
            time.sleep(0.5)
            
            # Check signal quality
            self.serial_connection.write(b'AT+CSQ\r\n')
            time.sleep(0.5)
            response = self.serial_connection.read(100)
            logger.info(f"📶 Signal: {response}")
            
            # Check network registration
            self.serial_connection.write(b'AT+CREG?\r\n')
            time.sleep(0.5)
            response = self.serial_connection.read(100)
            logger.info(f"📡 Network: {response}")
            
            logger.info("✅ GSM module initialized")
            return True
            
        except Exception as e:
            logger.error(f"GSM init error: {e}")
            return False
    
    def send_sms(self, phone_number, message):
        """Send real SMS via GSM module"""
        
        if self.use_simulated:
            logger.info("="*50)
            logger.info("📱 [SIMULATED SMS]")
            logger.info(f"   To: {phone_number}")
            logger.info(f"   Message: {message}")
            logger.info("="*50)
            return True
        
        try:
            # Ensure SMS text mode
            self.serial_connection.write(b'AT+CMGF=1\r\n')
            time.sleep(0.5)
            
            # Set recipient
            cmd = f'AT+CMGS="{phone_number}"\r\n'
            self.serial_connection.write(cmd.encode())
            time.sleep(0.5)
            
            # Send message (Ctrl+Z = 0x1A)
            self.serial_connection.write(f'{message}\x1A'.encode())
            time.sleep(3)
            
            # Read response
            response = self.serial_connection.read(200)
            
            if b'+CMGS' in response or b'OK' in response:
                logger.info(f"✅ REAL SMS sent to {phone_number}")
                logger.info(f"   Message: {message[:50]}...")
                return True
            else:
                logger.error(f"❌ SMS failed: {response}")
                return False
                
        except Exception as e:
            logger.error(f"SMS error: {e}")
            return False
    
    def check_status(self):
        """Check GSM module status"""
        if self.use_simulated:
            return "SIMULATED MODE"
        
        try:
            self.serial_connection.write(b'AT\r\n')
            time.sleep(0.5)
            if b'OK' in self.serial_connection.read(50):
                return "CONNECTED"
            return "ERROR"
        except:
            return "DISCONNECTED"

# Create global instance
gsm_handler = GSMHandler()

# Print status
if not gsm_handler.use_simulated:
    logger.info("📱 REAL GSM MODE ACTIVE - SMS will be sent to your phone")
else:
    logger.info("📱 SIMULATED MODE - Check GSM module connection")