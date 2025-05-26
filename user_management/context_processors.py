# user_management/context_processors.py
from django.contrib.auth import get_user_model
from django.db.models import Count

def user_stats(request):
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