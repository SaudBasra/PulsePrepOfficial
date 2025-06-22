# user_management/context_processors.py - Enhanced
from django.contrib.auth import get_user_model
from django.db.models import Count

def user_stats(request):
    """Existing user stats context processor"""
    User = get_user_model()
    
    if not request.user.is_authenticated:
        return {}
    
    # Only run these queries for admin users
    if request.user.is_admin or request.user.is_superuser:
        total_users = User.objects.count()
        pending_users = User.objects.filter(approval_status='pending').count()
        mbbs_users = User.objects.filter(degree='MBBS').count()
        bds_users = User.objects.filter(degree='BDS').count()
        
        return {
            'total_users': total_users,
            'pending_users': pending_users,
            'mbbs_users': mbbs_users,
            'bds_users': bds_users,
        }
    
    return {}


def user_access_context(request):
    """New context processor for user access information"""
    if not request.user.is_authenticated:
        return {
            'user_access_level': 'guest',
            'user_degree_year': None,
            'can_access_content': False,
        }
    
    user = request.user
    
    # Admin users
    if user.is_admin or user.is_superuser:
        return {
            'user_access_level': 'admin',
            'user_degree_year': 'Administrator',
            'can_access_content': True,
            'content_filter': None,
        }
    
    # Regular users
    if user.approval_status != 'approved':
        return {
            'user_access_level': 'pending',
            'user_degree_year': f"{user.degree} Year {user.year}" if user.degree and user.year else "Profile Incomplete",
            'can_access_content': False,
            'approval_status': user.approval_status,
        }
    
    if not user.degree or not user.year:
        return {
            'user_access_level': 'incomplete',
            'user_degree_year': "Profile Incomplete",
            'can_access_content': False,
        }
    
    # Approved users with complete profiles
    return {
        'user_access_level': 'student',
        'user_degree_year': f"{user.degree} Year {user.year}",
        'can_access_content': True,
        'content_filter': {
            'degree': user.degree,
            'year': user.year,
        },
        'user_degree': user.degree,
        'user_year': user.year,
    }