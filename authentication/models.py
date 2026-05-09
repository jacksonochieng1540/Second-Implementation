from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """Extended user profile for face recognition data"""
    USER_ROLES = (
        ('owner', 'Vehicle Owner (Admin)'),
        ('kinsman', 'Kinsman/Family Member'),
        ('user', 'Regular User'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=USER_ROLES, default='user')
    facial_encoding = models.BinaryField(null=True, blank=True)
    has_face_registered = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True)
    
    class Meta:
        db_table = 'user_profile'
        
    def __str__(self):
        return f"{self.user.username}'s profile - {self.get_role_display()}"


class AuthenticationLog(models.Model):
    """Log authentication attempts"""
    username = models.CharField(max_length=150)
    success = models.BooleanField(default=False)
    message = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.username} - {'SUCCESS' if self.success else 'FAILED'} at {self.timestamp}"


class FaceEncoding(models.Model):
    """Store face encodings for registered users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    face_name = models.CharField(max_length=100)
    encoding = models.TextField()  # Store JSON serialized encoding
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.face_name}"
