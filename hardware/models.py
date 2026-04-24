from django.db import models
from django.conf import settings

class VehicleCommand(models.Model):
    COMMAND_CHOICES = [
        ('IMMOBILIZE', 'Immobilize Engine'),
        ('ENABLE', 'Enable Engine'),
        ('LOCK', 'Lock Vehicle'),
        ('UNLOCK', 'Unlock Vehicle'),
    ]

    command = models.CharField(max_length=20, choices=COMMAND_CHOICES)
    executed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.command

class EventLog(models.Model):
    EVENT_TYPES = [
        ('AUTHORIZED_ACCESS', 'Authorized Access'),
        ('UNAUTHORIZED_ACCESS', 'Unauthorized Access'),
        ('COMMAND_SENT', 'Command Sent'),
        ('LOCATION_UPDATE', 'Location Update'),
    ]
    
    event_type = models.CharField(max_length=100, choices=EVENT_TYPES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.event_type} - {self.timestamp}"