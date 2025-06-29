# modelpaper/views.py - COMPLETE: Added image support throughout

import csv
import io
import json
import random
import html

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Max, Sum
from django.db import models
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model

from .models import ModelPaper, PaperQuestion, ModelPaperAttempt, ModelPaperResponse, PaperCSVImportHistory
from .forms import ModelPaperForm, PaperQuestionImportForm

# IMPORTS FOR ACCESS CONTROL
from user_management.decorators import (
    content_access_required, 
    admin_required, 
    filter_by_user_access as apply_user_access_filter
)
from user_management.utils import (
    get_user_access_info, 
    check_object_access
)

User = get_user_model()

@content_access_required
def take_paper(request, paper_id):
    """Enhanced student takes the paper with mode selection popup support and image support"""
    paper = get_object_or_404(ModelPaper, id=paper_id)
    student = request.user
    
    # Get practice mode from URL parameter (default to None for popup)
    practice_mode = request.GET.get('practice_mode')
    
    print(f"DEBUG: User {student} trying to take paper: {paper.title} with mode: {practice_mode}")
    
    # ACCESS CONTROL: Check if user can access this paper
    if not check_object_access(paper, student):
        messages.error(request, "You don't have access to this paper.")
        return redirect('student_model_papers')
    
    # Check if paper is active
    now = timezone.now()
    if paper.status != 'live':
        messages.error(request, f"This paper is not currently available. Status: {paper.status}")
        return redirect('student_model_papers')
    
    # Check time bounds
    if now < paper.start_datetime:
        messages.error(request, "This paper has not started yet.")
        return redirect('student_model_papers')
    
    if now > paper.end_datetime:
        messages.error(request, "This paper has already ended.")
        return redirect('student_model_papers')
    
    # Check attempt limit
    existing_attempts = ModelPaperAttempt.objects.filter(
        student=student, 
        model_paper=paper,
        status='completed'
    ).count()
    
    if existing_attempts >= paper.max_attempts:
        messages.error(request, f"You have reached the maximum attempts ({paper.max_attempts}) for this paper.")
        return redirect('student_model_papers')
    
    # Check if there's already an in-progress attempt
    current_attempt = ModelPaperAttempt.objects.filter(
        student=student,
        model_paper=paper,
        status='in_progress'
    ).first()
    
    # Determine if mode selection popup should be shown
    show_mode_popup = not practice_mode and not current_attempt
    
    # Set default practice mode if not specified
    if not practice_mode:
        practice_mode = 'student'  # Default mode
    
    # Create new attempt if none exists
    if not current_attempt:
        current_attempt = ModelPaperAttempt.objects.create(
            student=student,
            model_paper=paper,
            status='in_progress',
            started_at=timezone.now()
        )
        print(f"DEBUG: Created new attempt with ID: {current_attempt.id}")
    else:
        print(f"DEBUG: Found existing attempt with ID: {current_attempt.id}")
    
    # Get questions based on paper filters WITH ACCESS CONTROL
    paper_questions = paper.get_questions()
    paper_questions = apply_user_access_filter(paper_questions, request.user)
    
    if paper_questions.count() == 0:
        messages.error(request, "This paper has no accessible questions for you.")
        return redirect('student_model_papers')
    
    # Process questions - WITH image handling
    processed_questions = []
    for pq in paper_questions:
        question_data = {
            'id': pq.id,
            'order': len(processed_questions) + 1,
            'text': pq.question_text,
            'explanation': pq.explanation or '',
            'options': {},
            'correct_answer': pq.correct_answer,  # Add correct answer for student mode
            'has_paper_image': pq.has_paper_image,
            'has_explanation_image': pq.has_explanation_image,
            'paper_image_url': pq.paper_image_url,
            'explanation_image_url': pq.explanation_image_url,
        }
        
        # Add options
        if pq.option_a:
            question_data['options']['A'] = pq.option_a
        if pq.option_b:
            question_data['options']['B'] = pq.option_b
        if pq.option_c:
            question_data['options']['C'] = pq.option_c
        if pq.option_d:
            question_data['options']['D'] = pq.option_d
        if pq.option_e:
            question_data['options']['E'] = pq.option_e
        
        processed_questions.append(question_data)
    
    # Randomize if enabled
    if paper.randomize_questions:
        random.shuffle(processed_questions)
    
    context = {
        'paper': paper,
        'attempt': current_attempt,
        'paper_questions': processed_questions,
        'total_questions': len(processed_questions),
        'practice_mode': practice_mode,
        'show_mode_popup': show_mode_popup,  # Flag for popup display
        'user_access': get_user_access_info(student),
    }
    
    return render(request, 'modelpaper/take_paper.html', context)


@content_access_required
def paper_result(request, attempt_id):
    """Enhanced show paper results with access control and image support"""
    attempt = get_object_or_404(ModelPaperAttempt, id=attempt_id)
    
    # Security check: Only allow the student who took the paper to view results
    if attempt.student != request.user:
        messages.error(request, "You can only view your own paper results.")
        return redirect('student_model_papers')
    
    # ACCESS CONTROL: Check if user can access the paper
    if not check_object_access(attempt.model_paper, request.user):
        messages.error(request, "You don't have access to this paper's results.")
        return redirect('student_model_papers')
    
    # Ensure the paper is actually completed
    if attempt.status == 'in_progress':
        messages.warning(request, "This paper is still in progress.")
        return redirect('take_paper', paper_id=attempt.model_paper.id)
    
    # Get all responses with questions, including unanswered ones - FILTERED BY ACCESS
    all_questions = attempt.model_paper.get_questions()
    accessible_questions = apply_user_access_filter(all_questions, request.user)
    
    # Process responses - WITH image handling
    processed_responses = []
    for paper_question in accessible_questions:
        try:
            response = ModelPaperResponse.objects.get(
                attempt=attempt,
                paper_question=paper_question
            )
        except ModelPaperResponse.DoesNotExist:
            # Create a dummy response for unanswered questions
            response = ModelPaperResponse(
                attempt=attempt,
                paper_question=paper_question,
                selected_answer=None,
                is_correct=False
            )
        
        # Create response data - WITH image processing
        response_data = {
            'response': response,
            'question': paper_question,
            'is_correct': response.is_correct,
            'selected_answer': response.selected_answer,
            'time_spent': getattr(response, 'time_spent', 0),
            'has_paper_image': paper_question.has_paper_image,
            'has_explanation_image': paper_question.has_explanation_image,
            'paper_image_url': paper_question.paper_image_url,
            'explanation_image_url': paper_question.explanation_image_url,
        }
        
        processed_responses.append(response_data)
    
    # Calculate additional statistics based on accessible questions
    total_questions = len(processed_responses)
    answered_questions = len([r for r in processed_responses if r['response'].selected_answer])
    unanswered_questions = total_questions - answered_questions
    correct_answers = len([r for r in processed_responses if r['response'].is_correct])
    incorrect_answers = answered_questions - correct_answers
    
    # Calculate time efficiency
    time_efficiency = 0
    if attempt.model_paper.duration_minutes > 0:
        time_taken_minutes = attempt.time_taken / 60 if attempt.time_taken else 0
        time_efficiency = min(100, (time_taken_minutes / attempt.model_paper.duration_minutes) * 100)
    
    # Calculate grade based on percentage
    def get_grade(percentage):
        if percentage >= 90:
            return 'A+'
        elif percentage >= 80:
            return 'A'
        elif percentage >= 70:
            return 'B'
        elif percentage >= 60:
            return 'C'
        elif percentage >= 50:
            return 'D'
        else:
            return 'F'
    
    # Create calculated values instead of setting properties
    time_taken_display = f"{attempt.time_taken // 60}:{attempt.time_taken % 60:02d}" if attempt.time_taken else "0:00"
    time_taken_formatted = f"{attempt.time_taken // 60} minutes {attempt.time_taken % 60} seconds" if attempt.time_taken else "0 seconds"
    time_taken_minutes = attempt.time_taken / 60 if attempt.time_taken else 0
    
    context = {
        'attempt': attempt,
        'paper': attempt.model_paper,
        'responses': processed_responses,  # Using processed responses (with image data)
        'passed': attempt.passed,
        'user': request.user,
        
        # Additional statistics
        'total_questions': total_questions,
        'answered_questions': answered_questions,
        'unanswered_questions': unanswered_questions,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,
        'time_efficiency': round(time_efficiency, 1),
        'grade': get_grade(float(attempt.percentage)),
        'accessible_questions_count': total_questions,
        'original_questions_count': attempt.model_paper.total_questions,
        
        # Calculated time values (not setting as properties)
        'time_taken_display': time_taken_display,
        'time_taken_formatted': time_taken_formatted,
        'time_taken_minutes': time_taken_minutes,
        
        # Access control info
        'user_access': get_user_access_info(request.user),
        
        # For template calculations
        'current_year': timezone.now().year,
    }
    
    return render(request, 'modelpaper/paper_results.html', context)


