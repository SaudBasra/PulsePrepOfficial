
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
    PracticeSessionNote  # Make sure this is imported!
)
import random
import os
import csv
from datetime import datetime, timedelta

# Import your access control decorator
from user_management.decorators import auto_filter_content



@auto_filter_content
def practice_session(request, session_id):
    """Fixed practice session interface with proper MCQ display and navigation"""
    session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
    
    if session.status != 'in_progress':
        return redirect('practice_session_result', session_id=session.id)
    
    # Get questions for this session (automatically filtered by access control)
    questions_query = Question.objects.filter(
        question_type='MCQ',
        degree=session.degree,
        year=session.year,
        block=session.block,
        module=session.module,
        subject=session.subject,
        topic=session.topic
    )
    
    if session.difficulty_filter:
        questions_query = questions_query.filter(difficulty=session.difficulty_filter)
    
    # Get random questions for the session
    questions = list(questions_query.order_by('?')[:session.total_questions])
    
    if session.randomize_questions:
        random.shuffle(questions)
    
    # Process questions with proper data structure
    processed_questions = []
    for idx, question in enumerate(questions):
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
            'has_image': bool(question.image),
            'image_url': None,
            'image_filename': question.image if question.image else None,
            'degree': question.degree,
            'year': question.year,
            'block': question.block,
            'module': question.module,
            'subject': question.subject,
            'topic': question.topic
        }
        
        # Handle image URL generation
        if question.image:
            try:
                image_url, actual_filename = get_question_image_url(question)
                if image_url:
                    question_data['image_url'] = image_url
                    question_data['image_filename'] = actual_filename
            except Exception as e:
                print(f"Error processing image for question {question.id}: {str(e)}")
        
        processed_questions.append(question_data)
    
    context = {
        'session': session,
        'questions': processed_questions,
        'total_questions': len(processed_questions),
    }
    
    return render(request, 'managemodule/practice_session.html', context)


def get_question_image_url(question):
    """Fixed function to get image URL for a question"""
    if not question.image:
        return None, None
    
    try:
        # Get the image filename
        image_filename = question.image.strip()
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
        print(f"Error loading image for question {question.id}: {str(e)}")
        return None, getattr(question, 'image', None)


@require_POST
@login_required
def submit_practice_answer(request):
    """Fixed answer submission with proper validation"""
    session_id = request.POST.get('session_id')
    question_id = request.POST.get('question_id')
    answer = request.POST.get('answer')
    time_spent = int(request.POST.get('time_spent', 0))
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        question = get_object_or_404(Question, id=question_id)
        
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
            'practice_mode': session.practice_mode
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_POST
@login_required
def complete_practice_session(request):
    """Fixed session completion with proper accuracy calculation"""
    session_id = request.POST.get('session_id')
    total_time = int(request.POST.get('total_time', 0))
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        
        # Calculate results with proper decimal handling
        responses = session.responses.all()
        questions_attempted = responses.count()
        correct_answers = responses.filter(is_correct=True).count()
        
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
        
        # Update or create student progress
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
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'accuracy': float(session.accuracy),
            'correct_answers': session.correct_answers,
            'total_questions': session.questions_attempted,
            'redirect_url': f'/managemodule/student/session/{session.id}/result/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@auto_filter_content
def start_practice_session(request):
    """Fixed practice session configuration with proper validation"""
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
        
        # Validate that topic has questions
        questions_query = Question.objects.filter(
            question_type='MCQ',
            degree=degree,
            year=year,
            block=block,
            module=module,
            subject=subject,
            topic=topic
        )
        
        if difficulty_filter:
            questions_query = questions_query.filter(difficulty=difficulty_filter)
        
        available_count = questions_query.count()
        if available_count < total_questions:
            messages.error(request, f"Only {available_count} questions available for this topic with selected filters. Please adjust your selection.")
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
    
    # GET request - show practice configuration form
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    
    # Get questions count for each difficulty
    base_query = Question.objects.filter(
        question_type='MCQ',
        degree=degree,
        year=year,
        block=block,
        module=module,
        subject=subject,
        topic=topic
    )
    
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
    }
    
    return render(request, 'managemodule/start_practice_session.html', context)


