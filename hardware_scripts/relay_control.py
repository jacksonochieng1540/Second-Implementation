import RPi.GPIO as GPIO

RELAY_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

def engine_on():
    GPIO.output(RELAY_PIN, GPIO.LOW)
    print("Engine ON")

def engine_off():
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    print("Engine OFF")