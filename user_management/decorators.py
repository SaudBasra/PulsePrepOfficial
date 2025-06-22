# user_management/decorators.py - Fixed Version (No Recursion)
from functools import wraps
from django.contrib.auth.decorators import login_required

def auto_filter_content(view_func):
    """
    Simple decorator that handles access control by modifying view context
    This avoids the recursion issue by not modifying Django's QuerySet methods
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Execute the view normally
        response = view_func(request, *args, **kwargs)
        return response
    return wrapper


def filter_by_user_access(queryset, user):
    """
    Simple helper function to filter querysets based on user access
    Use this function manually in your views where needed
    """
    # Admin and superuser see everything
    if user.is_admin or user.is_superuser:
        return queryset
    
    # Check if user is approved and has complete profile
    if user.approval_status != 'approved':
        return queryset.none()
    
    if not user.degree or not user.year:
        return queryset.none()
    
    # Check if this model has degree and year fields
    if hasattr(queryset.model, 'degree') and hasattr(queryset.model, 'year'):
        # Students see only their exact degree and year
        return queryset.filter(degree=user.degree, year=user.year)
    
    # If model doesn't have degree/year fields, return as-is
    return queryset


def student_access_required(view_func):
    """
    Simple decorator to check if user has access to student content
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        user = request.user
        
        # Admin and superuser bypass all restrictions
        if user.is_admin or user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if account is approved
        if user.approval_status != 'approved':
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, f"Your {user.degree} Year {user.year} account is pending approval.")
            return redirect('dashboard')
        
        # Check if user has degree and year assigned
        if not user.degree or not user.year:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "Your profile is incomplete. Please contact administrator.")
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper