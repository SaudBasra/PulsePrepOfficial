# user_management/email_service.py - Complete Fixed Version
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from .models import EmailLog
import logging
import smtplib
import uuid

logger = logging.getLogger(__name__)

class EmailService:
    """Professional email service for user account management"""
    
    @staticmethod
    def validate_email_settings():
        """Validate email configuration"""
        required_settings = [
            'EMAIL_HOST',
            'EMAIL_PORT', 
            'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD',
            'DEFAULT_FROM_EMAIL'
        ]
        
        missing = []
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                missing.append(setting)
        
        if missing:
            raise Exception(f"Missing email settings: {', '.join(missing)}")
        
        return True
    
    @staticmethod
    def test_smtp_connection():
        """Test SMTP connection without sending email"""
        try:
            EmailService.validate_email_settings()
            
            # Test SMTP connection
            if getattr(settings, 'EMAIL_USE_SSL', False):
                smtp = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT)
            else:
                smtp = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
                if getattr(settings, 'EMAIL_USE_TLS', False):
                    smtp.starttls()
            
            smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            smtp.quit()
            
            logger.info("SMTP connection test successful")
            return True, "SMTP connection successful"
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def send_activation_email(user, request=None):
        """Send account activation email that stays in inbox permanently"""
        try:
            # Validate email settings first
            EmailService.validate_email_settings()
            
            # Test SMTP connection
            smtp_success, smtp_message = EmailService.test_smtp_connection()
            if not smtp_success:
                error_msg = f"SMTP connection failed: {smtp_message}"
                logger.error(error_msg)
                
                # Log failed email
                EmailLog.objects.create(
                    user=user,
                    email_type='activation',
                    recipient_email=user.email,
                    subject='Account Activation',
                    status='failed',
                    error_message=error_msg
                )
                
                return False, error_msg
            
            # Generate activation token
            if not user.activation_token:
                user.activation_token = str(uuid.uuid4())
                user.activation_sent_at = timezone.now()
                user.save(update_fields=['activation_token', 'activation_sent_at'])
            
            # Build activation URL
            if request:
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
            else:
                domain = 'pulseprep.net' if not settings.DEBUG else 'localhost:8000'
                protocol = 'https' if 'pulseprep.net' in domain else 'http'
            
            activation_url = f"{protocol}://{domain}{reverse('user_management:activate_account', kwargs={'token': user.activation_token})}"
            
            # Make it look like regular email, not system email
            degree_year = f"{user.degree} Year {user.year}" if user.degree and user.year else "Student"
            subject = f"Welcome to PulsePrep - Your {user.degree} Account Details"
            
            # Use personal, conversational tone
            message = f'''
Dear {user.first_name},

Thank you for joining PulsePrep! We're excited to have you as part of our {degree_year} community.

Your account has been approved and is ready to use. To get started with your studies, please confirm your account by clicking the link below:

🔗 Complete Your Registration: {activation_url}

ACCOUNT INFORMATION:
📧 Email: {user.email}
🎓 Program: {degree_year}
⏰ Access Expires: 72 hours from now

WHAT'S INCLUDED IN YOUR ACCOUNT:
• Complete question bank for {degree_year}
• Practice tests and mock examinations
• Study progress tracking and analytics
• Access to study notes and materials
• Performance insights and recommendations

IMPORTANT: Please save this email for your records. It contains your account information and registration link.

If you have any questions or need assistance, please don't hesitate to contact our support team at support@pulseprep.net.

Best regards,
Dr. Sarah Ahmed
Academic Director
PulsePrep Medical Education

---
PulsePrep - Your Medical Education Partner
📧 support@pulseprep.net | 🌐 pulseprep.net

This email contains important account information. Please keep it for your records.
            '''
            
            # Send with specific headers to avoid auto-deletion
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email='Dr. Sarah Ahmed <support@pulseprep.net>',
                to=[user.email],
                headers={
                    'X-Priority': '1',
                    'X-MSMail-Priority': 'High',
                    'Importance': 'high',
                    'X-Mailer': 'PulsePrep Education Platform',
                    'List-Unsubscribe': '<mailto:unsubscribe@pulseprep.net>',
                    'X-Auto-Response-Suppress': 'DR, RN, NRN, OOF, AutoReply',
                }
            )
            
            success = email.send(fail_silently=False)
            
            if success:
                # Log successful email
                EmailLog.objects.create(
                    user=user,
                    email_type='activation',
                    recipient_email=user.email,
                    subject=subject,
                    status='sent'
                )
                
                logger.info(f"Activation email sent successfully to {user.email}")
                return True, "Account welcome email sent successfully"
            else:
                error_msg = "Email sending returned False"
                logger.error(error_msg)
                
                EmailLog.objects.create(
                    user=user,
                    email_type='activation',
                    recipient_email=user.email,
                    subject=subject,
                    status='failed',
                    error_message=error_msg
                )
                
                return False, error_msg
                
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP Authentication failed: Check email credentials"
            logger.error(f"{error_msg}: {str(e)}")
            
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipient email rejected: {user.email}"
            logger.error(f"{error_msg}: {str(e)}")
            
        except smtplib.SMTPServerDisconnected as e:
            error_msg = f"SMTP server disconnected: Check network connection"
            logger.error(f"{error_msg}: {str(e)}")
            
        except Exception as e:
            error_msg = f"Email sending failed: {str(e)}"
            logger.error(error_msg)
        
        # Log failed email
        EmailLog.objects.create(
            user=user,
            email_type='activation',
            recipient_email=user.email,
            subject=subject if 'subject' in locals() else 'Account Activation',
            status='failed',
            error_message=error_msg
        )
        
        return False, error_msg
    
    @staticmethod
    def send_bulk_activation_emails(users, request=None):
        """Send activation emails to multiple users"""
        results = {
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for user in users:
            success, message = EmailService.send_activation_email(user, request)
            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"{user.email}: {message}")
        
        return results
    
    @staticmethod
    def send_approval_notification(user):
        """Send notification that account has been approved (without activation link)"""
        try:
            degree_year = f"{user.degree} Year {user.year}" if user.degree and user.year else "Student"
            
            subject = f"✅ Your {user.degree} Account Application Approved"
            message = f'''
Hello {user.first_name},

Great news! Your {degree_year} account application has been approved.

You will receive a separate email with activation instructions to complete your registration and access your study materials.

Thank you for choosing PulsePrep for your medical education journey!

Best regards,
PulsePrep Support Team
support@pulseprep.net
            '''
            
            success = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )
            
            # Log email
            EmailLog.objects.create(
                user=user,
                email_type='approval_notification',
                recipient_email=user.email,
                subject=subject,
                status='sent' if success else 'failed'
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send approval notification to {user.email}: {str(e)}")
            
            EmailLog.objects.create(
                user=user,
                email_type='approval_notification',
                recipient_email=user.email,
                subject=subject if 'subject' in locals() else 'Account Approved',
                status='failed',
                error_message=str(e)
            )
            
            return False
    
    @staticmethod
    def send_welcome_email_after_activation(user, request=None):
        """Send permanent welcome email after successful activation"""
        try:
            if request:
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
            else:
                domain = 'pulseprep.net' if not settings.DEBUG else 'localhost:8000'
                protocol = 'https' if 'pulseprep.net' in domain else 'http'
            
            degree_year = f"{user.degree} Year {user.year}" if user.degree and user.year else "Student"
            subject = f"📚 Your PulsePrep {user.degree} Study Account - Keep This Email"
            
            message = f'''
🎓 PULSEPREP ACCOUNT CONFIRMATION

Dear {user.first_name} {user.last_name},

This email confirms your PulsePrep account setup and contains important information to keep.

ACCOUNT DETAILS:
👤 Name: {user.first_name} {user.last_name}
📧 Login Email: {user.email}
🎓 Program: {degree_year}
📅 Account Activated: {timezone.now().strftime("%B %d, %Y")}

LOGIN INFORMATION:
🔗 Login Page: {protocol}://{domain}/user-management/login/
📧 Username: {user.email}
🔑 Password: [Your chosen password]

QUICK START GUIDE:
1. Login to your account using the link above
2. Browse the {degree_year} question bank
3. Take your first practice test
4. Check your progress in Analytics

SUPPORT CONTACT:
📧 Email: support@pulseprep.net
🕒 Support Hours: 9 AM - 6 PM (Monday - Saturday)

KEEP THIS EMAIL: Save this email in a folder for easy reference. It contains your login details and will not be automatically deleted.

Welcome to PulsePrep! We're here to support your medical education journey.

Best regards,
PulsePrep Support Team

---
PulsePrep Medical Education Platform
📧 support@pulseprep.net | 🌐 pulseprep.net

© 2025 PulsePrep. All rights reserved.
This is a confirmation email for your account. Please keep it for your records.
            '''
            
            # Send with headers to ensure it stays
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email='PulsePrep Support <support@pulseprep.net>',
                to=[user.email],
                headers={
                    'X-Priority': '3',  # Normal priority
                    'X-Auto-Response-Suppress': 'All',
                    'X-Entity-Type': 'account-confirmation',
                }
            )
            
            success = email.send(fail_silently=True)
            
            if success:
                # Log welcome email
                EmailLog.objects.create(
                    user=user,
                    email_type='approval_notification',
                    recipient_email=user.email,
                    subject=subject,
                    status='sent'
                )
                
                logger.info(f"Welcome email sent to {user.email}")
                return True, "Welcome email sent successfully"
            else:
                return False, "Welcome email failed to send"
                
        except Exception as e:
            logger.error(f"Welcome email failed for {user.email}: {str(e)}")
            return False, f"Welcome email error: {str(e)}"