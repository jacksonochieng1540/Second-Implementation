from django.db import models
from django.contrib.auth.models import User

class VehicleCommand(models.Model):
    COMMAND_CHOICES = [
        ('LOCK', 'Lock Engine'),
        ('UNLOCK', 'Unlock Engine'),
    ]
    
    command = models.CharField(max_length=10, choices=COMMAND_CHOICES)
    executed = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='commands')
    timestamp = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.command} at {self.timestamp}"

class EventLog(models.Model):
    EVENT_TYPES = [
        ('FACE_AUTH', 'Face Authentication'),
        ('COMMAND_SENT', 'Command Sent'),
        ('COMMAND_EXECUTED', 'Command Executed'),
        ('LOCATION_UPDATE', 'Location Update'),
        ('ALERT_TRIGGERED', 'Alert Triggered'),
        ('UNAUTHORIZED_ACCESS', 'Unauthorized Access'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.event_type} - {self.timestamp}"