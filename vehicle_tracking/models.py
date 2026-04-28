from django.db import models

class VehicleLocation(models.Model):
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    speed = models.FloatField(default=0.0)  
    heading = models.IntegerField(default=0)  
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        get_latest_by = 'timestamp'
        
    def __str__(self):
        return f"Lat: {self.latitude}, Lng: {self.longitude} at {self.timestamp}"
