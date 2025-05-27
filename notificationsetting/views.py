# notificationsetting/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.urls import reverse
import json

from .models import Notification, NotificationCategory, NotificationPreference, NotificationTemplate
from user_management.models import CustomUser

@login_required
def notificationsetting(request):
    """Main notification center view"""
    
    # Get user's notification preferences
    prefs = NotificationPreference.get_or_create_for_user(request.user)
    
    # Get filters from request
    category_filter = request.GET.get('category', '')
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', 'unread')  # Default to unread
    
    # Build query for user's notifications
    notifications = Notification.objects.filter(
        Q(recipient=request.user) | 
        Q(is_global=True, target_role__in=['all', 'admin' if request.user.is_admin else 'student'])
    ).exclude(is_archived=True)
    
    # Apply filters
    if category_filter:
        notifications = notifications.filter(category__name=category_filter)
    
    if type_filter:
        notifications = notifications.filter(notification_type=type_filter)
    
    if status_filter == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status_filter == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Order by priority and creation date
    notifications = notifications.select_related('category').order_by(
        '-priority', '-created_at'
    )
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    total_notifications = Notification.objects.filter(
        Q(recipient=request.user) | 
        Q(is_global=True, target_role__in=['all', 'admin' if request.user.is_admin else 'student'])
    ).exclude(is_archived=True).count()
    
    unread_count = Notification.objects.filter(
        Q(recipient=request.user) | 
        Q(is_global=True, target_role__in=['all', 'admin' if request.user.is_admin else 'student']),
        is_read=False
    ).exclude(is_archived=True).count()
    
    # Get categories for filter dropdown
    categories = NotificationCategory.objects.filter(is_active=True)
    
    # Recent activity for admin users
    recent_activity = []
    if request.user.is_admin or request.user.is_superuser:
        recent_activity = Notification.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).values('category__display_name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
    
    context = {
        'page_obj': page_obj,
        'preferences': prefs,
        'categories': categories,
        'total_notifications': total_notifications,
        'unread_count': unread_count,
        'recent_activity': recent_activity,
        
        # Filter values
        'category_filter': category_filter,
        'type_filter': type_filter,
        'status_filter': status_filter,
        
        # Choices for filters
        'type_choices': Notification.TYPE_CHOICES,
        'status_choices': [
            ('all', 'All'),
            ('unread', 'Unread'),
            ('read', 'Read'),
        ],
    }
    
    return render(request, 'notificationsetting/notification_center.html', context)


@login_required
def notification_preferences(request):
    """User notification preferences management"""
    
    prefs = NotificationPreference.get_or_create_for_user(request.user)
    
    if request.method == 'POST':
        # Update preferences
        prefs.email_enabled = request.POST.get('email_enabled') == 'on'
        prefs.email_digest_frequency = request.POST.get('email_digest_frequency', 'daily')
        prefs.webapp_enabled = request.POST.get('webapp_enabled') == 'on'
        prefs.show_desktop_notifications = request.POST.get('show_desktop_notifications') == 'on'
        prefs.system_notifications = request.POST.get('system_notifications') == 'on'
        prefs.test_notifications = request.POST.get('test_notifications') == 'on'
        prefs.user_notifications = request.POST.get('user_notifications') == 'on'
        prefs.import_notifications = request.POST.get('import_notifications') == 'on'
        prefs.announcement_notifications = request.POST.get('announcement_notifications') == 'on'
        prefs.sound_enabled = request.POST.get('sound_enabled') == 'on'
        prefs.show_notification_count = request.POST.get('show_notification_count') == 'on'
        
        prefs.save()
        messages.success(request, 'Notification preferences updated successfully!')
        return redirect('notification_preferences')
    
    context = {
        'preferences': prefs,
        'digest_choices': NotificationPreference._meta.get_field('email_digest_frequency').choices,
    }
    
    return render(request, 'notificationsetting/preferences.html', context)


@require_POST
@login_required
def mark_notification_read(request):
    """Mark a notification as read"""
    notification_id = request.POST.get('notification_id')
    try:
        notification = Notification.objects.get(
            Q(id=notification_id) &
            (Q(recipient=request.user) | Q(is_global=True, target_role__in=['all', 'admin' if request.user.is_admin else 'student']))
        )
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})
@require_POST
@login_required
def mark_all_read(request):
    """Mark all notifications as read for the current user"""
    notifications = Notification.objects.filter(
        Q(recipient=request.user) | 
        Q(is_global=True, target_role__in=['all', 'admin' if request.user.is_admin else 'student']),
        is_read=False
    ).exclude(is_archived=True)
    
    count = notifications.count()
    notifications.update(is_read=True, read_at=timezone.now())
    
    return JsonResponse({'success': True, 'count': count})

