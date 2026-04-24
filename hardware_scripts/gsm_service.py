import serial.tools.list_ports

class GSMService:

    def __init__(self):
        self.port = self.detect_port()
        self.ser = serial.Serial(self.port, 9600, timeout=1)

    def detect_port(self):
        ports = list(serial.tools.list_ports.comports())

        for p in ports:
            if "USB" in p.device:
                print("GSM Found on:", p.device)
                return p.device

        raise Exception("No GSM module found")

    def send_sms(self, number, message):
        self.ser.write(b'AT\r')
        self.ser.write(b'AT+CMGF=1\r')

        cmd = f'AT+CMGS="{number}"\r'.encode()
        self.ser.write(cmd)

        self.ser.write(message.encode() + b"\x1A")

        print("SMS Sent")