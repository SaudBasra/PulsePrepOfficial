# mocktest/views.py - Complete Enhanced Version with Access Control
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
import calendar
from datetime import datetime, timedelta

from .models import MockTest, TestQuestion, TestAttempt, TestResponse
from .forms import MockTestForm
from questionbank.models import Question

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
def mocktest_list(request):
    """List all mock tests with filtering - Enhanced with access control"""
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    degree_filter = request.GET.get('degree', '')
    
    tests = MockTest.objects.all()
    
    # APPLY USER ACCESS FILTER
    tests = apply_user_access_filter(tests, request.user)
    
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
    
    # ADD ACCESS INFO TO CONTEXT
    try:
        access_info = get_user_access_info(request.user)
    except:
        access_info = {'level': 'guest', 'can_access': False}
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'degree_filter': degree_filter,
        'user_access': access_info,
        'can_create_tests': access_info.get('level') == 'admin',
    }
    
    return render(request, 'mocktest/mocktest_list.html', context)


@admin_required
def create_test(request):
    """Enhanced create/edit mock test with availability checking - Admin only"""
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
                actual_count = generate_random_questions(test, request.user)
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
                    
                    # Add selected questions (with access control)
                    accessible_questions = Question.objects.filter(id__in=question_ids)
                    accessible_questions = apply_user_access_filter(accessible_questions, request.user)
                    
                    for order, question in enumerate(accessible_questions, 1):
                        TestQuestion.objects.create(
                            mock_test=test,
                            question=question,
                            question_order=order
                        )
                    
                    # Update total questions
                    actual_count = test.testquestion_set.count()
                    test.total_questions = actual_count
                    test.save()
                    
                    if actual_count != len(question_ids):
                        messages.warning(request, f"Test created with {actual_count} questions. Some questions were filtered out based on access control.")
                    else:
                        messages.success(request, f"Test {'updated' if is_edit else 'created'} successfully with {actual_count} questions!")
                else:
                    messages.error(request, "No questions selected for manual test creation.")
                    # Get filtered hierarchy data
                    questions = Question.objects.all()
                    questions = apply_user_access_filter(questions, request.user)
                    
                    return render(request, 'mocktest/create_test.html', {
                        'form': form,
                        'test': test,
                        'is_edit': is_edit,
                        'blocks': questions.values('block').distinct().order_by('block'),
                        'modules': questions.values('module').distinct().order_by('module'),
                        'subjects': questions.values('subject').distinct().order_by('subject'),
                        'topics': questions.values('topic').distinct().order_by('topic'),
                    })
            
            return redirect('mocktest_list')
    
    # Get hierarchy data for dropdowns - FILTERED BY ACCESS CONTROL
    questions = Question.objects.all()
    questions = apply_user_access_filter(questions, request.user)
    
    blocks = questions.values('block').distinct().order_by('block')
    modules = questions.values('module').distinct().order_by('module')
    subjects = questions.values('subject').distinct().order_by('subject')
    topics = questions.values('topic').distinct().order_by('topic')
    
    context = {
        'form': form,
        'test': test,
        'is_edit': is_edit,
        'blocks': blocks,
        'modules': modules,
        'subjects': subjects,
        'topics': topics,
        'user_access': get_user_access_info(request.user),
    }    
    return render(request, 'mocktest/create_test.html', context)


def generate_random_questions(test, user):
    """Enhanced random question generation with access control"""
    # Clear existing questions
    test.questions.clear()
    
    # Build query based on test filters
    query = Question.objects.filter(question_type='MCQ')
    
    # APPLY USER ACCESS FILTER FIRST
    query = apply_user_access_filter(query, user)
    
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
    hard_count = total - easy_count - medium_count
    
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


@admin_required
@require_POST
def delete_test(request, test_id):
    """Delete a mock test - Admin only"""
    test = get_object_or_404(MockTest, id=test_id)
    test.delete()
    messages.success(request, "Test deleted successfully!")
    return JsonResponse({'success': True})


