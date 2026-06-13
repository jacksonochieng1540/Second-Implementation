# Smart Vehicle Tracking and Anti-Theft System using Facial Recognition, GPS and GSM

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Django](https://img.shields.io/badge/Django-4.2-green.svg)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4B-red.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

##  Overview

A comprehensive vehicle security system that combines **facial recognition**, **real-time GPS tracking**, **GSM SMS alerts**, and **remote engine control** to provide complete vehicle protection. The system authenticates drivers using facial recognition before allowing engine start, tracks vehicle location continuously, and enables the owner to remotely immobilize the engine from anywhere in the world.

###  Key Features

- **Face Recognition Authentication** - Authorized drivers are identified using OpenCV
- **Real-Time GPS Tracking** - Live vehicle location every 3 seconds
- **GSM SMS Alerts** - Instant notifications for intrusions and engine status
- **Remote Engine Control** - Lock/unlock engine from web dashboard
- **Cloud Dashboard** - Monitor and control vehicle from any device
- **Intruder Capture** - Photos of unauthorized access attempts
- **Emergency Access** - Temporary access for family members

##  System Demo

### Web Dashboard - Admin Panel
<img width="1308" height="655" alt="WhatsApp Image 2026-05-08 at 20 07 34" src="https://github.com/user-attachments/assets/c10470da-9a7b-4c63-a90b-bb846f8f9b1f" />


### SMS Alert Example
 INTRUSION DETECTED!
 Location: -1.095555, 37.013904
 Google Maps: https://maps.google.com/?q=-1.095555,37.013904
Time: 2026-05-20 17:24:00

### Face Authentication
<img width="1308" height="655" alt="WhatsApp Image 2026-05-08 at 20 21 20" src="https://github.com/user-attachments/assets/460fd615-b169-45bd-9218-1bb68b39afe7" />



## Hardware Components

| Component | Model | Purpose | Approx. Cost (KES) |
|-----------|-------|---------|-------------------|
| Raspberry Pi | 4B/3B+ | Main controller | 8,000 |
| USB Camera | Logitech C270 | Face capture | 3,000 |
| GPS Module | NEO-6M / NEO-8M | Vehicle tracking | 2,500 |
| GSM Module | SIM800L | SMS alerts | 2,000 |
| Relay Module | 1-Channel 5V | Engine control | 500 |
| Power Supply | 5V 3A | Raspberry Pi power | 1,000 |
| **Total** | | | **~17,000 KES** |

##  Software Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Hardware Control | Python, RPi.GPIO, pigpio | GPIO control, serial communication |
| Face Recognition | OpenCV, Haar Cascades | Face detection and recognition |
| Backend | Django 4.2, Django REST Framework | API server, database, business logic |
| Frontend | HTML5, CSS3, JavaScript, Bootstrap | Web dashboard |
| Maps | Leaflet.js, Google Maps API | Location visualization |
| Database | SQLite3 | Data storage |
| SMS | GSM Module (SIM800L) | Text alerts |

circuit diagram
<img width="1200" height="1600" alt="image" src="https://github.com/user-attachments/assets/5675eaaa-b67f-4f27-8fbe-668fdde0b27b" />

The sms ouput sample in all the three scenarios:
<img width="713" height="274" alt="image" src="https://github.com/user-attachments/assets/9eaf108f-ec69-4fd6-b3a8-6041b8334073" />


