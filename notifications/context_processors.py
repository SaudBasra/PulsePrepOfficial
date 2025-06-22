# notifications/context_processors.py
from django.db.models import Q
from .models import NotificationMessage

def notification_context(request):
    """
    Simple context processor to provide notification count to all templates
    """
    if request.user.is_authenticated:
        try:
            # Get unread notifications for current user (including global notifications)
            unread_count = NotificationMessage.objects.filter(
                Q(recipient=request.user) | Q(recipient__isnull=True),
                is_read=False
            ).count()
            
            return {
                'unread_count': unread_count,
            }
        except Exception:
            return {'unread_count': 0}
    
    return {'unread_count': 0}