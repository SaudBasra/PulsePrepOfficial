# user_management/admin.py - Add context processor for navigation

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from django.utils.html import format_html
from django.urls import reverse, path
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import CustomUser, UserSession, EmailLog
from .email_service import EmailService
import json
import uuid

# Add this context processor function
def admin_navigation_context(request):
    """Provide navigation context for all admin pages"""
    try:
        pending_users = CustomUser.objects.filter(approval_status='pending').count()
        pending_activation = CustomUser.objects.filter(
            approval_status='approved', 
            is_account_activated=False
        ).count()
        context = {
            'pending_users': pending_users,
            'pending_activation': pending_activation,
        }
        print(f"DEBUG: Navigation context created: {context}")  # Debug line
        return context
    except Exception as e:
        print(f"DEBUG: Error in navigation context: {e}")  # Debug line
        return {
            'pending_users': 0,
            'pending_activation': 0,
        }

# Add this mixin for consistent navigation
class NavigationContextMixin:
    """Mixin to add navigation context to all admin views"""
    
    def get_common_context(self, request):
        """Get common navigation context"""
        return admin_navigation_context(request)
    
    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context.update(self.get_common_context(request))
        return super().changelist_view(request, extra_context=extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context.update(self.get_common_context(request))
        return super().change_view(request, object_id, form_url, extra_context)
    
    def add_view(self, request, form_url='', extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context.update(self.get_common_context(request))
        return super().add_view(request, form_url, extra_context)

class EmailLogInline(admin.TabularInline):
    model = EmailLog
    extra = 0
    readonly_fields = ('email_type', 'recipient_email', 'subject', 'status', 'sent_at', 'error_message')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

class CustomUserAdmin(NavigationContextMixin, UserAdmin):
    list_display = (
        'email', 'full_name', 'degree_year', 'voucher_reference', 
        'colored_approval_status', 'activation_status_display', 'email_status_display',
        'is_admin', 'date_joined', 'action_buttons'
    )
    list_filter = (
        'approval_status', 'is_account_activated', 'degree', 'year', 
        'is_admin', 'date_joined', 'voucher_reference'
    )
    search_fields = ('email', 'first_name', 'last_name', 'voucher_reference')
    ordering = ('-date_joined',)
    list_per_page = 10
    actions = [
        'approve_users_and_send_emails', 'reject_users', 'send_activation_emails', 
        'manually_activate_accounts', 'resend_activation_emails'
    ]
    
    inlines = [EmailLogInline]
    
    # Override ALL view methods to ensure navigation context
    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add navigation context"""
        if extra_context is None:
            extra_context = {}
        try:
            nav_context = admin_navigation_context(request)
            extra_context.update(nav_context)
            print(f"DEBUG: Changelist context added: {nav_context}")  # Debug line
        except Exception as e:
            print(f"DEBUG: Error adding navigation context: {e}")  # Debug line
            extra_context.update({'pending_users': 0, 'pending_activation': 0})
        
        return super().changelist_view(request, extra_context=extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Override change view to add navigation context"""
        if extra_context is None:
            extra_context = {}
        try:
            nav_context = admin_navigation_context(request)
            extra_context.update(nav_context)
        except Exception as e:
            extra_context.update({'pending_users': 0, 'pending_activation': 0})
        
        return super().change_view(request, object_id, form_url, extra_context)
    
    def add_view(self, request, form_url='', extra_context=None):
        """Override add view to add navigation context"""
        if extra_context is None:
            extra_context = {}
        try:
            nav_context = admin_navigation_context(request)
            extra_context.update(nav_context)
        except Exception as e:
            extra_context.update({'pending_users': 0, 'pending_activation': 0})
        
        return super().add_view(request, form_url, extra_context)
    
    # Custom display methods
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Name'
    
    def degree_year(self, obj):
        if obj.degree and obj.year:
            return f"{obj.degree} Year {obj.year}"
        return "Not Set"
    degree_year.short_description = 'Access Level'
    
    def colored_approval_status(self, obj):
        colors = {
            'pending': '#ffa800',
            'approved': '#28a745', 
            'rejected': '#6c757d'
        }
        color = colors.get(obj.approval_status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.approval_status.title()
        )
    colored_approval_status.short_description = 'Approval Status'
    
    def activation_status_display(self, obj):
        if obj.is_account_activated:
            return format_html('<span style="color: #28a745; font-weight: bold;">✅ Activated</span>')
        elif obj.activation_sent_at and obj.is_activation_token_valid():
            return format_html('<span style="color: #ffa800; font-weight: bold;">⏳ Pending</span>')
        elif obj.activation_sent_at and not obj.is_activation_token_valid():
            return format_html('<span style="color: #6c757d; font-weight: bold;">⏰ Expired</span>')
        else:
            return format_html('<span style="color: #6c757d;">📧 Not Sent</span>')
    activation_status_display.short_description = 'Activation Status'
    
    def email_status_display(self, obj):
        latest_email = obj.email_logs.filter(email_type='activation').first()
        if latest_email:
            if latest_email.status == 'sent':
                return format_html('<span style="color: #28a745;">📧 Sent</span>')
            elif latest_email.status == 'failed':
                return format_html('<span style="color: #6c757d;">❌ Failed</span>')
            elif latest_email.status == 'bounced':
                return format_html('<span style="color: #ffa800;">⚠️ Bounced</span>')
        return format_html('<span style="color: #6c757d;">-</span>')
    email_status_display.short_description = 'Email Status'
    
    def action_buttons(self, obj):
        """Enhanced action buttons with better styling and no red colors"""
        buttons = []
        
        if obj.approval_status == 'pending':
            buttons.append(
                f'<a class="admin-action-btn approve-btn" href="{reverse("admin:approve_user", args=[obj.pk])}" '
                f'title="Approve User">✅ Approve</a>'
            )
        
        if obj.approval_status == 'approved' and not obj.is_account_activated:
            buttons.append(
                f'<a class="admin-action-btn email-btn" href="{reverse("admin:send_activation_email", args=[obj.pk])}" '
                f'title="Send Activation Email">Send Email</a>'
            )
            buttons.append(
                f'<a class="admin-action-btn activate-btn" href="{reverse("admin:manual_activate", args=[obj.pk])}" '
                f'title="Manually Activate Account">Active Now</a>'
            )
        
        return mark_safe(''.join(buttons)) if buttons else '-'
    action_buttons.short_description = 'Quick Actions'
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'degree', 'year')}),
        ('Registration Info', {'fields': ('voucher_reference', 'terms_accepted')}),
        ('Status & Permissions', {'fields': ('approval_status', 'is_admin', 'is_active', 'is_staff')}),
        ('Activation Info', {
            'fields': ('is_account_activated', 'activation_sent_at', 'activated_at'),
            'classes': ('collapse',)
        }),
        ('Files', {'fields': ('profile_image', 'payment_slip')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'first_name', 'last_name', 
                      'degree', 'year', 'voucher_reference', 'approval_status'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login', 'activation_sent_at', 'activated_at')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('approve/<int:user_id>/', self.admin_site.admin_view(self.approve_user_view), name='approve_user'),
            path('send-activation/<int:user_id>/', self.admin_site.admin_view(self.send_activation_email_view), name='send_activation_email'),
            path('manual-activate/<int:user_id>/', self.admin_site.admin_view(self.manual_activate_view), name='manual_activate'),
            path('email-dashboard/', self.admin_site.admin_view(self.email_dashboard_view), name='email_dashboard'),
            path('api/navigation-counts/', self.admin_site.admin_view(self.navigation_counts_api), name='navigation_counts_api'),
        ]
        return custom_urls + urls
    
    def navigation_counts_api(self, request):
        """API endpoint for navigation counts"""
        context = admin_navigation_context(request)
        return JsonResponse(context)
    
    def approve_user_view(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        
        if user.approval_status != 'approved':
            user.approval_status = 'approved'
            user.save()
            
            success, message = EmailService.send_activation_email(user, request)
            
            if success:
                self.message_user(
                    request,
                    f"✅ {user.email} approved and activation email sent!",
                    messages.SUCCESS
                )
            else:
                self.message_user(
                    request,
                    f"✅ {user.email} approved but email failed: {message}",
                    messages.WARNING
                )
        else:
            self.message_user(request, f"{user.email} is already approved.", messages.INFO)
        
        return HttpResponseRedirect(reverse('admin:user_management_customuser_changelist'))
    
    def send_activation_email_view(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        
        if user.approval_status != 'approved':
            self.message_user(request, f"User {user.email} must be approved first.", messages.ERROR)
            return HttpResponseRedirect(reverse('admin:user_management_customuser_changelist'))
        
        if user.is_account_activated:
            self.message_user(request, f"User {user.email} is already activated.", messages.INFO)
            return HttpResponseRedirect(reverse('admin:user_management_customuser_changelist'))
        
        success, message = EmailService.send_activation_email(user, request)
        
        if success:
            self.message_user(
                request,
                f"✅ Activation email sent successfully to {user.email}!",
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                f"Email sending failed to {user.email}: {message}",
                messages.ERROR
            )
        
        return HttpResponseRedirect(reverse('admin:user_management_customuser_changelist'))
    
    def manual_activate_view(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        
        if user.is_account_activated:
            self.message_user(request, "User account is already activated.", messages.INFO)
        elif user.approval_status != 'approved':
            self.message_user(request, "User must be approved first.", messages.ERROR)
        else:
            user.is_account_activated = True
            user.activated_at = timezone.now()
            user.activation_token = None
            user.save()
            
            self.message_user(
                request,
                f"🔑 {user.email} account manually activated!",
                messages.SUCCESS
            )
        
        return HttpResponseRedirect(reverse('admin:user_management_customuser_changelist'))
    
    def email_dashboard_view(self, request):
        from django.core.paginator import Paginator
        
        total_emails = EmailLog.objects.count()
        sent_emails = EmailLog.objects.filter(status='sent').count()
        failed_emails = EmailLog.objects.filter(status='failed').count()
        
        recent_emails = EmailLog.objects.select_related('user').order_by('-sent_at')
        
        paginator = Paginator(recent_emails, 15)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        total_users = CustomUser.objects.count()
        activated_users = CustomUser.objects.filter(is_account_activated=True).count()
        pending_activation = CustomUser.objects.filter(
            approval_status='approved', 
            is_account_activated=False
        ).count()
        pending_users = CustomUser.objects.filter(approval_status='pending').count()
        
        context = {
            'title': 'Email Dashboard',
            'total_emails': total_emails,
            'sent_emails': sent_emails,
            'failed_emails': failed_emails,
            'recent_emails': recent_emails,
            'page_obj': page_obj,
            'total_users': total_users,
            'activated_users': activated_users,
            'pending_activation': pending_activation,
            'pending_users': pending_users,
            'success_rate': round((sent_emails / total_emails * 100) if total_emails > 0 else 100, 1),
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/email_dashboard.html', context)
    
    # Admin Actions
    @admin.action(description="✅ Approve selected users and send activation emails")
    def approve_users_and_send_emails(self, request, queryset):
        approved_count = 0
        email_sent_count = 0
        
        for user in queryset.filter(approval_status__in=['pending', 'rejected']):
            user.approval_status = 'approved'
            user.save()
            approved_count += 1
            
            if not user.is_account_activated:
                success, message = EmailService.send_activation_email(user, request)
                if success:
                    email_sent_count += 1
        
        self.message_user(
            request,
            f"✅ {approved_count} user{'s' if approved_count != 1 else ''} approved. "
            f"📧 {email_sent_count} activation email{'s' if email_sent_count != 1 else ''} sent.",
            messages.SUCCESS
        )
    
    @admin.action(description="⏸️ Set selected users to pending")
    def reject_users(self, request, queryset):
        updated = queryset.update(approval_status='rejected')
        self.message_user(
            request,
            f"⏸️ {updated} user{'s' if updated != 1 else ''} set to rejected status.",
            messages.WARNING
        )
    
    @admin.action(description="📧 Send activation emails to approved users")
    def send_activation_emails(self, request, queryset):
        users_to_email = queryset.filter(
            approval_status='approved',
            is_account_activated=False
        )
        
        if not users_to_email.exists():
            self.message_user(
                request,
                "No approved, non-activated users selected.",
                messages.WARNING
            )
            return
        
        results = EmailService.send_bulk_activation_emails(users_to_email, request)
        
        self.message_user(
            request,
            f"📧 Activation emails: {results['sent']} sent, {results['failed']} failed",
            messages.SUCCESS if results['sent'] > 0 else messages.ERROR
        )
    
    @admin.action(description="🔄 Resend activation emails")
    def resend_activation_emails(self, request, queryset):
        users_to_email = queryset.filter(
            approval_status='approved',
            is_account_activated=False
        )
        
        if not users_to_email.exists():
            self.message_user(
                request,
                "No approved, non-activated users selected.",
                messages.WARNING
            )
            return
        
        results = EmailService.send_bulk_activation_emails(users_to_email, request)
        
        self.message_user(
            request,
            f"🔄 Activation emails resent: {results['sent']} successful, {results['failed']} failed",
            messages.SUCCESS if results['sent'] > 0 else messages.ERROR
        )
    
    @admin.action(description="🔑 Manually activate selected accounts")
    def manually_activate_accounts(self, request, queryset):
        users_to_activate = queryset.filter(
            approval_status='approved',
            is_account_activated=False
        )
        
        if not users_to_activate.exists():
            self.message_user(
                request,
                "No approved, non-activated users selected.",
                messages.WARNING
            )
            return
        
        updated = users_to_activate.update(
            is_account_activated=True,
            activated_at=timezone.now(),
            activation_token=None
        )
        
        self.message_user(
            request,
            f"🔑 {updated} account{'s' if updated != 1 else ''} manually activated.",
            messages.SUCCESS
        )

class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_type', 'recipient_email', 'colored_status', 'sent_at')
    list_filter = ('email_type', 'status', 'sent_at')
    search_fields = ('user__email', 'recipient_email', 'subject')
    readonly_fields = ('user', 'email_type', 'recipient_email', 'subject', 'status', 'sent_at', 'error_message')
    ordering = ('-sent_at',)
    list_per_page = 25
    
    # Override changelist_view to add navigation context
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(admin_navigation_context(request))
        return super().changelist_view(request, extra_context=extra_context)
    
    # Override change_view to add navigation context
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(admin_navigation_context(request))
        return super().change_view(request, object_id, form_url, extra_context)
    
    def colored_status(self, obj):
        colors = {
            'sent': '#28a745',
            'delivered': '#20c997',
            'bounced': '#ffc107',
            'failed': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status.title()
        )
    colored_status.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('session_key', 'created_at')
    list_per_page = 20
    
    # Override changelist_view to add navigation context
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(admin_navigation_context(request))
        return super().changelist_view(request, extra_context=extra_context)

# Register models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(EmailLog, EmailLogAdmin)
admin.site.register(UserSession, UserSessionAdmin)

# Customize admin site
admin.site.site_header = 'PulsePrep Administration'
admin.site.site_title = 'PulsePrep Admin' 
admin.site.index_title = 'Welcome to PulsePrep Admin Portal'