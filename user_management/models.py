# user_management/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class CustomUser(AbstractUser):
    APPROVAL_STATUS = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    DEGREE_CHOICES = (
        ('MBBS', 'MBBS'),
        ('BDS', 'BDS'),
    )
    
    YEAR_CHOICES = (
        (1, 'First Year'),
        (2, 'Second Year'),
        (3, 'Third Year'),
        (4, 'Fourth Year'),
        (5, 'Fifth Year'),
    )
    
    email = models.EmailField(unique=True)
    is_admin = models.BooleanField(default=False)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS, default='pending')
    degree = models.CharField(max_length=10, choices=DEGREE_CHOICES, blank=True, null=True)
    year = models.IntegerField(choices=YEAR_CHOICES, blank=True, null=True)
    last_active = models.DateTimeField(blank=True, null=True)
    current_session_key = models.CharField(max_length=40, blank=True, null=True)
    terms_accepted = models.BooleanField(default=False)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    payment_slip = models.ImageField(upload_to='payment_slips/', blank=True, null=True)

    # Use email for authentication instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
        
    def save(self, *args, **kwargs):
        # If username is not set, use email as username
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)
        
        
class UserSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.email} - {self.created_at}"