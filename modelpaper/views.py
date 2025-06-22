# modelpaper/views.py - Updated with image support and all fixes
import csv
import io
import json
import random
import html

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

User = get_user_model()

def get_paper_question_image_url(paper_question):
    """
    Helper function to get the correct image URL for a paper question
    Reuses the same logic as mock test image handling
    """
    if not paper_question.image:
        return None, None
    
    try:
        from manageimage.models import QuestionImage
        
        image_filename = paper_question.image.strip()
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
        print(f"Error loading image for paper question {paper_question.id}: {str(e)}")
    
    return None, image_filename


def modelpaper_list(request):
    """List all model papers with filtering"""
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    degree_filter = request.GET.get('degree', '')
    paper_filter = request.GET.get('paper_name', '')
    
    papers = ModelPaper.objects.all()
    
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
    
    # Get unique paper names for filter dropdown
    paper_names = PaperQuestion.get_available_paper_names()
    
    # Get paper statistics for the "Available Paper Questions" section
    paper_stats = []
    for paper_name in paper_names:
        count = PaperQuestion.objects.filter(paper_name=paper_name).count()
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
    }
    
    return render(request, 'modelpaper/modelpaper_list.html', context)


from urllib.parse import unquote

def view_paper_questions(request, paper_name):
    """View questions for a specific paper name"""
    # Decode the URL-encoded paper name
    decoded_paper_name = unquote(paper_name)
    print(f"Original paper_name: '{paper_name}'")  # Debug line
    print(f"Decoded paper_name: '{decoded_paper_name}'")  # Debug line
    
    questions = PaperQuestion.objects.filter(paper_name=decoded_paper_name)
    print(f"Found {questions.count()} questions")  # Debug line
    
    # If still no results, try exact match or iexact match
    if questions.count() == 0:
        # Try case-insensitive match
        questions = PaperQuestion.objects.filter(paper_name__iexact=decoded_paper_name)
        print(f"Case-insensitive search found {questions.count()} questions")
        
        # If still no results, show all available paper names for debugging
        if questions.count() == 0:
            all_papers = PaperQuestion.objects.values_list('paper_name', flat=True).distinct()
            print("Available paper names in database:")
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
    }
    
    return render(request, 'modelpaper/view_paper_questions.html', context)


@login_required
def create_paper(request):
    """Create or edit model paper"""
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
            
            # Update total questions based on filters
            paper.update_total_questions()
            
            messages.success(request, f"Paper {'updated' if is_edit else 'created'} successfully! Total questions: {paper.total_questions}")
            return redirect('modelpaper_list')
    
    # Get available paper names count for context
    available_papers_count = PaperQuestion.get_available_paper_names().count()
    
    context = {
        'form': form,
        'paper': paper,
        'is_edit': is_edit,
        'available_papers_count': available_papers_count,
    }    
    return render(request, 'modelpaper/create_paper.html', context)


@require_POST
def delete_paper(request, paper_id):
    """Delete a model paper"""
    paper = get_object_or_404(ModelPaper, id=paper_id)
    paper.delete()
    messages.success(request, "Paper deleted successfully!")
    return JsonResponse({'success': True})


def preview_paper(request, paper_id):
    """Preview paper before publishing"""
    paper = get_object_or_404(ModelPaper, id=paper_id)
    paper_questions = paper.get_questions()[:10]  # Show first 10 questions for preview
    
    context = {
        'paper': paper,
        'paper_questions': paper_questions,
        'question_count': paper.total_questions,
        'showing_count': min(10, paper.total_questions),
    }
    
    return render(request, 'modelpaper/preview_paper.html', context)


