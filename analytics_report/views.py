# analytics_report/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Avg, Q, Max, Min
from django.utils import timezone
from datetime import datetime, timedelta
import json
import csv

from user_management.models import CustomUser
from questionbank.models import Question, CSVImportHistory
from mocktest.models import MockTest, TestAttempt, TestResponse


def safe_float(value):
    """Safely convert value to float, handling None and Decimal types"""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def calculate_growth(current, previous):
    """Calculate growth percentage between two values"""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def is_admin_required(user):
    """Check if user is admin"""
    return user.is_authenticated and (user.is_admin or user.is_superuser)


@login_required
def analytics_report(request):
    """Main analytics dashboard view"""
    if not is_admin_required(request.user):
        return render(request, 'analytics_report/analytics_report.html', {
            'analytics': get_default_analytics(),
            'current_filters': {
                'date_range': 30,
                'degree': '',
                'year': '',
            }
        })
    
    # Get filter parameters
    date_range = int(request.GET.get('date_range', 30))
    degree_filter = request.GET.get('degree', '')
    year_filter = request.GET.get('year', '')
    
    # Calculate date range
    end_date = timezone.now()
    start_date = end_date - timedelta(days=date_range)
    previous_start = start_date - timedelta(days=date_range)
    
    # Get analytics data
    analytics = get_analytics_data(start_date, end_date, previous_start, degree_filter, year_filter)
    
    context = {
        'analytics': analytics,
        'current_filters': {
            'date_range': date_range,
            'degree': degree_filter,
            'year': year_filter,
        }
    }
    
    return render(request, 'analytics_report/analytics_report.html', context)


def get_default_analytics():
    """Return default analytics data when no access or error"""
    return {
        'total_students': 0,
        'total_questions': 0,
        'total_tests': 0,
        'avg_test_score': 0,
        'students_growth': 0,
        'questions_growth': 0,
        'tests_growth': 0,
        'score_trend': 0,
        'degree_labels': json.dumps([]),
        'degree_data': json.dumps([]),
        'difficulty_data': json.dumps([0, 0, 0]),
        'trend_labels': json.dumps([]),
        'trend_scores': json.dumps([]),
        'trend_attempts': json.dumps([]),
        'test_performance': [],
        'top_students': [],
        'subject_performance': [],
        'active_tests': 0,
        'pending_students': 0,
        'recent_csv_imports': 0,
    }


