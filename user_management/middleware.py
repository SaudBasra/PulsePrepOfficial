# user_management/middleware.py - Enhanced with Back Button Prevention
from django.conf import settings
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from .models import UserSession

class SingleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Skip for admin users
            if not request.user.is_admin and not request.user.is_superuser:
                # Get current session key
                current_session_key = request.session.session_key
                
                # If user's stored session key doesn't match current one, log them out
                if request.user.current_session_key and request.user.current_session_key != current_session_key:
                    logout(request)
                    messages.warning(request, "You've been logged out because you signed in from another device.")
                    return redirect(settings.LOGIN_URL)
                
                # Update last active time - FIXED TIMEZONE ISSUE
                request.user.last_active = timezone.now()
                request.user.save(update_fields=['last_active'])
                
                # Check if current session is marked as inactive in UserSession
                try:
                    session = UserSession.objects.get(session_key=current_session_key)
                    if not session.is_active:
                        logout(request)
                        messages.warning(request, "Your session has been terminated.")
                        return redirect(settings.LOGIN_URL)
                except UserSession.DoesNotExist:
                    pass
        
        response = self.get_response(request)
        return response


class AutomaticAccessControlMiddleware:
    """
    Middleware that automatically handles access control without template changes
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # URLs that require access control (content viewing)
        self.protected_url_patterns = [
            '/questionbank/',
            '/managemodule/',
            '/mocktest/',
            '/analytics/',
            '/modelpaper/',
            '/dashboard/',  # Students need approval to see dashboard
            '/my_profile/',  # Add profile protection
            '/notes/',
            '/progress/',
            '/practice/',
        ]
        
        # URLs that are completely exempt
        self.exempt_urls = [
            '/login/',
            '/signup/',
            '/logout/',
            '/admin/',
            '/static/',
            '/media/',
            '/api/users/',  # Admin user management APIs
        ]

    def __call__(self, request):
        # Skip if not authenticated
        if not request.user.is_authenticated:
            response = self.get_response(request)
            return response
        
        # Skip if exempt URL
        if self._is_exempt_url(request.path):
            response = self.get_response(request)
            return response
        
        # Skip if admin/superuser
        if request.user.is_admin or request.user.is_superuser:
            response = self.get_response(request)
            return response
        
        # Check if URL requires access control
        if self._requires_access_control(request.path):
            # Check approval status
            if request.user.approval_status != 'approved':
                degree_year = f"{request.user.degree} Year {request.user.year}" if request.user.degree and request.user.year else "your"
                messages.error(request, f"Your {degree_year} account is pending approval.")
                return redirect('user_management:login')
            
            # Check profile completeness
            if not request.user.degree or not request.user.year:
                messages.error(request, "Your profile is incomplete. Please contact administrator.")
                return redirect('user_management:login')
        
        response = self.get_response(request)
        return response
    
    def _is_exempt_url(self, path):
        """Check if URL is completely exempt"""
        for exempt_url in self.exempt_urls:
            if path.startswith(exempt_url):
                return True
        return False
    
    def _requires_access_control(self, path):
        """Check if URL requires access control"""
        for pattern in self.protected_url_patterns:
            if path.startswith(pattern):
                return True
        return False


class BackButtonSecurityMiddleware(MiddlewareMixin):
    """
    NEW: Middleware to add cache prevention headers to protected pages
    and prevent back button access after logout
    """
    
    # Pages that should have cache prevention headers
    PROTECTED_URLS = [
        'dashboard',
        'student_dashboard', 
        'admin_dashboard',
        'my_profile',
        'questionbank',
        'managemodule',
        'mocktest',
        'analytics',
        'notes',
        'practice',
        'progress',
        'modelpaper',
    ]
    
    def process_response(self, request, response):
        """Add cache prevention headers to protected pages"""
        
        # Add cache prevention headers to all protected pages
        if self._is_protected_url(request.path):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            # Additional security headers
            response['X-Frame-Options'] = 'SAMEORIGIN'
            response['X-Content-Type-Options'] = 'nosniff'
            
        # Special handling for logout page
        if 'logout' in request.path:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache' 
            response['Expires'] = '0'
            
        return response
    
    def _is_protected_url(self, path):
        """Check if the URL path requires cache prevention"""
        return any(protected in path for protected in self.PROTECTED_URLS)