@content_access_required
def get_filtered_questions(request):
    """Get questions based on filters for manual selection with pagination - Access controlled"""
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))
    
    questions = Question.objects.filter(question_type='MCQ')
    
    # APPLY USER ACCESS FILTER
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
            'degree': q.degree,
            'year': q.year,
        })
    
    # Get user access info safely
    try:
        user_access_level = get_user_access_info(request.user)['level']
    except:
        user_access_level = 'guest'
    
    return JsonResponse({
        'questions': question_list,
        'total_count': total_count,
        'current_page': page,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'user_access_level': user_access_level,
    })


@content_access_required
def check_question_availability(request):
    """Check availability of questions for random selection - Access controlled"""
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    
    # Build base query
    query = Question.objects.filter(question_type='MCQ')
    
    # APPLY USER ACCESS FILTER
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
    if topic:
        query = query.filter(topic=topic)
    
    # Count by difficulty
    easy_count = query.filter(difficulty='Easy').count()
    medium_count = query.filter(difficulty='Medium').count()
    hard_count = query.filter(difficulty='Hard').count()
    total_available = easy_count + medium_count + hard_count
    
    # Get user access info safely
    try:
        user_access_level = get_user_access_info(request.user)['level']
    except:
        user_access_level = 'guest'
    
    return JsonResponse({
        'total_available': total_available,
        'easy': easy_count,
        'medium': medium_count,
        'hard': hard_count,
        'user_access_level': user_access_level,
    })


@admin_required
@require_POST
def save_manual_questions(request):
    """Save manually selected questions - Admin only"""
    test_id = request.POST.get('test_id')
    question_ids = json.loads(request.POST.get('question_ids', '[]'))
    
    test = get_object_or_404(MockTest, id=test_id)
    
    # Clear existing questions
    test.questions.clear()
    
    # Add selected questions with access control
    accessible_questions = Question.objects.filter(id__in=question_ids)
    accessible_questions = apply_user_access_filter(accessible_questions, request.user)
    
    added_count = 0
    for order, question in enumerate(accessible_questions, 1):
        TestQuestion.objects.create(
            mock_test=test,
            question=question,
            question_order=order
        )
        added_count += 1
    
    # Update total questions
    test.total_questions = added_count
    test.save()
    
    message = f'{added_count} questions added to test'
    if added_count != len(question_ids):
        message += f' (filtered from {len(question_ids)} selected)'
    
    return JsonResponse({'success': True, 'message': message})


@content_access_required
def preview_test(request, test_id):
    """Preview test before publishing - Access controlled"""
    test = get_object_or_404(MockTest, id=test_id)
    
    # CHECK OBJECT ACCESS
    if not check_object_access(test, request.user):
        messages.error(request, "You don't have permission to preview this test.")
        return redirect('mocktest_list')
    
    test_questions = test.testquestion_set.all().select_related('question')
    
    # FILTER QUESTIONS BY ACCESS CONTROL
    accessible_question_ids = []
    for tq in test_questions:
        if check_object_access(tq.question, request.user):
            accessible_question_ids.append(tq.id)
    
    filtered_test_questions = test_questions.filter(id__in=accessible_question_ids)
    
    context = {
        'test': test,
        'test_questions': filtered_test_questions,
        'question_count': filtered_test_questions.count(),
        'user_access': get_user_access_info(request.user),
        'can_edit': request.user.is_admin or request.user.is_superuser,
    }
    
    return render(request, 'mocktest/preview_test.html', context)


@content_access_required
def get_hierarchy_data(request):
    """Enhanced hierarchy data endpoint - Access controlled"""
    field = request.GET.get('field')
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    
    query = Question.objects.all()
    
    # APPLY USER ACCESS FILTER
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
    
    # Get user access info safely
    try:
        user_access_level = get_user_access_info(request.user)['level']
        user_filter_applied = user_access_level == 'student'
    except:
        user_access_level = 'guest'
        user_filter_applied = False
    
    return JsonResponse({
        'data': data,
        'user_access_level': user_access_level,
        'user_filter_applied': user_filter_applied
    })


