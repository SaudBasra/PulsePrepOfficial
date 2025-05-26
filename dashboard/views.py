# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from user_management.models import CustomUser
from django.utils import timezone
from mocktest.models import TestAttempt

from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
import json

@login_required
def dashboard(request):
    """Route to appropriate dashboard based on user type"""
    if request.user.is_admin or request.user.is_superuser:
        return admin_dashboard(request)
    else:
        return student_dashboard(request)


@login_required
def dashboard(request):
    # Different dashboard for admin and students
    if request.user.is_admin or request.user.is_superuser:
        return admin_dashboard(request)
    else:
        return student_dashboard(request)

@login_required
def admin_dashboard(request):
    # Exclude admin users from statistics (only count regular users)
    regular_users = CustomUser.objects.filter(is_admin=False)
    
    # Basic counts (excluding admins)
    total_users = regular_users.count()
    pending_users = regular_users.filter(approval_status='pending').count()
    approved_users = regular_users.filter(approval_status='approved').count()
    rejected_users = regular_users.filter(approval_status='rejected').count()

    # Degree-based counts (excluding admins)
    mbbs_users = regular_users.filter(degree='MBBS').count()
    bds_users = regular_users.filter(degree='BDS').count()

    # Calculate percentages
    mbbs_percentage = round((mbbs_users / total_users * 100) if total_users > 0 else 0, 1)
    bds_percentage = round((bds_users / total_users * 100) if total_users > 0 else 0, 1)
    pending_percentage = round((pending_users / total_users * 100) if total_users > 0 else 0, 1)
    approved_percentage = round((approved_users / total_users * 100) if total_users > 0 else 0, 1)

    # Recent users (last 7 days, excluding admins)
    one_week_ago = timezone.now() - timedelta(days=7)
    new_mbbs_users = regular_users.filter(
        degree='MBBS', 
        date_joined__gte=one_week_ago
    ).count()
    new_bds_users = regular_users.filter(
        degree='BDS', 
        date_joined__gte=one_week_ago
    ).count()

    # Registration trends for the last 7 days
    registration_trends = []
    for i in range(6, -1, -1):  # Last 7 days
        date = timezone.now().date() - timedelta(days=i)
        mbbs_count = regular_users.filter(
            degree='MBBS',
            date_joined__date=date
        ).count()
        bds_count = regular_users.filter(
            degree='BDS',
            date_joined__date=date
        ).count()
        
        registration_trends.append({
            'date': date.strftime('%a'),  # Mon, Tue, etc.
            'mbbs': mbbs_count,
            'bds': bds_count,
            'total': mbbs_count + bds_count
        })

    # Recent users for display (last 5 of each degree, excluding admins)
    recent_mbbs_users = regular_users.filter(degree='MBBS').order_by('-date_joined')[:5]
    recent_bds_users = regular_users.filter(degree='BDS').order_by('-date_joined')[:5]

    # Pending approvals (most recent first)
    pending_approvals = regular_users.filter(
        approval_status='pending'
    ).order_by('-date_joined')[:5]

    # Status distribution for charts
    status_distribution = {
        'approved': approved_users,
        'pending': pending_users,
        'rejected': rejected_users
    }

    # Weekly registration summary
    weekly_stats = {
        'current_week': new_mbbs_users + new_bds_users,
        'mbbs_growth': calculate_growth_percentage('MBBS', regular_users),
        'bds_growth': calculate_growth_percentage('BDS', regular_users),
    }

    # Quick stats for header
    quick_stats = {
        'total_questions': get_total_questions_count(),
        'active_sessions': get_active_sessions_count(),
        'completion_rate': calculate_completion_rate(),
    }

    context = {
        # Basic statistics
        'total_users': total_users,
        'pending_users': pending_users,
        'approved_users': approved_users,
        'rejected_users': rejected_users,
        
        # Degree statistics
        'mbbs_users': mbbs_users,
        'bds_users': bds_users,
        'mbbs_percentage': mbbs_percentage,
        'bds_percentage': bds_percentage,
        'pending_percentage': pending_percentage,
        'approved_percentage': approved_percentage,
        
        # Weekly data
        'new_mbbs_users': new_mbbs_users,
        'new_bds_users': new_bds_users,
        'weekly_stats': weekly_stats,
        
        # User lists
        'recent_mbbs_users': recent_mbbs_users,
        'recent_bds_users': recent_bds_users,
        'pending_approvals': pending_approvals,
        
        # Chart data
        'registration_trends': json.dumps(registration_trends),
        'status_distribution': status_distribution,
        
        # Additional stats
        'quick_stats': quick_stats,
        
        # Time information
        'current_time': timezone.now(),
        'timezone_label': "Pakistan (Pakistan Standard Time, UTC+5)",
        
        # Growth indicators
        'mbbs_growth_trend': 'up' if weekly_stats['mbbs_growth'] > 0 else 'down',
        'bds_growth_trend': 'up' if weekly_stats['bds_growth'] > 0 else 'down',
    }

    return render(request, 'dashboard/admin_dashboard.html', context)


