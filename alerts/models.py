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
        """Save alert - SMS handled by Raspberry Pi, NOT Django"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
       
        if is_new and self.severity in ['HIGH', 'CRITICAL'] and not self.sms_sent:
          
            Alert.objects.filter(pk=self.pk).update(sms_sent=True)
            print(f" Alert {self.pk} created - SMS will be sent by Raspberry Pi")
    
    def __str__(self):
        return f"{self.severity}: {self.title} - {self.timestamp}"