# STUDENT VIEWS WITH ACCESS CONTROL
@content_access_required
def student_mock_tests(request):
    """List available mock tests for students - Access controlled"""
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
    
    # APPLY USER ACCESS FILTER
    tests = apply_user_access_filter(tests, request.user)
    
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
    
    # Get upcoming tests - ALSO FILTERED
    upcoming_tests = MockTest.objects.filter(
        start_datetime__gt=now
            ).order_by('start_datetime')
    upcoming_tests = apply_user_access_filter(upcoming_tests, request.user)[:5]    
    context = {
        'active_tests': tests,
        'upcoming_tests': upcoming_tests,
        'user': user,
        'user_access': get_user_access_info(user),
    }
    
    return render(request, 'mocktest/student_mock_tests.html', context)

# mocktest/views.py - Updated sections for image support

# ADD THIS HELPER FUNCTION at the top of your mocktest/views.py file
def get_question_image_url_for_field(question, field_name):
    """
    Enhanced function to get image URL for a specific field (question_image or image)
    This matches the function from managemodule/views.py
    """
    image_filename = getattr(question, field_name, None)
    if not image_filename:
        return None, None
    
    try:
        from django.conf import settings
        import os
        
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


# REPLACE the existing take_test view with this updated version:
@content_access_required
def take_test(request, test_id):
    """Student takes the test - Updated with enhanced image support"""
    test = get_object_or_404(MockTest, id=test_id)
    student = request.user
    
    print(f"DEBUG: User {student} trying to take test: {test.title}")
    
    # CHECK ACCESS CONTROL
    if not check_object_access(test, student):
        messages.error(request, "You don't have access to this test.")
        return redirect('student_mock_tests')
    
    # Check if test is active
    now = timezone.now()
    if test.status != 'live':
        messages.error(request, f"This test is not currently available. Status: {test.status}")
        return redirect('student_mock_tests')
    
    # Check time bounds
    if now < test.start_datetime:
        messages.error(request, "This test has not started yet.")
        return redirect('student_mock_tests')
    
    if now > test.end_datetime:
        messages.error(request, "This test has already ended.")
        return redirect('student_mock_tests')
    
    # Check attempt limit
    existing_attempts = TestAttempt.objects.filter(
        student=student, 
        mock_test=test,
        status='completed'
    ).count()
    
    if existing_attempts >= test.max_attempts:
        messages.error(request, f"You have reached the maximum attempts ({test.max_attempts}) for this test.")
        return redirect('student_mock_tests')
    
    # Get or create current attempt
    current_attempt = TestAttempt.objects.filter(
        student=student,
        mock_test=test,
        status='in_progress'
    ).first()
    
    if not current_attempt:
        current_attempt = TestAttempt.objects.create(
            student=student,
            mock_test=test,
            status='in_progress',
            started_at=timezone.now()
        )
    
    # Get questions
    test_questions = test.testquestion_set.all().select_related('question')
    
    if test_questions.count() == 0:
        messages.error(request, "This test has no questions configured.")
        return redirect('student_mock_tests')
    
    # FILTER QUESTIONS BY ACCESS CONTROL
    accessible_questions = []
    for tq in test_questions:
        if check_object_access(tq.question, student):
            accessible_questions.append(tq)
    
    if len(accessible_questions) == 0:
        messages.error(request, "You don't have access to any questions in this test.")
        return redirect('student_mock_tests')
    
    # Process questions with ENHANCED image handling
    processed_questions = []
    for tq in accessible_questions:
        question_data = {
            'id': tq.question.id,
            'order': len(processed_questions) + 1,
            'text': tq.question.question_text,
            'options': {},
            # ENHANCED: Support both question_image and explanation image
            'has_question_image': bool(getattr(tq.question, 'question_image', None)),
            'question_image_url': None,
            'question_image_filename': getattr(tq.question, 'question_image', None),
            'has_explanation_image': bool(tq.question.image),
            'explanation_image_url': None,
            'explanation_image_filename': tq.question.image if tq.question.image else None,
            # Additional context
            'degree': tq.question.degree,
            'year': tq.question.year,
            'block': tq.question.block,
            'module': tq.question.module,
            'subject': tq.question.subject,
            'topic': tq.question.topic,
            'difficulty': tq.question.difficulty,
        }
        
        # ENHANCED: Handle question_image URL generation
        if hasattr(tq.question, 'question_image') and tq.question.question_image:
            try:
                question_image_url, actual_filename = get_question_image_url_for_field(tq.question, 'question_image')
                if question_image_url:
                    question_data['question_image_url'] = question_image_url
                    question_data['question_image_filename'] = actual_filename
            except Exception as e:
                print(f"Error processing question image for question {tq.question.id}: {str(e)}")
        
        # ENHANCED: Handle explanation image URL generation (existing logic)
        if tq.question.image:
            try:
                explanation_image_url, actual_filename = get_question_image_url_for_field(tq.question, 'image')
                if explanation_image_url:
                    question_data['explanation_image_url'] = explanation_image_url
                    question_data['explanation_image_filename'] = actual_filename
            except Exception as e:
                print(f"Error processing explanation image for question {tq.question.id}: {str(e)}")
        
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
    
    context = {
        'test': test,
        'attempt': current_attempt,
        'test_questions': processed_questions,
        'total_questions': len(processed_questions),
        'user_access': get_user_access_info(student),
    }
    
    return render(request, 'mocktest/take_test.html', context)