@require_POST
@login_required
def mark_question_for_review(request):
    """Fixed mark for review functionality"""
    session_id = request.POST.get('session_id')
    question_id = request.POST.get('question_id')
    marked = request.POST.get('marked', 'false').lower() == 'true'
    
    try:
        session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
        question = get_object_or_404(Question, id=question_id)
        
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
            'question_id': question_id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@auto_filter_content
def get_question_count_by_difficulty(request):
    """Fixed AJAX endpoint to get question count based on difficulty selection"""
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
    
    if difficulty:
        query = query.filter(difficulty=difficulty)
    
    count = query.count()
    
    return JsonResponse({
        'count': count,
        'difficulty': difficulty or 'all'
    })


@login_required
def practice_session_result(request, session_id):
    """Fixed practice session results display"""
    session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
    
    if session.status == 'in_progress':
        return redirect('practice_session', session_id=session.id)
    
    # Get all responses with questions
    responses = session.responses.all().select_related('question').order_by('answered_at')
    
    # Process responses to include image data
    processed_responses = []
    for response in responses:
        response_data = {
            'response': response,
            'question': response.question,
            'is_correct': response.is_correct,
            'selected_answer': response.selected_answer,
            'time_spent': response.time_spent,
            'image_url': None,
            'image_filename': None
        }
        
        # Get image data for results page
        if response.question.image:
            try:
                image_url, actual_filename = get_question_image_url(response.question)
                if image_url:
                    response_data['image_url'] = image_url
                    response_data['image_filename'] = actual_filename
            except Exception as e:
                print(f"Error processing image for question {response.question.id}: {str(e)}")
        
        processed_responses.append(response_data)
    
    # Calculate additional statistics
    total_questions = session.questions_attempted
    correct_answers = session.correct_answers
    incorrect_answers = total_questions - correct_answers
    
    # Difficulty breakdown
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
        'responses': processed_responses,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,
        'difficulty_stats': difficulty_stats,
    }
    
    return render(request, 'managemodule/practice_session_result.html', context)


# Add other existing views here unchanged...
@auto_filter_content
def managemodule(request):
    """Main hierarchy view with search and filtering - Auto-filtered by access control"""
    # Get search and filter parameters
    query = request.GET.get('q', '')
    filter_degree = request.GET.get('degree', '')
    filter_year = request.GET.get('year', '')
    filter_block = request.GET.get('filter_block', '')
    
    # This will automatically filter by user's degree/year for students
    questions = Question.objects.all()
    
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

    # Get unique blocks for filter dropdown
    all_blocks = Question.objects.values('block').distinct().order_by('block')

    # Group modules by block
    block_module_map = []
    for block in all_blocks:
        block_name = block['block']
        
        # Filter modules by current filters
        block_questions = questions.filter(block=block_name)
        if not block_questions.exists():
            continue
            
        modules = block_questions.values('module', 'degree', 'year').distinct().order_by('module', 'degree', 'year')
        module_list = []
        
        for module in modules:
            module_name = module['module']
            degree = module['degree']
            year = module['year']
            
            # Subjects for this module
            module_questions = block_questions.filter(
                module=module_name, degree=degree, year=year
            )
            subjects = module_questions.values('subject').distinct().order_by('subject')
            subject_list = []
            
            for subject in subjects:
                subject_name = subject['subject']
                
                # Topics for this subject
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

    # Calculate statistics
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
    }
    return render(request, 'managemodule/managemodule.html', context)


@auto_filter_content
def topic_questions(request):
    """Display questions for a specific topic - Enhanced with image support"""
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
        # Return image count for this topic
        questions = Question.objects.filter(
            block=block,
            module=module,
            subject=subject,
            topic=topic,
            degree=degree,
            year=year
        )
        
        image_count = questions.exclude(image__isnull=True).exclude(image__exact='').values('image').distinct().count()
        
        return JsonResponse({'image_count': image_count})
    
    elif ajax_type == 'images':
        # Return images for this topic
        questions = Question.objects.filter(
            block=block,
            module=module,
            subject=subject,
            topic=topic,
            degree=degree,
            year=year
        ).exclude(image__isnull=True).exclude(image__exact='')
        
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
            'media_url': settings.MEDIA_URL
        })
    
    # Regular page request
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
    
    # Enhanced context with image statistics
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
    }
    
    return render(request, 'managemodule/topic_questions.html', context)


