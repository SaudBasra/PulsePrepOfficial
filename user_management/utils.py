# user_management/utils.py - UPDATED TO HANDLE MODEL PAPERS
"""
Enhanced utility functions for access control system with ModelPaper support
"""

def convert_user_year_to_string(user_year):
    """
    Convert user's integer year to question's string format
    User model: year = 1, 2, 3, 4, 5 (integer)
    Question model: year = '1st', '2nd', '3rd', '4th', '5th' (string)
    """
    if not user_year:
        return None
    
    year_conversion = {
        1: '1st',
        2: '2nd', 
        3: '3rd',
        4: '4th',
        5: '5th'
    }
    return year_conversion.get(user_year)

def apply_user_access_filter(queryset, user):
    """
    ENHANCED Smart filter that automatically applies user access control
    NOW PROPERLY HANDLES MODEL PAPERS
    
    Args:
        queryset: Django QuerySet to filter
        user: CustomUser instance
    
    Returns:
        Filtered QuerySet based on user's access rights
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
    
    # Get model to handle different filtering logic
    model = queryset.model
    model_name = model.__name__
    
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
    
    # STANDARD HANDLING FOR OTHER MODELS
    # Check if this model has degree and year fields
    if hasattr(model, 'degree') and hasattr(model, 'year'):
        # Apply filtering - students see only their exact degree and year
        return queryset.filter(
            degree=user.degree,
            year=user_year_string
        )
    
    # For models that might be linked to questions (like notes, practice sessions)
    if hasattr(model, 'student'):
        # These are user-specific models, filter by user ownership first
        user_owned = queryset.filter(student=user)
        
        # Then apply degree/year filtering if the model has those fields
        if hasattr(model, 'degree') and hasattr(model, 'year'):
            return user_owned.filter(degree=user.degree, year=user_year_string)
        return user_owned
    
    # For models linked through foreign keys to questions
    if hasattr(model, 'question'):
        # Filter through the related question's degree and year
        return queryset.filter(
            question__degree=user.degree,
            question__year=user_year_string
        )
    
    # If model doesn't have degree/year fields and no question relation, return as-is
    return queryset

def get_user_access_info(user):
    """
    ENHANCED Get user access information for display and logic
    """
    if not user or not user.is_authenticated:
        return {
            'level': 'guest',
            'display': 'Guest User',
            'can_access': False,
            'degree': None,
            'year': None,
            'filter_params': {}
        }
    
    if user.is_admin or user.is_superuser:
        return {
            'level': 'admin',
            'display': 'Administrator - Full Access to All Content',
            'can_access': True,
            'degree': None,
            'year': None,
            'filter_params': {},
            'can_create_tests': True,
            'can_manage_users': True,
            'can_view_analytics': True,
        }
    
    if user.approval_status != 'approved':
        return {
            'level': 'pending',
            'display': f'{user.degree} Year {user.year} - Pending Approval',
            'can_access': False,
            'approval_status': user.approval_status,
            'degree': user.degree,
            'year': user.year,
            'filter_params': {}
        }
    
    if not user.degree or not user.year:
        return {
            'level': 'incomplete',
            'display': 'Profile Incomplete - Contact Administrator',
            'can_access': False,
            'degree': user.degree,
            'year': user.year,
            'filter_params': {}
        }
    
    # Approved student with complete profile
    user_year_string = convert_user_year_to_string(user.year)
    return {
        'level': 'student',
        'display': f'{user.degree} Year {user_year_string} - Content Access',
        'can_access': True,
        'degree': user.degree,
        'year': user.year,
        'year_string': user_year_string,
        'filter_params': {
            'degree': user.degree,
            'year': user_year_string
        },
        'can_create_tests': False,
        'can_manage_users': False,
        'can_view_analytics': False,
    }

def check_object_access(obj, user):
    """
    ENHANCED Check if user can access a specific object
    NOW PROPERLY HANDLES MODEL PAPERS
    """
    if not user or not user.is_authenticated:
        return False
    
    # Admins can access everything
    if user.is_admin or user.is_superuser:
        return True
    
    # Check basic user requirements
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
    
    # Check if object has degree/year fields (standard models)
    if hasattr(obj, 'degree') and hasattr(obj, 'year'):
        return (obj.degree == user.degree and obj.year == user_year_string)
    
    # Check if object is user-owned
    if hasattr(obj, 'student'):
        return obj.student == user
    
    # If no degree/year fields and not user-owned, allow access
    return True