# ALSO UPDATE the test_result view to handle images properly:
@content_access_required
def test_result(request, attempt_id):
    """Show test results with enhanced data and image support - Access controlled"""
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    
    # Security check: Only allow the student who took the test to view results
    if attempt.student != request.user:
        messages.error(request, "You can only view your own test results.")
        return redirect('student_mock_tests')
    
    # ACCESS CONTROL: Check if user can access the test
    if not check_object_access(attempt.mock_test, request.user):
        messages.error(request, "You don't have access to this test's results.")
        return redirect('student_mock_tests')
    
    # Ensure the test is actually completed
    if attempt.status == 'in_progress':
        messages.warning(request, "This test is still in progress.")
        return redirect('take_test', test_id=attempt.mock_test.id)
    
    # Get all responses with questions, including unanswered ones - FILTERED BY ACCESS
    all_questions = attempt.mock_test.testquestion_set.all().select_related('question')
    responses = []
    accessible_question_count = 0
    
    for test_question in all_questions:
        # CHECK ACCESS CONTROL FOR EACH QUESTION
        if check_object_access(test_question.question, request.user):
            accessible_question_count += 1
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
            
            # ENHANCED: Add image data to response
            response.question_image_url = None
            response.question_image_filename = None
            response.explanation_image_url = None
            response.explanation_image_filename = None
            
            # Process question image
            if hasattr(test_question.question, 'question_image') and test_question.question.question_image:
                try:
                    question_image_url, actual_filename = get_question_image_url_for_field(test_question.question, 'question_image')
                    if question_image_url:
                        response.question_image_url = question_image_url
                        response.question_image_filename = actual_filename
                except Exception as e:
                    print(f"Error processing question image for question {test_question.question.id}: {str(e)}")
            
            # Process explanation image
            if test_question.question.image:
                try:
                    explanation_image_url, actual_filename = get_question_image_url_for_field(test_question.question, 'image')
                    if explanation_image_url:
                        response.explanation_image_url = explanation_image_url
                        response.explanation_image_filename = actual_filename
                except Exception as e:
                    print(f"Error processing explanation image for question {test_question.question.id}: {str(e)}")
            
            responses.append(response)
    
    # Calculate additional statistics based on accessible questions
    total_questions = len(responses)
    answered_questions = len([r for r in responses if r.selected_answer])
    unanswered_questions = total_questions - answered_questions
    correct_answers = len([r for r in responses if r.is_correct])
    incorrect_answers = answered_questions - correct_answers
    
    # Calculate time efficiency
    time_efficiency = 0
    if attempt.mock_test.duration_minutes > 0:
        # Fix: Calculate time_taken_minutes from time_taken seconds
        time_taken_minutes = attempt.time_taken / 60 if attempt.time_taken else 0
        time_efficiency = min(100, (time_taken_minutes / attempt.mock_test.duration_minutes) * 100)
    
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
        'accessible_question_count': accessible_question_count,
        
        # Access control info
        'user_access': get_user_access_info(request.user),
        
        # For template calculations
        'current_year': timezone.now().year,
    }
    
    return render(request, 'mocktest/test_results.html', context)

