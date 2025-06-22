# notifications/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from user_management.models import CustomUser
from .models import NotificationMessage

@login_required
def notification_center(request):
    """Notification center with admin send functionality"""
    
    # Handle POST request for sending notifications (Admin only)
    if request.method == 'POST' and (request.user.is_admin or request.user.is_superuser):
        title = request.POST.get('title')
        content = request.POST.get('content')
        target_type = request.POST.get('target_type', 'all')
        
        if title and content:
            try:
                if target_type == 'all':
                    # Send to everyone (global notification)
                    NotificationMessage.objects.create(
                        title=title,
                        content=content,
                        recipient=None  # Global notification
                    )
                    messages.success(request, f'Notification sent to all users!')
                    
                elif target_type == 'students':
                    # Send to all students
                    students = CustomUser.objects.filter(is_admin=False, is_superuser=False)
                    count = 0
                    for student in students:
                        NotificationMessage.objects.create(
                            title=title,
                            content=content,
                            recipient=student
                        )
                        count += 1
                    messages.success(request, f'Notification sent to {count} students!')
                    
                elif target_type == 'admins':
                    # Send to all admins
                    admins = CustomUser.objects.filter(Q(is_admin=True) | Q(is_superuser=True))
                    count = 0
                    for admin in admins:
                        NotificationMessage.objects.create(
                            title=title,
                            content=content,
                            recipient=admin
                        )
                        count += 1
                    messages.success(request, f'Notification sent to {count} admins!')
                    
            except Exception as e:
                messages.error(request, f'Error sending notification: {str(e)}')
        else:
            messages.error(request, 'Title and content are required!')
        
        return redirect('notification_center')
    
    # Handle GET request (display notifications)
    try:
        # Get notifications for this user (or global ones)
        notifications_qs = NotificationMessage.objects.filter(
            Q(recipient=request.user) | Q(recipient__isnull=True)
        ).order_by('-created_at')
        
        # Pagination
        paginator = Paginator(notifications_qs, 10)
        page_number = request.GET.get('page')
        user_notifications = paginator.get_page(page_number)
        total_count = notifications_qs.count()
        
        # Count unread notifications
        unread_count = notifications_qs.filter(is_read=False).count()
        
    except Exception as e:
        user_notifications = []
        total_count = 0
        unread_count = 0
    
    context = {
        'notifications': user_notifications,
        'total_count': total_count,
        'unread_count': unread_count,
    }
    
    return render(request, 'notifications/notification_center.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    try:
        notification = NotificationMessage.objects.get(
            Q(id=notification_id) & (Q(recipient=request.user) | Q(recipient__isnull=True))
        )
        notification.is_read = True
        notification.save()
        messages.success(request, 'Notification marked as read!')
    except NotificationMessage.DoesNotExist:
        messages.error(request, 'Notification not found!')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    # Check where the user came from and redirect accordingly
    referer = request.META.get('HTTP_REFERER', '')
    if 'student' in referer:
        return redirect('student_notifications')
    else:
        return redirect('notification_center')


@login_required
def mark_all_read(request):
    """Mark all notifications as read for current user"""
    try:
        # Mark user-specific notifications as read
        user_notifications = NotificationMessage.objects.filter(
            Q(recipient=request.user) | Q(recipient__isnull=True),
            is_read=False
        )
        count = user_notifications.update(is_read=True)
        
        if count > 0:
            messages.success(request, f'Marked {count} notifications as read!')
        else:
            messages.info(request, 'No unread notifications found!')
            
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    # Check where the user came from and redirect accordingly
    referer = request.META.get('HTTP_REFERER', '')
    if 'student' in referer:
        return redirect('student_notifications')
    else:
        return redirect('notification_center')


@login_required
def student_notifications(request):
    """Student-only notification view"""
    
    try:
        # Get notifications for this user (or global ones)
        notifications_qs = NotificationMessage.objects.filter(
            Q(recipient=request.user) | Q(recipient__isnull=True)
        ).order_by('-created_at')
        
        # Pagination
        paginator = Paginator(notifications_qs, 10)
        page_number = request.GET.get('page')
        user_notifications = paginator.get_page(page_number)
        total_count = notifications_qs.count()
        
        # Count unread notifications
        unread_count = notifications_qs.filter(is_read=False).count()
        
    except Exception as e:
        user_notifications = []
        total_count = 0
        unread_count = 0
    
    context = {
        'notifications': user_notifications,
        'total_count': total_count,
        'unread_count': unread_count,
    }
    
    return render(request, 'notifications/student_notifications.html', context)


@login_required
def student_mark_notification_read(request, notification_id):
    """Mark a specific notification as read (Student version)"""
    try:
        notification = NotificationMessage.objects.get(
            Q(id=notification_id) & (Q(recipient=request.user) | Q(recipient__isnull=True))
        )
        notification.is_read = True
        notification.save()
        messages.success(request, 'Notification marked as read!')
    except NotificationMessage.DoesNotExist:
        messages.error(request, 'Notification not found!')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('student_notifications')


@login_required
def student_mark_all_read(request):
    """Mark all notifications as read for current user (Student version)"""
    try:
        # Mark user-specific notifications as read
        user_notifications = NotificationMessage.objects.filter(
            Q(recipient=request.user) | Q(recipient__isnull=True),
            is_read=False
        )
        count = user_notifications.update(is_read=True)
        
        if count > 0:
            messages.success(request, f'Marked {count} notifications as read!')
        else:
            messages.info(request, 'No unread notifications found!')
            
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('student_notifications')