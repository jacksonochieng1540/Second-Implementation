import time
import requests
import base64
import cv2

from relay_control import RelayControl
from gps_service import GPSService
from gsm_service import GSMService

SERVER = "http://YOUR_SERVER_IP:8000/api"

relay = RelayControl(pin=17)
gps = GPSService()
gsm = GSMService()


def capture_image():
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    cam.release()

    _, buffer = cv2.imencode('.jpg', frame)
    return base64.b64encode(buffer).decode('utf-8')


while True:
    try:
        # 🔹 FACE AUTH
        image = capture_image()

        res = requests.post(f"{SERVER}/face/authenticate/", json={
            "image": image
        }).json()

        print(res)

        if res["status"] == "AUTHORIZED":
            relay.engine_on()

        else:
            relay.engine_off()
            gsm.send_sms("+2547XXXXXXX", "Unauthorized vehicle access!")

        # 🔹 GPS UPDATE
        location = gps.get_location()

        if location:
            requests.post(f"{SERVER}/gps/update/", json=location)

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)

TOKEN = None

def authenticate():
    global TOKEN

    res = requests.post(f"{SERVER}/auth/login/", json={
        "username": "pi_device",
        "password": "strongpassword"
    })

    TOKEN = res.json()['access']


def get_headers():
    return {
        "Authorization": f"Bearer {TOKEN}"
    }
def check_remote_command():
    global TOKEN

    res = requests.get(
        f"{SERVER}/vehicle/get-command/",
        headers=get_headers()
    ).json()

    if res["command"] is None:
        return

    cmd_id = res["id"]
    command = res["command"]

    print("Received command:", command)

    if command == "IMMOBILIZE":
        relay.engine_off()
        gsm.send_sms("+2547XXXXXXX", "Vehicle immobilized remotely!")

    elif command == "ENABLE":
        relay.engine_on()
        gsm.send_sms("+2547XXXXXXX", "Vehicle enabled remotely!")

    # ✅ Mark command as executed
    requests.post(
        f"{SERVER}/vehicle/command-done/",
        json={"id": cmd_id},
        headers=get_headers()
    )