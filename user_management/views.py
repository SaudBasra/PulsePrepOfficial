# user_management/views.py - Fixed Imports Version
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count

from .models import CustomUser, UserSession
import json
import random
import string

# Helper function to check if user is admin
def is_admin(user):
    return user.is_authenticated and (user.is_admin or user.is_superuser)

# Signup view - Enhanced with better messaging
def signup_view(request):
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        degree = request.POST.get('degree')
        year = request.POST.get('year')
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
            
        # Create user
        user = CustomUser(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=email,  # Use email as username
            degree=degree,
            year=int(year),  # Convert to integer
            terms_accepted=bool(terms),
            approval_status='pending'
        )
        
        # Handle profile image upload
        if 'profile_image' in request.FILES:
            user.profile_image = request.FILES['profile_image']

        user.set_password(password)
        
        # Handle payment slip upload
        if 'payment_slip' in request.FILES:
            user.payment_slip = request.FILES['payment_slip']
        
        user.save()
        
        # Enhanced success message with access info
        messages.success(request, 
            f"Account created successfully for {degree} Year {year}! "
            f"Your registration is pending admin approval. Once approved, you'll have access to "
            f"{degree} Year {year} content including questions, modules, and mock tests."
        )
        return redirect('user_management:login')
    
    return render(request, 'user_management/signup.html')

# Login view - Enhanced with access control messaging
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # Enhanced approval check with degree/year info
            if not (user.is_admin or user.is_superuser):
                if user.approval_status != 'approved':
                    degree_year = f"{user.degree} Year {user.year}" if user.degree and user.year else "your"
                    approval_messages = {
                        'pending': f"Your {degree_year} account is pending approval. Please wait for administrator approval to access content.",
                        'rejected': f"Your {degree_year} account has been rejected. Please contact administrator for assistance."
                    }
                    messages.error(request, approval_messages.get(user.approval_status, "Account not approved."))
                    return render(request, 'user_management/login.html')
                
                # Check if profile is complete
                if not user.degree or not user.year:
                    messages.error(request, "Your profile is incomplete. Please contact administrator to complete your registration.")
                    return render(request, 'user_management/login.html')
                
            # Log user in
            login(request, user)
            
            # Force session creation to get a session key
            request.session['user_id'] = user.id
            request.session.save()
            
            # Session management (your existing code)
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
                user.last_active = timezone.now()  # Fixed timezone issue
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

# Logout view - Enhanced
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
    return redirect('user_management:login')

# Admin - Enhanced User management view
@user_passes_test(is_admin)
def manage_users(request):
    """Enhanced user management with filtering and better display"""
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    degree_filter = request.GET.get('degree', 'all')
    year_filter = request.GET.get('year', 'all')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    users = CustomUser.objects.all().order_by('-date_joined')
    
    # Apply search
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Apply filters
    if status_filter != 'all':
        users = users.filter(approval_status=status_filter)
    
    if degree_filter != 'all':
        users = users.filter(degree=degree_filter)
    
    if year_filter != 'all':
        users = users.filter(year=int(year_filter))
    
    # Pagination
    paginator = Paginator(users, 20)  # Show 20 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Count statistics for dashboard
    total_users = CustomUser.objects.count()
    pending_users = CustomUser.objects.filter(approval_status='pending').count()
    approved_users = CustomUser.objects.filter(approval_status='approved').count()
    rejected_users = CustomUser.objects.filter(approval_status='rejected').count()
    
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
        'mbbs_users': mbbs_users,
        'bds_users': bds_users,
        
        # Filter values for template
        'status_filter': status_filter,
        'degree_filter': degree_filter,
        'year_filter': year_filter,
        'search_query': search_query,
        
        # Choices for dropdowns
        'degree_choices': CustomUser.DEGREE_CHOICES,
        'year_choices': CustomUser.YEAR_CHOICES,
        'status_choices': CustomUser.APPROVAL_STATUS,
    }
    
    return render(request, 'user_management/manage_users.html', context)

