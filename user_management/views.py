# user_management/views.py - Complete Views with Email Activation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import CustomUser, UserSession, EmailLog
from .email_service import EmailService
import json
import random
import string
import re

# Helper function to check if user is admin
def is_admin(user):
    return user.is_authenticated and (user.is_admin or user.is_superuser)

# Signup view - Enhanced with email verification preparation
def signup_view(request):
    if request.method == 'POST':
        # Get form data including voucher
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        degree = request.POST.get('degree')
        year = request.POST.get('year')
        voucher_reference = request.POST.get('voucher_reference', '').strip()
        terms = request.POST.get('terms')
        
        # Validate form data
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'user_management/signup.html')
            
        # Check if user already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return render(request, 'user_management/signup.html')
        
        # Validate degree and year selection
        if not degree or not year:
            messages.error(request, "Please select both degree and year!")
            return render(request, 'user_management/signup.html')
        
        # Validate voucher reference if provided (alphanumeric only)
        if voucher_reference:
            if not re.match(r'^[a-zA-Z0-9]+$', voucher_reference):
                messages.error(request, "Voucher/Reference code can only contain letters and numbers!")
                return render(request, 'user_management/signup.html')
            
        # Create user
        user = CustomUser(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=email,  # Use email as username
            degree=degree,
            year=int(year),  # Convert to integer
            voucher_reference=voucher_reference if voucher_reference else None,
            terms_accepted=bool(terms),
            approval_status='pending',
            is_account_activated=False  # Account not activated by default
        )
        
        # Handle profile image upload
        if 'profile_image' in request.FILES:
            user.profile_image = request.FILES['profile_image']

        user.set_password(password)
        
        # Handle payment slip upload
        if 'payment_slip' in request.FILES:
            user.payment_slip = request.FILES['payment_slip']
        
        user.save()
        
        # Enhanced success message
        voucher_msg = f" (Voucher: {voucher_reference})" if voucher_reference else ""
        messages.success(request, 
            f"Account created successfully for {degree} Year {year}{voucher_msg}! "
            f"Your registration is pending admin approval. Once approved, you'll receive an activation email."
        )
        return redirect('user_management:login')
    
    return render(request, 'user_management/signup.html')

