# views.py - Fixed version
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Avg, Max

import json
import random

from .models import MockTest, TestQuestion, TestAttempt, TestResponse
from .forms import MockTestForm
from questionbank.models import Question

from mocktest.models import TestAttempt





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
    """Create or edit mock test"""
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
                generate_random_questions(test)
            else:
                # Manual selection
                selected_questions = request.POST.get('selected_questions')
                if selected_questions:
                    question_ids = json.loads(selected_questions)
                    
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
            
            messages.success(request, f"Test {'updated' if is_edit else 'created'} successfully!")
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
    """Generate random questions based on test criteria"""
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

@require_POST
def delete_test(request, test_id):
    """Delete a mock test"""
    test = get_object_or_404(MockTest, id=test_id)
    test.delete()
    messages.success(request, "Test deleted successfully!")
    return JsonResponse({'success': True})

def get_filtered_questions(request):
    """Get questions based on filters for manual selection"""
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    
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
    
    # Prepare data for JSON response
    question_list = []
    for q in questions[:100]:  # Limit to 100 questions
        question_list.append({
            'id': q.id,
            'text': q.question_text[:100] + '...' if len(q.question_text) > 100 else q.question_text,
            'difficulty': q.difficulty,
            'block': q.block,
            'module': q.module,
            'subject': q.subject,
            'topic': q.topic,
        })
    
    return JsonResponse({'questions': question_list})

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
    """Get hierarchy data for dropdowns"""
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
    
    return JsonResponse({'data': data})


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
    
    # Get upcoming tests - FIX: Don't filter by status='scheduled' after updating
    upcoming_tests = MockTest.objects.filter(
        start_datetime__gt=now
    ).order_by('start_datetime')[:5]
    
    context = {
        'active_tests': tests,
        'upcoming_tests': upcoming_tests,
        'user': user,
    }
    
    return render(request, 'mocktest/student_mock_tests.html', context)

# Add this helper function to mocktest/views.py

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


# Updated take_test view with better image handling
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
    """Show test results"""
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    
    # Get all responses with questions
    responses = attempt.responses.all().select_related('question')
    
    context = {
        'attempt': attempt,
        'test': attempt.mock_test,
        'responses': responses,
        'passed': attempt.passed,
    }
    
    return render(request, 'mocktest/test_results.html', context)



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
def student_progress(request):
    user = request.user
    attempts = TestAttempt.objects.filter(student=user).select_related('mock_test').order_by('-started_at')
    
    # Calculate stats
    completed_attempts = attempts.filter(status='completed')
    total_tests = attempts.count()
    best_score = completed_attempts.aggregate(Max('percentage'))['percentage__max'] or 0
    avg_score = completed_attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0
    avg_time = completed_attempts.aggregate(Avg('time_taken'))['time_taken__avg'] or 0
    
    context = {
        'attempts': attempts,
        'total_tests': total_tests,
        'best_score': best_score,
        'avg_score': avg_score,
        'avg_time': avg_time,
        'completed_attempts': completed_attempts,
    }
    return render(request, 'mocktest/student_progress.html', context)