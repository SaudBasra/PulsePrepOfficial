# notificationsetting/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class NotificationCategory(models.Model):
    """Categories for different types of notifications"""
    CATEGORY_CHOICES = [
        ('system', 'System Notifications'),
        ('test', 'Test Notifications'),
        ('user', 'User Management'),
        ('import', 'Import Notifications'),
        ('announcement', 'Announcements'),
    ]
    
    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-bell')
    color = models.CharField(max_length=7, default='#667eea')  # Hex color
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.display_name
    
    class Meta:
        ordering = ['display_name']
        verbose_name_plural = "Notification Categories"


class Notification(models.Model):
    """Main notification model"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    category = models.ForeignKey(NotificationCategory, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Recipients
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        null=True, 
        blank=True
    )
    is_global = models.BooleanField(default=False)  # Global notifications for all users
    target_role = models.CharField(
        max_length=20, 
        choices=[('admin', 'Admin'), ('student', 'Student'), ('all', 'All')],
        default='all'
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Optional data for dynamic content
    action_url = models.URLField(blank=True, null=True)
    action_text = models.CharField(max_length=100, blank=True)
    
    # Related objects (optional, for context)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['is_global', '-created_at']),
            models.Index(fields=['is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient or 'Global'}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @classmethod
    def create_notification(cls, title, message, category_name, recipient=None, 
                          notification_type='info', priority='medium', 
                          action_url=None, action_text=None, is_global=False, 
                          target_role='all', expires_in_days=None):
        """Helper method to create notifications"""
        try:
            category = NotificationCategory.objects.get(name=category_name)
        except NotificationCategory.DoesNotExist:
            # Create default category if it doesn't exist
            category = NotificationCategory.objects.create(
                name=category_name,
                display_name=category_name.title()
            )
        
        expires_at = None
        if expires_in_days:
            expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
        
        return cls.objects.create(
            title=title,
            message=message,
            category=category,
            recipient=recipient,
            notification_type=notification_type,
            priority=priority,
            action_url=action_url,
            action_text=action_text,
            is_global=is_global,
            target_role=target_role,
            expires_at=expires_at
        )


class NotificationPreference(models.Model):
    """User preferences for notifications"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email notifications
    email_enabled = models.BooleanField(default=True)
    email_digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly Digest'),
            ('never', 'Never'),
        ],
        default='daily'
    )
    
    # In-app notifications
    webapp_enabled = models.BooleanField(default=True)
    show_desktop_notifications = models.BooleanField(default=True)
    
    # Category preferences
    system_notifications = models.BooleanField(default=True)
    test_notifications = models.BooleanField(default=True)
    user_notifications = models.BooleanField(default=True)
    import_notifications = models.BooleanField(default=True)
    announcement_notifications = models.BooleanField(default=True)
    
    # Sound and visual
    sound_enabled = models.BooleanField(default=False)
    show_notification_count = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.user.email}"
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create notification preferences for a user"""
        prefs, created = cls.objects.get_or_create(user=user)
        return prefs


class NotificationTemplate(models.Model):
    """Templates for common notification types"""
    name = models.CharField(max_length=100, unique=True)
    title_template = models.CharField(max_length=200)
    message_template = models.TextField()
    category = models.ForeignKey(NotificationCategory, on_delete=models.CASCADE)
    notification_type = models.CharField(
        max_length=10, 
        choices=Notification.TYPE_CHOICES, 
        default='info'
    )
    priority = models.CharField(
        max_length=10, 
        choices=Notification.PRIORITY_CHOICES, 
        default='medium'
    )
    
    # Template variables help text
    available_variables = models.TextField(
        help_text="List of available template variables (e.g., {user_name}, {test_name})",
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def render(self, context=None):
        """Render the template with given context"""
        if context is None:
            context = {}
        
        title = self.title_template.format(**context)
        message = self.message_template.format(**context)
        
        return title, message
    
    class Meta:
        ordering = ['name']