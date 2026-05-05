"""
GSM SMS Handler - Using pigpio software serial (REAL SMS)
Works with SIM800L on GPIO17 (RX) and GPIO18 (TX)
"""

import pigpio
import time
import logging
import subprocess
import os

logger = logging.getLogger(__name__)

class GSMHandler:
    def __init__(self, tx_pin=18, rx_pin=17, baud=9600):
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.baud = baud
        self.pi = None
        self.use_simulated = True
        self.connect_gsm()
    
    def connect_gsm(self):
        """Connect to GSM module using pigpio software serial"""
        try:
            # Check if we're on Raspberry Pi (has GPIO)
            if not os.path.exists('/dev/gpiomem'):
                logger.warning("Not running on Raspberry Pi - using simulated SMS")
                self.use_simulated = True
                return False
            
            # Start pigpio daemon
            subprocess.run(['sudo', 'killall', 'pigpiod'], stderr=subprocess.DEVNULL)
            time.sleep(1)
            subprocess.run(['sudo', 'pigpiod'], stderr=subprocess.DEVNULL)
            time.sleep(2)
            
            self.pi = pigpio.pi()
            if not self.pi.connected:
                logger.warning("pigpio not running - using simulated SMS")
                self.use_simulated = True
                return False
            
            # Setup pins
            self.pi.set_mode(self.tx_pin, pigpio.OUTPUT)
            self.pi.set_mode(self.rx_pin, pigpio.INPUT)
            self.pi.bb_serial_read_open(self.rx_pin, self.baud, 8)
            
            # Test GSM with multiple attempts
            for attempt in range(3):
                logger.info(f"📱 Testing GSM (attempt {attempt+1}/3)...")
                response = self.send_command("AT\r")
                
                if b'OK' in response:
                    self.use_simulated = False
                    logger.info(f"✅✅✅ REAL GSM CONNECTED! ✅✅✅")
                    logger.info(f"   TX=GPIO{self.tx_pin}, RX=GPIO{self.rx_pin}")
                    
                    # Initialize GSM for SMS
                    self.send_command("AT+CMGF=1\r")
                    time.sleep(0.5)
                    self.send_command("AT+CSCS=\"GSM\"\r")
                    time.sleep(0.5)
                    
                    # Check signal
                    response = self.send_command("AT+CSQ\r")
                    logger.info(f"   Signal: {response}")
                    
                    return True
                time.sleep(1)
            
            logger.warning("⚠️ GSM not responding - using simulated SMS")
            self.use_simulated = True
            return False
                
        except Exception as e:
            logger.error(f"GSM connection error: {e}")
            self.use_simulated = True
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
        if self.use_simulated:
            logger.info("="*50)
            logger.info("📱 [SIMULATED SMS]")
            logger.info(f"   To: {phone_number}")
            logger.info(f"   Message: {message}")
            logger.info("="*50)
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
            time.sleep(4)  # Wait for SMS to send
            
            # Read response
            count, data = self.pi.bb_serial_read(self.rx_pin)
            
            if b'+CMGS' in data or b'OK' in data:
                logger.info(f"✅✅✅ REAL SMS SENT SUCCESSFULLY! ✅✅✅")
                logger.info(f"   To: {phone_number}")
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

# Create global instance
gsm_handler = GSMHandler()

# Print status on import
if not gsm_handler.use_simulated:
    logger.info("📱 GSM Handler: REAL MODE - SMS will be sent to your phone")
else:
    logger.info("📱 GSM Handler: SIMULATED MODE - SMS will only be logged")