# Admin - Get users API - Enhanced with better data
@user_passes_test(is_admin)
def get_users(request):
    """Enhanced API endpoint for user data with filtering"""
    # Get filter parameters
    status_filter = request.GET.get('status')
    degree_filter = request.GET.get('degree')
    year_filter = request.GET.get('year')
    search_query = request.GET.get('search', '')
    
    users = CustomUser.objects.all().order_by('-date_joined')
    
    # Apply search
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Apply filters
    if status_filter and status_filter != 'all':
        users = users.filter(approval_status=status_filter)
    
    if degree_filter and degree_filter != 'all':
        users = users.filter(degree=degree_filter)
    
    if year_filter and year_filter != 'all':
        users = users.filter(year=int(year_filter))
    
    # Limit results for performance
    users = users[:100]
    
    user_list = []
    for user in users:
        # Enhanced user data with access level info
        access_level = "Administrator" if user.is_admin else f"{user.degree} Year {user.year}" if user.degree and user.year else "Profile Incomplete"
        
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
            'picture': user.profile_image.url if user.profile_image else None,
            'payment_slip': user.payment_slip.url if user.payment_slip else None,
            'date_joined': user.date_joined.strftime('%Y-%m-%d'),
            'last_active': user.last_active.strftime('%Y-%m-%d %H:%M') if user.last_active else 'Never',
        }
        user_list.append(user_data)
    
    return JsonResponse({'users': user_list})

# Admin - Change user status - Enhanced with better logging
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
            
            # Enhanced logging and response
            access_info = f"{user.degree} Year {user.year}" if user.degree and user.year else "Profile Incomplete"
            
            # Log the change (you can expand this for audit trail)
            print(f"Admin {request.user.email} changed {user.email} ({access_info}) status from {old_status} to {new_status}")
            
            # Prepare response message based on status
            status_messages = {
                'approved': f"User approved! They now have access to {access_info} content.",
                'rejected': f"User rejected. They cannot access content until status is changed.",
                'pending': f"User status set to pending. They cannot access content until approved."
            }
            
            return JsonResponse({
                'success': True,
                'message': status_messages.get(new_status, f"Status changed to {new_status}"),
                'user_info': f"{user.first_name} {user.last_name} ({access_info})",
                'new_status': new_status,
                'new_status_display': user.get_approval_status_display(),
                'access_info': access_info
            })
        
    return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)

# Admin - Add new user - Enhanced with validation
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
            terms_accepted=True  # Admin-created users have terms accepted
        )
        user.set_password(temp_password)
        
        # Handle profile image upload
        if 'user-image' in request.FILES:
            user.profile_image = request.FILES['user-image']
        
        user.save()
        
        # Enhanced success message with access info
        if user_type == 'Admin':
            access_info = "Administrator - Full Access to All Content"
        else:
            access_info = f"{degree} Year {year} - Access to {degree} Year {year} Content Only"
        
        approval_status = "Approved" if status else "Pending Approval"
        
        messages.success(request, 
            f"User created successfully!\n"
            f"Access Level: {access_info}\n"
            f"Status: {approval_status}\n"
            f"Temporary Password: {temp_password}\n"
            f"(Please share the password securely with the user)"
        )
        return redirect('user_management:manage_users')
    
    return redirect('user_management:manage_users')

# Dashboard view (optional - if you want a unified dashboard)
@login_required
def dashboard_view(request):
    """Simple dashboard that handles different user types"""
    user = request.user
    
    # Check if user needs approval or profile completion
    if not (user.is_admin or user.is_superuser):
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
        # Add admin statistics
        context.update({
            'total_users': CustomUser.objects.count(),
            'pending_users': CustomUser.objects.filter(approval_status='pending').count(),
            'mbbs_users': CustomUser.objects.filter(degree='MBBS').count(),
            'bds_users': CustomUser.objects.filter(degree='BDS').count(),
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

# Admin - User details view
@user_passes_test(is_admin)
def user_details(request, user_id):
    """Detailed view of a specific user"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Get user's recent activity
    recent_sessions = UserSession.objects.filter(user=user).order_by('-created_at')[:10]
    
    context = {
        'viewed_user': user,
        'recent_sessions': recent_sessions,
        'access_level': f"{user.degree} Year {user.year}" if user.degree and user.year else "Profile Incomplete",
    }
    
    return render(request, 'user_management/user_details.html', context)

# Student - Profile view
@login_required
def profile_view(request):
    """Student profile view"""
    user = request.user
    
    context = {
        'user': user,
        'access_level': f"{user.degree} Year {user.year}" if user.degree and user.year else "Profile Incomplete",
        'approval_status_display': user.get_approval_status_display(),
    }
    
    return render(request, 'user_management/profile.html', context)