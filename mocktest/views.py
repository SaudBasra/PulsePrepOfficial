# mocktest/views.py - Complete Enhanced Version
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Max, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import calendar
from decimal import Decimal



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Avg, Max
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Max, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import calendar
import json
import random

from .models import MockTest, TestQuestion, TestAttempt, TestResponse
from .forms import MockTestForm
from questionbank.models import Question


def mocktest_list(request):
    """List all mock tests with filtering"""
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    degree_filter = request.GET.get('degree', '')
    
    tests = MockTest.objects.all()
    
    if query:
        tests = tests.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    
    if status_filter:
        tests = tests.filter(status=status_filter)
    
    if degree_filter:
        tests = tests.filter(degree=degree_filter)
    
    # Update status based on datetime
    for test in tests:
        now = timezone.now()
        if test.status == 'scheduled' and now >= test.start_datetime:
            test.status = 'live'
            test.save()
        elif test.status == 'live' and now > test.end_datetime:
            test.status = 'completed'
            test.save()
    
    paginator = Paginator(tests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'degree_filter': degree_filter,
    }
    
    return render(request, 'mocktest/mocktest_list.html', context)


@login_required
def create_test(request):
    """Enhanced create/edit mock test with availability checking"""
    test_id = request.GET.get('id')
    
    if test_id:
        test = get_object_or_404(MockTest, id=test_id)
        form = MockTestForm(instance=test)
        is_edit = True
    else:
        form = MockTestForm()
        test = None
        is_edit = False
    
    if request.method == 'POST':
        if test:
            form = MockTestForm(request.POST, instance=test)
        else:
            form = MockTestForm(request.POST)
        
        if form.is_valid():
            test = form.save(commit=False)
            if not test.created_by_id:
                test.created_by = request.user if request.user.is_authenticated else None
            test.save()
            
            # Handle question selection
            if test.selection_type == 'random':
                actual_count = generate_random_questions(test)
                if actual_count < test.total_questions:
                    messages.warning(
                        request, 
                        f"Test created with {actual_count} questions instead of {test.total_questions} "
                        f"due to availability constraints."
                    )
                else:
                    messages.success(request, f"Test created successfully with {actual_count} questions!")
            else:
                # Manual selection
                selected_questions = request.POST.get('selected_questions')
                if selected_questions:
                    question_ids = json.loads(selected_questions)
                    
                    # Clear existing questions
                    test.questions.clear()
                    
                    # Add selected questions
                    for order, q_id in enumerate(question_ids, 1):
                        try:
                            question = Question.objects.get(id=q_id)
                            TestQuestion.objects.create(
                                mock_test=test,
                                question=question,
                                question_order=order
                            )
                        except Question.DoesNotExist:
                            continue
                    
                    # Update total questions
                    actual_count = test.testquestion_set.count()
                    test.total_questions = actual_count
                    test.save()
                    
                    messages.success(request, f"Test {'updated' if is_edit else 'created'} successfully with {actual_count} questions!")
                else:
                    messages.error(request, "No questions selected for manual test creation.")
                    return render(request, 'mocktest/create_test.html', {
                        'form': form,
                        'test': test,
                        'is_edit': is_edit,
                        'blocks': Question.objects.values('block').distinct().order_by('block'),
                        'modules': Question.objects.values('module').distinct().order_by('module'),
                        'subjects': Question.objects.values('subject').distinct().order_by('subject'),
                        'topics': Question.objects.values('topic').distinct().order_by('topic'),
                    })
            
            return redirect('mocktest_list')
    
    # Get hierarchy data for dropdowns
    blocks = Question.objects.values('block').distinct().order_by('block')
    modules = Question.objects.values('module').distinct().order_by('module')
    subjects = Question.objects.values('subject').distinct().order_by('subject')
    topics = Question.objects.values('topic').distinct().order_by('topic')
    
    context = {
        'form': form,
        'test': test,
        'is_edit': is_edit,
        'blocks': blocks,
        'modules': modules,
        'subjects': subjects,
        'topics': topics,
    }    
    return render(request, 'mocktest/create_test.html', context)