@require_POST
@login_required
def archive_notification(request):
    """Archive a notification"""
    notification_id = request.POST.get('notification_id')
    
    try:
        notification = Notification.objects.get(
            Q(id=notification_id) &
            (Q(recipient=request.user) | Q(is_global=True, target_role__in=['all', 'admin' if request.user.is_admin else 'student']))
        )
        notification.is_archived = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})



@login_required
def get_notification_count(request):
    """Get unread notification count for the current user"""
    count = Notification.objects.filter(
        Q(recipient=request.user) | 
        Q(is_global=True, target_role__in=['all', 'admin' if request.user.is_admin else 'student']),
        is_read=False
    ).exclude(is_archived=True).count()
    
    return JsonResponse({'count': count})


# Admin views
@login_required
def admin_notifications(request):
    """Admin notification management"""
    if not (request.user.is_admin or request.user.is_superuser):
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('notificationsetting')
    
    # Get all notifications with statistics
    notifications = Notification.objects.all().select_related('category', 'recipient')
    
    # Get filter parameters
    category_filter = request.GET.get('category', '')
    type_filter = request.GET.get('type', '')
    recipient_filter = request.GET.get('recipient', '')
    
    # Apply filters
    if category_filter:
        notifications = notifications.filter(category__name=category_filter)
    if type_filter:
        notifications = notifications.filter(notification_type=type_filter)
    if recipient_filter:
        if recipient_filter == 'global':
            notifications = notifications.filter(is_global=True)
        else:
            notifications = notifications.filter(recipient__email__icontains=recipient_filter)
    
    # Pagination
    paginator = Paginator(notifications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total': Notification.objects.count(),
        'unread': Notification.objects.filter(is_read=False).count(),
        'global': Notification.objects.filter(is_global=True).count(),
        'this_week': Notification.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count(),
    }
    
    # Categories and templates
    categories = NotificationCategory.objects.filter(is_active=True)
    templates = NotificationTemplate.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'templates': templates,
        'stats': stats,
        'category_filter': category_filter,
        'type_filter': type_filter,
        'recipient_filter': recipient_filter,
        'type_choices': Notification.TYPE_CHOICES,
    }
    
    return render(request, 'notificationsetting/admin_notifications.html', context)


@login_required
def create_notification(request):
    """Admin create new notification"""
    if not (request.user.is_admin or request.user.is_superuser):
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            message = request.POST.get('message')
            category_id = request.POST.get('category')
            notification_type = request.POST.get('type', 'info')
            priority = request.POST.get('priority', 'medium')
            target_role = request.POST.get('target_role', 'all')
            recipient_email = request.POST.get('recipient_email', '')
            action_url = request.POST.get('action_url', '')
            action_text = request.POST.get('action_text', '')
            expires_in_days = request.POST.get('expires_in_days', '')
            
            # Get category
            category = NotificationCategory.objects.get(id=category_id)
            
            # Determine recipient and global flag
            recipient = None
            is_global = False
            
            if recipient_email:
                try:
                    recipient = CustomUser.objects.get(email=recipient_email)
                except CustomUser.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'User not found'})
            else:
                is_global = True
            
            # Handle expiration
            expires_at = None
            if expires_in_days:
                try:
                    days = int(expires_in_days)
                    expires_at = timezone.now() + timezone.timedelta(days=days)
                except ValueError:
                    pass
            
            # Create notification
            notification = Notification.objects.create(
                title=title,
                message=message,
                category=category,
                notification_type=notification_type,
                priority=priority,
                recipient=recipient,
                is_global=is_global,
                target_role=target_role,
                action_url=action_url or None,
                action_text=action_text or None,
                expires_at=expires_at
            )
            
            return JsonResponse({'success': True, 'notification_id': notification.id})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# Utility functions for creating notifications
def create_user_notification(user, title, message, category='user', notification_type='info'):
    """Helper function to create user-specific notifications"""
    return Notification.create_notification(
        title=title,
        message=message,
        category_name=category,
        recipient=user,
        notification_type=notification_type
    )

def create_global_notification(title, message, category='announcement', target_role='all', notification_type='info'):
    """Helper function to create global notifications"""
    return Notification.create_notification(
        title=title,
        message=message,
        category_name=category,
        is_global=True,
        target_role=target_role,
        notification_type=notification_type
    )