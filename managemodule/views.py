# managemodule/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Max
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from questionbank.models import Question
from .models import PracticeSession, PracticeResponse, StudentProgress
import random

def managemodule(request):
    """Main hierarchy view with search and filtering"""
    # Get search and filter parameters
    query = request.GET.get('q', '')
    filter_degree = request.GET.get('degree', '')
    filter_year = request.GET.get('year', '')
    filter_block = request.GET.get('filter_block', '')
    
    questions = Question.objects.all()
    
    # Apply filters
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
                
                if topic_list:  # Only add subject if it has topics
                    subject_list.append({
                        'name': subject_name,
                        'topics': topic_list,
                        'topics_count': len(topic_list),
                    })
            
            if subject_list:  # Only add module if it has subjects
                module_list.append({
                    'name': module_name,
                    'degree': degree,
                    'year': year,
                    'subjects': subject_list,
                    'subjects_count': len(subject_list),
                    'topics_count': sum(len(s['topics']) for s in subject_list),
                })
        
        if module_list:  # Only add block if it has modules
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
        
        # Count unique images
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
        
        from django.conf import settings
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
    paginator = Paginator(questions, 10)  # Show 10 questions per page
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


def get_topic_image_count(request):
    """API endpoint to get image count for a specific topic"""
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    
    # Get questions for this topic
    questions = Question.objects.filter(
        block=block,
        module=module,
        subject=subject,
        topic=topic,
        degree=degree,
        year=year
    )
    
    # Count unique images
    image_count = questions.exclude(image__isnull=True).exclude(image__exact='').values('image').distinct().count()
    
    return JsonResponse({'image_count': image_count})


# NEW STUDENT PRACTICE VIEWS

@login_required
def student_practice_modules(request):
    """Student view for practice modules hierarchy"""
    user = request.user
    
    # Get search and filter parameters
    query = request.GET.get('q', '')
    filter_degree = request.GET.get('degree', '')
    filter_year = request.GET.get('year', '')
    filter_block = request.GET.get('filter_block', '')
    
    questions = Question.objects.filter(question_type='MCQ')  # Only MCQ for practice
    
    # Apply filters
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
                        accuracy = progress.overall_accuracy
                        sessions_count = progress.total_sessions
                    except StudentProgress.DoesNotExist:
                        mastery_level = "Not Started"
                        accuracy = 0
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
                
                if topic_list:  # Only add subject if it has topics
                    subject_list.append({
                        'name': subject_name,
                        'topics': topic_list,
                        'topics_count': len(topic_list),
                    })
            
            if subject_list:  # Only add module if it has subjects
                module_list.append({
                    'name': module_name,
                    'degree': degree,
                    'year': year,
                    'subjects': subject_list,
                    'subjects_count': len(subject_list),
                    'topics_count': sum(len(s['topics']) for s in subject_list),
                })
        
        if module_list:  # Only add block if it has modules
            block_module_map.append({
                'block': block_name,
                'modules': module_list,
            })

    # Calculate overall stats for the student
    user_progress = StudentProgress.objects.filter(student=user)
    total_topics_practiced = user_progress.count()
    average_accuracy = user_progress.aggregate(avg=Avg('best_accuracy'))['avg'] or 0
    total_sessions = user_progress.aggregate(total=Count('total_sessions'))['total'] or 0

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