def generate_random_questions(test):
    """Enhanced random question generation with availability checking"""
    # Clear existing questions
    test.questions.clear()
    
    # Build query based on test filters
    query = Question.objects.filter(question_type='MCQ')
    
    if test.degree:
        query = query.filter(degree=test.degree)
    if test.year:
        query = query.filter(year=test.year)
    if test.block:
        query = query.filter(block=test.block)
    if test.module:
        query = query.filter(module=test.module)
    if test.subject:
        query = query.filter(subject=test.subject)
    if test.topic:
        query = query.filter(topic=test.topic)
    
    # Calculate questions per difficulty
    total = test.total_questions
    easy_count = int(total * test.easy_percentage / 100)
    medium_count = int(total * test.medium_percentage / 100)
    hard_count = total - easy_count - medium_count  # Remainder goes to hard
    
    # Check availability
    available_easy = query.filter(difficulty='Easy').count()
    available_medium = query.filter(difficulty='Medium').count()
    available_hard = query.filter(difficulty='Hard').count()
    
    # Adjust counts based on availability
    if easy_count > available_easy:
        overflow = easy_count - available_easy
        easy_count = available_easy
        medium_count += overflow // 2
        hard_count += overflow // 2 + overflow % 2
    
    if medium_count > available_medium:
        overflow = medium_count - available_medium
        medium_count = available_medium
        hard_count += overflow
    
    if hard_count > available_hard:
        hard_count = available_hard
    
    # Get questions by difficulty
    easy_questions = list(query.filter(difficulty='Easy').order_by('?')[:easy_count])
    medium_questions = list(query.filter(difficulty='Medium').order_by('?')[:medium_count])
    hard_questions = list(query.filter(difficulty='Hard').order_by('?')[:hard_count])
    
    # Combine all questions
    all_questions = easy_questions + medium_questions + hard_questions
    
    # If not enough questions, get more from any difficulty
    if len(all_questions) < total:
        remaining = total - len(all_questions)
        exclude_ids = [q.id for q in all_questions]
        extra_questions = list(query.exclude(id__in=exclude_ids).order_by('?')[:remaining])
        all_questions.extend(extra_questions)
    
    # Shuffle if randomize is enabled
    if test.randomize_questions:
        random.shuffle(all_questions)
    
    # Add questions to test
    for order, question in enumerate(all_questions, 1):
        TestQuestion.objects.create(
            mock_test=test,
            question=question,
            question_order=order
        )
    
    # Update actual total questions
    test.total_questions = len(all_questions)
    test.save()
    
    return len(all_questions)


@require_POST
def delete_test(request, test_id):
    """Delete a mock test"""
    test = get_object_or_404(MockTest, id=test_id)
    test.delete()
    messages.success(request, "Test deleted successfully!")
    return JsonResponse({'success': True})


def get_filtered_questions(request):
    """Get questions based on filters for manual selection with pagination"""
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 100))
    
    questions = Question.objects.filter(question_type='MCQ')
    
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
    
    # Get total count before pagination
    total_count = questions.count()
    
    # Apply pagination
    paginator = Paginator(questions, per_page)
    page_obj = paginator.get_page(page)
    
    # Prepare data for JSON response
    question_list = []
    for q in page_obj:
        question_list.append({
            'id': q.id,
            'text': q.question_text[:100] + '...' if len(q.question_text) > 100 else q.question_text,
            'difficulty': q.difficulty,
            'block': q.block,
            'module': q.module,
            'subject': q.subject,
            'topic': q.topic,
        })
    
    return JsonResponse({
        'questions': question_list,
        'total_count': total_count,
        'current_page': page,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })


def check_question_availability(request):
    """Check availability of questions for random selection"""
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    
    # Build base query
    query = Question.objects.filter(question_type='MCQ')
    
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
    if topic:
        query = query.filter(topic=topic)
    
    # Count by difficulty
    easy_count = query.filter(difficulty='Easy').count()
    medium_count = query.filter(difficulty='Medium').count()
    hard_count = query.filter(difficulty='Hard').count()
    total_available = easy_count + medium_count + hard_count
    
    return JsonResponse({
        'total_available': total_available,
        'easy': easy_count,
        'medium': medium_count,
        'hard': hard_count,
    })


