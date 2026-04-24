from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """Extended user profile for face recognition data"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    facial_encoding = models.BinaryField(null=True, blank=True)
    has_face_registered = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True)
    
    class Meta:
        db_table = 'user_profile'
        
    def __str__(self):
        return f"{self.user.username}'s profile"