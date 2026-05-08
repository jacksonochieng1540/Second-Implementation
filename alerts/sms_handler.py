"""
SMS Handler - DISABLED
All SMS are sent by the Raspberry Pi, not Django
"""
import logging

logger = logging.getLogger(__name__)
logger.info("📱 SMS Handler DISABLED - Raspberry Pi handles all SMS")

class GSMHandler:
    def __init__(self):
        self.use_simulated = True
        self.connected = False
    
    def send_sms(self, phone_number, message):
        """This is disabled - Pi sends SMS instead"""
        logger.info(f"[DISABLED] SMS would be sent to {phone_number}")
        logger.info(f"   Message: {message[:80]}...")
        logger.info(f"   Note: Raspberry Pi handles all SMS")
        return True
    
    def cleanup(self):
        pass

gsm_handler = GSMHandler()
