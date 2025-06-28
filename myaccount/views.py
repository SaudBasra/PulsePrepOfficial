# ===============================================
# myaccount/views.py - Updated with Reset Functionality
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone

from .forms import UserProfileForm, CustomPasswordChangeForm
from user_management.models import CustomUser

# Import student record models for reset functionality
from mocktest.models import TestAttempt
from modelpaper.models import ModelPaperAttempt  
from managemodule.models import StudentProgress, PracticeSession
from notes.models import StudentNote







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


# ===============================================
# NEW RESET FUNCTIONALITY
# ===============================================

@login_required
@require_http_methods(["POST"])
@csrf_protect
def reset_all_records(request):
    """
    Reset all student records with proper confirmation and logging.
    IMPORTANT: Admin-configured limits remain permanent and are NOT reset.
    
    This will delete:
    - All mock test attempts (but NOT the admin-set attempt limits)
    - All model paper attempts (but NOT the admin-set attempt limits) 
    - All practice sessions and progress
    - All student notes
    
    Admin limits (max_attempts) remain in effect permanently.
    """
    
    # Ensure only students can reset their own records (not admins)
    if request.user.is_admin or request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'message': 'Administrators cannot reset records through this interface.'
        }, status=403)
    
    # Get confirmation from POST data
    confirmation = request.POST.get('confirmation', '').strip().lower()
    if confirmation != 'reset my records':
        return JsonResponse({
            'success': False,
            'message': 'Invalid confirmation text. Please type exactly: "reset my records"'
        }, status=400)
    
    user = request.user
    deleted_counts = {}
    
    try:
        with transaction.atomic():
            # Count records before deletion for confirmation
            test_attempts_count = TestAttempt.objects.filter(student=user).count()
            model_paper_attempts_count = ModelPaperAttempt.objects.filter(student=user).count()
            practice_sessions_count = PracticeSession.objects.filter(student=user).count()
            student_progress_count = StudentProgress.objects.filter(student=user).count()
            student_notes_count = StudentNote.objects.filter(student=user).count()
            
            # Get limit information before deletion
            tests_with_limits = TestAttempt.objects.filter(student=user).values('mock_test').distinct().count()
            papers_with_limits = ModelPaperAttempt.objects.filter(student=user).values('model_paper').distinct().count()
            
            # Store counts for response
            deleted_counts = {
                'test_attempts': test_attempts_count,
                'model_paper_attempts': model_paper_attempts_count,
                'practice_sessions': practice_sessions_count,
                'student_progress': student_progress_count,
                'student_notes': student_notes_count,
                'total': (test_attempts_count + model_paper_attempts_count + 
                         practice_sessions_count + student_progress_count + student_notes_count),
                'tests_with_permanent_limits': tests_with_limits,
                'papers_with_permanent_limits': papers_with_limits
            }
            
            # Delete all records (this resets the temporary attempt counts)
            TestAttempt.objects.filter(student=user).delete()
            ModelPaperAttempt.objects.filter(student=user).delete()
            PracticeSession.objects.filter(student=user).delete()
            StudentProgress.objects.filter(student=user).delete()
            StudentNote.objects.filter(student=user).delete()
            
            # CRITICAL: We DO NOT delete or reset admin-configured limits
            # The max_attempts fields on MockTest and ModelPaper remain unchanged
            # The attempt checking logic will still enforce these limits permanently
            
            # Log the reset action
            print(f"User {user.email} reset all records at {timezone.now()}")
            print(f"Deleted: {deleted_counts}")
            print(f"IMPORTANT: Admin-configured limits remain in effect permanently")
            
        # Success response with clear messaging about permanent limits
        return JsonResponse({
            'success': True,
            'message': 'Study records reset successfully! Important: Admin-configured attempt limits remain permanently in effect.',
            'deleted_counts': deleted_counts,
            'reset_timestamp': timezone.now().isoformat(),
            'permanent_limits_note': 'You may still be restricted by admin-configured maximum attempts on tests and papers. These limits are permanent and cannot be reset.'
        })
        
    except Exception as e:
        # Error handling
        return JsonResponse({
            'success': False,
            'message': f'An error occurred while resetting records: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])

def get_reset_preview(request):
    """
    Get preview of records that will be deleted and limits that will remain permanent
    """
    user = request.user
    
    # Ensure only students can preview their records
    if request.user.is_admin or request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'message': 'Not available for administrators.'
        }, status=403)
    
    try:
        # Count all records that will be deleted
        test_attempts = TestAttempt.objects.filter(student=user)
        model_attempts = ModelPaperAttempt.objects.filter(student=user)
        
        # Get information about which tests/papers have permanent attempt limits
        tests_with_attempts = test_attempts.values('mock_test__title', 'mock_test__max_attempts').distinct()
        papers_with_attempts = model_attempts.values('model_paper__title', 'model_paper__max_attempts').distinct()
        
        preview_data = {
            'test_attempts': test_attempts.count(),
            'model_paper_attempts': model_attempts.count(),
            'practice_sessions': PracticeSession.objects.filter(student=user).count(),
            'student_progress': StudentProgress.objects.filter(student=user).count(),
            'student_notes': StudentNote.objects.filter(student=user).count(),
            
            # Information about permanent limits that will NOT be reset
            'tests_with_limits': list(tests_with_attempts),
            'papers_with_limits': list(papers_with_attempts),
            'tests_count_with_limits': tests_with_attempts.count(),
            'papers_count_with_limits': papers_with_attempts.count(),
        }
        
        preview_data['total'] = (preview_data['test_attempts'] + preview_data['model_paper_attempts'] + 
                               preview_data['practice_sessions'] + preview_data['student_progress'] + 
                               preview_data['student_notes'])
        
        return JsonResponse({
            'success': True,
            'preview_data': preview_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting preview: {str(e)}'
        }, status=500)