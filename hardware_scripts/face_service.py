import cv2
import face_recognition

def capture_face():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()

    if not ret:
        return None

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb)

    return encodings[0] if encodings else None