@require_POST
def save_manual_questions(request):
    """Save manually selected questions"""
    test_id = request.POST.get('test_id')
    question_ids = json.loads(request.POST.get('question_ids', '[]'))
    
    test = get_object_or_404(MockTest, id=test_id)
    
    # Clear existing questions
    test.questions.clear()
    
    # Add selected questions
    for order, q_id in enumerate(question_ids, 1):
        question = Question.objects.get(id=q_id)
        TestQuestion.objects.create(
            mock_test=test,
            question=question,
            question_order=order
        )
    
    # Update total questions
    test.total_questions = len(question_ids)
    test.save()
    
    return JsonResponse({'success': True, 'message': f'{len(question_ids)} questions added to test'})


def preview_test(request, test_id):
    """Preview test before publishing"""
    test = get_object_or_404(MockTest, id=test_id)
    test_questions = test.testquestion_set.all().select_related('question')
    
    context = {
        'test': test,
        'test_questions': test_questions,
        'question_count': test_questions.count(),
    }
    
    return render(request, 'mocktest/preview_test.html', context)


def get_hierarchy_data(request):
    """Enhanced hierarchy data endpoint"""
    field = request.GET.get('field')
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    
    query = Question.objects.all()
    
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
    
    return JsonResponse({'data': data})


# STUDENT VIEWS
@login_required
def student_mock_tests(request):
    """List available mock tests for students"""
    user = request.user
    now = timezone.now()
    
    # Update test statuses first
    all_tests_for_update = MockTest.objects.all()
    for test in all_tests_for_update:
        if test.status == 'scheduled' and now >= test.start_datetime:
            test.status = 'live'
            test.save()
        elif test.status == 'live' and now > test.end_datetime:
            test.status = 'completed'
            test.save()
    
    # Get active tests
    tests = MockTest.objects.filter(status='live')
    
    # Get user's attempts
    user_attempts = TestAttempt.objects.filter(student=user).values('mock_test_id', 'status').order_by('-started_at')
    
    # Create a dict of test attempts
    attempt_status = {}
    attempt_count = {}
    for attempt in user_attempts:
        test_id = attempt['mock_test_id']
        if test_id not in attempt_count:
            attempt_count[test_id] = 0
        if attempt['status'] == 'completed':
            attempt_count[test_id] += 1
            if test_id not in attempt_status:
                attempt_status[test_id] = 'completed'
    
    # Add attempt info to tests
    for test in tests:
        test.user_attempts = attempt_count.get(test.id, 0)
        test.can_attempt = test.user_attempts < test.max_attempts
        test.attempt_status = attempt_status.get(test.id, 'not_started')
    
    # Get upcoming tests
    upcoming_tests = MockTest.objects.filter(
        start_datetime__gt=now
    ).order_by('start_datetime')[:5]
    
    context = {
        'active_tests': tests,
        'upcoming_tests': upcoming_tests,
        'user': user,
    }
    
    return render(request, 'mocktest/student_mock_tests.html', context)


def get_question_image_url(question):
    """
    Helper function to get the correct image URL for a question
    Handles various image filename formats and matches with QuestionImage model
    """
    if not question.image:
        return None, None
    
    try:
        from manageimage.models import QuestionImage
        
        image_filename = question.image.strip()
        if not image_filename:
            return None, None
        
        # Strategy 1: Exact filename match
        try:
            image_obj = QuestionImage.objects.get(filename=image_filename)
            if image_obj.image:
                return image_obj.image.url, image_obj.filename
        except QuestionImage.DoesNotExist:
            pass
        
        # Strategy 2: Match without extension
        filename_no_ext = image_filename.rsplit('.', 1)[0] if '.' in image_filename else image_filename
        
        # Try to find by filename containing the base name
        possible_matches = QuestionImage.objects.filter(
            filename__icontains=filename_no_ext
        )
        
        for match in possible_matches:
            # Check if it's a close match
            match_no_ext = match.filename.rsplit('.', 1)[0] if '.' in match.filename else match.filename
            if match_no_ext.lower() == filename_no_ext.lower():
                if match.image:
                    return match.image.url, match.filename
        
        # Strategy 3: Partial matching (less strict)
        if len(filename_no_ext) > 3:  # Only for reasonable length names
            partial_matches = QuestionImage.objects.filter(
                filename__icontains=filename_no_ext[:min(len(filename_no_ext), 10)]
            )
            
            for match in partial_matches:
                # Additional similarity check could be added here
                if match.image:
                    return match.image.url, match.filename
        
        # Strategy 4: Try adding common extensions
        common_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        for ext in common_extensions:
            try:
                test_filename = filename_no_ext + ext
                image_obj = QuestionImage.objects.get(filename=test_filename)
                if image_obj.image:
                    return image_obj.image.url, image_obj.filename
            except QuestionImage.DoesNotExist:
                continue
        
    except ImportError:
        # manageimage app not available
        pass
    except Exception as e:
        print(f"Error loading image for question {question.id}: {str(e)}")
    
    return None, image_filename