def get_analytics_data(start_date, end_date, previous_start, degree_filter='', year_filter=''):
    """Calculate comprehensive analytics data"""
    try:
        # Base querysets with filters
        students_qs = CustomUser.objects.filter(is_admin=False, is_superuser=False)
        questions_qs = Question.objects.all()
        tests_qs = MockTest.objects.all()
        attempts_qs = TestAttempt.objects.all()
        
        # Apply degree filter
        if degree_filter:
            students_qs = students_qs.filter(degree=degree_filter)
            questions_qs = questions_qs.filter(degree=degree_filter)
            tests_qs = tests_qs.filter(degree=degree_filter)
        
        # Apply year filter
        if year_filter:
            questions_qs = questions_qs.filter(year=year_filter)
            tests_qs = tests_qs.filter(year=year_filter)
        
        # === KEY METRICS ===
        
        # Current period metrics
        current_students = students_qs.filter(date_joined__gte=start_date, date_joined__lte=end_date).count()
        current_questions = questions_qs.filter(created_on__gte=start_date, created_on__lte=end_date).count()
        current_tests = tests_qs.filter(created_at__gte=start_date, created_at__lte=end_date).count()
        current_attempts = attempts_qs.filter(started_at__gte=start_date, started_at__lte=end_date)
        
        # Previous period metrics for comparison
        previous_students = students_qs.filter(date_joined__gte=previous_start, date_joined__lt=start_date).count()
        previous_questions = questions_qs.filter(created_on__gte=previous_start, created_on__lt=start_date).count()
        previous_tests = tests_qs.filter(created_at__gte=previous_start, created_at__lt=start_date).count()
        previous_attempts = attempts_qs.filter(started_at__gte=previous_start, started_at__lt=start_date)
        
        # Calculate average scores
        current_avg_score = safe_float(current_attempts.filter(status='completed').aggregate(avg=Avg('percentage'))['avg'])
        previous_avg_score = safe_float(previous_attempts.filter(status='completed').aggregate(avg=Avg('percentage'))['avg'])
        
        # === CHART DATA ===
        
        # Degree distribution
        degree_data = questions_qs.values('degree').annotate(count=Count('id')).order_by('degree')
        degree_labels = [item['degree'] for item in degree_data]
        degree_counts = [item['count'] for item in degree_data]
        
        # Difficulty distribution
        difficulty_data = questions_qs.values('difficulty').annotate(count=Count('id')).order_by('difficulty')
        difficulty_counts = [0, 0, 0]  # Easy, Medium, Hard
        for item in difficulty_data:
            if item['difficulty'] == 'Easy':
                difficulty_counts[0] = item['count']
            elif item['difficulty'] == 'Medium':
                difficulty_counts[1] = item['count']
            elif item['difficulty'] == 'Hard':
                difficulty_counts[2] = item['count']
        
        # Performance trends (last 30 days)
        trend_labels = []
        trend_scores = []
        trend_attempts = []
        
        for i in range(30):
            date = end_date - timedelta(days=29-i)
            date_attempts = attempts_qs.filter(
                started_at__date=date.date(),
                status='completed'
            )
            
            daily_avg = safe_float(date_attempts.aggregate(avg=Avg('percentage'))['avg'])
            daily_count = date_attempts.count()
            
            trend_labels.append(date.strftime('%m/%d'))
            trend_scores.append(round(daily_avg, 1))
            trend_attempts.append(daily_count)
        
        # === TEST PERFORMANCE ===
        
        test_performance = []
        for test in tests_qs.select_related().order_by('-created_at')[:10]:
            test_attempts = attempts_qs.filter(mock_test=test)
            completed_attempts = test_attempts.filter(status='completed')
            
            total_attempts = test_attempts.count()
            completion_rate = (completed_attempts.count() / total_attempts * 100) if total_attempts > 0 else 0
            avg_score = safe_float(completed_attempts.aggregate(avg=Avg('percentage'))['avg'])
            
            test_performance.append({
                'id': test.id,
                'title': test.title,
                'degree': test.degree,
                'total_attempts': total_attempts,
                'completion_rate': round(completion_rate, 1),
                'avg_score': round(avg_score, 1),
                'status': test.status,
                'get_status_display': test.get_status_display(),
            })
        
        # === TOP PERFORMING STUDENTS ===
        
        top_students = []
        student_performance = attempts_qs.filter(
            status='completed',
            started_at__gte=start_date
        ).values('student').annotate(
            test_count=Count('id'),
            avg_score=Avg('percentage'),
            latest_score=Max('percentage')
        ).order_by('-avg_score')[:10]
        
        for perf in student_performance:
            try:
                student = CustomUser.objects.get(id=perf['student'])
                top_students.append({
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'degree': student.degree,
                    'profile_image': student.profile_image,
                    'test_count': perf['test_count'],
                    'avg_score': round(safe_float(perf['avg_score']), 1),
                    'latest_score': round(safe_float(perf['latest_score']), 1),
                })
            except CustomUser.DoesNotExist:
                continue
        
        # === SUBJECT PERFORMANCE ===
        
        subject_performance = []
        subjects = questions_qs.values('subject').annotate(
            question_count=Count('id')
        ).order_by('-question_count')[:10]
        
        for subject_data in subjects:
            subject_name = subject_data['subject']
            subject_questions = questions_qs.filter(subject=subject_name)
            
            # Get difficulty distribution
            easy_count = subject_questions.filter(difficulty='Easy').count()
            medium_count = subject_questions.filter(difficulty='Medium').count()
            hard_count = subject_questions.filter(difficulty='Hard').count()
            
            # Get most common block
            common_block = subject_questions.values('block').annotate(
                count=Count('id')
            ).order_by('-count').first()
            
            # Calculate average score for this subject
            subject_responses = TestResponse.objects.filter(
                question__subject=subject_name,
                attempt__status='completed',
                attempt__started_at__gte=start_date
            )
            
            if subject_responses.exists():
                correct_responses = subject_responses.filter(is_correct=True).count()
                total_responses = subject_responses.count()
                avg_score = (correct_responses / total_responses * 100) if total_responses > 0 else 0
            else:
                avg_score = 0
            
            subject_performance.append({
                'name': subject_name,
                'question_count': subject_data['question_count'],
                'easy_count': easy_count,
                'medium_count': medium_count,
                'hard_count': hard_count,
                'common_block': common_block['block'] if common_block else None,
                'avg_score': round(safe_float(avg_score), 1),
            })
        
        # === COMPILE ANALYTICS DATA ===
        
        analytics_data = {
            # Key metrics
            'total_students': students_qs.count(),
            'total_questions': questions_qs.count(),
            'total_tests': tests_qs.count(),
            'avg_test_score': round(safe_float(current_avg_score), 1),
            
            # Growth calculations
            'students_growth': calculate_growth(current_students, previous_students),
            'questions_growth': calculate_growth(current_questions, previous_questions),
            'tests_growth': calculate_growth(current_tests, previous_tests),
            'score_trend': calculate_growth(current_avg_score, previous_avg_score),
            
            # Chart data
            'degree_labels': json.dumps(degree_labels),
            'degree_data': json.dumps(degree_counts),
            'difficulty_data': json.dumps(difficulty_counts),
            'trend_labels': json.dumps(trend_labels),
            'trend_scores': json.dumps(trend_scores),
            'trend_attempts': json.dumps(trend_attempts),
            
            # Table data
            'test_performance': test_performance,
            'top_students': top_students,
            'subject_performance': subject_performance,
            
            # Additional stats
            'active_tests': tests_qs.filter(status='live').count(),
            'pending_students': students_qs.filter(approval_status='pending').count(),
            'recent_csv_imports': CSVImportHistory.objects.filter(
                uploaded_at__gte=start_date
            ).count(),
        }
        
        return analytics_data
        
    except Exception as e:
        # Return default data on any error
        print(f"Analytics error: {e}")
        return get_default_analytics()


