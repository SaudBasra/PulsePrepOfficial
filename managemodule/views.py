# managemodule/views.py - Enhanced with Comprehensive Access Control
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Max, Min
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from questionbank.models import Question
from .models import (
    PracticeSession, 
    PracticeResponse, 
    StudentProgress, 
    PracticeSessionNote
)
import random
import os
import csv
from datetime import datetime, timedelta

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


@content_access_required
def practice_session(request, session_id):
    """Enhanced practice session interface with access control and proper MCQ display"""
    session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
    
    # ACCESS CONTROL: Verify session belongs to user and user has access
    if session.student != request.user:
        messages.error(request, "You don't have access to this practice session.")
        return redirect('student_practice_modules')
    
    if session.status != 'in_progress':
        return redirect('practice_session_result', session_id=session.id)
    
    # Get questions for this session with access control
    questions_query = Question.objects.filter(
        question_type='MCQ',
        degree=session.degree,
        year=session.year,
        block=session.block,
        module=session.module,
        subject=session.subject,
        topic=session.topic
    )
    
    # APPLY USER ACCESS FILTER
    questions_query = apply_user_access_filter(questions_query, request.user)
    
    if session.difficulty_filter:
        questions_query = questions_query.filter(difficulty=session.difficulty_filter)
    
    # Get random questions for the session
    questions = list(questions_query.order_by('?')[:session.total_questions])
    
    if session.randomize_questions:
        random.shuffle(questions)
    
    # FILTER QUESTIONS BY ACCESS CONTROL AGAIN (double-check)
    accessible_questions = []
    for question in questions:
        if check_object_access(question, request.user):
            accessible_questions.append(question)
    
    # Process questions with proper data structure and access control
    processed_questions = []
    for idx, question in enumerate(accessible_questions):
        # Create options dictionary with proper handling
        options = {}
        if question.option_a and question.option_a.strip():
            options['A'] = question.option_a.strip()
        if question.option_b and question.option_b.strip():
            options['B'] = question.option_b.strip()
        if question.option_c and question.option_c.strip():
            options['C'] = question.option_c.strip()
        if question.option_d and question.option_d.strip():
            options['D'] = question.option_d.strip()
        if question.option_e and question.option_e.strip():
            options['E'] = question.option_e.strip()
        
        question_data = {
            'id': question.id,
            'order': idx + 1,
            'text': question.question_text if question.question_text else '',
            'options': options,
            'correct_answer': question.correct_answer if question.correct_answer else '',
            'explanation': question.explanation if question.explanation else '',
            'difficulty': question.difficulty if question.difficulty else 'Medium',
            # UPDATED: Support both question_image and explanation image
            'has_question_image': bool(question.question_image),
            'question_image_url': None,
            'question_image_filename': question.question_image if question.question_image else None,
            'has_explanation_image': bool(question.image),
            'explanation_image_url': None,
            'explanation_image_filename': question.image if question.image else None,
            'degree': question.degree,
            'year': question.year,
            'block': question.block,
            'module': question.module,
            'subject': question.subject,
            'topic': question.topic
        }
        
        # Handle question image URL generation
        if question.question_image:
            try:
                question_image_url, actual_filename = get_question_image_url_for_field(question, 'question_image')
                if question_image_url:
                    question_data['question_image_url'] = question_image_url
                    question_data['question_image_filename'] = actual_filename
            except Exception as e:
                print(f"Error processing question image for question {question.id}: {str(e)}")
        
        # Handle explanation image URL generation (existing logic)
        if question.image:
            try:
                explanation_image_url, actual_filename = get_question_image_url_for_field(question, 'image')
                if explanation_image_url:
                    question_data['explanation_image_url'] = explanation_image_url
                    question_data['explanation_image_filename'] = actual_filename
            except Exception as e:
                print(f"Error processing explanation image for question {question.id}: {str(e)}")
        
    processed_questions.append(question_data)
    
    
    
    # Update session if question count changed due to access control
    if len(processed_questions) != session.total_questions:
        session.total_questions = len(processed_questions)
        session.save()
        messages.info(request, f"Session adjusted to {len(processed_questions)} questions based on your access level.")
    
    context = {
        'session': session,
        'questions': processed_questions,
        'total_questions': len(processed_questions),
        'user_access': get_user_access_info(request.user),
        'accessible_question_count': len(processed_questions),
    }
    
    return render(request, 'managemodule/practice_session.html', context)

def get_question_image_url_for_field(question, field_name):
    """
    Enhanced function to get image URL for a specific field (question_image or image)
    """
    image_filename = getattr(question, field_name, None)
    if not image_filename:
        return None, None
    
    try:
        # Get the image filename
        image_filename = image_filename.strip()
        if not image_filename:
            return None, None
        
        # Check if it's already a full URL
        if image_filename.startswith(('http://', 'https://', '/')):
            return image_filename, image_filename.split('/')[-1]
        
        # Try different possible paths in MEDIA_ROOT
        possible_paths = [
            f"questions/{image_filename}",
            f"question_images/{image_filename}",
            f"images/{image_filename}",
            image_filename
        ]
        
        for path in possible_paths:
            full_path = os.path.join(settings.MEDIA_ROOT, path)
            if os.path.exists(full_path):
                return f"{settings.MEDIA_URL}{path}", image_filename
        
        # Try using QuestionImage model if available
        try:
            from manageimage.models import QuestionImage
            
            # Try exact match first
            try:
                image_obj = QuestionImage.objects.get(filename=image_filename)
                if image_obj.image:
                    return image_obj.image.url, image_obj.filename
            except QuestionImage.DoesNotExist:
                pass
            
            # Try without extension
            filename_no_ext = image_filename.rsplit('.', 1)[0] if '.' in image_filename else image_filename
            possible_matches = QuestionImage.objects.filter(filename__icontains=filename_no_ext)
            
            for match in possible_matches:
                match_no_ext = match.filename.rsplit('.', 1)[0] if '.' in match.filename else match.filename
                if match_no_ext.lower() == filename_no_ext.lower():
                    if match.image:
                        return match.image.url, match.filename
            
        except ImportError:
            # manageimage app not available
            pass
        
        return None, image_filename
        
    except Exception as e:
        print(f"Error loading image for question {question.id}, field {field_name}: {str(e)}")
        return None, getattr(question, field_name, None)
    
    
