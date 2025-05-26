# user_management/middleware.py
from django.conf import settings
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from .models import UserSession
import datetime

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
                
                # Update last active time
                request.user.last_active = datetime.datetime.now()
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