def import_paper_questions(request):
    """Import paper questions from CSV with image support"""
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
                        
                        # Handle optional fields
                        degree = str(row.get('degree', '')).strip().upper()
                        if degree and degree not in ['MBBS', 'BDS']:
                            degree = ''
                        
                        year = str(row.get('year', '')).strip()
                        if year and year not in ['1st', '2nd', '3rd', '4th', '5th']:
                            year = ''
                        
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
                        
                        # Handle image field
                        image = str(row.get('image', '') or row.get('Image', '') or '').strip()
                        
                        # Enhanced duplicate detection within same paper name
                        is_duplicate, duplicate_reason = enhanced_duplicate_detection(
                            paper_name, question_text, option_a, option_b, option_c, option_d, option_e
                        )
                        
                        if is_duplicate:
                            errors.append(f"Row {row_num}: {duplicate_reason} - '{question_text[:50]}...'")
                            error_count += 1
                            continue
                        
                        # Create paper question
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
                            image=image or None,
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
                    'errors': errors[:10] if errors else []
                })
                
            except Exception as e:
                # Update import record with failure
                import_record.status = 'FAILED'
                import_record.error_details = str(e)
                import_record.save()
                
                return JsonResponse({'error': str(e)}, status=400)
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


# Student Views
@login_required
def student_model_papers(request):
    """List available model papers for students"""
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
    
    # Get active papers
    papers = ModelPaper.objects.filter(status='live')
    
    # Get user's attempts
    user_attempts = ModelPaperAttempt.objects.filter(student=user).values('model_paper_id', 'status').order_by('-started_at')
    
    # Create a dict of paper attempts
    attempt_status = {}
    attempt_count = {}
    for attempt in user_attempts:
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
    
    # Get upcoming papers
    upcoming_papers = ModelPaper.objects.filter(
        start_datetime__gt=now
    ).order_by('start_datetime')[:5]
    
    context = {
        'active_papers': papers,
        'upcoming_papers': upcoming_papers,
        'user': user,
    }
    
    return render(request, 'modelpaper/student_model_papers.html', context)


@login_required
def take_paper(request, paper_id):
    """Student takes the paper - Enhanced with image support and proper paper name display"""
    paper = get_object_or_404(ModelPaper, id=paper_id)
    student = request.user
    
    print(f"DEBUG: User {student} trying to take paper: {paper.title}")
    print(f"DEBUG: Paper status: {paper.status}")
    print(f"DEBUG: Paper start time: {paper.start_datetime}")
    print(f"DEBUG: Paper end time: {paper.end_datetime}")
    print(f"DEBUG: Current time: {timezone.now()}")
    
    # Check if paper is active
    now = timezone.now()
    if paper.status != 'live':
        messages.error(request, f"This paper is not currently available. Status: {paper.status}")
        print(f"DEBUG: Paper blocked - status is {paper.status}, not 'live'")
        return redirect('student_model_papers')
    
    # Check time bounds
    if now < paper.start_datetime:
        messages.error(request, "This paper has not started yet.")
        print(f"DEBUG: Paper blocked - hasn't started yet")
        return redirect('student_model_papers')
    
    if now > paper.end_datetime:
        messages.error(request, "This paper has already ended.")
        print(f"DEBUG: Paper blocked - already ended")
        return redirect('student_model_papers')
    
    # Check attempt limit
    existing_attempts = ModelPaperAttempt.objects.filter(
        student=student, 
        model_paper=paper,
        status='completed'
    ).count()
    
    print(f"DEBUG: User has {existing_attempts} completed attempts out of {paper.max_attempts} allowed")
    
    if existing_attempts >= paper.max_attempts:
        messages.error(request, f"You have reached the maximum attempts ({paper.max_attempts}) for this paper.")
        print(f"DEBUG: Paper blocked - max attempts reached")
        return redirect('student_model_papers')
    
    # Get or create current attempt
    current_attempt = ModelPaperAttempt.objects.filter(
        student=student,
        model_paper=paper,
        status='in_progress'
    ).first()
    
    if not current_attempt:
        # Create new attempt
        current_attempt = ModelPaperAttempt.objects.create(
            student=student,
            model_paper=paper,
            status='in_progress',
            started_at=timezone.now()
        )
        print(f"DEBUG: Created new attempt with ID: {current_attempt.id}")
    else:
        print(f"DEBUG: Found existing attempt with ID: {current_attempt.id}")
    
    # Get questions based on paper filters
    paper_questions = paper.get_questions()
    
    if paper_questions.count() == 0:
        messages.error(request, "This paper has no questions configured.")
        print(f"DEBUG: Paper blocked - no questions found")
        return redirect('student_model_papers')
    
    # Process questions with enhanced image handling
    processed_questions = []
    for pq in paper_questions:
        question_data = {
            'id': pq.id,
            'order': len(processed_questions) + 1,
            'text': pq.question_text,
            'explanation': pq.explanation or '',
            'options': {},
            'has_image': bool(pq.image),
            'image_url': None,
            'image_filename': pq.image if pq.image else None
        }
        
        # Handle image URL generation with improved matching
        if pq.image:
            image_url, actual_filename = get_paper_question_image_url(pq)
            if image_url:
                question_data['image_url'] = image_url
                question_data['image_filename'] = actual_filename
                print(f"DEBUG: Found image for paper question {pq.id}: {image_url}")
            else:
                print(f"DEBUG: Image not found for paper question {pq.id}: {pq.image}")
        
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
        print(f"DEBUG: Questions randomized")
    
    print(f"DEBUG: Proceeding to paper page with attempt ID: {current_attempt.id}")
    print(f"DEBUG: Processed {len(processed_questions)} questions")
    
    context = {
        'paper': paper,
        'attempt': current_attempt,
        'paper_questions': processed_questions,
        'total_questions': len(processed_questions),
    }
    
    return render(request, 'modelpaper/take_paper.html', context)