def calculate_growth_percentage(degree, regular_users):
    """Calculate weekly growth percentage for a specific degree"""
    current_week = timezone.now() - timedelta(days=7)
    previous_week = timezone.now() - timedelta(days=14)
    
    current_count = regular_users.filter(
        degree=degree,
        date_joined__gte=current_week
    ).count()
    
    previous_count = regular_users.filter(
        degree=degree,
        date_joined__gte=previous_week,
        date_joined__lt=current_week
    ).count()
    
    if previous_count == 0:
        return 100 if current_count > 0 else 0
    
    return round(((current_count - previous_count) / previous_count) * 100, 1)


def get_total_questions_count():
    """Get total questions count from questionbank"""
    try:
        from questionbank.models import Question
        return Question.objects.count()
    except ImportError:
        return 0


def get_active_sessions_count():
    """Get active user sessions count"""
    try:
        from user_management.models import UserSession
        return UserSession.objects.filter(is_active=True).count()
    except ImportError:
        return 0


def calculate_completion_rate():
    """Calculate average completion rate (placeholder for now)"""
    # This would be calculated based on mock test completion rates
    # For now, return a placeholder value
    return 85.5

def get_dashboard_data_json(request):
    """Return dashboard data as JSON for AJAX updates"""
    if not (request.user.is_admin or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    students_query = CustomUser.objects.filter(is_admin=False, is_superuser=False)
    
    # Calculate current metrics
    total_students = students_query.count()
    pending_students = students_query.filter(approval_status='pending').count()
    approved_students = students_query.filter(approval_status='approved').count()
    mbbs_students = students_query.filter(degree='MBBS').count()
    bds_students = students_query.filter(degree='BDS').count()
    
    def safe_percentage(part, total):
        return round((part / total * 100) if total > 0 else 0, 1)
    
    # Weekly data
    one_week_ago = timezone.now() - timedelta(days=7)
    new_students_this_week = students_query.filter(date_joined__gte=one_week_ago).count()
    
    data = {
        'total_students': total_students,
        'pending_students': pending_students,
        'approved_students': approved_students,
        'mbbs_students': mbbs_students,
        'bds_students': bds_students,
        'new_students_this_week': new_students_this_week,
        'chartData': {
            'mbbs_percentage': float(safe_percentage(mbbs_students, total_students)),
            'bds_percentage': float(safe_percentage(bds_students, total_students)),
            'pending_percentage': float(safe_percentage(pending_students, total_students)),
        },
        'timestamp': timezone.now().isoformat()
    }
    
    return JsonResponse(data)

@login_required
def student_dashboard(request):
    """Student dashboard view"""
    context = {
        'user': request.user,
        'current_time': timezone.now(),
        'timezone_label': "Pakistan Standard Time (UTC+5)",
    }
    return render(request, 'dashboard/student_dashboard.html', context)
def student_dashboard(request):
    user = request.user
    context = {
        'user': user,
        'current_time': timezone.now(),
        'timezone_label': "Pakistan (Pakistan Standard Time, UTC+5)",
    }
    return render(request, 'dashboard/student_dashboard.html', context)



"""
# dashboard/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import logout

def dashboard(request):
    # Add any context data needed for the dashboard
    context = {
        # Example data for the dashboard
        'total_users': 5230,
        'active_subscriptions': 700,
        'mbbs_percentage': 72,
        'bds_percentage': 72,
        'new_users_mbbs': 300,
        'new_users_bds': 100,
    }
    return render(request, 'dashboard.html', context)
"""
def manage_questions(request):
    # Placeholder for the manage questions view
    return render(request, 'questionbank.html')

def manage_modules(request):
    # Placeholder for the manage modules view
    return render(request, 'manage_modules.html')

def manage_users(request):
    # Placeholder for the manage users view
    return render(request, 'manage_users.html')

def mock_test(request):
    # Placeholder for the mock test view
    return render(request, 'mock_test.html')

def analytics_reports(request):
    # Placeholder for the analytics reports view
    return render(request, 'analytics_reports.html')

def my_account(request):
    # Placeholder for the my account view
    return render(request, 'my_account.html')

def notification(request):
    # Placeholder for the notification settings view
    return render(request, 'notification.html')

def settings(request):
    # Placeholder for the settings view
    return render(request, 'settings.html')

def logout_view(request):
    logout(request)
    return redirect('login')  # Redirect to login page after logout

def all_notifications(request):
    # Placeholder for the all notifications view
    return render(request, 'all_notifications.html')
    