@require_POST
@content_access_required
def submit_practice_answer(request):
    """Enhanced answer submission with access control and proper validation"""
    session_id = request.POST.get('session_id')
    question_id = request.POST.get('question_id')
    answer = request.POST.get('answer')
    time_spent = int(request.POST.get('time_spent', 0))
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        question = get_object_or_404(Question, id=question_id)
        
        # ACCESS CONTROL: Verify user owns session and can access question
        if session.student != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access to practice session'
            }, status=403)
        
        if not check_object_access(question, request.user):
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
        response, created = PracticeResponse.objects.update_or_create(
            session=session,
            question=question,
            defaults={
                'selected_answer': answer,
                'time_spent': time_spent,
            }
        )
        
        # Check if answer is correct
        is_correct = response.check_answer()
        response.save()
        
        # Return response with explanation based on mode and settings
        explanation = None
        if session.show_explanations and session.practice_mode == 'student':
            explanation = question.explanation
        
        return JsonResponse({
            'success': True,
            'is_correct': is_correct,
            'correct_answer': question.correct_answer,
            'explanation': explanation,
            'selected_answer': answer,
            'practice_mode': session.practice_mode,
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_POST
@content_access_required
def complete_practice_session(request):
    """Enhanced session completion with access control and proper accuracy calculation"""
    session_id = request.POST.get('session_id')
    total_time = int(request.POST.get('total_time', 0))
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        
        # ACCESS CONTROL: Verify user owns session
        if session.student != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access to practice session'
            }, status=403)
        
        # Calculate results with access control filtering
        responses = session.responses.all()
        accessible_responses = []
        
        for response in responses:
            if check_object_access(response.question, request.user):
                accessible_responses.append(response)
        
        questions_attempted = len(accessible_responses)
        correct_answers = len([r for r in accessible_responses if r.is_correct])
        
        # Calculate accuracy to 1 decimal place
        if questions_attempted > 0:
            accuracy_value = round((correct_answers / questions_attempted) * 100, 1)
        else:
            accuracy_value = 0.0
        
        # Update session with all fields at once
        PracticeSession.objects.filter(id=session.id).update(
            status='completed',
            completed_at=timezone.now(),
            time_spent=total_time,
            questions_attempted=questions_attempted,
            correct_answers=correct_answers,
            accuracy=Decimal(str(accuracy_value))
        )
        
        # Refresh session object
        session.refresh_from_db()
        
        # Update or create student progress with access control
        try:
            progress, created = StudentProgress.objects.get_or_create(
                student=request.user,
                degree=session.degree,
                year=session.year,
                block=session.block,
                module=session.module,
                subject=session.subject,
                topic=session.topic,
            )
            
            progress.update_progress(session)
        except Exception as e:
            print(f"Error updating student progress: {e}")
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'accuracy': float(session.accuracy),
            'correct_answers': session.correct_answers,
            'total_questions': session.questions_attempted,
            'accessible_questions': questions_attempted,
            'redirect_url': f'/managemodule/student/session/{session.id}/result/',
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@content_access_required
def start_practice_session(request):
    """Enhanced practice session configuration with access control and proper validation"""
    if request.method == 'POST':
        # Get topic parameters
        degree = request.POST.get('degree')
        year = request.POST.get('year')
        block = request.POST.get('block')
        module = request.POST.get('module')
        subject = request.POST.get('subject')
        topic = request.POST.get('topic')
        
        # Get session configuration
        practice_mode = request.POST.get('practice_mode', 'student')
        total_questions = int(request.POST.get('total_questions', 10))
        difficulty_filter = request.POST.get('difficulty_filter', '')
        show_explanations = request.POST.get('show_explanations') == 'on'
        timed_practice = request.POST.get('timed_practice') == 'on'
        time_per_question = int(request.POST.get('time_per_question', 60)) if timed_practice else None
        randomize_questions = request.POST.get('randomize_questions') == 'on'
        
        # Validate that topic has questions with access control
        questions_query = Question.objects.filter(
            question_type='MCQ',
            degree=degree,
            year=year,
            block=block,
            module=module,
            subject=subject,
            topic=topic
        )
        
        # APPLY USER ACCESS FILTER
        questions_query = apply_user_access_filter(questions_query, request.user)
        
        if difficulty_filter:
            questions_query = questions_query.filter(difficulty=difficulty_filter)
        
        available_count = questions_query.count()
        if available_count < total_questions:
            user_access = get_user_access_info(request.user)
            if user_access.get('level') == 'student':
                access_msg = f" for {user_access.get('filter_params', {}).get('degree', 'your')} Year {user_access.get('filter_params', {}).get('year', '')}"
            else:
                access_msg = ""
            
            messages.error(request, f"Only {available_count} questions available{access_msg} for this topic with selected filters. Please adjust your selection.")
            return redirect(request.path + '?' + request.GET.urlencode())
        
        # Create practice session
        session = PracticeSession.objects.create(
            student=request.user,
            degree=degree,
            year=year,
            block=block,
            module=module,
            subject=subject,
            topic=topic,
            practice_mode=practice_mode,
            difficulty_filter=difficulty_filter if difficulty_filter else None,
            total_questions=total_questions,
            show_explanations=show_explanations,
            timed_practice=timed_practice,
            time_per_question=time_per_question,
            randomize_questions=randomize_questions,
            status='in_progress'
        )
        
        return redirect('practice_session', session_id=session.id)
    
    # GET request - show practice configuration form with access control
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    
    # Get questions count for each difficulty with access control
    base_query = Question.objects.filter(
        question_type='MCQ',
        degree=degree,
        year=year,
        block=block,
        module=module,
        subject=subject,
        topic=topic
    )
    
    # APPLY USER ACCESS FILTER
    base_query = apply_user_access_filter(base_query, request.user)
    
    total_questions = base_query.count()
    easy_count = base_query.filter(difficulty='Easy').count()
    medium_count = base_query.filter(difficulty='Medium').count()
    hard_count = base_query.filter(difficulty='Hard').count()
    
    # Get student's previous performance for this topic
    try:
        progress = StudentProgress.objects.get(
            student=request.user,
            degree=degree,
            year=year,
            block=block,
            module=module,
            subject=subject,
            topic=topic
        )
        previous_sessions = progress.total_sessions
        best_accuracy = round(progress.best_accuracy, 1)
        last_practiced = progress.last_practiced
    except StudentProgress.DoesNotExist:
        previous_sessions = 0
        best_accuracy = 0.0
        last_practiced = None
    
    context = {
        'degree': degree,
        'year': year,
        'block': block,
        'module': module,
        'subject': subject,
        'topic': topic,
        'total_questions': total_questions,
        'easy_count': easy_count,
        'medium_count': medium_count,
        'hard_count': hard_count,
        'previous_sessions': previous_sessions,
        'best_accuracy': best_accuracy,
        'last_practiced': last_practiced,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'managemodule/start_practice_session.html', context)