@content_access_required
@require_POST
def submit_paper_answer(request):
    """Enhanced save student's answer for paper question with mode support"""
    attempt_id = request.POST.get('attempt_id')
    question_id = request.POST.get('question_id')
    answer = request.POST.get('answer')
    practice_mode = request.POST.get('practice_mode', 'student')
    
    attempt = get_object_or_404(ModelPaperAttempt, id=attempt_id)
    paper_question = get_object_or_404(PaperQuestion, id=question_id)
    
    # ACCESS CONTROL: Verify user owns this attempt
    if attempt.student != request.user:
        return JsonResponse({
            'success': False,
            'error': 'Unauthorized access to paper attempt'
        }, status=403)
    
    # ACCESS CONTROL: Check if user can access this question
    if not check_object_access(paper_question, request.user):
        return JsonResponse({
            'success': False,
            'error': 'You don\'t have access to this question'
        }, status=403)
    
    # Validate answer format
    if answer not in ['A', 'B', 'C', 'D', 'E']:
        return JsonResponse({
            'success': False,
            'error': 'Invalid answer format'
        }, status=400)
    
    # Save or update response
    response, created = ModelPaperResponse.objects.update_or_create(
        attempt=attempt,
        paper_question=paper_question,
        defaults={
            'selected_answer': answer,
        }
    )
    
    # Check if answer is correct
    response.check_answer()
    response.save()
    
    # Prepare response data based on practice mode
    response_data = {
        'success': True,
        'selected_answer': answer,
        'practice_mode': practice_mode,
        'user_access_level': get_user_access_info(request.user).get('level', 'student')
    }
    
    # Only include feedback data for student mode
    if practice_mode == 'student':
        response_data.update({
            'is_correct': response.is_correct,
            'correct_answer': paper_question.correct_answer,
            'explanation': paper_question.explanation or '',
            'has_explanation_image': paper_question.has_explanation_image,
            'explanation_image_url': paper_question.explanation_image_url,
        })
    
    return JsonResponse(response_data)


@content_access_required
@require_POST
def submit_paper(request):
    """Enhanced submit the complete paper with access control"""
    attempt_id = request.POST.get('attempt_id')
    attempt = get_object_or_404(ModelPaperAttempt, id=attempt_id)
    
    # ACCESS CONTROL: Verify user owns this attempt
    if attempt.student != request.user:
        return JsonResponse({
            'success': False,
            'error': 'Unauthorized access to paper attempt'
        }, status=403)
    
    # ACCESS CONTROL: Check if user can access the paper
    if not check_object_access(attempt.model_paper, request.user):
        return JsonResponse({
            'success': False,
            'error': 'Paper access denied'
        }, status=403)
    
    # Calculate score based on accessible questions only
    paper_questions = attempt.model_paper.get_questions()
    accessible_questions = apply_user_access_filter(paper_questions, request.user)
    
    accessible_question_count = accessible_questions.count()
    correct_answers = 0
    
    for pq in accessible_questions:
        try:
            response = ModelPaperResponse.objects.get(attempt=attempt, paper_question=pq)
            if response.is_correct:
                correct_answers += 1
        except ModelPaperResponse.DoesNotExist:
            pass
    
    # Use accessible question count for calculations
    total_questions = accessible_question_count if accessible_question_count > 0 else attempt.model_paper.total_questions
    
    attempt.score = correct_answers
    attempt.percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    attempt.status = 'completed'
    attempt.completed_at = timezone.now()
    
    # Calculate time taken
    time_taken = (attempt.completed_at - attempt.started_at).total_seconds()
    attempt.time_taken = int(time_taken)
    
    attempt.save()
    
    return JsonResponse({
        'success': True,
        'score': attempt.score,
        'total': total_questions,
        'percentage': float(attempt.percentage),
        'passed': attempt.passed,
        'accessible_questions': accessible_question_count,
        'user_access_level': get_user_access_info(request.user).get('level', 'student')
    })