@login_required
def take_test(request, test_id):
    """Student takes the test - Updated with improved image support"""
    test = get_object_or_404(MockTest, id=test_id)
    student = request.user
    
    print(f"DEBUG: User {student} trying to take test: {test.title}")
    print(f"DEBUG: Test status: {test.status}")
    print(f"DEBUG: Test start time: {test.start_datetime}")
    print(f"DEBUG: Test end time: {test.end_datetime}")
    print(f"DEBUG: Current time: {timezone.now()}")
    
    # Check if test is active - simplified check
    now = timezone.now()
    if test.status != 'live':
        messages.error(request, f"This test is not currently available. Status: {test.status}")
        print(f"DEBUG: Test blocked - status is {test.status}, not 'live'")
        return redirect('student_mock_tests')
    
    # Optional: Check time bounds
    if now < test.start_datetime:
        messages.error(request, "This test has not started yet.")
        print(f"DEBUG: Test blocked - hasn't started yet")
        return redirect('student_mock_tests')
    
    if now > test.end_datetime:
        messages.error(request, "This test has already ended.")
        print(f"DEBUG: Test blocked - already ended")
        return redirect('student_mock_tests')
    
    # Check attempt limit
    existing_attempts = TestAttempt.objects.filter(
        student=student, 
        mock_test=test,
        status='completed'
    ).count()
    
    print(f"DEBUG: User has {existing_attempts} completed attempts out of {test.max_attempts} allowed")
    
    if existing_attempts >= test.max_attempts:
        messages.error(request, f"You have reached the maximum attempts ({test.max_attempts}) for this test.")
        print(f"DEBUG: Test blocked - max attempts reached")
        return redirect('student_mock_tests')
    
    # Get or create current attempt
    current_attempt = TestAttempt.objects.filter(
        student=student,
        mock_test=test,
        status='in_progress'
    ).first()
    
    if not current_attempt:
        # Create new attempt
        current_attempt = TestAttempt.objects.create(
            student=student,
            mock_test=test,
            status='in_progress',
            started_at=timezone.now()
        )
        print(f"DEBUG: Created new attempt with ID: {current_attempt.id}")
    else:
        print(f"DEBUG: Found existing attempt with ID: {current_attempt.id}")
    
    # Get questions
    test_questions = test.testquestion_set.all().select_related('question')
    print(f"DEBUG: Found {test_questions.count()} questions for this test")
    
    if test_questions.count() == 0:
        messages.error(request, "This test has no questions configured.")
        print(f"DEBUG: Test blocked - no questions found")
        return redirect('student_mock_tests')
    
    # Process questions with improved image handling
    processed_questions = []
    for tq in test_questions:
        question_data = {
            'id': tq.question.id,
            'order': len(processed_questions) + 1,
            'text': tq.question.question_text,
            'options': {},
            'has_image': bool(tq.question.image),
            'image_url': None,
            'image_filename': tq.question.image if tq.question.image else None
        }
        
        # Handle image URL generation with improved matching
        if tq.question.image:
            image_url, actual_filename = get_question_image_url(tq.question)
            if image_url:
                question_data['image_url'] = image_url
                question_data['image_filename'] = actual_filename
                print(f"DEBUG: Found image for question {tq.question.id}: {image_url}")
            else:
                print(f"DEBUG: Image not found for question {tq.question.id}: {tq.question.image}")
        
        # Add options
        if tq.question.option_a:
            question_data['options']['A'] = tq.question.option_a
        if tq.question.option_b:
            question_data['options']['B'] = tq.question.option_b
        if tq.question.option_c:
            question_data['options']['C'] = tq.question.option_c
        if tq.question.option_d:
            question_data['options']['D'] = tq.question.option_d
        if tq.question.option_e:
            question_data['options']['E'] = tq.question.option_e
        
        processed_questions.append(question_data)
    
    # Randomize if enabled
    if test.randomize_questions:
        random.shuffle(processed_questions)
        print(f"DEBUG: Questions randomized")
    
    print(f"DEBUG: Proceeding to test page with attempt ID: {current_attempt.id}")
    print(f"DEBUG: Processed {len(processed_questions)} questions with images")
    
    context = {
        'test': test,
        'attempt': current_attempt,
        'test_questions': processed_questions,  # Use processed questions
        'total_questions': len(processed_questions),
    }
    
    return render(request, 'mocktest/take_test.html', context)


