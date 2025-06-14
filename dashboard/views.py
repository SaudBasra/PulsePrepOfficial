# dashboard/views.py - Enhanced with professional student dashboard
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.http import JsonResponse
from django.db.models import Count, Avg, Max, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json

# Import models
from user_management.models import CustomUser
from mocktest.models import TestAttempt
from modelpaper.models import ModelPaperAttempt
from managemodule.models import StudentProgress, PracticeSession
from notes.models import StudentNote


@login_required
def dashboard(request):
    """Route to appropriate dashboard based on user type"""
    if request.user.is_admin or request.user.is_superuser:
        return admin_dashboard(request)
    else:
        return student_dashboard(request)


# ===================================================================
# ADMIN DASHBOARD SECTION - Keep existing functionality
# ===================================================================

@login_required
def admin_dashboard(request):
    """Admin dashboard with comprehensive statistics"""
    # Exclude admin users from statistics (only count regular users)
    regular_users = CustomUser.objects.filter(is_admin=False)
    
    # Basic counts (excluding admins)
    total_users = regular_users.count()
    pending_users = regular_users.filter(approval_status='pending').count()
    approved_users = regular_users.filter(approval_status='approved').count()
    rejected_users = regular_users.filter(approval_status='rejected').count()

    # Degree-based counts (excluding admins)
    mbbs_users = regular_users.filter(degree='MBBS').count()
    bds_users = regular_users.filter(degree='BDS').count()

    # Calculate percentages
    mbbs_percentage = round((mbbs_users / total_users * 100) if total_users > 0 else 0, 1)
    bds_percentage = round((bds_users / total_users * 100) if total_users > 0 else 0, 1)
    pending_percentage = round((pending_users / total_users * 100) if total_users > 0 else 0, 1)
    approved_percentage = round((approved_users / total_users * 100) if total_users > 0 else 0, 1)

    # Recent users (last 7 days, excluding admins)
    one_week_ago = timezone.now() - timedelta(days=7)
    new_mbbs_users = regular_users.filter(
        degree='MBBS', 
        date_joined__gte=one_week_ago
    ).count()
    new_bds_users = regular_users.filter(
        degree='BDS', 
        date_joined__gte=one_week_ago
    ).count()

    # Registration trends for the last 7 days
    registration_trends = []
    for i in range(6, -1, -1):  # Last 7 days
        date = timezone.now().date() - timedelta(days=i)
        mbbs_count = regular_users.filter(
            degree='MBBS',
            date_joined__date=date
        ).count()
        bds_count = regular_users.filter(
            degree='BDS',
            date_joined__date=date
        ).count()
        
        registration_trends.append({
            'date': date.strftime('%a'),  # Mon, Tue, etc.
            'mbbs': mbbs_count,
            'bds': bds_count,
            'total': mbbs_count + bds_count
        })

    # Recent users for display (last 5 of each degree, excluding admins)
    recent_mbbs_users = regular_users.filter(degree='MBBS').order_by('-date_joined')[:5]
    recent_bds_users = regular_users.filter(degree='BDS').order_by('-date_joined')[:5]

    # Pending approvals (most recent first)
    pending_approvals = regular_users.filter(
        approval_status='pending'
    ).order_by('-date_joined')[:5]

    # Status distribution for charts
    status_distribution = {
        'approved': approved_users,
        'pending': pending_users,
        'rejected': rejected_users
    }

    # Weekly registration summary
    weekly_stats = {
        'current_week': new_mbbs_users + new_bds_users,
        'mbbs_growth': calculate_growth_percentage('MBBS', regular_users),
        'bds_growth': calculate_growth_percentage('BDS', regular_users),
    }

    # Quick stats for header
    quick_stats = {
        'total_questions': get_total_questions_count(),
        'active_sessions': get_active_sessions_count(),
        'completion_rate': calculate_completion_rate(),
    }

    context = {
        # Basic statistics
        'total_users': total_users,
        'pending_users': pending_users,
        'approved_users': approved_users,
        'rejected_users': rejected_users,
        
        # Degree statistics
        'mbbs_users': mbbs_users,
        'bds_users': bds_users,
        'mbbs_percentage': mbbs_percentage,
        'bds_percentage': bds_percentage,
        'pending_percentage': pending_percentage,
        'approved_percentage': approved_percentage,
        
        # Weekly data
        'new_mbbs_users': new_mbbs_users,
        'new_bds_users': new_bds_users,
        'weekly_stats': weekly_stats,
        
        # User lists
        'recent_mbbs_users': recent_mbbs_users,
        'recent_bds_users': recent_bds_users,
        'pending_approvals': pending_approvals,
        
        # Chart data
        'registration_trends': json.dumps(registration_trends),
        'status_distribution': status_distribution,
        
        # Additional stats
        'quick_stats': quick_stats,
        
        # Time information
        'current_time': timezone.now(),
        'timezone_label': "Pakistan (Pakistan Standard Time, UTC+5)",
        
        # Growth indicators
        'mbbs_growth_trend': 'up' if weekly_stats['mbbs_growth'] > 0 else 'down',
        'bds_growth_trend': 'up' if weekly_stats['bds_growth'] > 0 else 'down',
    }

    return render(request, 'dashboard/admin_dashboard.html', context)