@content_access_required
@require_POST
def submit_answer(request):
    """Save student's answer - Access controlled"""
    attempt_id = request.POST.get('attempt_id')
    question_id = request.POST.get('question_id')
    answer = request.POST.get('answer')
    
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    question = get_object_or_404(Question, id=question_id)
    
    # SECURITY CHECK: Ensure user owns this attempt
    if attempt.student != request.user:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    # ACCESS CONTROL: Check if user can access this question
    if not check_object_access(question, request.user):
        return JsonResponse({'success': False, 'message': 'Question access denied'}, status=403)
    
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


@content_access_required
@require_POST
def submit_test(request):
    """Submit the complete test - Access controlled"""
    attempt_id = request.POST.get('attempt_id')
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    
    # SECURITY CHECK: Ensure user owns this attempt
    if attempt.student != request.user:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    # ACCESS CONTROL: Check if user can access the test
    if not check_object_access(attempt.mock_test, request.user):
        return JsonResponse({'success': False, 'message': 'Test access denied'}, status=403)
    
    # Calculate score based on accessible questions only
    test_questions = attempt.mock_test.testquestion_set.all()
    accessible_question_count = 0
    correct_answers = 0
    
    for tq in test_questions:
        if check_object_access(tq.question, request.user):
            accessible_question_count += 1
            try:
                response = TestResponse.objects.get(attempt=attempt, question=tq.question)
                if response.is_correct:
                    correct_answers += 1
            except TestResponse.DoesNotExist:
                pass
    
    # Use accessible question count for calculations
    total_questions = accessible_question_count if accessible_question_count > 0 else attempt.mock_test.total_questions
    
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
    })


@content_access_required
@require_POST
def report_warning(request):
    """Report tab switch warning - Access controlled"""
    attempt_id = request.POST.get('attempt_id')
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    
    # SECURITY CHECK: Ensure user owns this attempt
    if attempt.student != request.user:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
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


@content_access_required
def mock_test_progress(request):
    """Student progress tracking - Access controlled"""
    user = request.user
    attempts = TestAttempt.objects.filter(student=user).select_related('mock_test').order_by('-started_at')
    
    # FILTER ATTEMPTS BY ACCESS CONTROL
    accessible_attempts = []
    for attempt in attempts:
        if check_object_access(attempt.mock_test, user):
            accessible_attempts.append(attempt)
    
    # Calculate stats based on accessible attempts
    completed_attempts = [a for a in accessible_attempts if a.status == 'completed']
    total_tests = len(accessible_attempts)
    best_score = max([a.percentage for a in completed_attempts]) if completed_attempts else 0
    avg_score = sum([a.percentage for a in completed_attempts]) / len(completed_attempts) if completed_attempts else 0
    avg_time = sum([a.time_taken for a in completed_attempts]) / len(completed_attempts) if completed_attempts else 0
    
    # Calculate monthly progress
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
    
    # Get subject-wise performance - FILTERED
    subject_performance = {}
    for attempt in completed_attempts:
        test_subject = attempt.mock_test.subject or 'General'
        if test_subject not in subject_performance:
            subject_performance[test_subject] = {
                'attempts': 0,
                'total_score': 0,
                'best_score': 0
            }
        
        subject_performance[test_subject]['attempts'] += 1
        subject_performance[test_subject]['total_score'] += attempt.percentage
        subject_performance[test_subject]['best_score'] = max(
            subject_performance[test_subject]['best_score'],
            attempt.percentage
        )
    
    # Calculate averages
    for subject in subject_performance:
        data = subject_performance[subject]
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
        'total_tests': total_tests,
        'best_score': round(best_score, 1),
        'avg_score': round(avg_score, 1),
        'avg_time': round(avg_time / 60, 1) if avg_time else 0,  # Convert to minutes
        'monthly_data': monthly_data,
        'subject_performance': subject_performance,
        'recent_attempts': recent_attempts,
        'improvement': round(improvement, 1),
        'user': user,
        'user_access': get_user_access_info(user),
        'accessible_tests_count': total_tests,
    }
    
    return render(request, 'mocktest/student_progress.html', context)


