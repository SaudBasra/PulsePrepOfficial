# user_management/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from django.utils.html import format_html
from .models import CustomUser, UserSession

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'degree', 'year', 'colored_approval_status', 'is_admin', 'date_joined')
    list_filter = ('approval_status', 'degree', 'year', 'is_admin', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    actions = ['approve_users', 'reject_users']
    
    # Add colored status display
    def colored_approval_status(self, obj):
        colors = {
            'pending': '#ffa800',
            'approved': '#28a745', 
            'rejected': '#dc3545'
        }
        color = colors.get(obj.approval_status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.approval_status.title()
        )
    colored_approval_status.short_description = 'Status'
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'degree', 'year')}),
        ('Status & Permissions', {'fields': ('approval_status', 'is_admin', 'is_active', 'is_staff')}),
        ('Payment', {'fields': ('payment_slip',)}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'first_name', 'last_name', 
                      'degree', 'year', 'approval_status'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')
    
    @admin.action(description="✅ Approve selected users")
    def approve_users(self, request, queryset):
        updated = queryset.update(approval_status='approved')
        self.message_user(
            request,
            f"✅ {updated} user{'s' if updated != 1 else ''} approved successfully!",
            messages.SUCCESS
        )
    
    @admin.action(description="❌ Reject selected users")
    def reject_users(self, request, queryset):
        updated = queryset.update(approval_status='rejected')
        self.message_user(
            request,
            f"❌ {updated} user{'s' if updated != 1 else ''} rejected.",
            messages.WARNING
        )

# Simple UserSession admin
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('session_key', 'created_at')

# Register models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserSession, UserSessionAdmin)

# Customize admin site
admin.site.site_header = 'PulsePrep Administration'
admin.site.site_title = 'PulsePrep Admin' 
admin.site.index_title = 'Welcome to PulsePrep Admin Portal'