# Login view - Enhanced with activation check
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # Skip activation check for admin users
            if not (user.is_admin or user.is_superuser):
                # Check if account is activated
                if not user.is_account_activated:
                    degree_year = f"{user.degree} Year {user.year}" if user.degree and user.year else "your"
                    
                    if user.approval_status == 'pending':
                        messages.error(request, 
                            f"Your {degree_year} account is pending admin approval. "
                            f"You'll receive an activation email once approved.")
                    elif user.approval_status == 'approved':
                        if user.activation_sent_at and not user.is_activation_token_valid():
                            messages.error(request, 
                                f"Your activation link has expired. Please contact support at "
                                f"support@pulseprep.net for a new activation link.")
                        else:
                            messages.error(request, 
                                f"Your {degree_year} account requires activation. "
                                f"Please check your email for the activation link.")
                    else:  # rejected
                        messages.error(request, 
                            f"Your {degree_year} account has been rejected. "
                            f"Please contact administrator for assistance.")
                    
                    return render(request, 'user_management/login.html')
                
                # Check if profile is complete
                if not user.degree or not user.year:
                    messages.error(request, 
                        "Your profile is incomplete. Please contact administrator to complete your registration.")
                    return render(request, 'user_management/login.html')
                
            # Log user in
            login(request, user)
            
            # Force session creation to get a session key
            request.session['user_id'] = user.id
            request.session.save()
            
            # Session management
            if request.session.session_key:
                # Invalidate other sessions for this user
                UserSession.objects.filter(user=user).update(is_active=False)
                
                # Create new session
                session = UserSession(
                    user=user,
                    session_key=request.session.session_key,
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                session.save()
                
                # Update user's current session key
                user.current_session_key = request.session.session_key
                user.last_active = timezone.now()
                user.save()
            
            # Set session expiry if remember is not checked
            if not remember:
                # Session will expire when browser is closed
                request.session.set_expiry(0)
            
            # Enhanced success message with access info
            if user.is_admin or user.is_superuser:
                messages.success(request, "Welcome back, Administrator! You have access to all content and user management.")
            else:
                messages.success(request, f"Welcome back! You have access to {user.degree} Year {user.year} content.")
            
            # Redirect to dashboard for all users
            return redirect('dashboard')
            
        else:
            messages.error(request, "Invalid email or password!")
            return render(request, 'user_management/login.html')
    
    return render(request, 'user_management/login.html')

def activate_account(request, token):
    """Handle account activation via email link"""
    try:
        user = get_object_or_404(CustomUser, activation_token=token)
        
        # Check if token is valid
        if not user.is_activation_token_valid():
            messages.error(request, 
                "Activation link has expired (72 hours). Please contact support@pulseprep.net for assistance.")
            return redirect('user_management:login')
        
        # Check if already activated
        if user.is_account_activated:
            messages.info(request, "Your account is already activated. You can login normally.")
            return redirect('user_management:login')
        
        # Activate account
        user.is_account_activated = True
        user.activated_at = timezone.now()
        user.activation_token = None  # Clear token after use
        user.save(update_fields=['is_account_activated', 'activated_at', 'activation_token'])
        
        # Send welcome email after activation
        from .email_service import EmailService
        welcome_success, welcome_message = EmailService.send_welcome_email_after_activation(user, request)
        
        degree_year = f"{user.degree} Year {user.year}" if user.degree and user.year else "Student"
        
        if welcome_success:
            messages.success(request, 
                f"🎉 Account activated successfully! Welcome to PulsePrep {degree_year}. "
                f"You can now login with your credentials. Check your email for permanent login details.")
        else:
            messages.success(request, 
                f"🎉 Account activated successfully! Welcome to PulsePrep {degree_year}. "
                f"You can now login with your credentials.")
        
        return redirect('user_management:login')
        
    except CustomUser.DoesNotExist:
        messages.error(request, "Invalid activation link. Please contact support@pulseprep.net for assistance.")
        return redirect('user_management:login')
    
    
# Logout view
@login_required
def logout_view(request):
    # Mark session as inactive
    if request.session.session_key:
        UserSession.objects.filter(session_key=request.session.session_key).update(is_active=False)
    
    # Clear user's current session key
    if hasattr(request.user, 'current_session_key'):
        request.user.current_session_key = None
        request.user.save(update_fields=['current_session_key'])
    
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    
    # Redirect directly to login page
    response = redirect('user_management:login')
    
    # Add headers to prevent caching of previous protected pages
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response

# Admin - Enhanced User management view with email status
@user_passes_test(is_admin)
def manage_users(request):
    """Enhanced user management with filtering and email status"""
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    degree_filter = request.GET.get('degree', 'all')
    year_filter = request.GET.get('year', 'all')
    search_query = request.GET.get('search', '')
    activation_filter = request.GET.get('activation', 'all')
    
    # Base queryset with related data
    users = CustomUser.objects.select_related().prefetch_related('email_logs').order_by('-date_joined')
    
    # Apply search
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(voucher_reference__icontains=search_query)
        )
    
    # Apply filters
    if status_filter != 'all':
        users = users.filter(approval_status=status_filter)
    
    if degree_filter != 'all':
        users = users.filter(degree=degree_filter)
    
    if year_filter != 'all':
        users = users.filter(year=int(year_filter))
    
    # Activation filter
    if activation_filter == 'activated':
        users = users.filter(is_account_activated=True)
    elif activation_filter == 'pending_activation':
        users = users.filter(approval_status='approved', is_account_activated=False)
    elif activation_filter == 'not_sent':
        users = users.filter(approval_status='approved', activation_sent_at__isnull=True)
    elif activation_filter == 'expired':
        users = users.filter(activation_sent_at__isnull=False, is_account_activated=False)
    
    # Pagination
    paginator = Paginator(users, 10)  # Show 20 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Count statistics for dashboard
    total_users = CustomUser.objects.count()
    pending_users = CustomUser.objects.filter(approval_status='pending').count()
    approved_users = CustomUser.objects.filter(approval_status='approved').count()
    rejected_users = CustomUser.objects.filter(approval_status='rejected').count()
    activated_users = CustomUser.objects.filter(is_account_activated=True).count()
    pending_activation = CustomUser.objects.filter(approval_status='approved', is_account_activated=False).count()
    
    # Count by degree
    mbbs_users = CustomUser.objects.filter(degree='MBBS').count()
    bds_users = CustomUser.objects.filter(degree='BDS').count()
    
    context = {
        'page_obj': page_obj,
        'users': page_obj.object_list,
        'total_users': total_users,
        'pending_users': pending_users,
        'approved_users': approved_users,
        'rejected_users': rejected_users,
        'activated_users': activated_users,
        'pending_activation': pending_activation,
        'mbbs_users': mbbs_users,
        'bds_users': bds_users,
        
        # Filter values for template
        'status_filter': status_filter,
        'degree_filter': degree_filter,
        'year_filter': year_filter,
        'search_query': search_query,
        'activation_filter': activation_filter,
        
        # Choices for dropdowns
        'degree_choices': CustomUser.DEGREE_CHOICES,
        'year_choices': CustomUser.YEAR_CHOICES,
        'status_choices': CustomUser.APPROVAL_STATUS,
    }
    
    return render(request, 'user_management/manage_users.html', context)

