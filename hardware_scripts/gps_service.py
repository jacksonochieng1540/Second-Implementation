import serial
import pynmea2

class GPSService:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600):
        self.ser = serial.Serial(port, baudrate, timeout=1)

    def get_location(self):
        while True:
            try:
                data = self.ser.readline().decode('ascii', errors='replace')

                if data.startswith('$GPGGA'):
                    msg = pynmea2.parse(data)

                    return {
                        "latitude": msg.latitude,
                        "longitude": msg.longitude,
                        "altitude": msg.altitude,
                        "satellites": msg.num_sats
                    }

            except Exception as e:
                print("GPS Error:", e)
                return None