@require_POST
def submit_paper_answer(request):
    """Save student's answer for paper question"""
    attempt_id = request.POST.get('attempt_id')
    question_id = request.POST.get('question_id')
    answer = request.POST.get('answer')
    
    attempt = get_object_or_404(ModelPaperAttempt, id=attempt_id)
    paper_question = get_object_or_404(PaperQuestion, id=question_id)
    
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
    
    return JsonResponse({'success': True})


@require_POST
def submit_paper(request):
    """Submit the complete paper"""
    attempt_id = request.POST.get('attempt_id')
    attempt = get_object_or_404(ModelPaperAttempt, id=attempt_id)
    
    # Calculate score
    total_questions = attempt.model_paper.total_questions
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
def paper_result(request, attempt_id):
    """Show paper results with enhanced data and security - Enhanced Version"""
    attempt = get_object_or_404(ModelPaperAttempt, id=attempt_id)
    
    # Security check: Only allow the student who took the paper to view results
    if attempt.student != request.user:
        messages.error(request, "You can only view your own paper results.")
        return redirect('student_model_papers')
    
    # Ensure the paper is actually completed
    if attempt.status == 'in_progress':
        messages.warning(request, "This paper is still in progress.")
        return redirect('take_paper', paper_id=attempt.model_paper.id)
    
    # Get all responses with questions, including unanswered ones
    all_questions = attempt.model_paper.get_questions()
    responses = []
    
    for paper_question in all_questions:
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
        responses.append(response)
    
    # Calculate additional statistics
    total_questions = len(responses)
    answered_questions = len([r for r in responses if r.selected_answer])
    unanswered_questions = total_questions - answered_questions
    correct_answers = len([r for r in responses if r.is_correct])
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
        'grade': get_grade(float(attempt.percentage)),
        
        # Calculated time values (not setting as properties)
        'time_taken_display': time_taken_display,
        'time_taken_formatted': time_taken_formatted,
        'time_taken_minutes': time_taken_minutes,
        
        # For template calculations
        'current_year': timezone.now().year,
    }
    
    return render(request, 'modelpaper/paper_results.html', context)


@require_POST
def report_warning(request):
    """Report tab switch warning for paper"""
    attempt_id = request.POST.get('attempt_id')
    attempt = get_object_or_404(ModelPaperAttempt, id=attempt_id)
    
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
            'message': 'Paper auto-submitted due to multiple tab switches.'
        })
    
    return JsonResponse({
        'success': True,
        'warning_count': attempt.warning_count,
        'remaining_warnings': 3 - attempt.warning_count
    })