# Admin - Get users API with email status
@user_passes_test(is_admin)
def get_users(request):
    """Enhanced API endpoint for user data with email status"""
    # Get filter parameters
    status_filter = request.GET.get('status')
    degree_filter = request.GET.get('degree')
    year_filter = request.GET.get('year')
    search_query = request.GET.get('search', '')
    activation_filter = request.GET.get('activation')
    
    users = CustomUser.objects.prefetch_related('email_logs').order_by('-date_joined')
    
    # Apply search
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(voucher_reference__icontains=search_query)
        )
    
    # Apply filters
    if status_filter and status_filter != 'all':
        users = users.filter(approval_status=status_filter)
    
    if degree_filter and degree_filter != 'all':
        users = users.filter(degree=degree_filter)
    
    if year_filter and year_filter != 'all':
        users = users.filter(year=int(year_filter))
    
    if activation_filter and activation_filter != 'all':
        if activation_filter == 'activated':
            users = users.filter(is_account_activated=True)
        elif activation_filter == 'pending_activation':
            users = users.filter(approval_status='approved', is_account_activated=False)
        elif activation_filter == 'not_sent':
            users = users.filter(approval_status='approved', activation_sent_at__isnull=True)
    
    # Limit results for performance
    users = users[:100]
    
    user_list = []
    for user in users:
        # Enhanced user data with access level and email status info
        access_level = "Administrator" if user.is_admin else f"{user.degree} Year {user.year}" if user.degree and user.year else "Profile Incomplete"
        
        # Get latest email status
        latest_email = user.email_logs.filter(email_type='activation').first()
        email_status = latest_email.status if latest_email else 'not_sent'
        
        user_data = {
            'id': user.id,
            'name': f"{user.first_name} {user.last_name}",
            'email': user.email,
            'status': user.approval_status,
            'status_display': user.get_approval_status_display(),
            'category': 'Paid' if user.payment_slip else 'Unpaid',
            'type': 'Admin' if user.is_admin else 'Student',
            'field': user.degree or 'Not Set',
            'year': user.year or 'Not Set',
            'year_display': f'Year {user.year}' if user.year else 'Not Set',
            'access_level': access_level,
            'voucher_reference': user.voucher_reference or '',
            'picture': user.profile_image.url if user.profile_image else None,
            'payment_slip': user.payment_slip.url if user.payment_slip else None,
            'date_joined': user.date_joined.strftime('%Y-%m-%d'),
            'last_active': user.last_active.strftime('%Y-%m-%d %H:%M') if user.last_active else 'Never',
            # Email and activation status
            'is_account_activated': user.is_account_activated,
            'activation_status': user.activation_status_display,
            'email_status': email_status,
            'activation_sent_at': user.activation_sent_at.strftime('%Y-%m-%d %H:%M') if user.activation_sent_at else None,
            'activated_at': user.activated_at.strftime('%Y-%m-%d %H:%M') if user.activated_at else None,
        }
        user_list.append(user_data)
    
    return JsonResponse({'users': user_list})

