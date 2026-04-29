"""
GSM SMS Handler for Real SMS Alerts
"""

import serial
import time
import logging
import threading

logger = logging.getLogger(__name__)

class GSMHandler:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.is_connected = False
        self.use_simulated = True  # Default to simulated
        self.connect()
    
    def connect(self):
        """Connect to GSM module"""
        try:
            # Try multiple ports
            ports_to_try = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyS0']
            
            for port in ports_to_try:
                try:
                    self.serial_connection = serial.Serial(port, self.baudrate, timeout=2)
                    time.sleep(1)
                    
                    # Test AT command
                    self.serial_connection.write(b'AT\r\n')
                    time.sleep(0.5)
                    response = self.serial_connection.read(100)
                    
                    if b'OK' in response:
                        self.is_connected = True
                        self.use_simulated = False
                        self.port = port
                        logger.info(f"✅ GSM module connected on {port}")
                        return True
                    else:
                        self.serial_connection.close()
                        self.serial_connection = None
                        
                except Exception as e:
                    if self.serial_connection:
                        self.serial_connection.close()
                    self.serial_connection = None
                    continue
            
            # If we get here, no GSM module found
            logger.warning("⚠️ No GSM module found - Using simulated SMS mode")
            self.use_simulated = True
            return False
            
        except Exception as e:
            logger.warning(f"GSM connection error: {e}")
            self.use_simulated = True
            return False
    
    def send_sms(self, phone_number, message):
        """Send SMS using GSM module or simulation"""
        if self.use_simulated:
            logger.info(f"[SIMULATED SMS] To: {phone_number}")
            logger.info(f"[SIMULATED SMS] Message: {message}")
            return True
        
        try:
            # Set SMS text mode
            self.serial_connection.write(b'AT+CMGF=1\r\n')
            time.sleep(0.5)
            
            # Set recipient
            self.serial_connection.write(f'AT+CMGS="{phone_number}"\r\n'.encode())
            time.sleep(0.5)
            
            # Send message
            self.serial_connection.write(f'{message}\x1A'.encode())
            time.sleep(2)
            
            # Check response
            response = self.serial_connection.read(200)
            if b'+CMGS' in response or b'OK' in response:
                logger.info(f"✅ SMS sent to {phone_number}")
                return True
            else:
                logger.error(f"❌ SMS failed: {response}")
                return False
                
        except Exception as e:
            logger.error(f"SMS error: {e}")
            return False
    
    def check_balance(self):
        """Check SMS balance (optional)"""
        if self.use_simulated:
            logger.info("[SIMULATED] Balance: $10 (simulated)")
            return "Simulated balance"
        
        try:
            self.serial_connection.write(b'AT+CBC\r\n')
            time.sleep(0.5)
            response = self.serial_connection.read(100)
            logger.info(f"Battery status: {response}")
            return response
        except:
            return "Unknown"

# Global instance
gsm_handler = GSMHandler()