@require_POST
@content_access_required
def mark_question_for_review(request):
    """Enhanced mark for review functionality with access control"""
    session_id = request.POST.get('session_id')
    question_id = request.POST.get('question_id')
    marked = request.POST.get('marked', 'false').lower() == 'true'
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        question = get_object_or_404(Question, id=question_id)
        
        # ACCESS CONTROL: Verify user owns session and can access question
        if session.student != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access to practice session'
            }, status=403)
        
        if not check_object_access(question, request.user):
            return JsonResponse({
                'success': False,
                'error': 'You don\'t have access to this question'
            }, status=403)
        
        # Get or create response
        response, created = PracticeResponse.objects.get_or_create(
            session=session,
            question=question,
            defaults={'marked_for_review': marked}
        )
        
        if not created:
            response.marked_for_review = marked
            response.save()
        
        return JsonResponse({
            'success': True,
            'marked': marked,
            'question_id': question_id,
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@content_access_required
def get_question_count_by_difficulty(request):
    """Enhanced AJAX endpoint with access control to get question count based on difficulty selection"""
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    difficulty = request.GET.get('difficulty', '')
    
    # Build base query
    query = Question.objects.filter(
        question_type='MCQ',
        degree=degree,
        year=year,
        block=block,
        module=module,
        subject=subject,
        topic=topic
    )
    
    # APPLY USER ACCESS FILTER
    query = apply_user_access_filter(query, request.user)
    
    if difficulty:
        query = query.filter(difficulty=difficulty)
    
    count = query.count()
    user_access = get_user_access_info(request.user)
    
    return JsonResponse({
        'count': count,
        'difficulty': difficulty or 'all',
        'user_access_level': user_access.get('level', 'student'),
        'filter_applied': user_access.get('level') == 'student'
    })

# FIXED: Update the practice_session_result view to properly structure the context

@content_access_required
def practice_session_result(request, session_id):
    """Enhanced practice session results display with access control"""
    session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
    
    # ACCESS CONTROL: Verify user owns session
    if session.student != request.user:
        messages.error(request, "You can only view your own practice session results.")
        return redirect('student_practice_modules')
    
    if session.status == 'in_progress':
        return redirect('practice_session', session_id=session.id)
    
    # Get all responses with questions and apply access control
    responses = session.responses.all().select_related('question').order_by('answered_at')
    
    # Filter responses by access control and process them properly
    processed_responses = []
    for response in responses:
        if check_object_access(response.question, request.user):
            # Create the structure that template expects
            response_data = {
                'response': response,
                'question': response.question,
                'is_correct': response.is_correct,
                'selected_answer': response.selected_answer,
                'time_spent': response.time_spent,
                # UPDATED: Support both question and explanation images
                'question_image_url': None,
                'question_image_filename': None,
                'explanation_image_url': None,
                'explanation_image_filename': None
            }
            
            # UPDATED: Process question image
            if response.question.question_image:
                try:
                    question_image_url, actual_filename = get_question_image_url_for_field(response.question, 'question_image')
                    if question_image_url:
                        response_data['question_image_url'] = question_image_url
                        response_data['question_image_filename'] = actual_filename
                except Exception as e:
                    print(f"Error processing question image for question {response.question.id}: {str(e)}")
            
            # UPDATED: Process explanation image (existing logic)
            if response.question.image:
                try:
                    explanation_image_url, actual_filename = get_question_image_url_for_field(response.question, 'image')
                    if explanation_image_url:
                        response_data['explanation_image_url'] = explanation_image_url
                        response_data['explanation_image_filename'] = actual_filename
                except Exception as e:
                    print(f"Error processing explanation image for question {response.question.id}: {str(e)}")
            
            processed_responses.append(response_data)
                
    # Calculate statistics based on accessible responses only
    total_questions = len(processed_responses)
    correct_answers = len([r for r in processed_responses if r['response'].is_correct])
    incorrect_answers = total_questions - correct_answers
    
    # Difficulty breakdown (only for accessible responses)
    difficulty_stats = {}
    for response_data in processed_responses:
        response = response_data['response']
        difficulty = response.question.difficulty
        if difficulty not in difficulty_stats:
            difficulty_stats[difficulty] = {'total': 0, 'correct': 0}
        difficulty_stats[difficulty]['total'] += 1
        if response.is_correct:
            difficulty_stats[difficulty]['correct'] += 1
    
    # Calculate accuracy for each difficulty
    for difficulty, stats in difficulty_stats.items():
        if stats['total'] > 0:
            stats['accuracy'] = round((stats['correct'] / stats['total']) * 100, 1)
        else:
            stats['accuracy'] = 0.0
    
    context = {
        'session': session,
        'responses': processed_responses,  # FIXED: Pass processed responses with image data
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,
        'difficulty_stats': difficulty_stats,
        'user_access': get_user_access_info(request.user),
        'accessible_questions_count': total_questions,
        'original_questions_count': session.questions_attempted,
    }
    
    return render(request, 'managemodule/practice_session_result.html', context)



@content_access_required
def managemodule(request):
    """Enhanced main hierarchy view with search, filtering and access control"""
    # Get search and filter parameters
    query = request.GET.get('q', '')
    filter_degree = request.GET.get('degree', '')
    filter_year = request.GET.get('year', '')
    filter_block = request.GET.get('filter_block', '')
    
    # Start with all questions and apply access control
    questions = Question.objects.all()
    questions = apply_user_access_filter(questions, request.user)
    
    # Apply additional filters
    if query:
        questions = questions.filter(
            Q(block__icontains=query) |
            Q(module__icontains=query) |
            Q(subject__icontains=query) |
            Q(topic__icontains=query)
        )
    
    if filter_degree:
        questions = questions.filter(degree=filter_degree)
    
    if filter_year:
        questions = questions.filter(year=filter_year)
    
    if filter_block:
        questions = questions.filter(block__icontains=filter_block)

    # Get unique blocks for filter dropdown (access-controlled)
    all_blocks = questions.values('block').distinct().order_by('block')

    # Group modules by block with access control
    block_module_map = []
    for block in all_blocks:
        block_name = block['block']
        
        # Filter modules by current filters and access control
        block_questions = questions.filter(block=block_name)
        if not block_questions.exists():
            continue
            
        modules = block_questions.values('module', 'degree', 'year').distinct().order_by('module', 'degree', 'year')
        module_list = []
        
        for module in modules:
            module_name = module['module']
            degree = module['degree']
            year = module['year']
            
            # Subjects for this module (access-controlled)
            module_questions = block_questions.filter(
                module=module_name, degree=degree, year=year
            )
            subjects = module_questions.values('subject').distinct().order_by('subject')
            subject_list = []
            
            for subject in subjects:
                subject_name = subject['subject']
                
                # Topics for this subject (access-controlled)
                subject_questions = module_questions.filter(subject=subject_name)
                topics = subject_questions.values('topic').distinct().order_by('topic')
                topic_list = []
                
                for topic in topics:
                    topic_name = topic['topic']
                    topic_questions_count = subject_questions.filter(topic=topic_name).count()
                    
                    # Get image count for this topic
                    topic_questions_with_images = subject_questions.filter(
                        topic=topic_name
                    ).exclude(Q(image__isnull=True) | Q(image__exact=''))
                    topic_image_count = topic_questions_with_images.values('image').distinct().count()
                    
                    topic_list.append({
                        'name': topic_name,
                        'questions_count': topic_questions_count,
                        'image_count': topic_image_count,
                        'block': block_name,
                        'module': module_name,
                        'subject': subject_name,
                        'degree': degree,
                        'year': year,
                    })
                
                if topic_list:
                    subject_list.append({
                        'name': subject_name,
                        'topics': topic_list,
                        'topics_count': len(topic_list),
                    })
            
            if subject_list:
                module_list.append({
                    'name': module_name,
                    'degree': degree,
                    'year': year,
                    'subjects': subject_list,
                    'subjects_count': len(subject_list),
                    'topics_count': sum(len(s['topics']) for s in subject_list),
                })
        
        if module_list:
            block_module_map.append({
                'block': block_name,
                'modules': module_list,
            })

    # Calculate statistics (access-controlled)
    stats = {
        'modules_count': questions.values('module', 'degree', 'year').distinct().count(),
        'subjects_count': questions.values('subject').distinct().count(),
        'topics_count': questions.values('topic').distinct().count(),
        'total_questions': questions.count(),
    }

    context = {
        'block_module_map': block_module_map,
        'blocks': all_blocks,
        'stats': stats,
        'query': query,
        'filter_degree': filter_degree,
        'filter_year': filter_year,
        'filter_block': filter_block,
        'degree_choices': Question.DEGREE_CHOICES,
        'year_choices': Question.YEAR_CHOICES,
        'user_access': get_user_access_info(request.user),
    }
    return render(request, 'managemodule/managemodule.html', context)


@content_access_required
def topic_questions(request):
    """Enhanced topic questions display with access control and image support"""
    # Get topic parameters from URL
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    
    # Handle AJAX requests for image data
    ajax_type = request.GET.get('ajax', '')
    
    if ajax_type == 'image_count':
        # Return image count for this topic with access control
        questions = Question.objects.filter(
            block=block,
            module=module,
            subject=subject,
            topic=topic,
            degree=degree,
            year=year
        )
        
        # APPLY USER ACCESS FILTER
        questions = apply_user_access_filter(questions, request.user)
        
        image_count = questions.exclude(image__isnull=True).exclude(image__exact='').values('image').distinct().count()
        
        return JsonResponse({
            'image_count': image_count,
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
    
    elif ajax_type == 'images':
        # Return images for this topic with access control
        questions = Question.objects.filter(
            block=block,
            module=module,
            subject=subject,
            topic=topic,
            degree=degree,
            year=year
        ).exclude(image__isnull=True).exclude(image__exact='')
        
        # APPLY USER ACCESS FILTER
        questions = apply_user_access_filter(questions, request.user)
        
        # Group by image filename and count usage
        image_data = {}
        for q in questions:
            if q.image:
                if q.image not in image_data:
                    image_data[q.image] = {
                        'filename': q.image,
                        'question_count': 0
                    }
                image_data[q.image]['question_count'] += 1
        
        return JsonResponse({
            'images': list(image_data.values()),
            'media_url': settings.MEDIA_URL,
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
    
    # Regular page request with access control
    query = request.GET.get('q', '')
    
    # Filter questions for this specific topic
    questions = Question.objects.filter(
        block=block,
        module=module,
        subject=subject,
        topic=topic,
        degree=degree,
        year=year
    ).order_by('-created_on')
    
    # APPLY USER ACCESS FILTER
    questions = apply_user_access_filter(questions, request.user)
    
    # Apply search if provided
    if query:
        questions = questions.filter(
            Q(question_text__icontains=query) |
            Q(explanation__icontains=query)
        )
    
    # Pagination
    paginator = Paginator(questions, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Create breadcrumb info
    breadcrumb = {
        'block': block,
        'module': module,
        'subject': subject,
        'topic': topic,
        'degree': degree,
        'year': year,
    }
    
    # Enhanced context with image statistics (access-controlled)
    total_questions = questions.count()
    questions_with_images = questions.exclude(image__isnull=True).exclude(image__exact='').count()
    unique_images = questions.exclude(image__isnull=True).exclude(image__exact='').values('image').distinct().count()
    
    context = {
        'page_obj': page_obj,
        'breadcrumb': breadcrumb,
        'query': query,
        'total_questions': total_questions,
        'questions_with_images': questions_with_images,
        'unique_images': unique_images,
        'image_percentage': round((questions_with_images / total_questions * 100), 1) if total_questions > 0 else 0,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'managemodule/topic_questions.html', context)


@content_access_required
def student_practice_modules(request):
    """Enhanced student view for practice modules hierarchy with access control"""
    user = request.user
    
    # Get search and filter parameters
    query = request.GET.get('q', '')
    filter_degree = request.GET.get('degree', '')
    filter_year = request.GET.get('year', '')
    filter_block = request.GET.get('filter_block', '')
    
    # Only MCQ for practice with access control
    questions = Question.objects.filter(question_type='MCQ')
    questions = apply_user_access_filter(questions, request.user)
    
    # Apply additional filters
    if query:
        questions = questions.filter(
            Q(block__icontains=query) |
            Q(module__icontains=query) |
            Q(subject__icontains=query) |
            Q(topic__icontains=query)
        )
    
    if filter_degree:
        questions = questions.filter(degree=filter_degree)
    
    if filter_year:
        questions = questions.filter(year=filter_year)
    
    if filter_block:
        questions = questions.filter(block__icontains=filter_block)

    # Get unique blocks (access-controlled)
    all_blocks = questions.values('block').distinct().order_by('block')

    # Group modules by block with progress information and access control
    block_module_map = []
    for block in all_blocks:
        block_name = block['block']
        
        # Filter modules by current filters and access control
        block_questions = questions.filter(block=block_name)
        if not block_questions.exists():
            continue
            
        modules = block_questions.values('module', 'degree', 'year').distinct().order_by('module', 'degree', 'year')
        module_list = []
        
        for module in modules:
            module_name = module['module']
            degree = module['degree']
            year = module['year']
            
            # Subjects for this module (access-controlled)
            module_questions = block_questions.filter(
                module=module_name, degree=degree, year=year
            )
            subjects = module_questions.values('subject').distinct().order_by('subject')
            subject_list = []
            
            for subject in subjects:
                subject_name = subject['subject']
                
                # Topics for this subject (access-controlled)
                subject_questions = module_questions.filter(subject=subject_name)
                topics = subject_questions.values('topic').distinct().order_by('topic')
                topic_list = []
                
                for topic in topics:
                    topic_name = topic['topic']
                    topic_questions_count = subject_questions.filter(topic=topic_name).count()
                    
                    # Get student progress for this topic
                    try:
                        progress = StudentProgress.objects.get(
                            student=user,
                            degree=degree,
                            year=year,
                            block=block_name,
                            module=module_name,
                            subject=subject_name,
                            topic=topic_name
                        )
                        mastery_level = progress.mastery_level
                        accuracy = round(progress.overall_accuracy, 1)
                        sessions_count = progress.total_sessions
                    except StudentProgress.DoesNotExist:
                        mastery_level = "Not Started"
                        accuracy = 0.0
                        sessions_count = 0
                    
                    topic_list.append({
                        'name': topic_name,
                        'questions_count': topic_questions_count,
                        'block': block_name,
                        'module': module_name,
                        'subject': subject_name,
                        'degree': degree,
                        'year': year,
                        'mastery_level': mastery_level,
                        'accuracy': accuracy,
                        'sessions_count': sessions_count,
                    })
                
                if topic_list:
                    subject_list.append({
                        'name': subject_name,
                        'topics': topic_list,
                        'topics_count': len(topic_list),
                    })
            
            if subject_list:
                module_list.append({
                    'name': module_name,
                    'degree': degree,
                    'year': year,
                    'subjects': subject_list,
                    'subjects_count': len(subject_list),
                    'topics_count': sum(len(s['topics']) for s in subject_list),
                })
        
        if module_list:
            block_module_map.append({
                'block': block_name,
                'modules': module_list,
            })

    # Calculate overall stats for the student (access-controlled)
    user_progress = StudentProgress.objects.filter(student=user)
    total_topics_practiced = user_progress.count()
    average_accuracy = user_progress.aggregate(avg=Avg('best_accuracy'))['avg'] or 0
    total_sessions = sum(p.total_sessions for p in user_progress)

    stats = {
        'total_topics_practiced': total_topics_practiced,
        'average_accuracy': round(average_accuracy, 1),
        'total_sessions': total_sessions,
        'available_topics': questions.values('topic').distinct().count(),
    }

    context = {
        'block_module_map': block_module_map,
        'blocks': all_blocks,
        'stats': stats,
        'query': query,
        'filter_degree': filter_degree,
        'filter_year': filter_year,
        'filter_block': filter_block,
        'degree_choices': Question.DEGREE_CHOICES,
        'year_choices': Question.YEAR_CHOICES,
        'user': user,
        'user_access': get_user_access_info(request.user),
    }
    return render(request, 'managemodule/student_practice_modules.html', context)


@content_access_required
def student_practice_progress(request):
    """Enhanced student practice progress with pagination, filtering and access control"""
    user = request.user
    
    try:
        # Base queryset with access control
        progress_queryset = StudentProgress.objects.filter(student=user).select_related('student')
        
        # Apply filters
        mastery_filter = request.GET.get('mastery')
        subject_filter = request.GET.get('subject')
        
        if mastery_filter and mastery_filter != 'all':
            progress_queryset = progress_queryset.filter(mastery_level=mastery_filter)
        
        if subject_filter and subject_filter != 'all':
            progress_queryset = progress_queryset.filter(subject=subject_filter)
        
        # ADDITIONAL ACCESS CONTROL: Filter by user's degree/year if student
        user_access = get_user_access_info(user)
        if user_access.get('level') == 'student':
            filter_params = user_access.get('filter_params', {})
            if filter_params.get('degree'):
                progress_queryset = progress_queryset.filter(degree=filter_params['degree'])
            if filter_params.get('year'):
                progress_queryset = progress_queryset.filter(year=filter_params['year'])
        
        # Order by last practiced
        progress_queryset = progress_queryset.order_by('-last_practiced', '-best_accuracy')
        
        # Paginate results
        paginator = Paginator(progress_queryset, 10)
        page_number = request.GET.get('page')
        progress_list = paginator.get_page(page_number)
        
        # Calculate overall statistics (access-controlled)
        all_progress = StudentProgress.objects.filter(student=user)
        
        # Apply same access control to all_progress
        if user_access.get('level') == 'student':
            filter_params = user_access.get('filter_params', {})
            if filter_params.get('degree'):
                all_progress = all_progress.filter(degree=filter_params['degree'])
            if filter_params.get('year'):
                all_progress = all_progress.filter(year=filter_params['year'])
        
        total_topics = all_progress.count()
        total_sessions = sum(p.total_sessions for p in all_progress if p.total_sessions)
        total_questions = sum(p.total_questions_attempted for p in all_progress if p.total_questions_attempted)
        total_correct = sum(p.total_correct_answers for p in all_progress if p.total_correct_answers)
        overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
        
        # Best and worst performance
        best_accuracy = all_progress.aggregate(Max('best_accuracy'))['best_accuracy__max'] or 0
        lowest_accuracy = all_progress.filter(total_questions_attempted__gte=5).aggregate(
            Min('best_accuracy'))['best_accuracy__min'] or 0
        
        # Calculate consistency score
        accuracies = [p.best_accuracy for p in all_progress if p.best_accuracy and p.total_questions_attempted >= 5]
        consistency_score = 75  # Default
        if len(accuracies) >= 3:
            mean_acc = sum(accuracies) / len(accuracies)
            variance = sum((x - mean_acc) ** 2 for x in accuracies) / len(accuracies)
            std_dev = variance ** 0.5
            consistency_score = max(0, 100 - (std_dev * 2))
        
        # Recent sessions (access-controlled)
        recent_sessions = []
        try:
            recent_sessions_query = PracticeSession.objects.filter(
                student=user,
                status='completed'
            )
            
            # Apply access control to recent sessions
            if user_access.get('level') == 'student':
                filter_params = user_access.get('filter_params', {})
                if filter_params.get('degree'):
                    recent_sessions_query = recent_sessions_query.filter(degree=filter_params['degree'])
                if filter_params.get('year'):
                    recent_sessions_query = recent_sessions_query.filter(year=filter_params['year'])
            
            recent_sessions = recent_sessions_query.order_by('-completed_at')[:10]
        except:
            recent_sessions = []
        
        # Best performing topics (access-controlled)
        best_topics = all_progress.filter(
            total_questions_attempted__gte=5
        ).order_by('-best_accuracy')[:5]
        
        # Topics needing practice (access-controlled)
        needs_practice = all_progress.filter(
            total_questions_attempted__gte=5,
            best_accuracy__lt=70
        ).order_by('best_accuracy')[:5]
        
        # Calculate trends
        current_week = timezone.now() - timedelta(days=7)
        recent_progress = all_progress.filter(last_practiced__gte=current_week) if all_progress else []
        weekly_improvement = len(recent_progress)
        
        context = {
            'progress_list': progress_list,
            'total_topics': total_topics,
            'total_sessions': total_sessions,
            'total_questions': total_questions,
            'overall_accuracy': round(overall_accuracy, 1),
            'best_accuracy': round(best_accuracy, 1),
            'lowest_accuracy': round(lowest_accuracy, 1),
            'consistency_score': round(consistency_score, 1),
            'recent_sessions': recent_sessions,
            'best_topics': best_topics,
            'needs_practice': needs_practice,
            'weekly_improvement': weekly_improvement,
            'user': user,
            'current_mastery_filter': mastery_filter or 'all',
            'current_subject_filter': subject_filter or 'all',
            'user_access': user_access,
        }
        
    except Exception as e:
        print(f"Error in student_practice_progress: {e}")
        
        # Minimal safe context with access control
        progress_queryset = StudentProgress.objects.filter(student=user)
        
        # Apply access control even in error case
        user_access = get_user_access_info(user)
        if user_access.get('level') == 'student':
            filter_params = user_access.get('filter_params', {})
            if filter_params.get('degree'):
                progress_queryset = progress_queryset.filter(degree=filter_params['degree'])
            if filter_params.get('year'):
                progress_queryset = progress_queryset.filter(year=filter_params['year'])
        
        progress_queryset = progress_queryset.order_by('-last_practiced')
        paginator = Paginator(progress_queryset, 10)
        page_number = request.GET.get('page')
        progress_list = paginator.get_page(page_number)
        
        context = {
            'progress_list': progress_list,
            'total_topics': progress_queryset.count(),
            'total_sessions': 0,
            'total_questions': 0,
            'overall_accuracy': 0.0,
            'best_accuracy': 0.0,
            'lowest_accuracy': 0.0,
            'consistency_score': 75.0,
            'recent_sessions': [],
            'best_topics': [],
            'needs_practice': [],
            'weekly_improvement': 0,
            'user': user,
            'current_mastery_filter': 'all',
            'current_subject_filter': 'all',
            'user_access': user_access,
        }
    
    return render(request, 'managemodule/student_practice_progress.html', context)


@require_POST
@content_access_required
def save_practice_note(request):
    """Enhanced save practice session note with smart title generation and access control"""
    print("=== SAVE PRACTICE NOTE DEBUG START ===")
    print(f"User: {request.user}")
    print(f"Method: {request.method}")
    print(f"POST data: {request.POST}")
    
    session_id = request.POST.get('session_id')
    question_id = request.POST.get('question_id')
    note_text = request.POST.get('note_text', '').strip()
    
    print(f"Session ID: {session_id}")
    print(f"Question ID: {question_id}")
    print(f"Note text length: {len(note_text)}")
    
    # Get additional context data from the template
    degree = request.POST.get('degree', '')
    year = request.POST.get('year', '')
    block = request.POST.get('block', '')
    module = request.POST.get('module', '')
    subject = request.POST.get('subject', '')
    topic = request.POST.get('topic', '')
    
    print(f"Context - Degree: {degree}, Year: {year}")
    print(f"Context - Block: {block}, Module: {module}")
    print(f"Context - Subject: {subject}, Topic: {topic}")
    
    try:
        # Verify session exists and belongs to user
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        print(f"✓ Session found: {session}")
        
        # ACCESS CONTROL: Verify user owns session
        if session.student != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access to practice session'
            }, status=403)
        
        # Verify question exists and user has access
        question = get_object_or_404(Question, id=question_id)
        print(f"✓ Question found: Q{question.id}")
        
        # ACCESS CONTROL: Check if user can access this question
        if not check_object_access(question, request.user):
            return JsonResponse({
                'success': False,
                'error': 'You don\'t have access to this question'
            }, status=403)
        
        if note_text:
            # ENHANCED: Generate smart title based on question content and context
            smart_title = generate_smart_note_title(question, subject, topic, note_text)
            print(f"✓ Generated smart title: {smart_title}")
            
            # Save to PracticeSessionNote (original functionality)
            practice_note, created = PracticeSessionNote.objects.update_or_create(
                session=session,
                question=question,
                defaults={'note_text': note_text}
            )
            
            action = "created" if created else "updated"
            print(f"✓ Practice note {action}: {practice_note.id}")
            
            # ALSO save to StudentNote (notes app integration) with smart title
            try:
                # Import StudentNote from notes app
                from notes.models import StudentNote
                
                # Create or update corresponding StudentNote with enhanced title
                student_note, note_created = StudentNote.objects.update_or_create(
                    student=request.user,
                    question=question,  # Link to the same question
                    defaults={
                        'title': smart_title,  # Use smart title instead of generic one
                        'content': note_text,
                        'note_type': 'question_note',
                        'degree': degree or question.degree or 'MBBS',
                        'year': year or question.year or '1st',
                        'block': block or question.block or '',
                        'module': module or question.module or '',
                        'subject': subject or question.subject or '',
                        'topic': topic or question.topic or '',
                    }
                )
                
                note_action = "created" if note_created else "updated"
                print(f"✓ Student note {note_action}: {student_note.id}")
                
            except ImportError:
                print("! Notes app not available, skipping StudentNote creation")
            except Exception as note_error:
                print(f"! Error creating StudentNote: {note_error}")
            
            # Build hierarchy path for response
            hierarchy_parts = []
            if block: hierarchy_parts.append(block)
            if module: hierarchy_parts.append(module)
            if subject: hierarchy_parts.append(subject)
            if topic: hierarchy_parts.append(topic)
            hierarchy_path = ' → '.join(hierarchy_parts) if hierarchy_parts else f"{degree} - {year}"
            
            response_data = {
                'success': True,
                'message': f'Note {action} successfully',
                'note_id': practice_note.id,
                'has_note': True,
                'note_details': {
                    'question_id': question.id,
                    'question_text': question.question_text[:100] + '...' if len(question.question_text) > 100 else question.question_text,
                    'hierarchy_path': hierarchy_path,
                    'note_length': len(note_text),
                    'action': action,
                    'generated_title': smart_title,  # Include generated title in response
                    'also_saved_to_notes_app': 'student_note' in locals(),
                    'user_access_level': get_user_access_info(request.user).get('level', 'student')
                }
            }
            
            print(f"✓ Response data prepared: {response_data}")
            return JsonResponse(response_data)
            
        else:
            # Delete both practice note and student note if empty
            try:
                practice_note = PracticeSessionNote.objects.get(session=session, question=question)
                practice_note.delete()
                print("✓ Practice note deleted (empty content)")
                
                # Also delete from StudentNote
                try:
                    from notes.models import StudentNote
                    student_note = StudentNote.objects.get(student=request.user, question=question)
                    student_note.delete()
                    print("✓ Student note also deleted")
                except StudentNote.DoesNotExist:
                    print("! No corresponding StudentNote to delete")
                except ImportError:
                    print("! Notes app not available")
                
                return JsonResponse({
                    'success': True,
                    'message': 'Note deleted',
                    'has_note': False,
                    'note_details': {
                        'question_id': question.id,
                        'action': 'deleted',
                        'user_access_level': get_user_access_info(request.user).get('level', 'student')
                    }
                })
            except PracticeSessionNote.DoesNotExist:
                print("! No existing practice note to delete")
                return JsonResponse({
                    'success': True,
                    'message': 'No note to save',
                    'has_note': False,
                    'user_access_level': get_user_access_info(request.user).get('level', 'student')
                })
        
    except PracticeSession.DoesNotExist:
        error_msg = f"Practice session {session_id} not found or doesn't belong to user"
        print(f"❌ ERROR: {error_msg}")
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=404)
        
    except Question.DoesNotExist:
        error_msg = f"Question {question_id} not found"
        print(f"❌ ERROR: {error_msg}")
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=404)
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERROR: {error_msg}")
        print(f"❌ ERROR TYPE: {type(e)}")
        
        return JsonResponse({
            'success': False,
            'error': f'Error saving note: {error_msg}'
        }, status=400)
    
    finally:
        print("=== SAVE PRACTICE NOTE DEBUG END ===")
        print()


def generate_smart_note_title(question, subject, topic, note_text):
    """
    Generate intelligent note titles based on question content and context
    """
    import re
    
    # Clean the question text
    question_text = question.question_text.strip() if question.question_text else ""
    
    # Remove common question prefixes and patterns
    cleaned_question = re.sub(r'^(Question\s*\d*[:\.]?\s*|Q\d*[:\.]?\s*)', '', question_text, flags=re.IGNORECASE)
    
    # Remove HTML tags if any
    cleaned_question = re.sub(r'<[^>]+>', '', cleaned_question)
    
    # Remove extra whitespace
    cleaned_question = re.sub(r'\s+', ' ', cleaned_question).strip()
    
    # Strategy 1: Use first meaningful sentence from question
    if cleaned_question:
        # Split by common sentence endings
        sentences = re.split(r'[.!?:]', cleaned_question)
        
        # Find the first substantial sentence
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 15 and len(sentence) < 80:  # Good length for title
                # Clean up the sentence
                title_candidate = sentence
                
                # Remove common question words from the beginning
                title_candidate = re.sub(r'^(Which|What|How|When|Where|Why|The|A|An)\s+', '', title_candidate, flags=re.IGNORECASE)
                
                # Capitalize properly
                title_candidate = title_candidate.capitalize()
                
                # Add context if short
                if len(title_candidate) < 30 and topic:
                    title_candidate = f"{topic}: {title_candidate}"
                elif len(title_candidate) < 30 and subject:
                    title_candidate = f"{subject}: {title_candidate}"
                
                return title_candidate
    
    # Strategy 2: Use note content if question text is too long/short
    if note_text and len(note_text.strip()) > 10:
        note_words = note_text.strip().split()
        if len(note_words) <= 8:  # Short note, use as title
            return note_text.strip().capitalize()
        else:  # Long note, use first few words
            title_from_note = ' '.join(note_words[:6]) + "..."
            return title_from_note.capitalize()
    
    # Strategy 3: Use topic/subject context with question type detection
    if cleaned_question:
        # Detect question type
        question_type = detect_question_type(cleaned_question)
        
        if topic and subject:
            return f"{topic}: {question_type}"
        elif topic:
            return f"{topic} - {question_type}"
        elif subject:
            return f"{subject}: {question_type}"
    
    # Strategy 4: Fallback to context-based titles
    if topic:
        return f"Note on {topic}"
    elif subject:
        return f"{subject} Note"
    
    # Strategy 5: Final fallback
    return "Practice Session Note"


def detect_question_type(question_text):
    """
    Detect the type/topic of question based on keywords
    """
    question_lower = question_text.lower()
    
    # Medical/Scientific terms
    if any(term in question_lower for term in ['diagnosis', 'symptom', 'disease', 'patient', 'treatment']):
        return "Clinical Question"
    elif any(term in question_lower for term in ['anatomy', 'muscle', 'bone', 'organ', 'tissue']):
        return "Anatomy Question"
    elif any(term in question_lower for term in ['drug', 'medication', 'dosage', 'pharmacology']):
        return "Pharmacology Question"
    elif any(term in question_lower for term in ['biochemistry', 'enzyme', 'protein', 'metabol']):
        return "Biochemistry Question"
    elif any(term in question_lower for term in ['physiology', 'function', 'mechanism']):
        return "Physiology Question"
    elif any(term in question_lower for term in ['pathology', 'abnormal', 'disorder']):
        return "Pathology Question"
    
    # Question starters
    elif question_lower.startswith('which'):
        return "Multiple Choice Question"
    elif question_lower.startswith('what'):
        return "Definition Question"
    elif question_lower.startswith('how'):
        return "Process Question"
    elif question_lower.startswith('why'):
        return "Reasoning Question"
    elif question_lower.startswith('when'):
        return "Timing Question"
    elif question_lower.startswith('where'):
        return "Location Question"
    
    # Content-based detection
    elif any(term in question_lower for term in ['define', 'definition']):
        return "Definition"
    elif any(term in question_lower for term in ['calculate', 'compute', 'find']):
        return "Calculation"
    elif any(term in question_lower for term in ['compare', 'contrast', 'difference']):
        return "Comparison"
    elif any(term in question_lower for term in ['list', 'enumerate', 'name']):
        return "List Question"
    elif any(term in question_lower for term in ['explain', 'describe', 'discuss']):
        return "Explanation"
    
    # Default
    return "Study Question"


# ADMIN VIEWS WITH ACCESS CONTROL

@admin_required
def admin_practice_analytics(request):
    """Admin analytics for practice sessions across all users"""
    # Get all practice sessions
    sessions = PracticeSession.objects.filter(status='completed').select_related('student')
    
    # Calculate statistics
    total_sessions = sessions.count()
    total_students = sessions.values('student').distinct().count()
    avg_accuracy = sessions.aggregate(Avg('accuracy'))['accuracy__avg'] or 0
    
    # Sessions by degree/year
    degree_stats = {}
    for session in sessions:
        key = f"{session.degree} - {session.year}"
        if key not in degree_stats:
            degree_stats[key] = {'sessions': 0, 'accuracy': 0, 'students': set()}
        degree_stats[key]['sessions'] += 1
        degree_stats[key]['accuracy'] += float(session.accuracy or 0)
        degree_stats[key]['students'].add(session.student.id)
    
    # Calculate averages
    for key in degree_stats:
        stats = degree_stats[key]
        stats['avg_accuracy'] = round(stats['accuracy'] / stats['sessions'], 1) if stats['sessions'] > 0 else 0
        stats['unique_students'] = len(stats['students'])
        del stats['students']  # Remove set for JSON serialization
    
    # Recent activity (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_sessions = sessions.filter(completed_at__gte=thirty_days_ago)
    
    # Most active students
    active_students = sessions.values('student__first_name', 'student__last_name', 'student__email').annotate(
        session_count=Count('id'),
        avg_accuracy=Avg('accuracy')
    ).order_by('-session_count')[:10]
    
    # Most practiced topics
    popular_topics = sessions.values('topic', 'subject', 'degree', 'year').annotate(
        session_count=Count('id'),
        avg_accuracy=Avg('accuracy')
    ).order_by('-session_count')[:10]
    
    context = {
        'total_sessions': total_sessions,
        'total_students': total_students,
        'avg_accuracy': round(avg_accuracy, 1),
        'degree_stats': degree_stats,
        'recent_sessions_count': recent_sessions.count(),
        'active_students': active_students,
        'popular_topics': popular_topics,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'managemodule/admin_practice_analytics.html', context)


@admin_required
def export_practice_data(request):
    """Export practice session data to CSV"""
    # Get filter parameters
    degree_filter = request.GET.get('degree', '')
    year_filter = request.GET.get('year', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build query
    sessions = PracticeSession.objects.filter(status='completed').select_related('student')
    
    if degree_filter:
        sessions = sessions.filter(degree=degree_filter)
    if year_filter:
        sessions = sessions.filter(year=year_filter)
    if date_from:
        sessions = sessions.filter(completed_at__gte=date_from)
    if date_to:
        sessions = sessions.filter(completed_at__lte=date_to)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="practice_sessions_export.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Student Name', 'Email', 'Degree', 'Year', 'Block', 'Module', 
        'Subject', 'Topic', 'Practice Mode', 'Total Questions', 'Correct Answers',
        'Accuracy', 'Time Spent (minutes)', 'Difficulty Filter', 'Started At', 'Completed At'
    ])
    
    # Write data
    for session in sessions:
        writer.writerow([
            f"{session.student.first_name} {session.student.last_name}",
            session.student.email,
            session.degree,
            session.year,
            session.block,
            session.module,
            session.subject,
            session.topic,
            session.practice_mode,
            session.questions_attempted,
            session.correct_answers,
            f"{session.accuracy:.1f}%" if session.accuracy else "0.0%",
            round(session.time_spent / 60, 1) if session.time_spent else 0,
            session.difficulty_filter or 'All',
            session.started_at.strftime('%Y-%m-%d %H:%M:%S'),
            session.completed_at.strftime('%Y-%m-%d %H:%M:%S') if session.completed_at else 'N/A'
        ])
    
    return response


@admin_required
def student_progress_report(request):
    """Detailed progress report for a specific student"""
    student_id = request.GET.get('student_id')
    if not student_id:
        messages.error(request, "Student ID is required for progress report.")
        return redirect('admin_practice_analytics')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    student = get_object_or_404(User, id=student_id)
    
    # Get all progress records for this student
    progress_records = StudentProgress.objects.filter(student=student).order_by('degree', 'year', 'block', 'module', 'subject', 'topic')
    
    # Get all practice sessions for this student
    sessions = PracticeSession.objects.filter(student=student, status='completed').order_by('-completed_at')
    
    # Calculate overall statistics
    total_sessions = sessions.count()
    total_progress_records = progress_records.count()
    
    if total_sessions > 0:
        avg_accuracy = sessions.aggregate(Avg('accuracy'))['accuracy__avg'] or 0
        best_accuracy = sessions.aggregate(Max('accuracy'))['accuracy__max'] or 0
        total_time_minutes = sum(s.time_spent for s in sessions if s.time_spent) / 60
        
        # Calculate improvement trend
        if total_sessions >= 5:
            recent_sessions = sessions[:5]
            older_sessions = sessions[5:10] if total_sessions > 10 else sessions[5:]
            
            recent_avg = sum(s.accuracy for s in recent_sessions if s.accuracy) / len(recent_sessions)
            older_avg = sum(s.accuracy for s in older_sessions if s.accuracy) / len(older_sessions) if older_sessions else recent_avg
            
            improvement_trend = recent_avg - older_avg
        else:
            improvement_trend = 0
    else:
        avg_accuracy = best_accuracy = total_time_minutes = improvement_trend = 0
    
    # Group progress by subject
    subject_performance = {}
    for progress in progress_records:
        subject = progress.subject
        if subject not in subject_performance:
            subject_performance[subject] = {
                'topics': [],
                'total_sessions': 0,
                'avg_accuracy': 0,
                'best_accuracy': 0
            }
        
        subject_performance[subject]['topics'].append(progress)
        subject_performance[subject]['total_sessions'] += progress.total_sessions
        
    # Calculate subject averages
    for subject in subject_performance:
        topics = subject_performance[subject]['topics']
        if topics:
            subject_performance[subject]['avg_accuracy'] = round(
                sum(t.overall_accuracy for t in topics) / len(topics), 1
            )
            subject_performance[subject]['best_accuracy'] = round(
                max(t.best_accuracy for t in topics), 1
            )
    
    # Recent activity
    recent_sessions = sessions[:10]
    
    context = {
        'student': student,
        'progress_records': progress_records,
        'total_sessions': total_sessions,
        'total_progress_records': total_progress_records,
        'avg_accuracy': round(avg_accuracy, 1),
        'best_accuracy': round(best_accuracy, 1),
        'total_time_hours': round(total_time_minutes / 60, 1),
        'improvement_trend': round(improvement_trend, 1),
        'subject_performance': subject_performance,
        'recent_sessions': recent_sessions,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'managemodule/student_progress_report.html', context)


# UTILITY VIEWS AND FUNCTIONS

@content_access_required
def get_practice_statistics(request):
    """AJAX endpoint for practice statistics with access control"""
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    
    # Build base query with access control
    questions = Question.objects.filter(question_type='MCQ')
    questions = apply_user_access_filter(questions, request.user)
    
    if degree:
        questions = questions.filter(degree=degree)
    if year:
        questions = questions.filter(year=year)
    if block:
        questions = questions.filter(block=block)
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
    
    # Get user's progress for this topic (if specific topic)
    user_progress = None
    if topic and all([degree, year, block, module, subject]):
        try:
            progress = StudentProgress.objects.get(
                student=request.user,
                degree=degree,
                year=year,
                block=block,
                module=module,
                subject=subject,
                topic=topic
            )
            user_progress = {
                'mastery_level': progress.mastery_level,
                'best_accuracy': round(progress.best_accuracy, 1),
                'total_sessions': progress.total_sessions,
                'last_practiced': progress.last_practiced.strftime('%Y-%m-%d') if progress.last_practiced else None
            }
        except StudentProgress.DoesNotExist:
            user_progress = {
                'mastery_level': 'Not Started',
                'best_accuracy': 0.0,
                'total_sessions': 0,
                'last_practiced': None
            }
    
    return JsonResponse({
        'total_questions': total_count,
        'difficulty_breakdown': {
            'easy': easy_count,
            'medium': medium_count,
            'hard': hard_count
        },
        'user_progress': user_progress,
        'user_access': get_user_access_info(request.user),
    })


@content_access_required
def validate_practice_config(request):
    """AJAX endpoint to validate practice session configuration"""
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    difficulty = request.GET.get('difficulty', '')
    total_questions = int(request.GET.get('total_questions', 10))
    
    # Build query with access control
    questions = Question.objects.filter(
        question_type='MCQ',
        degree=degree,
        year=year,
        block=block,
        module=module,
        subject=subject,
        topic=topic
    )
    
    questions = apply_user_access_filter(questions, request.user)
    
    if difficulty:
        questions = questions.filter(difficulty=difficulty)
    
    available_count = questions.count()
    is_valid = available_count >= total_questions
    
    # Get recommendations if not enough questions
    recommendations = []
    if not is_valid:
        if difficulty:
            # Suggest removing difficulty filter
            all_difficulty_count = Question.objects.filter(
                question_type='MCQ',
                degree=degree,
                year=year,
                block=block,
                module=module,
                subject=subject,
                topic=topic
            )
            all_difficulty_count = apply_user_access_filter(all_difficulty_count, request.user).count()
            
            if all_difficulty_count >= total_questions:
                recommendations.append(f"Remove difficulty filter (all difficulties: {all_difficulty_count} questions)")
        
        # Suggest reducing question count
        if available_count > 0:
            recommendations.append(f"Reduce to {available_count} questions")
        
        # Check other topics in same subject
        subject_questions = Question.objects.filter(
            question_type='MCQ',
            degree=degree,
            year=year,
            subject=subject
        )
        subject_questions = apply_user_access_filter(subject_questions, request.user)
        
        other_topics = subject_questions.exclude(topic=topic).values('topic').distinct()[:3]
        for other_topic in other_topics:
            topic_count = subject_questions.filter(topic=other_topic['topic']).count()
            if topic_count >= total_questions:
                recommendations.append(f"Try topic: {other_topic['topic']} ({topic_count} questions)")
    
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
def get_practice_hierarchy(request):
    """AJAX endpoint for dynamic hierarchy loading with access control"""
    field = request.GET.get('field')
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    
    # Build base query with access control
    query = Question.objects.filter(question_type='MCQ')
    query = apply_user_access_filter(query, request.user)
    
    if degree:
        query = query.filter(degree=degree)
    if year:
        query = query.filter(year=year)
    if block:
        query = query.filter(block=block)
    if module:
        query = query.filter(module=module)
    if subject:
        query = query.filter(subject=subject)
    
    if field == 'blocks':
        data = list(query.values_list('block', flat=True).distinct().order_by('block'))
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


# DEBUG AND TESTING VIEWS (Remove in production)

@admin_required
def debug_access_control(request):
    """Debug view to test access control functionality (remove in production)"""
    if not request.user.is_admin and not request.user.is_superuser:
        return JsonResponse({'error': 'Admin only'}, status=403)
    
    user_id = request.GET.get('user_id')
    if user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        test_user = get_object_or_404(User, id=user_id)
    else:
        test_user = request.user
    
    # Test access control on different models
    all_questions = Question.objects.all()
    filtered_questions = apply_user_access_filter(all_questions, test_user)
    
    # Test practice sessions
    all_sessions = PracticeSession.objects.all()
    user_sessions = all_sessions.filter(student=test_user)
    
    # Test student progress
    user_progress = StudentProgress.objects.filter(student=test_user)
    
    access_info = get_user_access_info(test_user)
    
    debug_data = {
        'user_info': {
            'id': test_user.id,
            'email': test_user.email,
            'degree': test_user.degree,
            'year': test_user.year,
            'approval_status': test_user.approval_status,
            'is_admin': test_user.is_admin,
        },
        'access_info': access_info,
        'question_counts': {
            'total_questions': all_questions.count(),
            'accessible_questions': filtered_questions.count(),
            'filter_difference': all_questions.count() - filtered_questions.count(),
        },
        'session_counts': {
            'total_sessions': all_sessions.count(),
            'user_sessions': user_sessions.count(),
        },
        'progress_counts': {
            'user_progress_records': user_progress.count(),
        },
        'sample_accessible_questions': [
            {
                'id': q.id,
                'degree': q.degree,
                'year': q.year,
                'topic': q.topic,
            } for q in filtered_questions[:5]
        ],
    }
    
    return JsonResponse(debug_data, indent=2)


# ENHANCED ERROR HANDLING

def handle_practice_error(request, error_type, error_message):
    """Centralized error handling for practice sessions"""
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
    
    return render(request, 'managemodule/practice_error.html', error_context)


# MISSING FUNCTION: Check Question Note
@content_access_required
def check_question_note(request):
    """Check if a question has an existing practice note"""
    question_id = request.GET.get('question_id')
    session_id = request.GET.get('session_id')
    
    if not question_id or not session_id:
        return JsonResponse({
            'success': False,
            'error': 'Missing question_id or session_id'
        }, status=400)
    
    try:
        # Verify session belongs to user
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        question = get_object_or_404(Question, id=question_id)
        
        # ACCESS CONTROL: Check if user can access this question
        if not check_object_access(question, request.user):
            return JsonResponse({
                'success': False,
                'error': 'You don\'t have access to this question'
            }, status=403)
        
        # Check for existing note
        try:
            note = PracticeSessionNote.objects.get(session=session, question=question)
            return JsonResponse({
                'success': True,
                'has_note': True,
                'note_text': note.note_text,
                'note_id': note.id,
                'user_access_level': get_user_access_info(request.user).get('level', 'student')
            })
        except PracticeSessionNote.DoesNotExist:
            return JsonResponse({
                'success': True,
                'has_note': False,
                'note_text': '',
                'note_id': None,
                'user_access_level': get_user_access_info(request.user).get('level', 'student')
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# MISSING FUNCTION: Get Practice Note
@content_access_required
def get_practice_note(request):
    """Get practice note for a specific question in a session"""
    question_id = request.GET.get('question_id')
    session_id = request.GET.get('session_id')
    
    if not question_id or not session_id:
        return JsonResponse({
            'success': False,
            'error': 'Missing question_id or session_id'
        }, status=400)
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        question = get_object_or_404(Question, id=question_id)
        
        # ACCESS CONTROL
        if session.student != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access'
            }, status=403)
        
        if not check_object_access(question, request.user):
            return JsonResponse({
                'success': False,
                'error': 'Question access denied'
            }, status=403)
        
        try:
            note = PracticeSessionNote.objects.get(session=session, question=question)
            return JsonResponse({
                'success': True,
                'note_text': note.note_text,
                'note_id': note.id,
                'created_at': note.created_at.isoformat() if hasattr(note, 'created_at') else None,
                'user_access_level': get_user_access_info(request.user).get('level', 'student')
            })
        except PracticeSessionNote.DoesNotExist:
            return JsonResponse({
                'success': True,
                'note_text': '',
                'note_id': None,
                'user_access_level': get_user_access_info(request.user).get('level', 'student')
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# MISSING FUNCTION: Delete Practice Note
@require_POST
@content_access_required
def delete_practice_note(request):
    """Delete a practice session note"""
    note_id = request.POST.get('note_id')
    session_id = request.POST.get('session_id')
    question_id = request.POST.get('question_id')
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        question = get_object_or_404(Question, id=question_id)
        
        # ACCESS CONTROL
        if session.student != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access'
            }, status=403)
        
        if not check_object_access(question, request.user):
            return JsonResponse({
                'success': False,
                'error': 'Question access denied'
            }, status=403)
        
        # Delete practice note
        if note_id:
            note = get_object_or_404(PracticeSessionNote, id=note_id, session=session, question=question)
            note.delete()
        else:
            # Delete by session and question
            PracticeSessionNote.objects.filter(session=session, question=question).delete()
        
        # Also delete from StudentNote if exists
        try:
            from notes.models import StudentNote
            StudentNote.objects.filter(student=request.user, question=question).delete()
        except ImportError:
            pass
        except Exception as e:
            print(f"Error deleting StudentNote: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Note deleted successfully',
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# MISSING FUNCTION: Get Practice Response
@content_access_required
def get_practice_response(request):
    """Get practice response for a specific question"""
    question_id = request.GET.get('question_id')
    session_id = request.GET.get('session_id')
    
    if not question_id or not session_id:
        return JsonResponse({
            'success': False,
            'error': 'Missing question_id or session_id'
        }, status=400)
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        question = get_object_or_404(Question, id=question_id)
        
        # ACCESS CONTROL
        if session.student != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access'
            }, status=403)
        
        if not check_object_access(question, request.user):
            return JsonResponse({
                'success': False,
                'error': 'Question access denied'
            }, status=403)
        
        try:
            response = PracticeResponse.objects.get(session=session, question=question)
            return JsonResponse({
                'success': True,
                'selected_answer': response.selected_answer,
                'is_correct': response.is_correct,
                'marked_for_review': response.marked_for_review,
                'time_spent': response.time_spent,
                'answered_at': response.answered_at.isoformat() if hasattr(response, 'answered_at') else None,
                'user_access_level': get_user_access_info(request.user).get('level', 'student')
            })
        except PracticeResponse.DoesNotExist:
            return JsonResponse({
                'success': True,
                'selected_answer': None,
                'is_correct': False,
                'marked_for_review': False,
                'time_spent': 0,
                'answered_at': None,
                'user_access_level': get_user_access_info(request.user).get('level', 'student')
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# MISSING FUNCTION: Update Practice Settings
@require_POST
@content_access_required
def update_practice_settings(request):
    """Update practice session settings during session"""
    session_id = request.POST.get('session_id')
    show_explanations = request.POST.get('show_explanations', 'false').lower() == 'true'
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        
        # ACCESS CONTROL
        if session.student != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access'
            }, status=403)
        
        # Update settings
        session.show_explanations = show_explanations
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Settings updated successfully',
            'show_explanations': session.show_explanations,
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# MISSING FUNCTION: Pause Practice Session
@require_POST
@content_access_required
def pause_practice_session(request):
    """Pause a practice session"""
    session_id = request.POST.get('session_id')
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        
        # ACCESS CONTROL
        if session.student != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access'
            }, status=403)
        
        if session.status != 'in_progress':
            return JsonResponse({
                'success': False,
                'error': 'Session is not in progress'
            }, status=400)
        
        # Update session status
        session.status = 'paused'
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Session paused successfully',
            'status': session.status,
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# MISSING FUNCTION: Resume Practice Session
@require_POST
@content_access_required
def resume_practice_session(request):
    """Resume a paused practice session"""
    session_id = request.POST.get('session_id')
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        
        # ACCESS CONTROL
        if session.student != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access'
            }, status=403)
        
        if session.status != 'paused':
            return JsonResponse({
                'success': False,
                'error': 'Session is not paused'
            }, status=400)
        
        # Update session status
        session.status = 'in_progress'
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Session resumed successfully',
            'status': session.status,
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# MISSING FUNCTION: Get Session Progress
@content_access_required
def get_session_progress(request):
    """Get progress for a practice session"""
    session_id = request.GET.get('session_id')
    
    if not session_id:
        return JsonResponse({
            'success': False,
            'error': 'Missing session_id'
        }, status=400)
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        
        # ACCESS CONTROL
        if session.student != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access'
            }, status=403)
        
        # Get responses with access control
        responses = session.responses.all()
        accessible_responses = []
        
        for response in responses:
            if check_object_access(response.question, request.user):
                accessible_responses.append(response)
        
        total_questions = session.total_questions
        answered_questions = len([r for r in accessible_responses if r.selected_answer])
        correct_answers = len([r for r in accessible_responses if r.is_correct])
        marked_for_review = len([r for r in accessible_responses if r.marked_for_review])
        
        # Calculate time spent
        time_spent = 0
        if session.started_at:
            time_spent = int((timezone.now() - session.started_at).total_seconds())
        
        return JsonResponse({
            'success': True,
            'total_questions': total_questions,
            'answered_questions': answered_questions,
            'correct_answers': correct_answers,
            'marked_for_review': marked_for_review,
            'time_spent': time_spent,
            'status': session.status,
            'accessible_questions': len(accessible_responses),
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# PERFORMANCE OPTIMIZATION VIEWS

def handle_practice_error(request, error_type, error_message):
    """Centralized error handling for practice sessions"""
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
    
    return render(request, 'managemodule/practice_error.html', error_context)


# PERFORMANCE OPTIMIZATION VIEWS

@content_access_required
def get_cached_hierarchy_stats(request):
    """Cached version of hierarchy statistics for better performance"""
    from django.core.cache import cache
    
    user = request.user
    user_access = get_user_access_info(user)
    
    # Create cache key based on user access level
    cache_key = f"hierarchy_stats_{user_access.get('level', 'guest')}_{user_access.get('filter_params', {}).get('degree', 'all')}_{user_access.get('filter_params', {}).get('year', 'all')}"
    
    # Try to get from cache first
    cached_stats = cache.get(cache_key)
    if cached_stats:
        return JsonResponse(cached_stats)
    
    # Calculate fresh stats with access control
    questions = Question.objects.filter(question_type='MCQ')
    questions = apply_user_access_filter(questions, user)
    
    stats = {
        'total_questions': questions.count(),
        'blocks': questions.values('block').distinct().count(),
        'modules': questions.values('module').distinct().count(),
        'subjects': questions.values('subject').distinct().count(),
        'topics': questions.values('topic').distinct().count(),
        'difficulty_breakdown': {
            'easy': questions.filter(difficulty='Easy').count(),
            'medium': questions.filter(difficulty='Medium').count(),
            'hard': questions.filter(difficulty='Hard').count(),
        },
        'user_access_level': user_access.get('level', 'student'),
        'filter_applied': user_access.get('level') == 'student'
    }
    
    # Cache for 15 minutes
    cache.set(cache_key, stats, 900)
    
    return JsonResponse(stats)