# Admin - Change user status with automatic email sending
@user_passes_test(is_admin)
def change_user_status(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(CustomUser, id=user_id)
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status in ['approved', 'rejected', 'pending']:
            old_status = user.approval_status
            user.approval_status = new_status
            user.save()
            
            access_info = f"{user.degree} Year {user.year}" if user.degree and user.year else "Profile Incomplete"
            
            # Send activation email when approved
            email_sent = False
            email_message = ""
            if new_status == 'approved' and old_status != 'approved' and not user.is_account_activated:
                success, message = EmailService.send_activation_email(user, request)
                email_sent = success
                email_message = message
            
            # Enhanced status messages
            status_messages = {
                'approved': f"User approved! Activation email {'sent successfully' if email_sent else 'failed to send'} to {user.email}.",
                'rejected': f"User rejected. They cannot access content until status is changed.",
                'pending': f"User status set to pending. They cannot access content until approved."
            }
            
            # Log the change
            print(f"Admin {request.user.email} changed {user.email} ({access_info}) status from {old_status} to {new_status}")
            
            return JsonResponse({
                'success': True,
                'message': status_messages.get(new_status, f"Status changed to {new_status}"),
                'user_info': f"{user.first_name} {user.last_name} ({access_info})",
                'new_status': new_status,
                'new_status_display': user.get_approval_status_display(),
                'access_info': access_info,
                'email_sent': email_sent if new_status == 'approved' else None,
                'email_message': email_message if new_status == 'approved' else None
            })
        
    return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)

# Admin - Bulk send activation emails
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def bulk_send_activation_emails(request):
    """Send activation emails to all approved but not activated users"""
    try:
        # Get approved users who haven't been activated
        users_to_activate = CustomUser.objects.filter(
            approval_status='approved',
            is_account_activated=False
        ).exclude(is_admin=True)
        
        if not users_to_activate.exists():
            return JsonResponse({
                'success': False,
                'message': 'No approved users found who need activation emails.'
            })
        
        # Send bulk emails
        results = EmailService.send_bulk_activation_emails(users_to_activate, request)
        
        message = f"Activation emails sent: {results['sent']} successful, {results['failed']} failed"
        if results['errors']:
            message += f". Errors: {'; '.join(results['errors'][:3])}"  # Show first 3 errors
        
        return JsonResponse({
            'success': True,
            'message': message,
            'sent': results['sent'],
            'failed': results['failed']
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Error sending bulk emails: {str(e)}"
        })

# Admin - Resend activation email for specific user
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def resend_activation_email(request, user_id):
    """Resend activation email to specific user"""
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        
        if user.is_account_activated:
            return JsonResponse({
                'success': False,
                'message': 'User account is already activated.'
            })
        
        if user.approval_status != 'approved':
            return JsonResponse({
                'success': False,
                'message': 'User must be approved before sending activation email.'
            })
        
        success, message = EmailService.send_activation_email(user, request)
        
        return JsonResponse({
            'success': success,
            'message': f"Activation email {'sent successfully' if success else 'failed'} to {user.email}. {message}"
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Error: {str(e)}"
        })

# Admin - Add new user with enhanced validation
@user_passes_test(is_admin)
def add_user(request):
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('user-name', '').split()[0] if request.POST.get('user-name') else ''
        last_name = ' '.join(request.POST.get('user-name', '').split()[1:]) if len(request.POST.get('user-name', '').split()) > 1 else ''
        email = request.POST.get('user-email')
        category = request.POST.get('user-category')
        user_type = request.POST.get('user-type')
        degree = request.POST.get('user-field')
        year_str = request.POST.get('user-year')
        status = request.POST.get('user-status') == 'on'
        
        # Enhanced validation
        if not all([first_name, email]):
            messages.error(request, "Name and email are required!")
            return redirect('user_management:manage_users')
        
        if '@' not in email:
            messages.error(request, "Please enter a valid email address!")
            return redirect('user_management:manage_users')
        
        # Check if user already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, f"Email {email} is already registered!")
            return redirect('user_management:manage_users')
        
        # Generate a temporary password
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        # Parse year (handle "1st", "2nd", etc.)
        year = None
        if year_str and year_str != 'Not Set':
            try:
                year = int(year_str[0]) if year_str[0].isdigit() else None
            except (ValueError, IndexError):
                year = None
        
        # Enhanced validation for students
        if user_type != 'Admin':
            if not degree or degree == 'Not Set':
                messages.error(request, "Degree is required for students!")
                return redirect('user_management:manage_users')
            if not year:
                messages.error(request, "Year is required for students!")
                return redirect('user_management:manage_users')
        
        # Create user
        user = CustomUser(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=email,
            degree=degree if degree and degree != 'Not Set' else None,
            year=year,
            is_admin=user_type=='Admin',
            approval_status='approved' if status else 'pending',
            terms_accepted=True,  # Admin-created users have terms accepted
            is_account_activated=user_type=='Admin'  # Admins are auto-activated
        )
        user.set_password(temp_password)
        
        # Handle profile image upload
        if 'user-image' in request.FILES:
            user.profile_image = request.FILES['user-image']
        
        user.save()
        
        # Send activation email for non-admin approved users
        email_sent = False
        if user_type != 'Admin' and status and not user.is_account_activated:
            success, message = EmailService.send_activation_email(user, request)
            email_sent = success
        
        # Enhanced success message with access info
        if user_type == 'Admin':
            access_info = "Administrator - Full Access to All Content"
            activation_msg = "Account activated automatically."
        else:
            access_info = f"{degree} Year {year} - Access to {degree} Year {year} Content Only"
            if status:
                activation_msg = f"Activation email {'sent' if email_sent else 'failed to send'}."
            else:
                activation_msg = "Account pending approval."
        
        approval_status = "Approved" if status else "Pending Approval"
        
        messages.success(request, 
            f"User created successfully!\n"
            f"Access Level: {access_info}\n"
            f"Status: {approval_status}\n"
            f"Activation: {activation_msg}\n"
            f"Temporary Password: {temp_password}\n"
            f"(Please share the password securely with the user)"
        )
        return redirect('user_management:manage_users')
    
    return redirect('user_management:manage_users')

