
# notificationsetting/admin.py
from django.contrib import admin
from .models import Notification, NotificationCategory, NotificationPreference, NotificationTemplate

@admin.register(NotificationCategory)
class NotificationCategoryAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'is_active', 'color')
    list_filter = ('is_active',)
    search_fields = ('name', 'display_name')
    list_editable = ('is_active',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'notification_type', 'priority', 'recipient', 'is_read', 'created_at')
    list_filter = ('category', 'notification_type', 'priority', 'is_read', 'is_global', 'created_at')
    search_fields = ('title', 'message', 'recipient__email')
    date_hierarchy = 'created_at'
    list_editable = ('is_read',)
    readonly_fields = ('created_at', 'read_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'message', 'category', 'notification_type', 'priority')
        }),
        ('Recipient', {
            'fields': ('recipient', 'is_global', 'target_role')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_archived')
        }),
        ('Additional Options', {
            'fields': ('action_url', 'action_text', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'related_object_type', 'related_object_id'),
            'classes': ('collapse',)
        })
    )

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_enabled', 'webapp_enabled', 'email_digest_frequency')
    list_filter = ('email_enabled', 'webapp_enabled', 'email_digest_frequency')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'notification_type', 'priority', 'is_active')
    list_filter = ('category', 'notification_type', 'priority', 'is_active')
    search_fields = ('name', 'title_template', 'message_template')
    list_editable = ('is_active',)