@require_POST
def submit_answer(request):
    """Save student's answer"""
    attempt_id = request.POST.get('attempt_id')
    question_id = request.POST.get('question_id')
    answer = request.POST.get('answer')
    
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    question = get_object_or_404(Question, id=question_id)
    
    # Save or update response
    response, created = TestResponse.objects.update_or_create(
        attempt=attempt,
        question=question,
        defaults={
            'selected_answer': answer,
        }
    )
    
    # Check if answer is correct
    response.check_answer()
    response.save()
    
    return JsonResponse({'success': True})


@require_POST
def submit_test(request):
    """Submit the complete test"""
    attempt_id = request.POST.get('attempt_id')
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    
    # Calculate score
    total_questions = attempt.mock_test.total_questions
    correct_answers = attempt.responses.filter(is_correct=True).count()
    
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
    })


@login_required
def test_result(request, attempt_id):
    """Show test results with enhanced data and security"""
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    
    # Security check: Only allow the student who took the test to view results
    if attempt.student != request.user:
        messages.error(request, "You can only view your own test results.")
        return redirect('student_mock_tests')
    
    # Ensure the test is actually completed
    if attempt.status == 'in_progress':
        messages.warning(request, "This test is still in progress.")
        return redirect('take_test', test_id=attempt.mock_test.id)
    
    # Get all responses with questions, including unanswered ones
    all_questions = attempt.mock_test.testquestion_set.all().select_related('question')
    responses = []
    
    for test_question in all_questions:
        try:
            response = TestResponse.objects.get(
                attempt=attempt,
                question=test_question.question
            )
        except TestResponse.DoesNotExist:
            # Create a dummy response for unanswered questions
            response = TestResponse(
                attempt=attempt,
                question=test_question.question,
                selected_answer=None,
                is_correct=False
            )
        responses.append(response)
    
    # Calculate additional statistics
    total_questions = len(responses)
    answered_questions = len([r for r in responses if r.selected_answer])
    unanswered_questions = total_questions - answered_questions
    correct_answers = len([r for r in responses if r.is_correct])
    incorrect_answers = answered_questions - correct_answers
    
    # Calculate time efficiency
    time_efficiency = 0
    if attempt.mock_test.duration_minutes > 0:
        time_efficiency = min(100, (attempt.time_taken_minutes / attempt.mock_test.duration_minutes) * 100)
    
    context = {
        'attempt': attempt,
        'test': attempt.mock_test,
        'responses': responses,
        'passed': attempt.passed,
        'user': request.user,
        
        # Additional statistics
        'total_questions': total_questions,
        'answered_questions': answered_questions,
        'unanswered_questions': unanswered_questions,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,
        'time_efficiency': round(time_efficiency, 1),
        
        # For template calculations
        'current_year': timezone.now().year,
    }
    
    return render(request, 'mocktest/test_results.html', context)


@require_POST
def report_warning(request):
    """Report tab switch warning"""
    attempt_id = request.POST.get('attempt_id')
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    
    attempt.warning_count += 1
    attempt.save()
    
    if attempt.warning_count >= 3:
        # Auto-submit test
        attempt.status = 'abandoned'
        attempt.completed_at = timezone.now()
        attempt.save()
        
        return JsonResponse({
            'success': True,
            'auto_submit': True,
            'message': 'Test auto-submitted due to multiple tab switches.'
        })
    
    return JsonResponse({
        'success': True,
        'warning_count': attempt.warning_count,
        'remaining_warnings': 3 - attempt.warning_count
    })