# Dashboard view with activation check
@login_required
def dashboard_view(request):
    """Dashboard that handles different user types and activation status"""
    user = request.user
    
    # Check if user needs activation (skip for admins)
    if not (user.is_admin or user.is_superuser):
        if not user.is_account_activated:
            context = {
                'not_activated': True,
                'approval_status': user.approval_status,
                'degree': user.degree,
                'year': user.year,
                'activation_sent': user.activation_sent_at is not None,
                'activation_expired': user.activation_sent_at and not user.is_activation_token_valid(),
            }
            return render(request, 'dashboard/not_activated.html', context)
        
        if user.approval_status != 'approved':
            context = {
                'approval_status': user.approval_status,
                'degree': user.degree,
                'year': user.year,
                'access_message': f"Your {user.degree} Year {user.year} account is {user.approval_status}."
            }
            return render(request, 'dashboard/pending_approval.html', context)
        
        if not user.degree or not user.year:
            context = {
                'profile_incomplete': True,
                'message': "Your profile is incomplete. Please contact administrator."
            }
            return render(request, 'dashboard/profile_incomplete.html', context)
    
    # Regular dashboard
    context = {
        'user': user,
        'is_admin': user.is_admin or user.is_superuser,
        'access_level': f"{user.degree} Year {user.year}" if user.degree and user.year else "Administrator",
    }
    
    if user.is_admin or user.is_superuser:
        # Add admin statistics with email tracking
        context.update({
            'total_users': CustomUser.objects.count(),
            'pending_users': CustomUser.objects.filter(approval_status='pending').count(),
            'approved_users': CustomUser.objects.filter(approval_status='approved').count(),
            'activated_users': CustomUser.objects.filter(is_account_activated=True).count(),
            'pending_activation': CustomUser.objects.filter(approval_status='approved', is_account_activated=False).count(),
            'mbbs_users': CustomUser.objects.filter(degree='MBBS').count(),
            'bds_users': CustomUser.objects.filter(degree='BDS').count(),
            'failed_emails': EmailLog.objects.filter(status='failed').count(),
        })
        return render(request, 'dashboard/admin_dashboard.html', context)
    else:
        return render(request, 'dashboard/student_dashboard.html', context)

