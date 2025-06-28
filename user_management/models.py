# user_management/models.py - Enhanced with Email Verification
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

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
    voucher_reference = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Optional voucher code or reference number"
    )
    
    # NEW: Email verification and activation fields
    email_verified = models.BooleanField(default=False)
    activation_token = models.CharField(max_length=100, blank=True, null=True)
    activation_sent_at = models.DateTimeField(blank=True, null=True)
    activated_at = models.DateTimeField(blank=True, null=True)
    is_account_activated = models.BooleanField(default=False)  # Final activation status

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
    
    def generate_activation_token(self):
        """Generate a unique activation token"""
        self.activation_token = str(uuid.uuid4())
        return self.activation_token
    
    def is_activation_token_valid(self):
        """Check if activation token is still valid (72 hours)"""
        if not self.activation_sent_at:
            return False
        expiry_time = self.activation_sent_at + timezone.timedelta(hours=72)
        return timezone.now() < expiry_time
    
    @property
    def can_login(self):
        """Check if user can login (must be activated)"""
        return self.is_account_activated and self.approval_status == 'approved'
    
    @property
    def activation_status_display(self):
        """Human readable activation status"""
        if self.is_account_activated:
            return "Activated"
        elif self.activation_sent_at and self.is_activation_token_valid():
            return "Activation Pending"
        elif self.activation_sent_at and not self.is_activation_token_valid():
            return "Activation Expired"
        else:
            return "Not Sent"


class EmailLog(models.Model):
    EMAIL_TYPES = (
        ('activation', 'Account Activation'),
        ('approval_notification', 'Approval Notification'),
    )
    
    EMAIL_STATUS = (
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('bounced', 'Bounced'),
        ('failed', 'Failed'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='email_logs')
    email_type = models.CharField(max_length=50, choices=EMAIL_TYPES)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=EMAIL_STATUS, default='sent')
    sent_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.email_type} to {self.recipient_email} - {self.status}"


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