@login_required
def mock_test_progress(request):
    """Student progress tracking with pagination and filtering - Error-Safe Version"""
    user = request.user
    
    try:
        # Base queryset
        attempts = TestAttempt.objects.filter(student=user).select_related('mock_test').order_by('-started_at')
        
        # Apply filters
        status_filter = request.GET.get('status')
        date_filter = request.GET.get('date')
        subject_filter = request.GET.get('subject')
        
        # Filter by status
        if status_filter and status_filter != 'all':
            attempts = attempts.filter(status=status_filter)
        
        # Filter by date
        if date_filter and date_filter != 'all':
            today = timezone.now().date()
            if date_filter == 'today':
                attempts = attempts.filter(started_at__date=today)
            elif date_filter == 'week':
                week_ago = today - timedelta(days=7)
                attempts = attempts.filter(started_at__date__gte=week_ago)
            elif date_filter == 'month':
                month_ago = today - timedelta(days=30)
                attempts = attempts.filter(started_at__date__gte=month_ago)
        
        # Filter by subject
        if subject_filter and subject_filter != 'all':
            if subject_filter == 'mbbs':
                attempts = attempts.filter(mock_test__subject__icontains='MBBS')
            elif subject_filter == 'bds':
                attempts = attempts.filter(mock_test__subject__icontains='BDS')
        
        # Paginate results (10 per page)
        paginator = Paginator(attempts, 10)
        page_number = request.GET.get('page')
        attempts = paginator.get_page(page_number)
        
        # Calculate stats (using all attempts, not just paginated ones)
        all_attempts = TestAttempt.objects.filter(student=user).select_related('mock_test')
        completed_attempts = all_attempts.filter(status='completed').order_by('started_at')
        
        # Basic stats with safe calculations
        total_tests = all_attempts.count()
        
        # Safe aggregation with default values
        best_score_result = completed_attempts.aggregate(Max('percentage'))['percentage__max']
        best_score = float(best_score_result) if best_score_result is not None else 0
        
        avg_score_result = completed_attempts.aggregate(Avg('percentage'))['percentage__avg']
        avg_score = float(avg_score_result) if avg_score_result is not None else 0
        
        avg_time_result = completed_attempts.aggregate(Avg('time_taken'))['time_taken__avg']
        avg_time = float(avg_time_result) if avg_time_result is not None else 0
        
        # Get subject-wise performance with safe calculations
        subject_performance = {}
        for attempt in completed_attempts:
            if attempt.percentage is None:
                continue
                
            test_subject = getattr(attempt.mock_test, 'subject', None) or 'General'
            if test_subject not in subject_performance:
                subject_performance[test_subject] = {
                    'attempts': 0,
                    'total_score': 0,
                    'best_score': 0
                }
            
            subject_performance[test_subject]['attempts'] += 1
            subject_performance[test_subject]['total_score'] += float(attempt.percentage)
            subject_performance[test_subject]['best_score'] = max(
                subject_performance[test_subject]['best_score'],
                float(attempt.percentage)
            )
        
        # Calculate averages safely
        for subject in subject_performance:
            data = subject_performance[subject]
            if data['attempts'] > 0:
                data['avg_score'] = round(data['total_score'] / data['attempts'], 1)
            else:
                data['avg_score'] = 0
        
        # Calculate improvement trend safely
        improvement_rate = 0
        if completed_attempts.count() >= 4:
            try:
                half_point = completed_attempts.count() // 2
                recent_half = list(completed_attempts[:half_point])
                older_half = list(completed_attempts[half_point:])
                
                # Filter out None values and convert to float
                recent_scores = [float(a.percentage) for a in recent_half if a.percentage is not None]
                older_scores = [float(a.percentage) for a in older_half if a.percentage is not None]
                
                if recent_scores and older_scores:
                    recent_avg = sum(recent_scores) / len(recent_scores)
                    older_avg = sum(older_scores) / len(older_scores)
                    improvement_rate = recent_avg - older_avg
            except (TypeError, ValueError, ZeroDivisionError):
                improvement_rate = 0
        
        # Calculate consistency rate safely
        consistency_rate = 75  # Default value
        if completed_attempts.count() >= 3:
            try:
                # Filter out None values and convert to float
                scores = [float(a.percentage) for a in completed_attempts if a.percentage is not None]
                
                if len(scores) >= 3:
                    mean_score = sum(scores) / len(scores)
                    variance = sum((x - mean_score) ** 2 for x in scores) / len(scores)
                    std_dev = variance ** 0.5
                    # Convert to consistency percentage (lower std dev = higher consistency)
                    consistency_rate = max(0, 100 - (std_dev * 2))
            except (TypeError, ValueError, ZeroDivisionError):
                consistency_rate = 75
        
        # Calculate test frequency safely
        test_frequency = 0
        if completed_attempts.count() > 0:
            try:
                first_test = completed_attempts.last().started_at
                days_since_first = (timezone.now() - first_test).days
                if days_since_first > 0:
                    test_frequency = (completed_attempts.count() * 7) / days_since_first
            except (AttributeError, TypeError, ZeroDivisionError):
                test_frequency = 0
        
        # Calculate trends for stats safely
        test_trend = 0
        score_improvement = 0
        
        try:
            # Calculate monthly test trend
            current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month = (current_month - timedelta(days=1)).replace(day=1)
            
            current_month_tests = all_attempts.filter(started_at__gte=current_month).count()
            last_month_tests = all_attempts.filter(
                started_at__gte=last_month,
                started_at__lt=current_month
            ).count()
            
            if last_month_tests > 0:
                test_trend = ((current_month_tests - last_month_tests) / last_month_tests) * 100
        except (TypeError, ZeroDivisionError):
            test_trend = 0
        
        # Calculate score improvement trend safely
        if completed_attempts.count() >= 4:
            try:
                recent_scores = completed_attempts[:2]
                older_scores = completed_attempts[2:4]
                
                recent_values = [float(a.percentage) for a in recent_scores if a.percentage is not None]
                older_values = [float(a.percentage) for a in older_scores if a.percentage is not None]
                
                if recent_values and older_values:
                    recent_avg = sum(recent_values) / len(recent_values)
                    older_avg = sum(older_values) / len(older_values)
                    
                    if older_avg > 0:
                        score_improvement = ((recent_avg - older_avg) / older_avg) * 100
            except (TypeError, ValueError, ZeroDivisionError):
                score_improvement = 0

        context = {
            'attempts': attempts,
            'completed_attempts': completed_attempts,
            'total_tests': total_tests,
            'best_score': round(best_score, 1),
            'avg_score': round(avg_score, 1),
            'avg_time': round(avg_time / 60, 1) if avg_time else 0,  # Convert to minutes
            'subject_performance': subject_performance,
            'improvement_rate': round(improvement_rate, 1),
            'consistency_rate': round(consistency_rate, 1),
            'test_frequency': round(test_frequency, 1),
            'test_trend': round(test_trend, 1),
            'score_improvement': round(score_improvement, 1),
            'user': user,
            # Add filter values for template
            'current_status_filter': status_filter or 'all',
            'current_date_filter': date_filter or 'all',
            'current_subject_filter': subject_filter or 'all',
        }
        
    except Exception as e:
        # Fallback in case of any error
        print(f"Error in mock_test_progress: {e}")
        
        # Minimal safe context
        attempts = TestAttempt.objects.filter(student=user).select_related('mock_test').order_by('-started_at')
        paginator = Paginator(attempts, 10)
        page_number = request.GET.get('page')
        attempts = paginator.get_page(page_number)
        
        completed_attempts = TestAttempt.objects.filter(student=user, status='completed').order_by('started_at')
        
        context = {
            'attempts': attempts,
            'completed_attempts': completed_attempts,
            'total_tests': TestAttempt.objects.filter(student=user).count(),
            'best_score': 0,
            'avg_score': 0,
            'avg_time': 0,
            'subject_performance': {},
            'improvement_rate': 0,
            'consistency_rate': 75,
            'test_frequency': 0,
            'test_trend': 0,
            'score_improvement': 0,
            'user': user,
            'current_status_filter': 'all',
            'current_date_filter': 'all',
            'current_subject_filter': 'all',
        }
    
    return render(request, 'mocktest/student_progress.html', context)