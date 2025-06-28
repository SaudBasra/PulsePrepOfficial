# user_management/context_processors.py - Enhanced with Admin Navigation
"""
Context processors for user management admin interface
"""
from django.contrib.auth import get_user_model
from django.db.models import Count

def admin_navigation_stats(request):
    """
    Provide statistics for admin navigation header
    """
    User = get_user_model()
    
    if not request.user.is_authenticated:
        return {}
    
    # Only provide stats for admin users in admin interface
    if (request.user.is_admin or request.user.is_superuser) and '/admin/' in request.path:
        try:
            pending_users = User.objects.filter(approval_status='pending').count()
            pending_activation = User.objects.filter(
                approval_status='approved', 
                is_account_activated=False
            ).count()
            
            return {
                'pending_users': pending_users,
                'pending_activation': pending_activation,
            }
        except Exception:
            # Return defaults if database query fails
            return {
                'pending_users': 0,
                'pending_activation': 0,
            }
    
    return {}

def user_stats(request):
    """
    General user statistics context processor
    """
    User = get_user_model()

    if not request.user.is_authenticated:
        return {}

    # Only run these queries for admin users
    if request.user.is_admin or request.user.is_superuser:
        try:
            total_users = User.objects.count()
            pending_users = User.objects.filter(approval_status='pending').count()
            activated_users = User.objects.filter(is_account_activated=True).count()
            mbbs_users = User.objects.filter(degree='MBBS').count()
            bds_users = User.objects.filter(degree='BDS').count()

            return {
                'total_users': total_users,
                'pending_users': pending_users,
                'activated_users': activated_users,
                'mbbs_users': mbbs_users,
                'bds_users': bds_users,
            }
        except Exception:
            # Return defaults if database query fails
            return {
                'total_users': 0,
                'pending_users': 0,
                'activated_users': 0,
                'mbbs_users': 0,
                'bds_users': 0,
            }

    return {}

def user_access_context(request):
    """
    User access context processor for general application use
    """
    if not request.user.is_authenticated:
        return {
            'user_access_level': 'guest',
            'user_access_display': 'Guest User',
            'can_access_content': False,
            'user_filter_params': None,
        }

    user = request.user

    # Determine user access level
    if user.is_admin or user.is_superuser:
        access_info = {
            'level': 'admin',
            'display': 'Administrator',
            'can_access': True,
            'filter_params': None
        }
    elif user.approval_status == 'approved' and user.is_account_activated and user.degree and user.year:
        access_info = {
            'level': 'student',
            'display': f'{user.degree} Year {user.year}',
            'can_access': True,
            'filter_params': {'degree': user.degree, 'year': user.year}
        }
    elif user.approval_status == 'approved' and not user.is_account_activated:
        access_info = {
            'level': 'pending_activation',
            'display': 'Pending Activation',
            'can_access': False,
            'filter_params': None
        }
    elif user.approval_status == 'pending':
        access_info = {
            'level': 'pending_approval',
            'display': 'Pending Approval',
            'can_access': False,
            'filter_params': None
        }
    else:
        access_info = {
            'level': 'restricted',
            'display': 'Access Restricted',
            'can_access': False,
            'filter_params': None
        }

    return {
        'user_access_level': access_info['level'],
        'user_access_display': access_info['display'], 
        'can_access_content': access_info['can_access'],
        'user_filter_params': access_info.get('filter_params'),
        'is_admin': user.is_admin or user.is_superuser,
        'is_student': not (user.is_admin or user.is_superuser),
    }