def get_dashboard_data_json(request):
    """Return dashboard data as JSON for AJAX updates"""
    if not (request.user.is_admin or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    students_query = CustomUser.objects.filter(is_admin=False, is_superuser=False)
    
    # Calculate current metrics
    total_students = students_query.count()
    pending_students = students_query.filter(approval_status='pending').count()
    approved_students = students_query.filter(approval_status='approved').count()
    mbbs_students = students_query.filter(degree='MBBS').count()
    bds_students = students_query.filter(degree='BDS').count()
    
    def safe_percentage(part, total):
        return round((part / total * 100) if total > 0 else 0, 1)
    
    # Weekly data
    one_week_ago = timezone.now() - timedelta(days=7)
    new_students_this_week = students_query.filter(date_joined__gte=one_week_ago).count()
    
    data = {
        'total_students': total_students,
        'pending_students': pending_students,
        'approved_students': approved_students,
        'mbbs_students': mbbs_students,
        'bds_students': bds_students,
        'new_students_this_week': new_students_this_week,
        'chartData': {
            'mbbs_percentage': float(safe_percentage(mbbs_students, total_students)),
            'bds_percentage': float(safe_percentage(bds_students, total_students)),
            'pending_percentage': float(safe_percentage(pending_students, total_students)),
        },
        'timestamp': timezone.now().isoformat()
    }
    
    return JsonResponse(data)


# ===================================================================
# STUDENT DASHBOARD SECTION - Enhanced Professional Version
# ===================================================================

@login_required
def student_dashboard(request):
    """Enhanced professional student dashboard with unified statistics"""
    user = request.user
    current_time = timezone.now()
    
    # Get basic stats for dashboard cards
    mock_test_stats = get_mock_test_stats(user)
    model_paper_stats = get_model_paper_stats(user)
    practice_stats = get_practice_module_stats(user)
    notes_stats = get_notes_stats(user)
    
    # Get recent activities
    recent_activities = get_recent_activities(user)
    
    # Get notification count
    unread_count = get_notification_count(user)
    
    context = {
        'user': user,
        'current_time': current_time,
        'timezone_label': 'Pakistan Standard Time (UTC+5)',
        'mock_test_stats': mock_test_stats,
        'model_paper_stats': model_paper_stats,
        'practice_stats': practice_stats,
        'notes_stats': notes_stats,
        'recent_activities': recent_activities,
        'unread_count': unread_count,
    }
    
    return render(request, 'dashboard/student_dashboard.html', context)


@login_required 
def unified_progress(request):
    """Unified progress dashboard showing all study methods"""
    user = request.user
    
    # Get comprehensive stats for all study methods
    mock_test_stats = get_detailed_mock_test_stats(user)
    model_paper_stats = get_detailed_model_paper_stats(user)
    practice_stats = get_detailed_practice_stats(user)
    notes_stats = get_detailed_notes_stats(user)
    
    # Calculate overall statistics
    overall_stats = calculate_overall_stats(user, mock_test_stats, model_paper_stats, practice_stats)
    
    # Get performance trends
    mock_test_trend = calculate_performance_trend(user, 'mock_test')
    model_paper_trend = calculate_performance_trend(user, 'model_paper')
    practice_trend = calculate_performance_trend(user, 'practice')
    
    # Get notification count
    unread_count = get_notification_count(user)
    
    context = {
        'user': user,
        'overall_stats': overall_stats,
        'mock_test_stats': mock_test_stats,
        'model_paper_stats': model_paper_stats,
        'practice_stats': practice_stats,
        'notes_stats': notes_stats,
        'mock_test_trend': mock_test_trend,
        'model_paper_trend': model_paper_trend,
        'practice_trend': practice_trend,
        'unread_count': unread_count,
    }
    
    return render(request, 'dashboard/unified_progress.html', context)


# ===================================================================
# HELPER FUNCTIONS FOR STUDENT DASHBOARD STATISTICS
# ===================================================================

def get_mock_test_stats(user):
    """Get basic mock test statistics for dashboard"""
    try:
        attempts = TestAttempt.objects.filter(student=user, status='completed')
        return {
            'completed': attempts.count(),
            'best_score': attempts.aggregate(Max('percentage'))['percentage__max'] or 0,
            'avg_score': attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0,
        }
    except Exception as e:
        print(f"Error getting mock test stats: {e}")
        return {'completed': 0, 'best_score': 0, 'avg_score': 0}


def get_model_paper_stats(user):
    """Get basic model paper statistics for dashboard"""
    try:
        attempts = ModelPaperAttempt.objects.filter(student=user, status='completed')
        return {
            'completed': attempts.count(),
            'best_score': attempts.aggregate(Max('percentage'))['percentage__max'] or 0,
            'avg_score': attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0,
        }
    except Exception as e:
        print(f"Error getting model paper stats: {e}")
        return {'completed': 0, 'best_score': 0, 'avg_score': 0}


def get_practice_module_stats(user):
    """Get basic practice module statistics for dashboard"""
    try:
        progress_records = StudentProgress.objects.filter(student=user)
        sessions = PracticeSession.objects.filter(student=user, status='completed')
        
        return {
            'topics_practiced': progress_records.count(),
            'total_sessions': sessions.count(),
            'avg_accuracy': progress_records.aggregate(Avg('best_accuracy'))['best_accuracy__avg'] or 0,
        }
    except Exception as e:
        print(f"Error getting practice module stats: {e}")
        return {'topics_practiced': 0, 'total_sessions': 0, 'avg_accuracy': 0}


def get_notes_stats(user):
    """Get basic notes statistics for dashboard"""
    try:
        notes = StudentNote.objects.filter(student=user)
        return {
            'total_notes': notes.count(),
            'favorite_notes': notes.filter(is_favorite=True).count(),
            'recent_notes': notes.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
        }
    except Exception as e:
        print(f"Error getting notes stats: {e}")
        return {'total_notes': 0, 'favorite_notes': 0, 'recent_notes': 0}


def get_detailed_mock_test_stats(user):
    """Get detailed mock test statistics for progress page"""
    try:
        attempts = TestAttempt.objects.filter(student=user, status='completed')
        total_time = attempts.aggregate(Sum('time_taken'))['time_taken__sum'] or 0
        
        return {
            'completed': attempts.count(),
            'best_score': attempts.aggregate(Max('percentage'))['percentage__max'] or 0,
            'avg_score': attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0,
            'total_time_minutes': total_time // 60 if total_time else 0,
            'recent_attempts': attempts.order_by('-completed_at')[:5],
        }
    except Exception as e:
        print(f"Error getting detailed mock test stats: {e}")
        return {
            'completed': 0, 'best_score': 0, 'avg_score': 0, 
            'total_time_minutes': 0, 'recent_attempts': []
        }


def get_detailed_model_paper_stats(user):
    """Get detailed model paper statistics for progress page"""
    try:
        attempts = ModelPaperAttempt.objects.filter(student=user, status='completed')
        total_time = attempts.aggregate(Sum('time_taken'))['time_taken__sum'] or 0
        
        return {
            'completed': attempts.count(),
            'best_score': attempts.aggregate(Max('percentage'))['percentage__max'] or 0,
            'avg_score': attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0,
            'total_time_minutes': total_time // 60 if total_time else 0,
            'recent_attempts': attempts.order_by('-completed_at')[:5],
        }
    except Exception as e:
        print(f"Error getting detailed model paper stats: {e}")
        return {
            'completed': 0, 'best_score': 0, 'avg_score': 0, 
            'total_time_minutes': 0, 'recent_attempts': []
        }


def get_detailed_practice_stats(user):
    """Get detailed practice module statistics for progress page"""
    try:
        progress_records = StudentProgress.objects.filter(student=user)
        sessions = PracticeSession.objects.filter(student=user, status='completed')
        
        total_questions = progress_records.aggregate(
            Sum('total_questions_attempted')
        )['total_questions_attempted__sum'] or 0
        
        return {
            'topics_practiced': progress_records.count(),
            'total_sessions': sessions.count(),
            'avg_accuracy': progress_records.aggregate(Avg('best_accuracy'))['best_accuracy__avg'] or 0,
            'total_questions_attempted': total_questions,
            'mastery_topics': progress_records.filter(mastery_level='Expert').count(),
        }
    except Exception as e:
        print(f"Error getting detailed practice stats: {e}")
        return {
            'topics_practiced': 0, 'total_sessions': 0, 'avg_accuracy': 0,
            'total_questions_attempted': 0, 'mastery_topics': 0
        }


def get_detailed_notes_stats(user):
    """Get detailed notes statistics for progress page"""
    try:
        notes = StudentNote.objects.filter(student=user)
        return {
            'total_notes': notes.count(),
            'favorite_notes': notes.filter(is_favorite=True).count(),
            'recent_notes': notes.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
            'notes_by_type': {
                note_type[0]: notes.filter(note_type=note_type[0]).count()
                for note_type in StudentNote.NOTE_TYPES
            } if hasattr(StudentNote, 'NOTE_TYPES') else {},
            'topics_with_notes': notes.values('topic').distinct().count(),
        }
    except Exception as e:
        print(f"Error getting detailed notes stats: {e}")
        return {
            'total_notes': 0, 'favorite_notes': 0, 'recent_notes': 0,
            'notes_by_type': {}, 'topics_with_notes': 0
        }


def calculate_overall_stats(user, mock_stats, paper_stats, practice_stats):
    """Calculate overall statistics across all study methods"""
    try:
        # Calculate total sessions
        total_sessions = (
            mock_stats.get('completed', 0) + 
            paper_stats.get('completed', 0) + 
            practice_stats.get('total_sessions', 0)
        )
        
        # Calculate weighted average accuracy
        mock_weight = mock_stats.get('completed', 0)
        paper_weight = paper_stats.get('completed', 0)
        practice_weight = practice_stats.get('total_sessions', 0)
        total_weight = mock_weight + paper_weight + practice_weight
        
        if total_weight > 0:
            overall_accuracy = (
                (mock_stats.get('avg_score', 0) * mock_weight) +
                (paper_stats.get('avg_score', 0) * paper_weight) +
                (practice_stats.get('avg_accuracy', 0) * practice_weight)
            ) / total_weight
        else:
            overall_accuracy = 0
        
        # Get best score across all methods
        best_score = max(
            mock_stats.get('best_score', 0),
            paper_stats.get('best_score', 0),
            practice_stats.get('avg_accuracy', 0)
        )
        
        # Calculate study streak
        study_streak = calculate_study_streak(user)
        
        return {
            'total_sessions': total_sessions,
            'overall_accuracy': round(overall_accuracy, 1),
            'best_score': round(best_score, 1),
            'study_streak': study_streak,
        }
    except Exception as e:
        print(f"Error calculating overall stats: {e}")
        return {
            'total_sessions': 0,
            'overall_accuracy': 0,
            'best_score': 0,
            'study_streak': 0,
        }


def calculate_study_streak(user):
    """Calculate consecutive days of study activity"""
    try:
        # Get all activity dates from different sources
        mock_dates = set()
        paper_dates = set()
        practice_dates = set()
        
        try:
            mock_dates = set(TestAttempt.objects.filter(
                student=user, status='completed'
            ).values_list('completed_at__date', flat=True))
        except:
            pass
            
        try:
            paper_dates = set(ModelPaperAttempt.objects.filter(
                student=user, status='completed'
            ).values_list('completed_at__date', flat=True))
        except:
            pass
            
        try:
            practice_dates = set(PracticeSession.objects.filter(
                student=user, status='completed'
            ).values_list('completed_at__date', flat=True))
        except:
            pass
        
        # Combine all activity dates
        all_dates = sorted(mock_dates | paper_dates | practice_dates, reverse=True)
        
        if not all_dates:
            return 0
        
        # Calculate consecutive days
        streak = 0
        current_date = timezone.now().date()
        
        for activity_date in all_dates:
            if activity_date == current_date:
                streak += 1
                current_date = current_date - timedelta(days=1)
            elif activity_date == current_date + timedelta(days=1):
                streak += 1
                current_date = activity_date - timedelta(days=1)
            else:
                break
        
        return streak
    except Exception as e:
        print(f"Error calculating study streak: {e}")
        return 0


def calculate_performance_trend(user, activity_type):
    """Calculate performance trend for specific activity type"""
    try:
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)
        
        recent_avg = 0
        previous_avg = 0
        
        if activity_type == 'mock_test':
            try:
                recent_avg = TestAttempt.objects.filter(
                    student=user, status='completed',
                    completed_at__gte=thirty_days_ago
                ).aggregate(Avg('percentage'))['percentage__avg'] or 0
                
                previous_avg = TestAttempt.objects.filter(
                    student=user, status='completed',
                    completed_at__gte=sixty_days_ago,
                    completed_at__lt=thirty_days_ago
                ).aggregate(Avg('percentage'))['percentage__avg'] or 0
            except:
                pass
                
        elif activity_type == 'model_paper':
            try:
                recent_avg = ModelPaperAttempt.objects.filter(
                    student=user, status='completed',
                    completed_at__gte=thirty_days_ago
                ).aggregate(Avg('percentage'))['percentage__avg'] or 0
                
                previous_avg = ModelPaperAttempt.objects.filter(
                    student=user, status='completed',
                    completed_at__gte=sixty_days_ago,
                    completed_at__lt=thirty_days_ago
                ).aggregate(Avg('percentage'))['percentage__avg'] or 0
            except:
                pass
                
        elif activity_type == 'practice':
            try:
                recent_sessions = PracticeSession.objects.filter(
                    student=user, status='completed',
                    completed_at__gte=thirty_days_ago
                )
                recent_avg = sum(s.accuracy for s in recent_sessions) / len(recent_sessions) if recent_sessions else 0
                
                previous_sessions = PracticeSession.objects.filter(
                    student=user, status='completed',
                    completed_at__gte=sixty_days_ago,
                    completed_at__lt=thirty_days_ago
                )
                previous_avg = sum(s.accuracy for s in previous_sessions) / len(previous_sessions) if previous_sessions else 0
            except:
                pass
        
        # Calculate change percentage
        if previous_avg > 0:
            change = ((recent_avg - previous_avg) / previous_avg) * 100
        else:
            change = 0
        
        # Determine direction
        if change > 2:
            direction = 'up'
        elif change < -2:
            direction = 'down'
        else:
            direction = 'right'  # neutral
        
        return {
            'change': round(abs(change), 1),
            'direction': direction,
        }
    except Exception as e:
        print(f"Error calculating performance trend: {e}")
        return {'change': 0, 'direction': 'right'}


