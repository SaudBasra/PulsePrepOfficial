# user_management/decorators.py - UPDATED TO HANDLE MODEL PAPERS
"""
Enhanced decorators file that properly handles ModelPaper filtering
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse

def convert_user_year_to_string(user_year):
    """Convert user's integer year to question's string format"""
    if not user_year:
        return None
    
    year_conversion = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 5: '5th'}
    return year_conversion.get(user_year)

def apply_user_access_filter(queryset, user):
    """
    ENHANCED Filter queryset based on user access - NOW HANDLES MODEL PAPERS CORRECTLY
    """
    # Admin and superuser see everything
    if user.is_admin or user.is_superuser:
        return queryset
    
    # Check if user has access
    if user.approval_status != 'approved':
        return queryset.none()
    
    if not user.degree or not user.year:
        return queryset.none()
    
    # Convert user year to string format
    user_year_string = convert_user_year_to_string(user.year)
    if not user_year_string:
        return queryset.none()
    
    # Get model name to handle different filtering logic
    model_name = queryset.model.__name__
    
    # SPECIAL HANDLING FOR MODEL PAPERS
    if model_name == 'ModelPaper':
        # ModelPaper uses filter_degree and filter_year fields
        # Logic: Show papers where:
        # 1. Both filter fields are empty (accessible to all), OR
        # 2. filter_degree matches user degree (if set), AND
        # 3. filter_year matches user year (if set)
        
        from django.db.models import Q
        
        # Papers with no degree filter OR degree matches user
        degree_condition = (
            Q(filter_degree__isnull=True) |
            Q(filter_degree='') |
            Q(filter_degree=user.degree)
        )
        
        # Papers with no year filter OR year matches user
        year_condition = (
            Q(filter_year__isnull=True) |
            Q(filter_year='') |
            Q(filter_year=user_year_string)
        )
        
        # Combine conditions
        filter_condition = degree_condition & year_condition
        
        return queryset.filter(filter_condition)
    
    # STANDARD HANDLING FOR OTHER MODELS (Questions, etc.)
    # Check if this model has degree and year fields
    if hasattr(queryset.model, 'degree') and hasattr(queryset.model, 'year'):
        # Apply filtering - students see only their exact degree and year
        return queryset.filter(
            degree=user.degree,
            year=user_year_string
        )
    
    # For models that might be linked to questions (like notes, practice sessions)
    if hasattr(queryset.model, 'student'):
        # These are user-specific models, filter by user ownership first
        user_owned = queryset.filter(student=user)
        
        # Then apply degree/year filtering if the model has those fields
        if hasattr(queryset.model, 'degree') and hasattr(queryset.model, 'year'):
            return user_owned.filter(degree=user.degree, year=user_year_string)
        return user_owned
    
    # For models linked through foreign keys to questions
    if hasattr(queryset.model, 'question'):
        # Filter through the related question's degree and year
        return queryset.filter(
            question__degree=user.degree,
            question__year=user_year_string
        )
    
    # If model doesn't have degree/year fields and no question relation, return as-is
    return queryset

def check_object_access(obj, user):
    """
    ENHANCED Check if a user can access a specific object
    """
    if not user or not user.is_authenticated:
        return False
    
    # Admin and superuser can access everything
    if user.is_admin or user.is_superuser:
        return True
    
    # Check user approval and profile
    if user.approval_status != 'approved' or not user.degree or not user.year:
        return False
    
    # Convert user year to string format
    user_year_string = convert_user_year_to_string(user.year)
    if not user_year_string:
        return False
    
    # Get model name to handle different types
    model_name = obj.__class__.__name__
    
    # SPECIAL HANDLING FOR MODEL PAPERS
    if model_name == 'ModelPaper':
        # ModelPaper access logic: if filter fields are set, they must match user's degree/year
        # If filter fields are empty, paper is accessible to all
        
        # If both filter_degree and filter_year are empty, paper is accessible
        if not obj.filter_degree and not obj.filter_year:
            return True
        
        # If only degree filter is set, check degree match
        if obj.filter_degree and not obj.filter_year:
            return obj.filter_degree == user.degree
        
        # If only year filter is set, check year match
        if obj.filter_year and not obj.filter_degree:
            return obj.filter_year == user_year_string
        
        # If both filters are set, both must match
        if obj.filter_degree and obj.filter_year:
            return (obj.filter_degree == user.degree and 
                   obj.filter_year == user_year_string)
        
        return True
    
    # Check object-specific access for other models
    if hasattr(obj, 'student'):
        # User-owned objects (notes, practice sessions, etc.)
        if obj.student != user:
            return False
        
        # Also check degree/year if the object has them
        if hasattr(obj, 'degree') and hasattr(obj, 'year'):
            return obj.degree == user.degree and obj.year == user_year_string
        
        return True
    
    # Objects with degree/year fields (questions, etc.)
    if hasattr(obj, 'degree') and hasattr(obj, 'year'):
        return obj.degree == user.degree and obj.year == user_year_string
    
    # Objects linked to questions
    if hasattr(obj, 'question'):
        question = obj.question
        if hasattr(question, 'degree') and hasattr(question, 'year'):
            return question.degree == user.degree and question.year == user_year_string
    
    # For mock tests, check through test questions
    if model_name == 'MockTest':
        # Check if any test questions are accessible to the user
        test_questions = obj.testquestion_set.all()
        for tq in test_questions:
            if hasattr(tq.question, 'degree') and hasattr(tq.question, 'year'):
                if (tq.question.degree == user.degree and 
                    tq.question.year == user_year_string):
                    return True
        return False
    
    # Default: allow access if no specific restrictions
    return True

def content_access_required(view_func):
    """
    Decorator that checks if user can access content
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        user = request.user
        
        # Allow admins through without any restrictions
        if user.is_admin or user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if account is approved
        if user.approval_status != 'approved':
            messages.error(request, f"Your {user.degree} Year {user.year} account is pending approval.")
            return redirect('/dashboard/')
        
        # Check if user has degree and year assigned
        if not user.degree or not user.year:
            messages.error(request, "Your profile is incomplete. Please contact administrator.")
            return redirect('/dashboard/')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

def admin_required(view_func):
    """
    Decorator for admin-only views
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        user = request.user
        
        if not (user.is_admin or user.is_superuser):
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({'error': 'Admin access required'}, status=403)
            messages.error(request, "You don't have permission to access this page.")
            return redirect('/dashboard/')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

# LEGACY COMPATIBILITY - These are the functions your existing views are importing
def auto_filter_content(view_func):
    """
    Legacy decorator - redirects to content_access_required
    This fixes the import error in managemodule/views.py
    """
    return content_access_required(view_func)

def filter_by_user_access(queryset, user):
    """
    Legacy function - redirects to apply_user_access_filter
    This maintains compatibility with existing code
    """
    return apply_user_access_filter(queryset, user)

def student_access_required(view_func):
    """
    Legacy decorator - redirects to content_access_required
    This maintains compatibility with existing code
    """
    return content_access_required(view_func)