# notifications/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class NotificationMessage(models.Model):
    """Notification message model"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    # Optional: who it's for (None = everyone)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='user_notifications'
    )
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'notifications_message'
        verbose_name = 'Notification Message'
        verbose_name_plural = 'Notification Messages'
    
    def __str__(self):
        return self.title


# ===============================================
# notifications/apps.py
from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'


# ===============================================
# notifications/admin.py
from django.contrib import admin
from .models import NotificationMessage

@admin.register(NotificationMessage)
class NotificationMessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('title', 'content', 'recipient__email')
    date_hierarchy = 'created_at'
    list_editable = ('is_read',)
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient')