# Admin - Delete user
@user_passes_test(is_admin)
def delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(CustomUser, id=user_id)
        
        # Prevent deleting yourself
        if user == request.user:
            return JsonResponse({'success': False, 'message': 'Cannot delete your own account'}, status=400)
        
        # Prevent deleting other admins (optional security measure)
        if user.is_admin or user.is_superuser:
            return JsonResponse({'success': False, 'message': 'Cannot delete admin accounts'}, status=400)
        
        user_info = f"{user.first_name} {user.last_name} ({user.email})"
        user.delete()
        
        return JsonResponse({
            'success': True,
            'message': f"User {user_info} deleted successfully"
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

# Admin - User details view with email logs
@user_passes_test(is_admin)
def user_details(request, user_id):
    """Detailed view of a specific user with email history"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Get user's recent activity
    recent_sessions = UserSession.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Get email logs
    email_logs = EmailLog.objects.filter(user=user).order_by('-sent_at')[:20]
    
    context = {
        'viewed_user': user,
        'recent_sessions': recent_sessions,
        'email_logs': email_logs,
        'access_level': f"{user.degree} Year {user.year}" if user.degree and user.year else "Profile Incomplete",
        'latest_email_status': email_logs.first().status if email_logs.exists() else None,
    }
    
    return render(request, 'user_management/user_details.html', context)

# Student - Profile view
@login_required
def profile_view(request):
    """Student profile view with activation status"""
    user = request.user
    
    # Get user's email logs
    email_logs = EmailLog.objects.filter(user=user).order_by('-sent_at')[:5]
    
    context = {
        'user': user,
        'access_level': f"{user.degree} Year {user.year}" if user.degree and user.year else "Profile Incomplete",
        'approval_status_display': user.get_approval_status_display(),
        'activation_status': user.activation_status_display,
        'email_logs': email_logs,
        'can_request_resend': (
            user.approval_status == 'approved' and 
            not user.is_account_activated and 
            (not user.activation_sent_at or not user.is_activation_token_valid())
        ),
    }
    
    return render(request, 'user_management/profile.html', context)

# Admin - Email logs view
@user_passes_test(is_admin)
def email_logs_view(request):
    """View all email logs with filtering"""
    # Get filter parameters
    email_type_filter = request.GET.get('type', 'all')
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    logs = EmailLog.objects.select_related('user').order_by('-sent_at')
    
    # Apply filters
    if email_type_filter != 'all':
        logs = logs.filter(email_type=email_type_filter)
    
    if status_filter != 'all':
        logs = logs.filter(status=status_filter)
    
    if search_query:
        logs = logs.filter(
            Q(user__email__icontains=search_query) |
            Q(recipient_email__icontains=search_query) |
            Q(subject__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_emails = EmailLog.objects.count()
    sent_emails = EmailLog.objects.filter(status='sent').count()
    failed_emails = EmailLog.objects.filter(status='failed').count()
    activation_emails = EmailLog.objects.filter(email_type='activation').count()
    
    context = {
        'page_obj': page_obj,
        'logs': page_obj.object_list,
        'total_emails': total_emails,
        'sent_emails': sent_emails,
        'failed_emails': failed_emails,
        'activation_emails': activation_emails,
        
        # Filter values
        'email_type_filter': email_type_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        
        # Choices
        'email_type_choices': EmailLog.EMAIL_TYPES,
        'status_choices': EmailLog.EMAIL_STATUS,
    }
    
    return render(request, 'user_management/email_logs.html', context)

# Admin - Retry failed emails
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def retry_failed_emails(request):
    """Retry sending failed activation emails"""
    try:
        # Get failed activation emails from last 24 hours
        failed_logs = EmailLog.objects.filter(
            email_type='activation',
            status='failed',
            sent_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).select_related('user')
        
        if not failed_logs.exists():
            return JsonResponse({
                'success': False,
                'message': 'No recent failed activation emails found to retry.'
            })
        
        # Get unique users from failed emails
        users_to_retry = CustomUser.objects.filter(
            id__in=failed_logs.values_list('user_id', flat=True).distinct(),
            approval_status='approved',
            is_account_activated=False
        )
        
        # Retry sending emails
        results = EmailService.send_bulk_activation_emails(users_to_retry, request)
        
        return JsonResponse({
            'success': True,
            'message': f"Retried failed emails: {results['sent']} successful, {results['failed']} failed",
            'sent': results['sent'],
            'failed': results['failed']
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Error retrying emails: {str(e)}"
        })

# Admin - Manual account activation (bypass email)
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def manual_activate_account(request, user_id):
    """Manually activate user account bypassing email activation"""
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        
        if user.is_account_activated:
            return JsonResponse({
                'success': False,
                'message': 'User account is already activated.'
            })
        
        if user.approval_status != 'approved':
            return JsonResponse({
                'success': False,
                'message': 'User must be approved before manual activation.'
            })
        
        # Manually activate account
        user.is_account_activated = True
        user.activated_at = timezone.now()
        user.activation_token = None  # Clear any existing token
        user.save(update_fields=['is_account_activated', 'activated_at', 'activation_token'])
        
        # Log the manual activation
        print(f"Admin {request.user.email} manually activated account for {user.email}")
        
        return JsonResponse({
            'success': True,
            'message': f"Account manually activated for {user.email}. User can now login."
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Error: {str(e)}"
        })

# Admin - Test email functionality
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def test_email_config(request):
    """Test email configuration by sending a test email"""
    try:
        admin_email = request.user.email
        
        # Send test email
        from django.core.mail import send_mail
        from django.conf import settings
        
        success = send_mail(
            subject='PulsePrep Email Configuration Test',
            message='This is a test email to verify email configuration is working correctly.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            html_message='''
            <html>
                <body>
                    <h2>✅ Email Configuration Test</h2>
                    <p>This is a test email to verify that your PulsePrep email configuration is working correctly.</p>
                    <p><strong>If you received this email, your email settings are configured properly!</strong></p>
                    <hr>
                    <p><small>Sent from PulsePrep Admin Panel</small></p>
                </body>
            </html>
            ''',
            fail_silently=False
        )
        
        if success:
            # Log successful test
            EmailLog.objects.create(
                user=request.user,
                email_type='activation',  # Using existing choices
                recipient_email=admin_email,
                subject='PulsePrep Email Configuration Test',
                status='sent'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Test email sent successfully to {admin_email}. Check your inbox to confirm delivery.'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Test email failed to send. Check your email configuration.'
            })
            
    except Exception as e:
        # Log failed test
        EmailLog.objects.create(
            user=request.user,
            email_type='activation',
            recipient_email=request.user.email,
            subject='PulsePrep Email Configuration Test',
            status='failed',
            error_message=str(e)
        )
        
        return JsonResponse({
            'success': False,
            'message': f'Test email failed: {str(e)}'
        })

# Admin - Export user data with email status
@user_passes_test(is_admin)
def export_users_csv(request):
    """Export user data including email status to CSV"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="pulseprep_users.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'ID', 'Name', 'Email', 'Degree', 'Year', 'Approval Status', 
        'Activation Status', 'Email Status', 'Voucher Reference',
        'Date Joined', 'Last Active', 'Activation Sent', 'Activated At'
    ])
    
    # Get all users with related data
    users = CustomUser.objects.prefetch_related('email_logs').order_by('-date_joined')
    
    for user in users:
        # Get latest email status
        latest_email = user.email_logs.filter(email_type='activation').first()
        email_status = latest_email.status if latest_email else 'not_sent'
        
        writer.writerow([
            user.id,
            f"{user.first_name} {user.last_name}",
            user.email,
            user.degree or '',
            user.year or '',
            user.get_approval_status_display(),
            'Activated' if user.is_account_activated else 'Not Activated',
            email_status,
            user.voucher_reference or '',
            user.date_joined.strftime('%Y-%m-%d %H:%M'),
            user.last_active.strftime('%Y-%m-%d %H:%M') if user.last_active else '',
            user.activation_sent_at.strftime('%Y-%m-%d %H:%M') if user.activation_sent_at else '',
            user.activated_at.strftime('%Y-%m-%d %H:%M') if user.activated_at else '',
        ])
    
    return response

