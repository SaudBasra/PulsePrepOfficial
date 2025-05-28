# user_management/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from .models import CustomUser, UserSession
import json

# Helper function to check if user is admin
def is_admin(user):
    return user.is_authenticated and (user.is_admin or user.is_superuser)

# Signup view
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
            
        # Create user
        user = CustomUser(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=email,  # Use email as username
            degree=degree,
            year=year,
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
        
        # TODO: Send notification to admin
        
        messages.success(request, "Account created successfully! Please wait for admin approval.")
        return redirect('login')
    
    return render(request, 'user_management/signup.html')

# Login view - FIXED VERSION
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # Check if account is approved
            if user.approval_status != 'approved' and not user.is_admin and not user.is_superuser:
                messages.error(request, "Your account is pending approval. Please wait for administrator approval.")
                return render(request, 'user_management/login.html')
                
            # Log user in
            login(request, user)
            
            # Force session creation to get a session key
            request.session['user_id'] = user.id
            request.session.save()
            
            # Now the session key should be available
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
            
            # FIXED: Redirect to dashboard for all users
            # The dashboard view will handle routing based on user type
            return redirect('dashboard')
            
        else:
            messages.error(request, "Invalid email or password!")
            return render(request, 'user_management/login.html')
    
    return render(request, 'user_management/login.html')

# Logout view
@login_required
def logout_view(request):
    # Mark session as inactive
    if request.session.session_key:
        UserSession.objects.filter(session_key=request.session.session_key).update(is_active=False)
    
    logout(request)
    return redirect('login')

# Admin - User management view
@user_passes_test(is_admin)
def manage_users(request):
    pending_users = CustomUser.objects.filter(approval_status='pending')
    return render(request, 'user_management/manage_users.html', {'pending_users': pending_users})

@user_passes_test(is_admin)
def get_users(request):
    users = CustomUser.objects.all().order_by('-date_joined')
    
    user_list = []
    for user in users:
        user_data = {
            'id': user.id,
            'name': f"{user.first_name} {user.last_name}",
            'email': user.email,
            'status': user.approval_status,
            'category': 'Paid' if user.payment_slip else 'Unpaid',
            'type': 'Admin' if user.is_admin else 'Student',
            'field': user.degree,
            'year': user.year,
            'picture': user.profile_image.url if user.profile_image else None,
        }
        user_list.append(user_data)
    
    return JsonResponse({'users': user_list})

# Admin - Change user status
@user_passes_test(is_admin)
def change_user_status(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(CustomUser, id=user_id)
        data = json.loads(request.body)
        status = data.get('status')
        
        if status in ['approved', 'rejected', 'pending']:
            user.approval_status = status
            user.save()
            
            # TODO: Send notification to user
            
            return JsonResponse({'success': True})
        
    return JsonResponse({'success': False}, status=400)

# Admin - Add new user
@user_passes_test(is_admin)
def add_user(request):
    if request.method == 'POST':
        # Create a new user directly
        first_name = request.POST.get('user-name', '').split()[0]
        last_name = ' '.join(request.POST.get('user-name', '').split()[1:]) if len(request.POST.get('user-name', '').split()) > 1 else ''
        email = request.POST.get('user-email')
        category = request.POST.get('user-category')
        user_type = request.POST.get('user-type')
        degree = request.POST.get('user-field')
        year = request.POST.get('user-year')
        status = request.POST.get('user-status') == 'on'
        
        # Generate a temporary password
        import random
        import string
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        
        # Check if user already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect('manage_users')
        
        # Create user
        user = CustomUser(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=email,
            degree=degree,
            year=int(year[0]) if year else None,  # Extract first character from "1st", "2nd", etc.
            is_admin=user_type=='Admin',
            approval_status='approved' if status else 'pending'
        )
        user.set_password(temp_password)
        
        # Handle profile image
        if 'user-image' in request.FILES:
            user.payment_slip = request.FILES['user-image']
        
        user.save()
        
        # TODO: Send email to user with temporary password
        
        messages.success(request, f"User created successfully! Temporary password: {temp_password}")
        return redirect('manage_users')
    
    return redirect('manage_users')