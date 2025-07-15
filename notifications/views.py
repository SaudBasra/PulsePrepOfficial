# notifications/views.py - Enhanced with Degree/Year Filtering
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from user_management.models import CustomUser
from .models import NotificationMessage

@login_required
def notification_center(request):
    """Enhanced notification center with degree/year filtering"""
    
    # Handle POST request for sending notifications (Admin only)
    if request.method == 'POST' and (request.user.is_admin or request.user.is_superuser):
        title = request.POST.get('title')
        content = request.POST.get('content')
        target_type = request.POST.get('target_type', 'all')
        target_degree = request.POST.get('target_degree', '')
        target_year = request.POST.get('target_year', '')
        
        if title and content:
            try:
                recipients = []
                count = 0
                
                if target_type == 'all':
                    # Send to everyone (global notification)
                    NotificationMessage.objects.create(
                        title=title,
                        content=content,
                        recipient=None  # Global notification
                    )
                    count = CustomUser.objects.count()
                    messages.success(request, f'Notification sent to all users ({count} users)!')
                    
                elif target_type == 'students':
                    # Get base queryset for students
                    students_query = CustomUser.objects.filter(
                        is_admin=False, 
                        is_superuser=False,
                        approval_status='approved'  # Only send to approved students
                    )
                    
                    # Apply degree filter if specified
                    if target_degree and target_degree != 'all':
                        students_query = students_query.filter(degree=target_degree)
                    
                    # Apply year filter if specified
                    if target_year and target_year != 'all':
                        try:
                            year_int = int(target_year)
                            students_query = students_query.filter(year=year_int)
                        except (ValueError, TypeError):
                            pass
                    
                    # Create notifications for filtered students
                    students = students_query.all()
                    for student in students:
                        NotificationMessage.objects.create(
                            title=title,
                            content=content,
                            recipient=student
                        )
                        count += 1
                    
                    # Build success message with filter details
                    filter_details = []
                    if target_degree and target_degree != 'all':
                        filter_details.append(f"Degree: {target_degree}")
                    if target_year and target_year != 'all':
                        year_display = dict(CustomUser.YEAR_CHOICES).get(int(target_year), target_year)
                        filter_details.append(f"Year: {year_display}")
                    
                    filter_text = f" ({', '.join(filter_details)})" if filter_details else ""
                    messages.success(request, f'Notification sent to {count} students{filter_text}!')
                    
                elif target_type == 'admins':
                    # Send to all admins
                    admins = CustomUser.objects.filter(Q(is_admin=True) | Q(is_superuser=True))
                    for admin in admins:
                        NotificationMessage.objects.create(
                            title=title,
                            content=content,
                            recipient=admin
                        )
                        count += 1
                    messages.success(request, f'Notification sent to {count} admins!')
                    
                elif target_type == 'specific':
                    # Send to specific degree/year combination
                    if target_degree and target_year:
                        try:
                            year_int = int(target_year)
                            specific_users = CustomUser.objects.filter(
                                degree=target_degree,
                                year=year_int,
                                approval_status='approved',
                                is_admin=False,
                                is_superuser=False
                            )
                            
                            for user in specific_users:
                                NotificationMessage.objects.create(
                                    title=title,
                                    content=content,
                                    recipient=user
                                )
                                count += 1
                                
                            year_display = dict(CustomUser.YEAR_CHOICES).get(year_int, target_year)
                            messages.success(request, f'Notification sent to {count} students in {target_degree} Year {year_display}!')
                        except (ValueError, TypeError):
                            messages.error(request, 'Invalid year selection!')
                    else:
                        messages.error(request, 'Both degree and year must be selected for specific targeting!')
                    
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
        
        # Get admin stats (for admin users)
        admin_stats = {}
        if request.user.is_admin or request.user.is_superuser:
            admin_stats = {
                'total_notifications': NotificationMessage.objects.count(),
                'global_notifications': NotificationMessage.objects.filter(recipient__isnull=True).count(),
                'user_specific_notifications': NotificationMessage.objects.filter(recipient__isnull=False).count(),
                'unread_system_wide': NotificationMessage.objects.filter(is_read=False).count(),
            }
        
        # Get user statistics for form dropdowns (admin only)
        user_stats = {}
        if request.user.is_admin or request.user.is_superuser:
            # Count students by degree
            mbbs_students = CustomUser.objects.filter(
                degree='MBBS', is_admin=False, is_superuser=False, approval_status='approved'
            ).count()
            bds_students = CustomUser.objects.filter(
                degree='BDS', is_admin=False, is_superuser=False, approval_status='approved'
            ).count()
            
            # Count students by year
            year_counts = {}
            for year_num, year_display in CustomUser.YEAR_CHOICES:
                year_counts[year_num] = CustomUser.objects.filter(
                    year=year_num, is_admin=False, is_superuser=False, approval_status='approved'
                ).count()
            
            # Count students by degree and year combination
            degree_year_counts = {}
            for degree in ['MBBS', 'BDS']:
                degree_year_counts[degree] = {}
                for year_num, year_display in CustomUser.YEAR_CHOICES:
                    degree_year_counts[degree][year_num] = CustomUser.objects.filter(
                        degree=degree, year=year_num, is_admin=False, is_superuser=False, approval_status='approved'
                    ).count()
            
            user_stats = {
                'mbbs_students': mbbs_students,
                'bds_students': bds_students,
                'year_counts': year_counts,
                'degree_year_counts': degree_year_counts,
                'total_students': mbbs_students + bds_students,
                'total_admins': CustomUser.objects.filter(Q(is_admin=True) | Q(is_superuser=True)).count(),
            }
        
    except Exception as e:
        user_notifications = []
        total_count = 0
        unread_count = 0
        admin_stats = {}
        user_stats = {}
    
    context = {
        'notifications': user_notifications,
        'total_count': total_count,
        'unread_count': unread_count,
        'admin_stats': admin_stats,
        'user_stats': user_stats,
        'degree_choices': CustomUser.DEGREE_CHOICES,
        'year_choices': CustomUser.YEAR_CHOICES,
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
def delete_notification(request, notification_id):
    """Delete a specific notification for the current user"""
    try:
        # Only allow deletion of user-specific notifications or if user is admin
        if request.user.is_admin or request.user.is_superuser:
            # Admins can delete any notification
            notification = get_object_or_404(NotificationMessage, id=notification_id)
            notification.delete()
            messages.success(request, 'Notification deleted successfully!')
        else:
            # Regular users can only delete their own notifications (not global ones)
            notification = get_object_or_404(
                NotificationMessage, 
                id=notification_id, 
                recipient=request.user
            )
            notification.delete()
            messages.success(request, 'Notification deleted successfully!')
            
    except NotificationMessage.DoesNotExist:
        messages.error(request, 'Notification not found or you do not have permission to delete it!')
    except Exception as e:
        messages.error(request, f'Error deleting notification: {str(e)}')
    
    # Check where the user came from and redirect accordingly
    referer = request.META.get('HTTP_REFERER', '')
    if 'student' in referer:
        return redirect('student_notifications')
    else:
        return redirect('notification_center')


@login_required
@require_POST
def reset_all_notifications(request):
    """Reset all notifications - Admin only with warning confirmation"""
    if not (request.user.is_admin or request.user.is_superuser):
        messages.error(request, 'You do not have permission to reset all notifications!')
        return redirect('notification_center')
    
    # Check for confirmation
    confirmation = request.POST.get('confirm_reset')
    if confirmation != 'RESET_ALL_NOTIFICATIONS':
        messages.error(request, 'Invalid confirmation. Please type exactly: RESET_ALL_NOTIFICATIONS')
        return redirect('notification_center')
    
    try:
        # Get count before deletion
        total_count = NotificationMessage.objects.count()
        
        # Delete ALL notifications
        NotificationMessage.objects.all().delete()
        
        messages.success(request, f'Successfully reset all notifications! Deleted {total_count} notifications from the system.')
        
    except Exception as e:
        messages.error(request, f'Error resetting notifications: {str(e)}')
    
    return redirect('notification_center')


# ====================================================================
# STUDENT-SPECIFIC VIEWS
# ====================================================================

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
        
        # Count read notifications (for delete functionality)
        read_count = notifications_qs.filter(is_read=True).count()
        
    except Exception as e:
        user_notifications = []
        total_count = 0
        unread_count = 0
        read_count = 0
    
    context = {
        'notifications': user_notifications,
        'total_count': total_count,
        'unread_count': unread_count,
        'read_count': read_count,
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


# ====================================================================
# AJAX/API VIEWS
# ====================================================================

@login_required
@require_POST
@csrf_exempt
def ajax_mark_read(request, notification_id):
    """AJAX endpoint to mark notification as read"""
    try:
        notification = NotificationMessage.objects.get(
            Q(id=notification_id) & (Q(recipient=request.user) | Q(recipient__isnull=True))
        )
        notification.is_read = True
        notification.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
    except NotificationMessage.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Notification not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_POST
@csrf_exempt
def ajax_delete_notification(request, notification_id):
    """AJAX endpoint to delete notification"""
    try:
        if request.user.is_admin or request.user.is_superuser:
            notification = get_object_or_404(NotificationMessage, id=notification_id)
        else:
            notification = get_object_or_404(
                NotificationMessage, 
                id=notification_id, 
                recipient=request.user
            )
        
        notification.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification deleted successfully'
        })
    except NotificationMessage.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Notification not found or permission denied'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ====================================================================