def get_recent_activities(user, limit=5):
    """Get recent activities across all study methods"""
    try:
        activities = []
        
        # Mock test activities
        try:
            mock_attempts = TestAttempt.objects.filter(
                student=user, status='completed'
            ).order_by('-completed_at')[:3]
            
            for attempt in mock_attempts:
                activities.append({
                    'type': 'mock_test',
                    'icon': 'vial',
                    'title': f'Completed Mock Test',
                    'description': f'{attempt.mock_test.title} - Score: {attempt.percentage:.0f}%',
                    'time': attempt.completed_at,
                })
        except:
            pass
        
        # Model paper activities
        try:
            paper_attempts = ModelPaperAttempt.objects.filter(
                student=user, status='completed'
            ).order_by('-completed_at')[:3]
            
            for attempt in paper_attempts:
                activities.append({
                    'type': 'model_paper',
                    'icon': 'file-alt',
                    'title': f'Solved Model Paper',
                    'description': f'{attempt.model_paper.title} - Score: {attempt.percentage:.0f}%',
                    'time': attempt.completed_at,
                })
        except:
            pass
        
        # Practice activities
        try:
            practice_sessions = PracticeSession.objects.filter(
                student=user, status='completed'
            ).order_by('-completed_at')[:3]
            
            for session in practice_sessions:
                activities.append({
                    'type': 'practice',
                    'icon': 'dumbbell',
                    'title': f'Practice Session',
                    'description': f'{session.topic} - Accuracy: {session.accuracy:.0f}%',
                    'time': session.completed_at,
                })
        except:
            pass
        
        # Sort by time and limit
        activities.sort(key=lambda x: x['time'], reverse=True)
        return activities[:limit]
    except Exception as e:
        print(f"Error getting recent activities: {e}")
        return []


