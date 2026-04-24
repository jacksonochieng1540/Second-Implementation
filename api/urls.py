from django.urls import path
from . import views

urlpatterns = [
    path('face-auth/', views.face_auth, name='face_auth'),
    path('vehicle/send-command/', views.send_command, name='send_command'),
    path('alerts/create/', views.create_alert, name='create_alert'),
]