# Student - Request activation email resend (optional feature)
@login_required
@require_http_methods(["POST"])
def request_activation_resend(request):
    """Allow student to request activation email resend"""
    user = request.user
    
    # Check if user is eligible for resend
    if user.is_account_activated:
        return JsonResponse({
            'success': False,
            'message': 'Your account is already activated.'
        })
    
    if user.approval_status != 'approved':
        return JsonResponse({
            'success': False,
            'message': 'Your account must be approved before requesting activation email.'
        })
    
    # Check if too many recent requests (rate limiting)
    recent_emails = EmailLog.objects.filter(
        user=user,
        email_type='activation',
        sent_at__gte=timezone.now() - timezone.timedelta(hours=1)
    ).count()
    
    if recent_emails >= 3:
        return JsonResponse({
            'success': False,
            'message': 'Too many activation email requests. Please wait before requesting again.'
        })
    
    # Send activation email
    success, message = EmailService.send_activation_email(user, request)
    
    return JsonResponse({
        'success': success,
        'message': f"Activation email {'sent successfully' if success else 'failed to send'}. {message}"
    })

# Helper function for AJAX responses
def ajax_response(success, message, data=None):
    """Helper function to standardize AJAX responses"""
    response_data = {
        'success': success,
        'message': message
    }
    if data:
        response_data.update(data)
    return JsonResponse(response_data)