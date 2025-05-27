# notificationsetting/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from questionbank.models import CSVImportHistory
from mocktest.models import TestAttempt
from .models import Notification, NotificationCategory
from .views import create_user_notification, create_global_notification

User = get_user_model()

@receiver(post_save, sender=User)
def user_registration_notification(sender, instance, created, **kwargs):
    """Send notification when a new user registers"""
    if created and not instance.is_admin and not instance.is_superuser:
        # Notify admins about new user registration
        admin_users = User.objects.filter(is_admin=True)
        
        for admin in admin_users:
            create_user_notification(
                user=admin,
                title="New User Registration",
                message=f"A new user {instance.first_name} {instance.last_name} ({instance.email}) has registered and is pending approval.",
                category='user',
                notification_type='info'
            )

@receiver(post_save, sender=User)
def user_approval_notification(sender, instance, **kwargs):
    """Send notification when user status changes"""
    if not instance.is_admin and not instance.is_superuser:
        # Check if approval status changed
        if hasattr(instance, '_state') and instance._state.adding == False:
            if instance.approval_status == 'approved':
                create_user_notification(
                    user=instance,
                    title="Account Approved! 🎉",
                    message="Congratulations! Your account has been approved. You can now access all features of PulsePrep.",
                    category='user',
                    notification_type='success'
                )
            elif instance.approval_status == 'rejected':
                create_user_notification(
                    user=instance,
                    title="Account Status Update",
                    message="Your account application has been reviewed. Please contact support for more information.",
                    category='user',
                    notification_type='warning'
                )

@receiver(post_save, sender=CSVImportHistory)
def csv_import_notification(sender, instance, created, **kwargs):
    """Send notification when CSV import completes"""
    if not created and instance.status != 'PROCESSING':
        user = instance.uploaded_by
        if user:
            if instance.status == 'SUCCESS':
                title = "CSV Import Successful ✅"
                message = f"Your CSV import '{instance.file_name}' completed successfully. {instance.successful_imports} questions were imported."
                notification_type = 'success'
            else:
                title = "CSV Import Failed ❌"
                message = f"Your CSV import '{instance.file_name}' failed. Please check the file format and try again."
                notification_type = 'error'
            
            create_user_notification(
                user=user,
                title=title,
                message=message,
                category='import',
                notification_type=notification_type
            )

@receiver(post_save, sender=TestAttempt)
def test_completion_notification(sender, instance, created, **kwargs):
    """Send notification when test is completed"""
    if not created and instance.status == 'completed':
        if instance.passed:
            title = "Test Passed! 🏆"
            message = f"Congratulations! You passed '{instance.mock_test.title}' with {instance.percentage:.1f}%."
            notification_type = 'success'
        else:
            title = "Test Completed"
            message = f"You completed '{instance.mock_test.title}' with {instance.percentage:.1f}%. Keep practicing!"
            notification_type = 'info'
        
        create_user_notification(
            user=instance.student,
            title=title,
            message=message,
            category='test',
            notification_type=notification_type
        )