@content_access_required
@require_POST
def report_warning(request):
    """Enhanced report tab switch warning for paper with access control"""
    attempt_id = request.POST.get('attempt_id')
    attempt = get_object_or_404(ModelPaperAttempt, id=attempt_id)
    
    # ACCESS CONTROL: Verify user owns this attempt
    if attempt.student != request.user:
        return JsonResponse({
            'success': False,
            'error': 'Unauthorized access to paper attempt'
        }, status=403)
    
    attempt.warning_count += 1
    attempt.save()
    
    if attempt.warning_count >= 3:
        # Auto-submit paper
        attempt.status = 'abandoned'
        attempt.completed_at = timezone.now()
        attempt.save()
        
        return JsonResponse({
            'success': True,
            'auto_submit': True,
            'message': 'Paper auto-submitted due to multiple tab switches.',
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
    
    return JsonResponse({
        'success': True,
        'warning_count': attempt.warning_count,
        'remaining_warnings': 3 - attempt.warning_count,
        'user_access_level': get_user_access_info(request.user).get('level', 'student')
    })


@content_access_required
def student_paper_progress(request):
    """Enhanced student progress tracking for model papers with access control"""
    user = request.user
    attempts = ModelPaperAttempt.objects.filter(student=user).select_related('model_paper').order_by('-started_at')
    
    # FILTER ATTEMPTS BY ACCESS CONTROL
    accessible_attempts = []
    for attempt in attempts:
        if check_object_access(attempt.model_paper, user):
            accessible_attempts.append(attempt)
    
    # Calculate stats based on accessible attempts
    completed_attempts = [a for a in accessible_attempts if a.status == 'completed']
    total_papers = len(accessible_attempts)
    best_score = max([a.percentage for a in completed_attempts]) if completed_attempts else 0
    avg_score = sum([a.percentage for a in completed_attempts]) / len(completed_attempts) if completed_attempts else 0
    avg_time = sum([a.time_taken for a in completed_attempts]) / len(completed_attempts) if completed_attempts else 0
    
    # Calculate monthly progress
    from datetime import datetime, timedelta
    import calendar
    
    # Get last 6 months data
    monthly_data = []
    current_date = timezone.now()
    
    for i in range(6):
        month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 1:
            month_end = month_start.replace(month=12, year=month_start.year-1, day=31)
        else:
            next_month = month_start.replace(month=month_start.month-1)
            month_end = next_month.replace(day=calendar.monthrange(next_month.year, next_month.month)[1])
        
        month_attempts = [a for a in completed_attempts if month_end <= a.completed_at < month_start]
        month_avg = sum([a.percentage for a in month_attempts]) / len(month_attempts) if month_attempts else 0
        
        monthly_data.append({
            'month': month_end.strftime('%b %Y'),
            'attempts': len(month_attempts),
            'avg_score': round(month_avg, 1)
        })
        
        current_date = month_end
    
    monthly_data.reverse()  # Show oldest to newest
    
    # Get paper-wise performance (by paper name) - FILTERED
    paper_performance = {}
    for attempt in completed_attempts:
        paper_name = attempt.model_paper.selected_paper_name or 'General'
        if paper_name not in paper_performance:
            paper_performance[paper_name] = {
                'attempts': 0,
                'total_score': 0,
                'best_score': 0
            }
        
        paper_performance[paper_name]['attempts'] += 1
        paper_performance[paper_name]['total_score'] += attempt.percentage
        paper_performance[paper_name]['best_score'] = max(
            paper_performance[paper_name]['best_score'],
            attempt.percentage
        )
    
    # Calculate averages
    for paper_name in paper_performance:
        data = paper_performance[paper_name]
        data['avg_score'] = round(data['total_score'] / data['attempts'], 1)
    
    # Get recent activity (last 10 attempts) - FILTERED
    recent_attempts = accessible_attempts[:10]
    
    # Calculate improvement trend (comparing first half vs second half of attempts)
    if len(completed_attempts) >= 4:
        half_point = len(completed_attempts) // 2
        recent_half = completed_attempts[:half_point]
        older_half = completed_attempts[half_point:]
        
        recent_avg = sum(a.percentage for a in recent_half) / len(recent_half)
        older_avg = sum(a.percentage for a in older_half) / len(older_half)
        
        improvement = recent_avg - older_avg
    else:
        improvement = 0
    
    context = {
        'attempts': accessible_attempts,
        'completed_attempts': completed_attempts,
        'total_papers': total_papers,
        'best_score': round(best_score, 1),
        'avg_score': round(avg_score, 1),
        'avg_time': round(avg_time / 60, 1) if avg_time else 0,  # Convert to minutes
        'monthly_data': monthly_data,
        'paper_performance': paper_performance,
        'recent_attempts': recent_attempts,
        'improvement': round(improvement, 1),
        'user': user,
        'user_access': get_user_access_info(user),
        'accessible_papers_count': total_papers,
    }
    
    return render(request, 'modelpaper/student_progress.html', context)


# ENHANCED API ENDPOINTS WITH ACCESS CONTROL

@content_access_required
def get_paper_question_counts(request):
    """Enhanced API to get question counts for paper name filters with access control"""
    paper_name = request.GET.get('paper_name')
    
    if not paper_name:
        return JsonResponse({'error': 'Paper name required'}, status=400)
    
    questions = PaperQuestion.objects.filter(paper_name=paper_name)
    
    # APPLY USER ACCESS FILTER
    questions = apply_user_access_filter(questions, request.user)
    
    # Get filter options for accessible questions only
    filter_options = {}
    if questions.exists():
        filter_options = {
            'degrees': list(questions.values_list('degree', flat=True).distinct().order_by('degree')),
            'years': list(questions.values_list('year', flat=True).distinct().order_by('year')),
            'modules': list(questions.values_list('module', flat=True).distinct().order_by('module')),
            'subjects': list(questions.values_list('subject', flat=True).distinct().order_by('subject')),
            'topics': list(questions.values_list('topic', flat=True).distinct().order_by('topic')),
        }
        
        # Remove empty values
        for key in filter_options:
            filter_options[key] = [item for item in filter_options[key] if item]
    
    user_access = get_user_access_info(request.user)
    
    return JsonResponse({
        'total_questions': questions.count(),
        'filters': filter_options,
        'user_access_level': user_access.get('level', 'student'),
        'filter_applied': user_access.get('level') == 'student'
    })


@content_access_required
def get_filtered_question_count(request):
    """Enhanced API to get question count based on filters with access control"""
    paper_name = request.GET.get('paper_name')
    degree = request.GET.get('degree')
    year = request.GET.get('year')
    module = request.GET.get('module')
    subject = request.GET.get('subject')
    topic = request.GET.get('topic')
    
    if not paper_name:
        return JsonResponse({'error': 'Paper name required'}, status=400)
    
    # Build base query
    questions = PaperQuestion.objects.filter(paper_name=paper_name)
    
    # APPLY USER ACCESS FILTER FIRST
    questions = apply_user_access_filter(questions, request.user)
    
    # Apply additional filters
    if degree:
        questions = questions.filter(degree=degree)
    if year:
        questions = questions.filter(year=year)
    if module:
        questions = questions.filter(module=module)
    if subject:
        questions = questions.filter(subject=subject)
    if topic:
        questions = questions.filter(topic=topic)
    
    user_access = get_user_access_info(request.user)
    
    return JsonResponse({
        'count': questions.count(),
        'user_access_level': user_access.get('level', 'student'),
        'filter_applied': user_access.get('level') == 'student'
    })


# ADMIN VIEWS WITH ACCESS CONTROL

@admin_required
def admin_paper_analytics(request):
    """Admin analytics for model papers across all users"""
    # Get all papers
    papers = ModelPaper.objects.all()
    
    # Apply admin filtering if needed (admins see all by default)
    # papers = apply_user_access_filter(papers, request.user)  # Uncomment if admins should be filtered too
    
    paper_stats = []
    for paper in papers:
        attempts = ModelPaperAttempt.objects.filter(model_paper=paper, status='completed')
        
        if attempts.exists():
            avg_score = attempts.aggregate(Avg('percentage'))['percentage__avg']
            best_score = attempts.aggregate(Max('percentage'))['percentage__max']
            total_attempts = attempts.count()
            pass_rate = attempts.filter(percentage__gte=paper.passing_percentage).count() / total_attempts * 100
        else:
            avg_score = best_score = total_attempts = pass_rate = 0
        
        paper_stats.append({
            'paper': paper,
            'total_attempts': total_attempts,
            'avg_score': round(avg_score or 0, 1),
            'best_score': round(best_score or 0, 1),
            'pass_rate': round(pass_rate, 1),
        })
    
    context = {
        'paper_stats': paper_stats,
        'total_papers': papers.count(),
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'modelpaper/admin_analytics.html', context)


@admin_required
def export_paper_questions(request, paper_id):
    """Enhanced export questions for a specific paper as CSV with image support"""
    paper = get_object_or_404(ModelPaper, id=paper_id)
    questions = paper.get_questions()
    
    # Apply access control even for admin exports (optional)
    # questions = apply_user_access_filter(questions, request.user)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{paper.title.replace(" ", "_")}_questions.csv"'
    
    writer = csv.writer(response)
    
    # Write header with metadata
    writer.writerow([f'# Model Paper: {paper.title}'])
    writer.writerow([f'# Paper Name: {paper.selected_paper_name}'])
    writer.writerow([f'# Total Questions: {paper.total_questions}'])
    writer.writerow([f'# Exported by: {request.user.email}'])
    writer.writerow([f'# Exported: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([])  # Empty row
    
    # Write column headers - WITH image columns
    writer.writerow([
        'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'option_e', 
        'correct_answer', 'paper_name', 'degree', 'year', 'module', 'subject', 'topic',
        'difficulty', 'explanation', 'paper_image', 'image', 'marks'
    ])
    
    # Write questions - WITH image fields
    for question in questions:
        writer.writerow([
            question.question_text,
            question.option_a,
            question.option_b,
            question.option_c,
            question.option_d,
            question.option_e,
            question.correct_answer,
            question.paper_name,
            question.degree,
            question.year,
            question.module,
            question.subject,
            question.topic,
            question.difficulty,
            question.explanation,
            question.paper_image or '',  # Paper image field
            question.image or '',  # Explanation image field
            question.marks
        ])
    
    return response


def export_modelpaper_questions(request, paper_name):
    """Export model paper questions by paper name with image support"""
    from urllib.parse import unquote
    
    # Decode the URL-encoded paper name
    decoded_paper_name = unquote(paper_name)
    
    # Get questions for this paper
    questions = PaperQuestion.objects.filter(paper_name=decoded_paper_name).order_by('id')
    
    if not questions.exists():
        return JsonResponse({'error': f'No questions found for paper: {decoded_paper_name}'}, status=404)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    safe_filename = decoded_paper_name.replace(' ', '_').replace('/', '_')
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}_questions.csv"'
    
    writer = csv.writer(response)
    
    # Write header with metadata
    writer.writerow([f'# Model Paper: {decoded_paper_name}'])
    writer.writerow([f'# Total Questions: {questions.count()}'])
    writer.writerow([f'# Exported: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([])  # Empty row
    
# Write column headers with image fields
    writer.writerow([
        'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'option_e', 
        'correct_answer', 'paper_name', 'degree', 'year', 'module', 'subject', 'topic',
        'difficulty', 'explanation', 'paper_image', 'image', 'marks'
    ])
    
    # Write questions with image fields
    for question in questions:
        writer.writerow([
            question.question_text,
            question.option_a,
            question.option_b,
            question.option_c,
            question.option_d,
            question.option_e,
            question.correct_answer,
            question.paper_name,
            question.degree,
            question.year,
            question.module,
            question.subject,
            question.topic,
            question.difficulty,
            question.explanation,
            question.paper_image or '',  # Paper image field
            question.image or '',  # Explanation image field
            question.marks
        ])
    
    return response


@admin_required
def import_paper_questions(request):
    """Enhanced import paper questions from CSV with image support - Admin only"""
    if request.method == 'POST':
        form = PaperQuestionImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Create import history record
            import_record = PaperCSVImportHistory.objects.create(
                file_name=csv_file.name,
                uploaded_by=request.user if request.user.is_authenticated else None,
                file_size=csv_file.size,
                status='PROCESSING'
            )
            
            try:
                # Try different encodings
                file_content = csv_file.read()
                decoded_file = None
                
                encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
                
                for encoding in encodings:
                    try:
                        decoded_file = file_content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if decoded_file is None:
                    raise Exception("Could not decode file. Please save your CSV with UTF-8 encoding.")
                
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)
                
                question_count = 0
                error_count = 0
                total_rows = 0
                errors = []
                paper_names_imported = set()
                
                # GET USER ACCESS INFO FOR VALIDATION
                user_access = get_user_access_info(request.user)
                
                for row_num, row in enumerate(reader, start=1):
                    total_rows += 1
                    try:
                        # Required fields
                        question_text = str(row.get('question_text', '') or row.get('Question', '') or row.get('question', '')).strip()
                        paper_name = str(row.get('paper_name', '') or row.get('Paper_Name', '') or row.get('paper', '')).strip()
                        
                        if not question_text:
                            errors.append(f"Row {row_num}: Missing question text")
                            error_count += 1
                            continue
                            
                        if not paper_name:
                            errors.append(f"Row {row_num}: Missing paper name")
                            error_count += 1
                            continue
                        
                        # Handle options
                        option_a = str(row.get('option_a', '') or row.get('option_A', '') or row.get('Option_A', '') or '').strip()
                        option_b = str(row.get('option_b', '') or row.get('option_B', '') or row.get('Option_B', '') or '').strip()
                        option_c = str(row.get('option_c', '') or row.get('option_C', '') or row.get('Option_C', '') or '').strip()
                        option_d = str(row.get('option_d', '') or row.get('option_D', '') or row.get('Option_D', '') or '').strip()
                        option_e = str(row.get('option_e', '') or row.get('option_E', '') or row.get('Option_E', '') or '').strip()
                        
                        # Validate required options
                        if not all([option_a, option_b, option_c, option_d]):
                            errors.append(f"Row {row_num}: Missing required options (A, B, C, D)")
                            error_count += 1
                            continue
                        
                        # Handle correct answer
                        correct_answer = str(row.get('correct_answer', '') or row.get('correct_option', '') or row.get('Correct_Answer', '') or row.get('answer', '') or '').strip().upper()
                        if correct_answer not in ['A', 'B', 'C', 'D', 'E']:
                            errors.append(f"Row {row_num}: Invalid correct answer '{correct_answer}'. Must be A, B, C, D, or E")
                            error_count += 1
                            continue
                        
                        # Handle optional fields with access control validation
                        degree = str(row.get('degree', '')).strip().upper()
                        if degree and degree not in ['MBBS', 'BDS']:
                            degree = ''
                        
                        year = str(row.get('year', '')).strip()
                        if year and year not in ['1st', '2nd', '3rd', '4th', '5th']:
                            year = ''
                        
                        # ACCESS CONTROL: For non-admin users importing, apply their restrictions
                        if user_access['level'] == 'student':
                            filter_params = user_access.get('filter_params', {})
                            if filter_params.get('degree') and degree and degree != filter_params['degree']:
                                errors.append(f"Row {row_num}: You can only import {filter_params['degree']} questions")
                                error_count += 1
                                continue
                            if filter_params.get('year') and year and year != filter_params['year']:
                                errors.append(f"Row {row_num}: You can only import Year {filter_params['year']} questions")
                                error_count += 1
                                continue
                            
                            # Set user's degree/year if not specified
                            if not degree:
                                degree = filter_params.get('degree', '')
                            if not year:
                                year = filter_params.get('year', '')
                        
                        # Handle difficulty
                        difficulty_raw = str(row.get('difficulty', 'Medium')).strip()
                        if difficulty_raw.lower() == 'easy':
                            difficulty = 'Easy'
                        elif difficulty_raw.lower() == 'medium':
                            difficulty = 'Medium'
                        elif difficulty_raw.lower() == 'hard':
                            difficulty = 'Hard'
                        else:
                            difficulty = 'Medium'
                        
                        # Handle image fields (paper_image and image)
                        paper_image_filename = str(row.get('paper_image', '')).strip()
                        explanation_image_filename = str(row.get('image', '')).strip()
                        
                        # Enhanced duplicate detection within same paper name
                        is_duplicate, duplicate_reason = enhanced_duplicate_detection(
                            paper_name, question_text, option_a, option_b, option_c, option_d, option_e
                        )
                        
                        if is_duplicate:
                            errors.append(f"Row {row_num}: {duplicate_reason} - '{question_text[:50]}...'")
                            error_count += 1
                            continue
                        
                        # Create paper question - WITH image fields
                        PaperQuestion.objects.create(
                            question_text=question_text,
                            option_a=option_a,
                            option_b=option_b,
                            option_c=option_c,
                            option_d=option_d,
                            option_e=option_e or None,
                            correct_answer=correct_answer,
                            paper_name=paper_name,
                            degree=degree,
                            year=year,
                            module=str(row.get('module', '')).strip(),
                            subject=str(row.get('subject', '')).strip(),
                            topic=str(row.get('topic', '')).strip(),
                            difficulty=difficulty,
                            explanation=str(row.get('explanation', '')).strip() or None,
                            paper_image=paper_image_filename or None,  # Paper image field
                            image=explanation_image_filename or None,  # Explanation image field
                            marks=int(row.get('marks', 1)) if str(row.get('marks', '')).isdigit() else 1,
                            created_by=request.user if request.user.is_authenticated else None
                        )
                        question_count += 1
                        paper_names_imported.add(paper_name)
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        error_count += 1
                
                # Update import record
                import_record.total_rows = total_rows
                import_record.successful_imports = question_count
                import_record.failed_imports = error_count
                import_record.status = 'SUCCESS' if error_count == 0 else ('FAILED' if question_count == 0 else 'SUCCESS')
                import_record.error_details = '\n'.join(errors) if errors else None
                import_record.paper_names_imported = json.dumps(list(paper_names_imported))
                import_record.save()
                
                return JsonResponse({
                    'success': True,
                    'imported': question_count,
                    'failed': error_count,
                    'total': total_rows,
                    'paper_names': list(paper_names_imported),
                    'errors': errors[:10] if errors else [],
                    'user_access_level': user_access.get('level', 'admin')
                })
                
            except Exception as e:
                # Update import record with failure
                import_record.status = 'FAILED'
                import_record.error_details = str(e)
                import_record.save()
                
                return JsonResponse({
                    'error': str(e),
                    'user_access_level': get_user_access_info(request.user).get('level', 'admin')
                }, status=400)
        else:
            return JsonResponse({'error': 'Invalid form submission'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def enhanced_duplicate_detection(paper_name, question_text, option_a, option_b, option_c, option_d, option_e=None):
    """Enhanced duplicate detection for paper questions within the same paper name"""
    # Clean inputs
    question_text = question_text.strip().lower()
    option_a = option_a.strip().lower() if option_a else ""
    option_b = option_b.strip().lower() if option_b else ""
    option_c = option_c.strip().lower() if option_c else ""
    option_d = option_d.strip().lower() if option_d else ""
    option_e = option_e.strip().lower() if option_e else ""
    
    # Check for exact question text match within same paper name
    exact_question_matches = PaperQuestion.objects.filter(
        paper_name=paper_name,
        question_text__iexact=question_text
    )
    
    if exact_question_matches.exists():
        return True, "Exact question text match found in this paper"
    
    # Check question text + first two options within same paper name
    if option_a and option_b:
        mcq_matches = PaperQuestion.objects.filter(
            paper_name=paper_name,
            question_text__icontains=question_text[:30],  # First 30 chars
            option_a__iexact=option_a,
            option_b__iexact=option_b
        )
        
        if mcq_matches.exists():
            return True, "Similar MCQ found in this paper with matching options"
    
    return False, None


def modelpaper_list(request):
    """Enhanced list all model papers with access control and filtering"""
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    degree_filter = request.GET.get('degree', '')
    paper_filter = request.GET.get('paper_name', '')
    
    papers = ModelPaper.objects.all()
    
    # APPLY USER ACCESS FILTER
    papers = apply_user_access_filter(papers, request.user)
    
    if query:
        papers = papers.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(selected_paper_name__icontains=query)
        )
    
    if status_filter:
        papers = papers.filter(status=status_filter)
    
    if degree_filter:
        papers = papers.filter(filter_degree=degree_filter)
        
    if paper_filter:
        papers = papers.filter(selected_paper_name__icontains=paper_filter)
    
    # Update status based on datetime
    for paper in papers:
        now = timezone.now()
        if paper.status == 'scheduled' and now >= paper.start_datetime:
            paper.status = 'live'
            paper.save()
        elif paper.status == 'live' and now > paper.end_datetime:
            paper.status = 'completed'
            paper.save()
    
    paginator = Paginator(papers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique paper names for filter dropdown - FILTERED BY ACCESS CONTROL
    paper_questions = PaperQuestion.objects.all()
    paper_questions = apply_user_access_filter(paper_questions, request.user)
    paper_names = paper_questions.values_list('paper_name', flat=True).distinct().order_by('paper_name')
    
    # Get paper statistics for the "Available Paper Questions" section - ACCESS CONTROLLED
    paper_stats = []
    for paper_name in paper_names:
        accessible_questions = paper_questions.filter(paper_name=paper_name)
        count = accessible_questions.count()
        if count > 0:  # Only show papers with accessible questions
            paper_stats.append({
                'name': paper_name,
                'question_count': count
            })
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'degree_filter': degree_filter,
        'paper_filter': paper_filter,
        'paper_names': paper_names,
        'paper_stats': paper_stats,
        'user_access': get_user_access_info(request.user),
        'can_create_papers': request.user.is_admin or request.user.is_superuser,
    }
    
    return render(request, 'modelpaper/modelpaper_list.html', context)


from urllib.parse import unquote

@content_access_required
def view_paper_questions(request, paper_name):
    """Enhanced view questions for a specific paper name with access control and image support"""
    # Decode the URL-encoded paper name
    decoded_paper_name = unquote(paper_name)
    print(f"Original paper_name: '{paper_name}'")  # Debug line
    print(f"Decoded paper_name: '{decoded_paper_name}'")  # Debug line
    
    questions = PaperQuestion.objects.filter(paper_name=decoded_paper_name)
    
    # APPLY USER ACCESS FILTER
    questions = apply_user_access_filter(questions, request.user)
    
    print(f"Found {questions.count()} accessible questions")  # Debug line
    
    # If still no results, try exact match or iexact match
    if questions.count() == 0:
        # Try case-insensitive match
        all_questions = PaperQuestion.objects.filter(paper_name__iexact=decoded_paper_name)
        questions = apply_user_access_filter(all_questions, request.user)
        print(f"Case-insensitive search found {questions.count()} accessible questions")
        
        # If still no results, show available paper names for debugging (access controlled)
        if questions.count() == 0:
            accessible_papers = PaperQuestion.objects.all()
            accessible_papers = apply_user_access_filter(accessible_papers, request.user)
            all_papers = accessible_papers.values_list('paper_name', flat=True).distinct()
            print("Available paper names in database (user accessible):")
            for paper in all_papers:
                print(f"  - '{paper}'")
    
    # Pagination
    paginator = Paginator(questions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'paper_name': decoded_paper_name,  # Use decoded name for display
        'total_questions': questions.count(),
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'modelpaper/view_paper_questions.html', context)


@content_access_required
def student_model_papers(request):
    """Enhanced list available model papers for students with access control"""
    user = request.user
    now = timezone.now()
    
    # Update paper statuses first
    all_papers_for_update = ModelPaper.objects.all()
    for paper in all_papers_for_update:
        if paper.status == 'scheduled' and now >= paper.start_datetime:
            paper.status = 'live'
            paper.save()
        elif paper.status == 'live' and now > paper.end_datetime:
            paper.status = 'completed'
            paper.save()
    
    # Get active papers with access control
    papers = ModelPaper.objects.filter(status='live')
    papers = apply_user_access_filter(papers, request.user)
    
    # Get user's attempts
    user_attempts = ModelPaperAttempt.objects.filter(student=user).values('model_paper_id', 'status').order_by('-started_at')
    
    # Filter attempts by accessible papers
    accessible_paper_ids = set(papers.values_list('id', flat=True))
    accessible_attempts = [attempt for attempt in user_attempts if attempt['model_paper_id'] in accessible_paper_ids]
    
    # Create a dict of paper attempts
    attempt_status = {}
    attempt_count = {}
    for attempt in accessible_attempts:
        paper_id = attempt['model_paper_id']
        if paper_id not in attempt_count:
            attempt_count[paper_id] = 0
        if attempt['status'] == 'completed':
            attempt_count[paper_id] += 1
            if paper_id not in attempt_status:
                attempt_status[paper_id] = 'completed'
    
    # Add attempt info to papers
    for paper in papers:
        paper.user_attempts = attempt_count.get(paper.id, 0)
        paper.can_attempt = paper.user_attempts < paper.max_attempts
        paper.attempt_status = attempt_status.get(paper.id, 'not_started')
    
    # Get upcoming papers - ALSO FILTERED
    upcoming_papers = ModelPaper.objects.filter(
        start_datetime__gt=now
    ).order_by('start_datetime')
    upcoming_papers = apply_user_access_filter(upcoming_papers, request.user)[:5]
    
    context = {
        'active_papers': papers,
        'upcoming_papers': upcoming_papers,
        'user': user,
        'user_access': get_user_access_info(user),
    }
    
    return render(request, 'modelpaper/student_model_papers.html', context)


@admin_required
def create_paper(request):
    """Enhanced create/edit model paper - Admin only with access control"""
    paper_id = request.GET.get('id')
    
    if paper_id:
        paper = get_object_or_404(ModelPaper, id=paper_id)
        form = ModelPaperForm(instance=paper)
        is_edit = True
    else:
        form = ModelPaperForm()
        paper = None
        is_edit = False
    
    if request.method == 'POST':
        if paper:
            form = ModelPaperForm(request.POST, instance=paper)
        else:
            form = ModelPaperForm(request.POST)
        
        if form.is_valid():
            paper = form.save(commit=False)
            if not paper.created_by_id:
                paper.created_by = request.user if request.user.is_authenticated else None
            paper.save()
            
            # Update total questions based on filters with access control
            paper.update_total_questions()
            
            # Validate that the paper has accessible questions
            accessible_questions = paper.get_questions()
            accessible_questions = apply_user_access_filter(accessible_questions, request.user)
            actual_count = accessible_questions.count()
            
            if actual_count != paper.total_questions:
                messages.warning(
                    request, 
                    f"Paper {'updated' if is_edit else 'created'} successfully! "
                    f"Questions available to users: {actual_count} (Total: {paper.total_questions})"
                )
            else:
                messages.success(request, f"Paper {'updated' if is_edit else 'created'} successfully! Total questions: {paper.total_questions}")
            
            return redirect('modelpaper_list')
    
    # Get available paper names count for context - ACCESS CONTROLLED
    accessible_paper_questions = PaperQuestion.objects.all()
    accessible_paper_questions = apply_user_access_filter(accessible_paper_questions, request.user)
    available_papers_count = accessible_paper_questions.values('paper_name').distinct().count()
    
    context = {
        'form': form,
        'paper': paper,
        'is_edit': is_edit,
        'available_papers_count': available_papers_count,
        'user_access': get_user_access_info(request.user),
    }    
    return render(request, 'modelpaper/create_paper.html', context)


@admin_required
@require_POST
def delete_paper(request, paper_id):
    """Enhanced delete a model paper - Admin only"""
    paper = get_object_or_404(ModelPaper, id=paper_id)
    paper_title = paper.title
    paper.delete()
    messages.success(request, f"Paper '{paper_title}' deleted successfully!")
    return JsonResponse({'success': True, 'message': f"Paper '{paper_title}' deleted successfully!"})


@content_access_required
def preview_paper(request, paper_id):
    """Enhanced preview paper before publishing with access control and image support"""
    paper = get_object_or_404(ModelPaper, id=paper_id)
    
    # CHECK OBJECT ACCESS
    if not check_object_access(paper, request.user):
        messages.error(request, "You don't have permission to preview this paper.")
        return redirect('modelpaper_list')
    
    # Get questions with access control
    paper_questions = paper.get_questions()
    paper_questions = apply_user_access_filter(paper_questions, request.user)
    
    # Show first 10 questions for preview
    preview_questions = paper_questions[:10]
    
    context = {
        'paper': paper,
        'paper_questions': preview_questions,
        'question_count': paper_questions.count(),
        'showing_count': min(10, paper_questions.count()),
        'total_available': paper.total_questions,
        'user_access': get_user_access_info(request.user),
        'can_edit': request.user.is_admin or request.user.is_superuser,
    }
    
    return render(request, 'modelpaper/preview_paper.html', context)


# ADDITIONAL UTILITY VIEWS WITH IMAGE SUPPORT

@content_access_required
def get_paper_hierarchy_data(request):
    """AJAX endpoint for dynamic hierarchy loading with access control"""
    field = request.GET.get('field')
    paper_name = request.GET.get('paper_name', '')
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    
    # Build base query with access control
    query = PaperQuestion.objects.all()
    query = apply_user_access_filter(query, request.user)
    
    if paper_name:
        query = query.filter(paper_name=paper_name)
    if degree:
        query = query.filter(degree=degree)
    if year:
        query = query.filter(year=year)
    if module:
        query = query.filter(module=module)
    if subject:
        query = query.filter(subject=subject)
    
    if field == 'papers':
        data = list(query.values_list('paper_name', flat=True).distinct().order_by('paper_name'))
    elif field == 'degrees':
        data = list(query.values_list('degree', flat=True).distinct().order_by('degree'))
    elif field == 'years':
        data = list(query.values_list('year', flat=True).distinct().order_by('year'))
    elif field == 'modules':
        data = list(query.values_list('module', flat=True).distinct().order_by('module'))
    elif field == 'subjects':
        data = list(query.values_list('subject', flat=True).distinct().order_by('subject'))
    elif field == 'topics':
        data = list(query.values_list('topic', flat=True).distinct().order_by('topic'))
    else:
        data = []
    
    # Remove empty values
    data = [item for item in data if item and item.strip()]
    
    user_access = get_user_access_info(request.user)
    
    return JsonResponse({
        'data': data,
        'user_access_level': user_access.get('level', 'student'),
        'filter_applied': user_access.get('level') == 'student',
        'count': len(data)
    })


@content_access_required
def validate_paper_config(request):
    """AJAX endpoint to validate paper configuration"""
    paper_name = request.GET.get('paper_name', '')
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    total_questions = int(request.GET.get('total_questions', 10))
    
    # Build query with access control
    questions = PaperQuestion.objects.all()
    questions = apply_user_access_filter(questions, request.user)
    
    if paper_name:
        questions = questions.filter(paper_name=paper_name)
    if degree:
        questions = questions.filter(degree=degree)
    if year:
        questions = questions.filter(year=year)
    if module:
        questions = questions.filter(module=module)
    if subject:
        questions = questions.filter(subject=subject)
    if topic:
        questions = questions.filter(topic=topic)
    
    available_count = questions.count()
    is_valid = available_count >= total_questions
    
    # Get recommendations if not enough questions
    recommendations = []
    if not is_valid:
        # Suggest reducing question count
        if available_count > 0:
            recommendations.append(f"Reduce to {available_count} questions")
        
        # Check if removing filters would help
        if degree or year or module or subject or topic:
            base_query = PaperQuestion.objects.filter(paper_name=paper_name) if paper_name else PaperQuestion.objects.all()
            base_query = apply_user_access_filter(base_query, request.user)
            
            if base_query.count() >= total_questions:
                recommendations.append(f"Remove some filters (all questions: {base_query.count()})")
        
        # Check other paper names
        if paper_name:
            other_papers = PaperQuestion.objects.exclude(paper_name=paper_name)
            other_papers = apply_user_access_filter(other_papers, request.user)
            other_paper_names = other_papers.values('paper_name').distinct()[:3]
            
            for other_paper in other_paper_names:
                other_count = other_papers.filter(paper_name=other_paper['paper_name']).count()
                if other_count >= total_questions:
                    recommendations.append(f"Try paper: {other_paper['paper_name']} ({other_count} questions)")
    
    user_access = get_user_access_info(request.user)
    
    return JsonResponse({
        'is_valid': is_valid,
        'available_count': available_count,
        'required_count': total_questions,
        'recommendations': recommendations,
        'user_access_level': user_access.get('level', 'student'),
        'filter_applied': user_access.get('level') == 'student'
    })


@content_access_required
def get_paper_statistics(request):
    """AJAX endpoint for paper statistics with access control"""
    paper_name = request.GET.get('paper_name', '')
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    
    # Build base query with access control
    questions = PaperQuestion.objects.all()
    questions = apply_user_access_filter(questions, request.user)
    
    if paper_name:
        questions = questions.filter(paper_name=paper_name)
    if degree:
        questions = questions.filter(degree=degree)
    if year:
        questions = questions.filter(year=year)
    if module:
        questions = questions.filter(module=module)
    if subject:
        questions = questions.filter(subject=subject)
    if topic:
        questions = questions.filter(topic=topic)
    
    # Get difficulty breakdown
    easy_count = questions.filter(difficulty='Easy').count()
    medium_count = questions.filter(difficulty='Medium').count()
    hard_count = questions.filter(difficulty='Hard').count()
    total_count = easy_count + medium_count + hard_count
    
    # Get image statistics
    with_paper_images = questions.exclude(Q(paper_image__isnull=True) | Q(paper_image__exact='')).count()
    with_explanation_images = questions.exclude(Q(image__isnull=True) | Q(image__exact='')).count()
    
    # Get user's progress for this paper (if specific paper)
    user_progress = None
    if paper_name and request.user.is_authenticated:
        try:
            user_attempts = ModelPaperAttempt.objects.filter(
                student=request.user,
                model_paper__selected_paper_name=paper_name,
                status='completed'
            )
            
            if user_attempts.exists():
                best_attempt = user_attempts.order_by('-percentage').first()
                user_progress = {
                    'best_score': round(best_attempt.percentage, 1),
                    'total_attempts': user_attempts.count(),
                    'last_attempted': best_attempt.completed_at.strftime('%Y-%m-%d') if best_attempt.completed_at else None
                }
        except:
            user_progress = {
                'best_score': 0.0,
                'total_attempts': 0,
                'last_attempted': None
            }
    
    user_access = get_user_access_info(request.user)
    
    return JsonResponse({
        'total_questions': total_count,
        'difficulty_breakdown': {
            'easy': easy_count,
            'medium': medium_count,
            'hard': hard_count
        },
        'image_statistics': {
            'with_paper_images': with_paper_images,
            'with_explanation_images': with_explanation_images,
            'total_with_images': questions.filter(
                Q(paper_image__isnull=False, paper_image__gt='') | 
                Q(image__isnull=False, image__gt='')
            ).count()
        },
        'user_progress': user_progress,
        'user_access_level': user_access.get('level', 'student'),
        'filter_applied': user_access.get('level') == 'student'
    })


# ADDITIONAL UTILITY VIEWS

@content_access_required
def paper_question_detail(request, question_id):
    """View detailed information about a specific paper question with image support"""
    question = get_object_or_404(PaperQuestion, id=question_id)
    
    # ACCESS CONTROL: Check if user can access this question
    if not check_object_access(question, request.user):
        messages.error(request, "You don't have access to this question.")
        return redirect('modelpaper_list')
    
    # Get related questions from same paper
    related_questions = PaperQuestion.objects.filter(
        paper_name=question.paper_name,
        subject=question.subject
    ).exclude(id=question.id)
    
    # Apply access control to related questions
    related_questions = apply_user_access_filter(related_questions, request.user)[:5]
    
    context = {
        'question': question,
        'related_questions': related_questions,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'modelpaper/paper_question_detail.html', context)


@content_access_required
def paper_search(request):
    """Search across papers and questions with access control"""
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', 'all')  # 'papers', 'questions', 'all'
    
    results = {}
    
    if query and len(query) >= 3:  # Minimum 3 characters
        if search_type in ['papers', 'all']:
            # Search papers
            papers = ModelPaper.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(selected_paper_name__icontains=query)
            )
            papers = apply_user_access_filter(papers, request.user)
            results['papers'] = papers[:10]
        
        if search_type in ['questions', 'all']:
            # Search questions
            questions = PaperQuestion.objects.filter(
                Q(question_text__icontains=query) |
                Q(paper_name__icontains=query) |
                Q(subject__icontains=query) |
                Q(topic__icontains=query)
            )
            questions = apply_user_access_filter(questions, request.user)
            results['questions'] = questions[:20]
    
    context = {
        'query': query,
        'search_type': search_type,
        'results': results,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'modelpaper/paper_search.html', context)


@content_access_required
def student_paper_statistics(request):
    """General paper statistics for students"""
    user = request.user
    
    # Get user's accessible papers
    all_papers = ModelPaper.objects.all()
    accessible_papers = apply_user_access_filter(all_papers, user)
    
    # Get user's attempts
    attempts = ModelPaperAttempt.objects.filter(student=user, status='completed')
    
    # Filter attempts by accessible papers
    accessible_attempts = []
    for attempt in attempts:
        if check_object_access(attempt.model_paper, user):
            accessible_attempts.append(attempt)
    
    # Calculate statistics
    total_accessible_papers = accessible_papers.count()
    total_attempts = len(accessible_attempts)
    unique_papers_attempted = len(set(attempt.model_paper.id for attempt in accessible_attempts))
    
    avg_score = sum(attempt.percentage for attempt in accessible_attempts) / len(accessible_attempts) if accessible_attempts else 0
    best_score = max((attempt.percentage for attempt in accessible_attempts), default=0)
    
    # Recent performance (last 5 attempts)
    recent_attempts = sorted(accessible_attempts, key=lambda x: x.completed_at, reverse=True)[:5]
    recent_avg = sum(attempt.percentage for attempt in recent_attempts) / len(recent_attempts) if recent_attempts else 0
    
    # Performance trend (comparing first half vs second half of attempts)
    if len(recent_attempts) >= 2:
        latest_score = recent_attempts[0].percentage
        previous_avg = sum(attempt.percentage for attempt in recent_attempts[1:]) / len(recent_attempts[1:])
        trend = "improving" if latest_score > previous_avg else "declining" if latest_score < previous_avg else "stable"
    else:
        trend = "insufficient_data"
    
    context = {
        'total_accessible_papers': total_accessible_papers,
        'total_attempts': total_attempts,
        'unique_papers_attempted': unique_papers_attempted,
        'avg_score': round(avg_score, 1),
        'best_score': round(best_score, 1),
        'recent_avg': round(recent_avg, 1),
        'trend': trend,
        'recent_attempts': recent_attempts,
        'user_access': get_user_access_info(user),
    }
    
    return render(request, 'modelpaper/student_paper_statistics.html', context)


# IMPORT HISTORY AND MANAGEMENT

@admin_required
def import_history(request):
    """View CSV import history with filtering"""
    imports = PaperCSVImportHistory.objects.all().order_by('-uploaded_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        imports = imports.filter(status=status_filter)
    
    paginator = Paginator(imports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'modelpaper/import_history.html', context)


@admin_required
def import_detail(request, import_id):
    """View detailed information about a specific import"""
    import_record = get_object_or_404(PaperCSVImportHistory, id=import_id)
    
    # Parse paper names if available
    paper_names = []
    if import_record.paper_names_imported:
        try:
            paper_names = json.loads(import_record.paper_names_imported)
        except:
            pass
    
    context = {
        'import_record': import_record,
        'paper_names': paper_names,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'modelpaper/import_detail.html', context)


# PERFORMANCE OPTIMIZATION VIEWS

@content_access_required
def get_cached_paper_stats(request):
    """Cached version of paper statistics for better performance"""
    from django.core.cache import cache
    
    user = request.user
    user_access = get_user_access_info(user)
    
    # Create cache key based on user access level
    cache_key = f"paper_stats_{user_access.get('level', 'guest')}_{user_access.get('filter_params', {}).get('degree', 'all')}_{user_access.get('filter_params', {}).get('year', 'all')}"
    
    # Try to get from cache first
    cached_stats = cache.get(cache_key)
    if cached_stats:
        return JsonResponse(cached_stats)
    
    # Calculate fresh stats with access control
    papers = ModelPaper.objects.all()
    papers = apply_user_access_filter(papers, user)
    
    questions = PaperQuestion.objects.all()
    questions = apply_user_access_filter(questions, user)
    
    stats = {
        'total_papers': papers.count(),
        'total_questions': questions.count(),
        'paper_names': questions.values('paper_name').distinct().count(),
        'subjects': questions.values('subject').distinct().count(),
        'difficulty_breakdown': {
            'easy': questions.filter(difficulty='Easy').count(),
            'medium': questions.filter(difficulty='Medium').count(),
            'hard': questions.filter(difficulty='Hard').count(),
        },
        'image_statistics': {
            'with_paper_images': questions.exclude(Q(paper_image__isnull=True) | Q(paper_image__exact='')).count(),
            'with_explanation_images': questions.exclude(Q(image__isnull=True) | Q(image__exact='')).count(),
        },
        'user_access_level': user_access.get('level', 'student'),
        'filter_applied': user_access.get('level') == 'student'
    }
    
    # Cache for 15 minutes
    cache.set(cache_key, stats, 900)
    
    return JsonResponse(stats)


# ERROR HANDLING

def handle_paper_error(request, error_type, error_message):
    """Centralized error handling for model papers"""
    error_context = {
        'error_type': error_type,
        'error_message': error_message,
        'user': request.user,
        'user_access': get_user_access_info(request.user),
        'timestamp': timezone.now(),
    }
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'success': False,
            'error': error_message,
            'error_type': error_type,
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        }, status=400)
    
    return render(request, 'modelpaper/paper_error.html', error_context)


# BULK OPERATIONS

@admin_required
def bulk_paper_actions(request):
    """Admin view for bulk paper management"""
    if request.method == 'POST':
        action = request.POST.get('action')
        paper_ids = request.POST.getlist('paper_ids')
        
        if action == 'activate':
            ModelPaper.objects.filter(id__in=paper_ids).update(status='live')
            messages.success(request, f"Activated {len(paper_ids)} papers.")
        elif action == 'deactivate':
            ModelPaper.objects.filter(id__in=paper_ids).update(status='draft')
            messages.success(request, f"Deactivated {len(paper_ids)} papers.")
        elif action == 'delete':
            ModelPaper.objects.filter(id__in=paper_ids).delete()
            messages.success(request, f"Deleted {len(paper_ids)} papers.")
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@admin_required
def paper_performance_report(request):
    """Generate detailed performance report for a specific paper"""
    paper_id = request.GET.get('paper_id')
    if not paper_id:
        messages.error(request, "Paper ID is required for performance report.")
        return redirect('admin_paper_analytics')
    
    paper = get_object_or_404(ModelPaper, id=paper_id)
    attempts = ModelPaperAttempt.objects.filter(model_paper=paper, status='completed').select_related('student')
    
    # Calculate detailed statistics
    total_attempts = attempts.count()
    if total_attempts == 0:
        messages.info(request, f"No completed attempts found for paper: {paper.title}")
        return redirect('admin_paper_analytics')
    
    # Score distribution
    score_ranges = {
        '90-100': attempts.filter(percentage__gte=90).count(),
        '80-89': attempts.filter(percentage__gte=80, percentage__lt=90).count(),
        '70-79': attempts.filter(percentage__gte=70, percentage__lt=80).count(),
        '60-69': attempts.filter(percentage__gte=60, percentage__lt=70).count(),
        '50-59': attempts.filter(percentage__gte=50, percentage__lt=60).count(),
        'Below 50': attempts.filter(percentage__lt=50).count(),
    }
    
    # Top performers
    top_performers = attempts.order_by('-percentage')[:10]
    
    # Question-wise analysis
    question_stats = {}
    paper_questions = paper.get_questions()
    
    for pq in paper_questions:
        responses = ModelPaperResponse.objects.filter(
            attempt__in=attempts,
            paper_question=pq
        )
        total_responses = responses.count()
        correct_responses = responses.filter(is_correct=True).count()
        
        question_stats[pq.id] = {
            'question': pq,
            'total_responses': total_responses,
            'correct_responses': correct_responses,
            'accuracy': (correct_responses / total_responses * 100) if total_responses > 0 else 0,
            'difficulty_actual': 'Easy' if correct_responses / total_responses > 0.8 else 'Hard' if correct_responses / total_responses < 0.5 else 'Medium' if total_responses > 0 else 'Unknown'
        }
    
    # Time analysis
    avg_time = attempts.aggregate(Avg('time_taken'))['time_taken__avg'] or 0
    time_distribution = {
        'Under 30 min': attempts.filter(time_taken__lt=1800).count(),
        '30-45 min': attempts.filter(time_taken__gte=1800, time_taken__lt=2700).count(),
        '45-60 min': attempts.filter(time_taken__gte=2700, time_taken__lte=3600).count(),
        'Over 60 min': attempts.filter(time_taken__gt=3600).count(),
    }
    
    context = {
        'paper': paper,
        'total_attempts': total_attempts,
        'score_ranges': score_ranges,
        'top_performers': top_performers,
        'question_stats': question_stats,
        'avg_time_minutes': round(avg_time / 60, 1),
        'time_distribution': time_distribution,
        'pass_rate': attempts.filter(percentage__gte=paper.passing_percentage).count() / total_attempts * 100,
        'avg_score': attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'modelpaper/paper_performance_report.html', context)


@admin_required
def export_paper_results(request, paper_id):
    """Export paper results to CSV"""
    paper = get_object_or_404(ModelPaper, id=paper_id)
    attempts = ModelPaperAttempt.objects.filter(model_paper=paper, status='completed').select_related('student')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{paper.title}_results.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Student Name', 'Email', 'Degree', 'Year', 'Score', 'Total Questions', 
        'Percentage', 'Passed', 'Time Taken (minutes)', 'Started At', 'Completed At'
    ])
    
    # Write data
    for attempt in attempts:
        writer.writerow([
            f"{attempt.student.first_name} {attempt.student.last_name}",
            attempt.student.email,
            attempt.student.degree or 'N/A',
            attempt.student.year or 'N/A',
            attempt.score,
            paper.total_questions,
            round(attempt.percentage, 2),
            'Yes' if attempt.passed else 'No',
            round(attempt.time_taken / 60, 2) if attempt.time_taken else 0,
            attempt.started_at.strftime('%Y-%m-%d %H:%M:%S'),
            attempt.completed_at.strftime('%Y-%m-%d %H:%M:%S') if attempt.completed_at else 'N/A'
        ])
    
    return response


# DEBUG AND TESTING VIEWS (Remove in production)

@admin_required
def debug_paper_access(request, paper_id):
    """Debug view to test paper access control functionality (remove in production)"""
    if not request.user.is_admin and not request.user.is_superuser:
        return JsonResponse({'error': 'Admin only'}, status=403)
    
    paper = get_object_or_404(ModelPaper, id=paper_id)
    user_id = request.GET.get('user_id')
    
    if user_id:
        check_user = get_object_or_404(User, id=user_id)
    else:
        check_user = request.user
    
    # Test access control on different models
    all_papers = ModelPaper.objects.all()
    filtered_papers = apply_user_access_filter(all_papers, check_user)
    
    # Test paper questions
    all_questions = PaperQuestion.objects.all()
    filtered_questions = apply_user_access_filter(all_questions, check_user)
    
    # Test paper attempts
    all_attempts = ModelPaperAttempt.objects.all()
    user_attempts = all_attempts.filter(student=check_user)
    
    access_info = get_user_access_info(check_user)
    can_access_paper = check_object_access(paper, check_user)
    
    debug_data = {
        'user_info': {
            'id': check_user.id,
            'email': check_user.email,
            'degree': check_user.degree,
            'year': check_user.year,
            'approval_status': check_user.approval_status,
            'is_admin': check_user.is_admin,
        },
        'access_info': access_info,
        'paper_info': {
            'id': paper.id,
            'title': paper.title,
            'filter_degree': paper.filter_degree,
            'filter_year': paper.filter_year,
            'status': paper.status,
        },
        'access_results': {
            'can_access_paper': can_access_paper,
            'total_papers': all_papers.count(),
            'accessible_papers': filtered_papers.count(),
            'total_questions': all_questions.count(),
            'accessible_questions': filtered_questions.count(),
            'user_attempts': user_attempts.count(),
        },
        'sample_accessible_questions': [
            {
                'id': q.id,
                'paper_name': q.paper_name,
                'degree': q.degree,
                'year': q.year,
                'subject': q.subject,
                'has_paper_image': q.has_paper_image,
                'has_explanation_image': q.has_explanation_image,
            } for q in filtered_questions[:5]
        ],
    }
    
    return JsonResponse(debug_data, indent=2)