# ADDITIONAL ADMIN VIEWS WITH ACCESS CONTROL

@admin_required
def admin_test_analytics(request):
    """Admin view for test analytics across all users"""
    tests = MockTest.objects.all()
    
    # Apply admin filtering if needed (admins see all by default)
    # tests = apply_user_access_filter(tests, request.user)  # Uncomment if admins should be filtered too
    
    test_stats = []
    for test in tests:
        attempts = TestAttempt.objects.filter(mock_test=test, status='completed')
        
        if attempts.exists():
            avg_score = attempts.aggregate(Avg('percentage'))['percentage__avg']
            best_score = attempts.aggregate(Max('percentage'))['percentage__max']
            total_attempts = attempts.count()
            pass_rate = attempts.filter(percentage__gte=test.passing_percentage).count() / total_attempts * 100
        else:
            avg_score = best_score = total_attempts = pass_rate = 0
        
        test_stats.append({
            'test': test,
            'total_attempts': total_attempts,
            'avg_score': round(avg_score or 0, 1),
            'best_score': round(best_score or 0, 1),
            'pass_rate': round(pass_rate, 1),
        })
    
    context = {
        'test_stats': test_stats,
        'total_tests': tests.count(),
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'mocktest/admin_analytics.html', context)


@admin_required
def bulk_test_actions(request):
    """Admin view for bulk test management"""
    if request.method == 'POST':
        action = request.POST.get('action')
        test_ids = request.POST.getlist('test_ids')
        
        if action == 'activate':
            MockTest.objects.filter(id__in=test_ids).update(status='live')
            messages.success(request, f"Activated {len(test_ids)} tests.")
        elif action == 'deactivate':
            MockTest.objects.filter(id__in=test_ids).update(status='draft')
            messages.success(request, f"Deactivated {len(test_ids)} tests.")
        elif action == 'delete':
            MockTest.objects.filter(id__in=test_ids).delete()
            messages.success(request, f"Deleted {len(test_ids)} tests.")
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@admin_required
def test_performance_report(request):
    """Generate detailed performance report for a specific test"""
    test_id = request.GET.get('test_id')
    if not test_id:
        messages.error(request, "Test ID is required for performance report.")
        return redirect('admin_test_analytics')
    
    test = get_object_or_404(MockTest, id=test_id)
    attempts = TestAttempt.objects.filter(mock_test=test, status='completed').select_related('student')
    
    # Calculate detailed statistics
    total_attempts = attempts.count()
    if total_attempts == 0:
        messages.info(request, f"No completed attempts found for test: {test.title}")
        return redirect('admin_test_analytics')
    
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
    test_questions = test.testquestion_set.all().select_related('question')
    
    for tq in test_questions:
        responses = TestResponse.objects.filter(
            attempt__in=attempts,
            question=tq.question
        )
        total_responses = responses.count()
        correct_responses = responses.filter(is_correct=True).count()
        
        question_stats[tq.question.id] = {
            'question': tq.question,
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
        'test': test,
        'total_attempts': total_attempts,
        'score_ranges': score_ranges,
        'top_performers': top_performers,
        'question_stats': question_stats,
        'avg_time_minutes': round(avg_time / 60, 1),
        'time_distribution': time_distribution,
        'pass_rate': attempts.filter(percentage__gte=test.passing_percentage).count() / total_attempts * 100,
        'avg_score': attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'mocktest/test_performance_report.html', context)