# AJAX API FOR USER COUNTS (Admin only)
# ====================================================================

@login_required
@require_POST
@csrf_exempt
def get_user_count(request):
    """AJAX endpoint to get user count for specific filters"""
    if not (request.user.is_admin or request.user.is_superuser):
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    try:
        target_type = request.POST.get('target_type')
        target_degree = request.POST.get('target_degree', '')
        target_year = request.POST.get('target_year', '')
        
        count = 0
        
        if target_type == 'all':
            count = CustomUser.objects.count()
        elif target_type == 'students':
            students_query = CustomUser.objects.filter(
                is_admin=False, 
                is_superuser=False,
                approval_status='approved'
            )
            
            if target_degree and target_degree != 'all':
                students_query = students_query.filter(degree=target_degree)
            
            if target_year and target_year != 'all':
                try:
                    year_int = int(target_year)
                    students_query = students_query.filter(year=year_int)
                except (ValueError, TypeError):
                    pass
            
            count = students_query.count()
        elif target_type == 'admins':
            count = CustomUser.objects.filter(Q(is_admin=True) | Q(is_superuser=True)).count()
        elif target_type == 'specific':
            if target_degree and target_year:
                try:
                    year_int = int(target_year)
                    count = CustomUser.objects.filter(
                        degree=target_degree,
                        year=year_int,
                        approval_status='approved',
                        is_admin=False,
                        is_superuser=False
                    ).count()
                except (ValueError, TypeError):
                    count = 0
        
        return JsonResponse({
            'success': True,
            'count': count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)