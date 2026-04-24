from django.db import models

class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    ALERT_TYPES = [
        ('UNAUTHORIZED_ACCESS', 'Unauthorized Access Attempt'),
        ('THEFT_ATTEMPT', 'Theft Attempt'),
        ('GEO_FENCE', 'Geo-fence Violation'),
        ('SYSTEM_ERROR', 'System Error'),
        ('LOW_BATTERY', 'Low Battery'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES, default='UNAUTHORIZED_ACCESS')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='MEDIUM')
    image = models.ImageField(upload_to='alerts/', null=True, blank=True)
    location_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
        
    def save(self, *args, **kwargs):
        """Send SMS alert when alert is created"""
        super().save(*args, **kwargs)
        
        if not self.sms_sent:
            self.send_sms_alert()
    
    def send_sms_alert(self):
        """Send SMS notification for critical alerts"""
        if self.severity in ['HIGH', 'CRITICAL']:
            from .sms_handler import gsm_handler
            
            # Get owner's phone number from user profile
            owner_phone = '+254700000000'  # Configure this from user profile
            
            message = f"🚨 VEHICLE ALERT: {self.title}\n{self.description}\nTime: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            
            success = gsm_handler.send_sms(owner_phone, message)
            if success:
                self.sms_sent = True
                super().save(update_fields=['sms_sent'])
    
    def __str__(self):
        return f"{self.severity}: {self.title} - {self.timestamp}"