@admin_required
def export_test_results(request, test_id):
    """Export test results to CSV"""
    test = get_object_or_404(MockTest, id=test_id)
    attempts = TestAttempt.objects.filter(mock_test=test, status='completed').select_related('student')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{test.title}_results.csv"'
    
    import csv
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
            test.total_questions,
            round(attempt.percentage, 2),
            'Yes' if attempt.passed else 'No',
            round(attempt.time_taken / 60, 2) if attempt.time_taken else 0,
            attempt.started_at.strftime('%Y-%m-%d %H:%M:%S'),
            attempt.completed_at.strftime('%Y-%m-%d %H:%M:%S') if attempt.completed_at else 'N/A'
        ])
    
    return response


# ERROR HANDLING AND DEBUGGING VIEWS

@content_access_required
def debug_test_access(request, test_id):
    """Debug view to check test access (remove in production)"""
    if not request.user.is_admin and not request.user.is_superuser:
        return JsonResponse({'error': 'Admin only'}, status=403)
    
    test = get_object_or_404(MockTest, id=test_id)
    user_id = request.GET.get('user_id')
    
    if user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        check_user = get_object_or_404(User, id=user_id)
    else:
        check_user = request.user
    
    access_info = get_user_access_info(check_user)
    can_access = check_object_access(test, check_user)
    
    debug_info = {
        'test_info': {
            'id': test.id,
            'title': test.title,
            'degree': test.degree,
            'year': test.year,
            'status': test.status,
        },
        'user_info': {
            'id': check_user.id,
            'email': check_user.email,
            'degree': check_user.degree,
            'year': check_user.year,
            'approval_status': check_user.approval_status,
        },
        'access_info': access_info,
        'can_access_test': can_access,
        'filter_params': access_info.get('filter_params'),
    }
    
    return JsonResponse(debug_info, indent=2)


# UTILITY VIEWS

@content_access_required
def test_statistics(request):
    """General test statistics for students"""
    user = request.user
    
    # Get user's accessible tests
    all_tests = MockTest.objects.all()
    accessible_tests = apply_user_access_filter(all_tests, user)
    
    # Get user's attempts
    attempts = TestAttempt.objects.filter(student=user, status='completed')
    
    # Filter attempts by accessible tests
    accessible_attempts = []
    for attempt in attempts:
        if check_object_access(attempt.mock_test, user):
            accessible_attempts.append(attempt)
    
    # Calculate statistics
    total_accessible_tests = accessible_tests.count()
    total_attempts = len(accessible_attempts)
    unique_tests_attempted = len(set(attempt.mock_test.id for attempt in accessible_attempts))
    
    avg_score = sum(attempt.percentage for attempt in accessible_attempts) / len(accessible_attempts) if accessible_attempts else 0
    best_score = max((attempt.percentage for attempt in accessible_attempts), default=0)
    
    # Recent performance (last 5 attempts)
    recent_attempts = sorted(accessible_attempts, key=lambda x: x.completed_at, reverse=True)[:5]
    recent_avg = sum(attempt.percentage for attempt in recent_attempts) / len(recent_attempts) if recent_attempts else 0
    
    # Performance trend
    if len(recent_attempts) >= 2:
        latest_score = recent_attempts[0].percentage
        previous_avg = sum(attempt.percentage for attempt in recent_attempts[1:]) / len(recent_attempts[1:])
        trend = "improving" if latest_score > previous_avg else "declining" if latest_score < previous_avg else "stable"
    else:
        trend = "insufficient_data"
    
    context = {
        'total_accessible_tests': total_accessible_tests,
        'total_attempts': total_attempts,
        'unique_tests_attempted': unique_tests_attempted,
        'avg_score': round(avg_score, 1),
        'best_score': round(best_score, 1),
        'recent_avg': round(recent_avg, 1),
        'trend': trend,
        'recent_attempts': recent_attempts,
        'user_access': get_user_access_info(user),
    }
    
    return render(request, 'mocktest/test_statistics.html', context)