@login_required
def export_analytics_report(request):
    """Export analytics data as CSV"""
    if not is_admin_required(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        # Get filter parameters
        date_range = int(request.GET.get('date_range', 30))
        degree_filter = request.GET.get('degree', '')
        year_filter = request.GET.get('year', '')
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=date_range)
        previous_start = start_date - timedelta(days=date_range)
        
        # Get analytics data
        analytics = get_analytics_data(start_date, end_date, previous_start, degree_filter, year_filter)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="analytics_report_{end_date.strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow(['PulsePrep Analytics Report'])
        writer.writerow([f'Generated: {end_date.strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([f'Date Range: Last {date_range} days'])
        if degree_filter:
            writer.writerow([f'Degree Filter: {degree_filter}'])
        if year_filter:
            writer.writerow([f'Year Filter: {year_filter}'])
        writer.writerow([])
        
        # Key Metrics
        writer.writerow(['KEY METRICS'])
        writer.writerow(['Metric', 'Value', 'Growth %'])
        writer.writerow(['Total Students', analytics['total_students'], analytics['students_growth']])
        writer.writerow(['Total Questions', analytics['total_questions'], analytics['questions_growth']])
        writer.writerow(['Total Tests', analytics['total_tests'], analytics['tests_growth']])
        writer.writerow(['Avg Test Score', f"{analytics['avg_test_score']}%", analytics['score_trend']])
        writer.writerow([])
        
        # Test Performance
        writer.writerow(['TEST PERFORMANCE'])
        writer.writerow(['Test Title', 'Degree', 'Total Attempts', 'Avg Score %', 'Completion Rate %', 'Status'])
        for test in analytics['test_performance']:
            writer.writerow([
                test['title'],
                test['degree'] or 'All',
                test['total_attempts'],
                safe_float(test['avg_score']),
                safe_float(test['completion_rate']),
                test['status']
            ])
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def analytics_api(request):
    """API endpoint for real-time analytics data"""
    if not is_admin_required(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        # Get basic stats for dashboard widgets
        data = {
            'total_students': CustomUser.objects.filter(is_admin=False).count(),
            'total_questions': Question.objects.count(),
            'active_tests': MockTest.objects.filter(status='live').count(),
            'pending_approvals': CustomUser.objects.filter(approval_status='pending').count(),
            'recent_attempts': TestAttempt.objects.filter(
                started_at__gte=timezone.now() - timedelta(hours=24)
            ).count(),
            'timestamp': timezone.now().isoformat()
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def subject_analytics(request, subject_name):
    """Detailed analytics for a specific subject"""
    if not is_admin_required(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        # Get subject questions
        questions = Question.objects.filter(subject=subject_name)
        
        # Get subject performance data
        responses = TestResponse.objects.filter(
            question__subject=subject_name,
            attempt__status='completed'
        )
        
        # Calculate metrics
        total_questions = questions.count()
        total_responses = responses.count()
        correct_responses = responses.filter(is_correct=True).count()
        accuracy = (correct_responses / total_responses * 100) if total_responses > 0 else 0
        
        # Difficulty breakdown
        difficulty_stats = questions.values('difficulty').annotate(
            count=Count('id')
        )
        
        # Convert difficulty stats to safe format
        safe_difficulty_stats = []
        for stat in difficulty_stats:
            safe_difficulty_stats.append({
                'difficulty': stat['difficulty'],
                'count': stat['count'],
            })
        
        # Topic breakdown
        topic_stats = questions.values('topic').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        data = {
            'subject_name': subject_name,
            'total_questions': total_questions,
            'total_responses': total_responses,
            'accuracy': round(safe_float(accuracy), 1),
            'difficulty_stats': safe_difficulty_stats,
            'topic_stats': list(topic_stats),
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)