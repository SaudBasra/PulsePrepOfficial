
# notificationsetting/context_processors.py
from .models import Notification

def notification_context(request):
    """Add notification count to template context"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
            is_archived=False
        ).count()
        
        # Add global notifications
        global_count = Notification.objects.filter(
            is_global=True,
            target_role__in=['all', 'admin' if request.user.is_admin else 'student'],
            is_read=False,
            is_archived=False
        ).count()
        
        total_unread = unread_count + global_count
        
        return {
            'notification_count': total_unread,
            'has_notifications': total_unread > 0
        }
    
    return {
        'notification_count': 0,
        'has_notifications': False
    }

# Integration helper functions for other apps
def notify_user_registration(user):
    """Helper function to notify about user registration"""
    from .views import create_global_notification
    
    create_global_notification(
        title="New User Registered",
        message=f"A new user {user.first_name} {user.last_name} ({user.email}) has registered.",
        category='user',
        target_role='admin',
        notification_type='info'
    )

def notify_csv_import_complete(import_record):
    """Helper function to notify about CSV import completion"""
    from .views import create_user_notification
    
    if import_record.uploaded_by:
        if import_record.status == 'SUCCESS':
            create_user_notification(
                user=import_record.uploaded_by,
                title="CSV Import Completed",
                message=f"Successfully imported {import_record.successful_imports} questions from {import_record.file_name}",
                category='import',
                notification_type='success'
            )
        else:
            create_user_notification(
                user=import_record.uploaded_by,
                title="CSV Import Failed",
                message=f"Import of {import_record.file_name} failed. {import_record.failed_imports} errors occurred.",
                category='import',
                notification_type='error'
            )

def notify_test_result(test_attempt):
    """Helper function to notify about test completion"""
    from .views import create_user_notification
    
    if test_attempt.status == 'completed':
        if test_attempt.passed:
            title = "Test Passed! 🎉"
            message = f"Congratulations! You passed '{test_attempt.mock_test.title}' with {test_attempt.percentage:.1f}%."
            notification_type = 'success'
        else:
            title = "Test Completed"
            message = f"You completed '{test_attempt.mock_test.title}' with {test_attempt.percentage:.1f}%. Keep practicing!"
            notification_type = 'info'
        
        create_user_notification(
            user=test_attempt.student,
            title=title,
            message=message,
            category='test',
            notification_type=notification_type
        )

def notify_system_maintenance(start_time, duration_hours):
    """Helper function for system maintenance notifications"""
    from .views import create_global_notification
    
    create_global_notification(
        title="Scheduled Maintenance",
        message=f"System maintenance is scheduled for {start_time}. Expected duration: {duration_hours} hours. Some features may be unavailable during this time.",
        category='system',
        target_role='all',
        notification_type='warning'
    )

def notify_new_feature(feature_name, description):
    """Helper function for new feature announcements"""
    from .views import create_global_notification
    
    create_global_notification(
        title=f"New Feature: {feature_name}",
        message=description,
        category='announcement',
        target_role='all',
        notification_type='info'
    )