@login_required
def student_paper_progress(request):
    """Student progress tracking for model papers"""
    user = request.user
    attempts = ModelPaperAttempt.objects.filter(student=user).select_related('model_paper').order_by('-started_at')
    
    # Calculate stats
    completed_attempts = attempts.filter(status='completed')
    total_papers = attempts.count()
    best_score = completed_attempts.aggregate(Max('percentage'))['percentage__max'] or 0
    avg_score = completed_attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0
    avg_time = completed_attempts.aggregate(Avg('time_taken'))['time_taken__avg'] or 0
    
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
        
        month_attempts = completed_attempts.filter(
            completed_at__gte=month_end,
            completed_at__lt=month_start
        )
        
        month_avg = month_attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0
        
        monthly_data.append({
            'month': month_end.strftime('%b %Y'),
            'attempts': month_attempts.count(),
            'avg_score': round(month_avg, 1)
        })
        
        current_date = month_end
    
    monthly_data.reverse()  # Show oldest to newest
    
    # Get paper-wise performance (by paper name)
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
    
    # Get recent activity (last 10 attempts)
    recent_attempts = attempts[:10]
    
    # Calculate improvement trend (comparing first half vs second half of attempts)
    if completed_attempts.count() >= 4:
        half_point = completed_attempts.count() // 2
        recent_half = list(completed_attempts[:half_point])
        older_half = list(completed_attempts[half_point:])
        
        recent_avg = sum(a.percentage for a in recent_half) / len(recent_half)
        older_avg = sum(a.percentage for a in older_half) / len(older_half)
        
        improvement = recent_avg - older_avg
    else:
        improvement = 0
    
    context = {
        'attempts': attempts,
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
    }
    
    return render(request, 'modelpaper/student_progress.html', context)


# API endpoints
def get_paper_question_counts(request):
    """API to get question counts for paper name filters"""
    paper_name = request.GET.get('paper_name')
    
    if not paper_name:
        return JsonResponse({'error': 'Paper name required'}, status=400)
    
    questions = PaperQuestion.objects.filter(paper_name=paper_name)
    
    # Get filter options
    filter_options = PaperQuestion.get_paper_filter_options(paper_name)
    
    return JsonResponse({
        'total_questions': questions.count(),
        'filters': filter_options
    })


def get_filtered_question_count(request):
    """API to get question count based on filters"""
    paper_name = request.GET.get('paper_name')
    degree = request.GET.get('degree')
    year = request.GET.get('year')
    module = request.GET.get('module')
    subject = request.GET.get('subject')
    topic = request.GET.get('topic')
    
    if not paper_name:
        return JsonResponse({'error': 'Paper name required'}, status=400)
    
    count = PaperQuestion.get_filtered_questions(
        paper_name=paper_name,
        degree=degree,
        year=year,
        module=module,
        subject=subject,
        topic=topic
    ).count()
    
    return JsonResponse({'count': count})


# Export functionality
@login_required
def export_paper_questions(request, paper_id):
    """Export questions for a specific paper as CSV"""
    paper = get_object_or_404(ModelPaper, id=paper_id)
    questions = paper.get_questions()
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{paper.title.replace(" ", "_")}_questions.csv"'
    
    writer = csv.writer(response)
    
    # Write header with metadata
    writer.writerow([f'# Model Paper: {paper.title}'])
    writer.writerow([f'# Paper Name: {paper.selected_paper_name}'])
    writer.writerow([f'# Total Questions: {paper.total_questions}'])
    writer.writerow([f'# Exported: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([])  # Empty row
    
    # Write column headers
    writer.writerow([
        'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'option_e', 
        'correct_answer', 'paper_name', 'degree', 'year', 'module', 'subject', 'topic',
        'difficulty', 'explanation', 'image', 'marks'
    ])
    
    # Write questions
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
            question.image,
            question.marks
        ])
    
    return response