@auto_filter_content
def student_practice_modules(request):
    """Student view for practice modules hierarchy"""
    user = request.user
    
    # Get search and filter parameters
    query = request.GET.get('q', '')
    filter_degree = request.GET.get('degree', '')
    filter_year = request.GET.get('year', '')
    filter_block = request.GET.get('filter_block', '')
    
    # Only MCQ for practice
    questions = Question.objects.filter(question_type='MCQ')
    
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

    # Get unique blocks
    all_blocks = Question.objects.filter(question_type='MCQ').values('block').distinct().order_by('block')

    # Group modules by block with progress information
    block_module_map = []
    for block in all_blocks:
        block_name = block['block']
        
        # Filter modules by current filters
        block_questions = questions.filter(block=block_name)
        if not block_questions.exists():
            continue
            
        modules = block_questions.values('module', 'degree', 'year').distinct().order_by('module', 'degree', 'year')
        module_list = []
        
        for module in modules:
            module_name = module['module']
            degree = module['degree']
            year = module['year']
            
            # Subjects for this module
            module_questions = block_questions.filter(
                module=module_name, degree=degree, year=year
            )
            subjects = module_questions.values('subject').distinct().order_by('subject')
            subject_list = []
            
            for subject in subjects:
                subject_name = subject['subject']
                
                # Topics for this subject
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

    # Calculate overall stats for the student
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
    }
    return render(request, 'managemodule/student_practice_modules.html', context)


@auto_filter_content
def student_practice_progress(request):
    """Student practice progress with pagination and filtering"""
    user = request.user
    
    try:
        # Base queryset
        progress_queryset = StudentProgress.objects.filter(student=user).select_related('student')
        
        # Apply filters
        mastery_filter = request.GET.get('mastery')
        subject_filter = request.GET.get('subject')
        
        if mastery_filter and mastery_filter != 'all':
            progress_queryset = progress_queryset.filter(mastery_level=mastery_filter)
        
        if subject_filter and subject_filter != 'all':
            progress_queryset = progress_queryset.filter(subject=subject_filter)
        
        # Order by last practiced
        progress_queryset = progress_queryset.order_by('-last_practiced', '-best_accuracy')
        
        # Paginate results
        paginator = Paginator(progress_queryset, 10)
        page_number = request.GET.get('page')
        progress_list = paginator.get_page(page_number)
        
        # Calculate overall statistics
        all_progress = StudentProgress.objects.filter(student=user)
        
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
        
        # Recent sessions
        recent_sessions = []
        try:
            recent_sessions = PracticeSession.objects.filter(
                student=user,
                status='completed'
            ).order_by('-completed_at')[:10]
        except:
            recent_sessions = []
        
        # Best performing topics
        best_topics = all_progress.filter(
            total_questions_attempted__gte=5
        ).order_by('-best_accuracy')[:5]
        
        # Topics needing practice
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
        }
        
    except Exception as e:
        print(f"Error in student_practice_progress: {e}")
        
        # Minimal safe context
        progress_queryset = StudentProgress.objects.filter(student=user).order_by('-last_practiced')
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
        }
    
    return render(request, 'managemodule/student_practice_progress.html', context)
# SOLUTION 1: Update your managemodule/views.py save_practice_note function
# Replace your existing save_practice_note function with this unified version
# Replace your save_practice_note function in managemodule/views.py with this enhanced version
# This version generates better titles based on question content and context

@require_POST
@login_required
def save_practice_note(request):
    """Enhanced save practice session note with smart title generation"""
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
        
        # Verify question exists
        question = get_object_or_404(Question, id=question_id)
        print(f"✓ Question found: Q{question.id}")
        
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
                    'also_saved_to_notes_app': 'student_note' in locals()
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
                        'action': 'deleted'
                    }
                })
            except PracticeSessionNote.DoesNotExist:
                print("! No existing practice note to delete")
                return JsonResponse({
                    'success': True,
                    'message': 'No note to save',
                    'has_note': False
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


def check_question_note(question_text):
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

