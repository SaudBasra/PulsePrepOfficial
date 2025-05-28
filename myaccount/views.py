
# ===============================================
# myaccount/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.db import transaction
from .forms import UserProfileForm, CustomPasswordChangeForm
from user_management.models import CustomUser


@login_required
def my_profile(request):
    """Display and update user profile"""
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    messages.success(request, 'Your profile has been updated successfully!')
                    return redirect('my_profile')
            except Exception as e:
                messages.error(request, f'Error updating profile: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'form': form,
        'user': request.user,
    }
    
    # Use different templates for admin and student
    if request.user.is_admin or request.user.is_superuser:
        return render(request, 'myaccount/admin_profile.html', context)
    else:
        return render(request, 'myaccount/student_profile.html', context)


@login_required
def change_password(request):
    """Change user password"""
    
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        
        if form.is_valid():
            try:
                user = form.save()
                # Important: Update the session to prevent logout
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password has been changed successfully!')
                return redirect('my_profile')
            except Exception as e:
                messages.error(request, f'Error changing password: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'user': request.user,
    }
    
    # Use different templates for admin and student
    if request.user.is_admin or request.user.is_superuser:
        return render(request, 'myaccount/admin_change_password.html', context)
    else:
        return render(request, 'myaccount/student_change_password.html', context)


@login_required
def account_settings(request):
    """Account settings overview page"""
    
    context = {
        'user': request.user,
    }
    
    # Use different templates for admin and student
    if request.user.is_admin or request.user.is_superuser:
        return render(request, 'myaccount/admin_account_settings.html', context)
    else:
        return render(request, 'myaccount/student_account_settings.html', context)