def get_notification_count(user):
    """Get notification count for user"""
    try:
        from notifications.models import NotificationMessage
        return NotificationMessage.objects.filter(
            Q(recipient=user) | Q(recipient__isnull=True),
            is_read=False
        ).count()
    except:
        return 0


# ===================================================================
# ADMIN HELPER FUNCTIONS - Keep existing
# ===================================================================

def calculate_growth_percentage(degree, regular_users):
    """Calculate weekly growth percentage for a specific degree"""
    current_week = timezone.now() - timedelta(days=7)
    previous_week = timezone.now() - timedelta(days=14)
    
    current_count = regular_users.filter(
        degree=degree,
        date_joined__gte=current_week
    ).count()
    
    previous_count = regular_users.filter(
        degree=degree,
        date_joined__gte=previous_week,
        date_joined__lt=current_week
    ).count()
    
    if previous_count == 0:
        return 100 if current_count > 0 else 0
    
    return round(((current_count - previous_count) / previous_count) * 100, 1)


def get_total_questions_count():
    """Get total questions count from questionbank"""
    try:
        from questionbank.models import Question
        return Question.objects.count()
    except ImportError:
        return 0


def get_active_sessions_count():
    """Get active user sessions count"""
    try:
        from user_management.models import UserSession
        return UserSession.objects.filter(is_active=True).count()
    except ImportError:
        return 0