@login_required
def start_practice_session(request):
    """Start a new practice session for a topic - Enhanced student version"""
    if request.method == 'POST':
        # Get topic parameters
        degree = request.POST.get('degree')
        year = request.POST.get('year')
        block = request.POST.get('block')
        module = request.POST.get('module')
        subject = request.POST.get('subject')
        topic = request.POST.get('topic')
        
        # Get session configuration
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
            return redirect(f"{request.path}?{request.GET.urlencode()}")
        
        # Create practice session
        session = PracticeSession.objects.create(
            student=request.user,
            degree=degree,
            year=year,
            block=block,
            module=module,
            subject=subject,
            topic=topic,
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
        best_accuracy = progress.best_accuracy
        last_practiced = progress.last_practiced
    except StudentProgress.DoesNotExist:
        previous_sessions = 0
        best_accuracy = 0
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


@login_required
def get_question_count_by_difficulty(request):
    """AJAX endpoint to get question count based on difficulty selection"""
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
def practice_session(request, session_id):
    """Practice session interface"""
    session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
    
    if session.status != 'in_progress':
        return redirect('practice_session_result', session_id=session.id)
    
    # Get questions for this session
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
    
    # Process questions with image support (similar to mock test)
    processed_questions = []
    for question in questions:
        question_data = {
            'id': question.id,
            'order': len(processed_questions) + 1,
            'text': question.question_text,
            'options': {},
            'correct_answer': question.correct_answer,
            'explanation': question.explanation,
            'difficulty': question.difficulty,
            'has_image': bool(question.image),
            'image_url': None,
            'image_filename': question.image if question.image else None
        }
        
        # Handle image URL generation (reuse from mock test)
        if question.image:
            try:
                from mocktest.views import get_question_image_url
                image_url, actual_filename = get_question_image_url(question)
                if image_url:
                    question_data['image_url'] = image_url
                    question_data['image_filename'] = actual_filename
            except:
                pass
        
        # Add options
        if question.option_a:
            question_data['options']['A'] = question.option_a
        if question.option_b:
            question_data['options']['B'] = question.option_b
        if question.option_c:
            question_data['options']['C'] = question.option_c
        if question.option_d:
            question_data['options']['D'] = question.option_d
        if question.option_e:
            question_data['options']['E'] = question.option_e
        
        processed_questions.append(question_data)
    
    context = {
        'session': session,
        'questions': processed_questions,
        'total_questions': len(processed_questions),
    }
    
    return render(request, 'managemodule/practice_session.html', context)


@require_POST
@login_required
def submit_practice_answer(request):
    """Submit answer for practice question"""
    session_id = request.POST.get('session_id')
    question_id = request.POST.get('question_id')
    answer = request.POST.get('answer')
    time_spent = int(request.POST.get('time_spent', 0))
    
    session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
    question = get_object_or_404(Question, id=question_id)
    
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
    
    # Return response with explanation
    return JsonResponse({
        'success': True,
        'is_correct': is_correct,
        'correct_answer': question.correct_answer,
        'explanation': question.explanation if session.show_explanations else None,
        'selected_answer': answer
    })


@require_POST
@login_required
def complete_practice_session(request):
    """Complete the practice session"""
    session_id = request.POST.get('session_id')
    total_time = int(request.POST.get('total_time', 0))
    
    session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
    
    # Update session
    session.status = 'completed'
    session.completed_at = timezone.now()
    session.time_spent = total_time
    
    # Calculate results
    responses = session.responses.all()
    session.questions_attempted = responses.count()
    session.correct_answers = responses.filter(is_correct=True).count()
    
    session.save()
    
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
        'accuracy': session.accuracy,
        'correct_answers': session.correct_answers,
        'total_questions': session.questions_attempted
    })


@login_required
def practice_session_result(request, session_id):
    """Show practice session results"""
    session = get_object_or_404(PracticeSession, id=session_id, student=request.user)
    
    if session.status == 'in_progress':
        return redirect('practice_session', session_id=session.id)
    
    # Get all responses with questions
    responses = session.responses.all().select_related('question').order_by('answered_at')
    
    # Calculate additional statistics
    total_questions = session.questions_attempted
    correct_answers = session.correct_answers
    incorrect_answers = total_questions - correct_answers
    
    # Difficulty breakdown
    difficulty_stats = {}
    for response in responses:
        difficulty = response.question.difficulty
        if difficulty not in difficulty_stats:
            difficulty_stats[difficulty] = {'total': 0, 'correct': 0}
        difficulty_stats[difficulty]['total'] += 1
        if response.is_correct:
            difficulty_stats[difficulty]['correct'] += 1
    
    context = {
        'session': session,
        'responses': responses,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,
        'difficulty_stats': difficulty_stats,
    }
    
    return render(request, 'managemodule/practice_session_result.html', context)


@login_required
def student_practice_progress(request):
    """Student overall practice progress"""
    user = request.user
    
    # Get all student progress
    progress_list = StudentProgress.objects.filter(student=user).order_by('-last_practiced')
    
    # Calculate overall statistics
    total_topics = progress_list.count()
    total_sessions = sum(p.total_sessions for p in progress_list)
    total_questions = sum(p.total_questions_attempted for p in progress_list)
    total_correct = sum(p.total_correct_answers for p in progress_list)
    overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
    
    # Recent sessions
    recent_sessions = PracticeSession.objects.filter(
        student=user,
        status='completed'
    ).order_by('-completed_at')[:10]
    
    # Best performing topics
    best_topics = progress_list.filter(total_questions_attempted__gte=5).order_by('-best_accuracy')[:5]
    
    # Topics needing practice
    needs_practice = progress_list.filter(
        total_questions_attempted__gte=5,
        best_accuracy__lt=70
    ).order_by('best_accuracy')[:5]
    
    context = {
        'progress_list': progress_list,
        'total_topics': total_topics,
        'total_sessions': total_sessions,
        'total_questions': total_questions,
        'overall_accuracy': round(overall_accuracy, 1),
        'recent_sessions': recent_sessions,
        'best_topics': best_topics,
        'needs_practice': needs_practice,
    }
    
    return render(request, 'managemodule/student_practice_progress.html', context)