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
        """Save alert - SMS now handled by api/views.py to avoid duplicates"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # DO NOT SEND SMS HERE - let api/views.py handle it
        # This prevents duplicate SMS messages
        
    def __str__(self):
        return f"{self.severity}: {self.title} - {self.timestamp}"