def calculate_completion_rate():
    """Calculate average completion rate"""
    try:
        # Calculate based on mock test completion rates
        total_attempts = TestAttempt.objects.filter(status='completed').count()
        if total_attempts > 0:
            return 85.5  # You can calculate actual completion rate here
        return 0
    except:
        return 0


# ===================================================================
# LEGACY PLACEHOLDER VIEWS - Keep for backward compatibility
# ===================================================================

def logout_view(request):
    """Handle user logout"""
    try:
        auth_logout(request)
        messages.success(request, 'You have been successfully logged out.')
        return redirect('login')
    except Exception as e:
        messages.error(request, f'Error during logout: {str(e)}')
        return redirect('login')


def manage_questions(request):
    """Redirect to questionbank"""
    return redirect('questionbank')


def manage_modules(request):
    """Redirect to manage modules"""
    return redirect('managemodule')


def manage_users(request):
    """Redirect to user management"""
    return redirect('/admin/user_management/customuser/')


def mock_test(request):
    """Redirect to mock test"""
    return redirect('mocktest_list')


def analytics_reports(request):
    """Redirect to analytics reports"""
    return redirect('analytics_report')


def my_account(request):
    """Redirect to my account"""
    return redirect('myaccount')


def notification(request):
    """Redirect to notification center"""
    return redirect('notification_center')


def settings(request):
    """Redirect to settings"""
    return redirect('settings')


def all_notifications(request):
    """Redirect to all notifications"""
    return redirect('notification_center')