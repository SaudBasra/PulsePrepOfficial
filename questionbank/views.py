# questionbank/views.py - COMPLETE: Updated with CSV deletion functionality

import json
import io
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .models import Question, CSVImportHistory
from .forms import QuestionForm, QuestionImportForm

# Import model paper models if available
try:
    from modelpaper.models import PaperQuestion, PaperCSVImportHistory
    from modelpaper.forms import PaperQuestionImportForm
    MODELPAPER_AVAILABLE = True
except ImportError:
    MODELPAPER_AVAILABLE = False
    PaperQuestion = None
    PaperCSVImportHistory = None
    PaperQuestionImportForm = None

# Get the custom user model
User = get_user_model()


def questionbank(request):
    """View to display all questions with search and filter"""
    query = request.GET.get('q', '')
    filter_block = request.GET.get('block', '')
    filter_degree = request.GET.get('degree', '')
    filter_difficulty = request.GET.get('difficulty', '')
    filter_type = request.GET.get('type', '')
    
    questions = Question.objects.all().order_by('-created_on')
    
    # Apply search query if provided
    if query:
        questions = questions.filter(
            Q(question_text__icontains=query) |
            Q(block__icontains=query) |
            Q(module__icontains=query) |
            Q(subject__icontains=query) |
            Q(topic__icontains=query)
        )
    
    # Apply filters if provided
    if filter_block:
        questions = questions.filter(block__icontains=filter_block)
    
    if filter_degree:
        questions = questions.filter(degree=filter_degree)
    
    if filter_difficulty:
        questions = questions.filter(difficulty=filter_difficulty)
    
    if filter_type:
        questions = questions.filter(question_type=filter_type)
    
    # Pagination
    paginator = Paginator(questions, 10)  # Show 10 questions per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get distinct values for filters
    blocks = Question.objects.values_list('block', flat=True).distinct().order_by('block')
    
    # Get analytics data
    analytics = Question.get_stats()
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'filter_block': filter_block,
        'filter_degree': filter_degree,
        'filter_difficulty': filter_difficulty,
        'filter_type': filter_type,
        'blocks': blocks,
        'degree_choices': Question.DEGREE_CHOICES,
        'difficulty_choices': Question.DIFFICULTY_CHOICES,
        'type_choices': Question.QUESTION_TYPE_CHOICES,
        'analytics': analytics,
    }
    
    return render(request, 'questionbank/questionbank.html', context)


def question_detail(request, pk=None):
    """View to create a new question or edit an existing one"""
    if pk:
        question = get_object_or_404(Question, pk=pk)
        form_title = "Edit Question"
    else:
        question = None
        form_title = "Add New Question"
    
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            question = form.save(commit=False)
            
            # Use the first superuser as the creator
            superusers = User.objects.filter(is_superuser=True)
            if superusers.exists():
                question.created_by = superusers.first()
            else:
                question.created_by = None
            
            question.save()
            messages.success(request, "Question saved successfully!")
            return redirect('questionbank')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = QuestionForm(instance=question)
    
    context = {
        'form': form,
        'question': question,
        'form_title': form_title,
    }
    
    return render(request, 'questionbank/question_detail.html', context)


def delete_question(request, pk):
    """View to delete a question"""
    question = get_object_or_404(Question, pk=pk)
    
    if request.method == 'POST':
        question.delete()
        messages.success(request, "Question deleted successfully!")
        return redirect('questionbank')
    
    context = {
        'question': question,
    }
    
    return render(request, 'questionbank/delete_question.html', context)


def import_questions(request):
    """Legacy view for basic CSV import - kept for backward compatibility"""
    if request.method == 'POST':
        form = QuestionImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Check if file is CSV
            if not csv_file.name.endswith('.csv'):
                return JsonResponse({'error': 'Please upload a CSV file'}, status=400)
            
            # Process CSV file
            try:
                decoded_file = csv_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)

                # Get superuser to assign as creator
                creator = None
                superusers = User.objects.filter(is_superuser=True)
                if superusers.exists():
                    creator = superusers.first()
                
                question_count = 0
                for row in reader:
                    # Handle image fields
                    question_image_filename = str(row.get('question_image', '')).strip()
                    explanation_image_filename = str(row.get('image', '')).strip()
                    
                    # Create question from CSV row
                    Question.objects.create(
                        question_text=row.get('question_text', ''),
                        question_type=row.get('question_type', 'MCQ'),
                        option_a=row.get('option_a', ''),
                        option_b=row.get('option_b', ''),
                        option_c=row.get('option_c', ''),
                        option_d=row.get('option_d', ''),
                        option_e=row.get('option_e', ''),
                        correct_answer=row.get('correct_answer', ''),
                        degree=row.get('degree', 'MBBS'),
                        year=row.get('year', '1st'),
                        block=row.get('block', ''),
                        module=row.get('module', ''),
                        subject=row.get('subject', ''),
                        topic=row.get('topic', ''),
                        difficulty=row.get('difficulty', 'Medium'),
                        explanation=row.get('explanation', ''),
                        question_image=question_image_filename or None,
                        image=explanation_image_filename or None,
                        created_by=creator
                    )
                    question_count += 1
                
                return JsonResponse({'count': question_count})
                
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
        else:
            return JsonResponse({'error': 'Invalid form submission'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# questionbank/views.py - Enhanced manage_csv view with pagination and detailed delete info

def manage_csv(request):
    """Enhanced CSV management view with pagination and detailed delete confirmation"""
    
    # Get questionbank statistics
    questionbank_total_imports = CSVImportHistory.objects.count()
    questionbank_successful_imports = CSVImportHistory.objects.filter(status='SUCCESS').count()
    questionbank_failed_imports = CSVImportHistory.objects.filter(status='FAILED').count()
    questionbank_total_questions_imported = CSVImportHistory.objects.filter(status='SUCCESS').aggregate(
        total=models.Sum('successful_imports')
    )['total'] or 0
    
    # Get model paper statistics if available
    modelpaper_stats = {
        'total_imports': 0,
        'successful_imports': 0,
        'failed_imports': 0,
        'total_paper_names': 0,
        'success_rate': 0
    }
    
    if MODELPAPER_AVAILABLE:
        modelpaper_total_imports = PaperCSVImportHistory.objects.count()
        modelpaper_successful_imports = PaperCSVImportHistory.objects.filter(status='SUCCESS').count()
        modelpaper_failed_imports = PaperCSVImportHistory.objects.filter(status='FAILED').count()
        modelpaper_total_paper_names = PaperQuestion.objects.values('paper_name').distinct().count()
        
        modelpaper_stats = {
            'total_imports': modelpaper_total_imports,
            'successful_imports': modelpaper_successful_imports,
            'failed_imports': modelpaper_failed_imports,
            'total_paper_names': modelpaper_total_paper_names,
            'success_rate': round((modelpaper_successful_imports / modelpaper_total_imports * 100), 1) if modelpaper_total_imports > 0 else 0
        }
    
    # PAGINATION FOR IMPORT HISTORY
    # Get questionbank history with pagination
    questionbank_history_queryset = CSVImportHistory.objects.all().order_by('-uploaded_at')
    questionbank_paginator = Paginator(questionbank_history_queryset, 10)  # 10 per page
    questionbank_page = request.GET.get('qb_page', 1)
    questionbank_history_page = questionbank_paginator.get_page(questionbank_page)
    
    # Get modelpaper history with pagination
    modelpaper_history_page = None
    if MODELPAPER_AVAILABLE:
        modelpaper_history_queryset = PaperCSVImportHistory.objects.all().order_by('-uploaded_at')
        modelpaper_paginator = Paginator(modelpaper_history_queryset, 10)  # 10 per page
        modelpaper_page = request.GET.get('mp_page', 1)
        modelpaper_history_page = modelpaper_paginator.get_page(modelpaper_page)
    
    # ENHANCED DELETION IMPACT CALCULATION
    # For each record, calculate detailed impact information
    questionbank_history_enhanced = []
    for record in questionbank_history_page:
        # Calculate import time range for finding associated questions
        time_buffer = timedelta(minutes=5)
        start_time = record.uploaded_at - time_buffer
        end_time = record.uploaded_at + time_buffer
        
        # Find associated questions
        associated_questions = Question.objects.filter(
            created_on__range=(start_time, end_time),
            created_by=record.uploaded_by
        )
        
        if not record.uploaded_by:
            associated_questions = Question.objects.filter(
                created_on__range=(start_time, end_time)
            )
        
        # Calculate impact details
        question_count = associated_questions.count()
        affected_blocks = list(associated_questions.values_list('block', flat=True).distinct()[:5])
        affected_subjects = list(associated_questions.values_list('subject', flat=True).distinct()[:5])
        questions_with_images = associated_questions.exclude(
            Q(question_image__isnull=True) | Q(question_image__exact='') |
            Q(image__isnull=True) | Q(image__exact='')
        ).count()
        
        # Calculate time since import
        time_since_import = timezone.now() - record.uploaded_at
        days_ago = time_since_import.days
        hours_ago = time_since_import.seconds // 3600
        
        record_enhanced = {
            'record': record,
            'deletion_impact': {
                'question_count': question_count,
                'affected_blocks': affected_blocks,
                'affected_subjects': affected_subjects,
                'questions_with_images': questions_with_images,
                'days_ago': days_ago,
                'hours_ago': hours_ago,
                'is_recent': days_ago < 7,  # Recent if within a week
                'is_large_import': question_count > 50,  # Large if > 50 questions
            }
        }
        questionbank_history_enhanced.append(record_enhanced)
    
    # Enhanced modelpaper history
    modelpaper_history_enhanced = []
    if MODELPAPER_AVAILABLE and modelpaper_history_page:
        for record in modelpaper_history_page:
            time_buffer = timedelta(minutes=5)
            start_time = record.uploaded_at - time_buffer
            end_time = record.uploaded_at + time_buffer
            
            associated_questions = PaperQuestion.objects.filter(
                created_at__range=(start_time, end_time),
                created_by=record.uploaded_by
            )
            
            if not record.uploaded_by:
                associated_questions = PaperQuestion.objects.filter(
                    created_at__range=(start_time, end_time)
                )
            
            # Calculate impact details
            question_count = associated_questions.count()
            affected_papers = list(associated_questions.values_list('paper_name', flat=True).distinct())
            affected_subjects = list(associated_questions.values_list('subject', flat=True).distinct()[:5])
            questions_with_images = associated_questions.exclude(
                Q(paper_image__isnull=True) | Q(paper_image__exact='') |
                Q(image__isnull=True) | Q(image__exact='')
            ).count()
            
            time_since_import = timezone.now() - record.uploaded_at
            days_ago = time_since_import.days
            hours_ago = time_since_import.seconds // 3600
            
            record_enhanced = {
                'record': record,
                'deletion_impact': {
                    'question_count': question_count,
                    'affected_papers': affected_papers,
                    'affected_subjects': affected_subjects,
                    'questions_with_images': questions_with_images,
                    'days_ago': days_ago,
                    'hours_ago': hours_ago,
                    'is_recent': days_ago < 7,
                    'is_large_import': question_count > 30,  # Large if > 30 questions for papers
                }
            }
            modelpaper_history_enhanced.append(record_enhanced)
    
    context = {
        'questionbank_stats': {
            'total_imports': questionbank_total_imports,
            'successful_imports': questionbank_successful_imports,
            'failed_imports': questionbank_failed_imports,
            'total_questions_imported': questionbank_total_questions_imported,
            'success_rate': round((questionbank_successful_imports / questionbank_total_imports * 100), 1) if questionbank_total_imports > 0 else 0
        },
        'modelpaper_stats': modelpaper_stats,
        
        # ENHANCED PAGINATION DATA
        'questionbank_history': questionbank_history_enhanced,
        'questionbank_history_page': questionbank_history_page,
        'modelpaper_history': modelpaper_history_enhanced,
        'modelpaper_history_page': modelpaper_history_page,
        'modelpaper_available': MODELPAPER_AVAILABLE,
        
        # PAGINATION INFO
        'show_pagination': (
            questionbank_history_page.paginator.num_pages > 1 or 
            (modelpaper_history_page and modelpaper_history_page.paginator.num_pages > 1)
        ),
    }
    
    return render(request, 'questionbank/manage_csv.html', context)


# API endpoint to get detailed deletion impact for AJAX requests
def get_deletion_impact_api(request, record_id):
    """API endpoint to get detailed deletion impact information"""
    try:
        import_type = request.GET.get('type', 'questionbank')
        
        if import_type == 'questionbank':
            record = get_object_or_404(CSVImportHistory, id=record_id)
            
            # Calculate impact
            time_buffer = timedelta(minutes=5)
            start_time = record.uploaded_at - time_buffer
            end_time = record.uploaded_at + time_buffer
            
            associated_questions = Question.objects.filter(
                created_on__range=(start_time, end_time),
                created_by=record.uploaded_by
            )
            
            if not record.uploaded_by:
                associated_questions = Question.objects.filter(
                    created_on__range=(start_time, end_time)
                )
            
            # Detailed impact analysis
            impact_data = {
                'total_questions': associated_questions.count(),
                'by_degree': list(associated_questions.values('degree').annotate(count=models.Count('id'))),
                'by_difficulty': list(associated_questions.values('difficulty').annotate(count=models.Count('id'))),
                'affected_blocks': list(associated_questions.values_list('block', flat=True).distinct()),
                'affected_modules': list(associated_questions.values_list('module', flat=True).distinct()),
                'affected_subjects': list(associated_questions.values_list('subject', flat=True).distinct()),
                'questions_with_images': associated_questions.exclude(
                    Q(question_image__isnull=True) | Q(question_image__exact='') |
                    Q(image__isnull=True) | Q(image__exact='')
                ).count(),
                'import_date': record.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                'days_since_import': (timezone.now() - record.uploaded_at).days,
            }
            
        elif import_type == 'modelpaper' and MODELPAPER_AVAILABLE:
            record = get_object_or_404(PaperCSVImportHistory, id=record_id)
            
            time_buffer = timedelta(minutes=5)
            start_time = record.uploaded_at - time_buffer
            end_time = record.uploaded_at + time_buffer
            
            associated_questions = PaperQuestion.objects.filter(
                created_at__range=(start_time, end_time),
                created_by=record.uploaded_by
            )
            
            if not record.uploaded_by:
                associated_questions = PaperQuestion.objects.filter(
                    created_at__range=(start_time, end_time)
                )
            
            impact_data = {
                'total_questions': associated_questions.count(),
                'by_degree': list(associated_questions.values('degree').annotate(count=models.Count('id'))),
                'by_difficulty': list(associated_questions.values('difficulty').annotate(count=models.Count('id'))),
                'affected_papers': list(associated_questions.values_list('paper_name', flat=True).distinct()),
                'affected_modules': list(associated_questions.values_list('module', flat=True).distinct()),
                'affected_subjects': list(associated_questions.values_list('subject', flat=True).distinct()),
                'questions_with_images': associated_questions.exclude(
                    Q(paper_image__isnull=True) | Q(paper_image__exact='') |
                    Q(image__isnull=True) | Q(image__exact='')
                ).count(),
                'import_date': record.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                'days_since_import': (timezone.now() - record.uploaded_at).days,
            }
        else:
            return JsonResponse({'error': 'Invalid import type'}, status=400)
        
        return JsonResponse({
            'success': True,
            'impact': impact_data,
            'file_name': record.file_name,
            'import_type': import_type
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
def import_questions_with_history(request):
    """Enhanced CSV import that handles both QuestionBank and Model Paper imports"""
    if request.method == 'POST':
        import_type = request.POST.get('import_type', 'questionbank')
        
        if import_type == 'questionbank':
            return import_to_questionbank(request)
        elif import_type == 'modelpaper' and MODELPAPER_AVAILABLE:
            return import_to_modelpaper(request)
        else:
            return JsonResponse({'error': 'Invalid import type'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def import_to_questionbank(request):
    """Import questions to questionbank with image support"""
    form = QuestionImportForm(request.POST, request.FILES)
    if form.is_valid():
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'error': 'Please upload a CSV file'}, status=400)
        
        # Create import history record
        import_record = CSVImportHistory.objects.create(
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
            
            # Get superuser to assign as creator
            creator = None
            superusers = User.objects.filter(is_superuser=True)
            if superusers.exists():
                creator = superusers.first()
            
            question_count = 0
            error_count = 0
            total_rows = 0
            errors = []
            
            # Store import start time for tracking imported questions
            import_start_time = import_record.uploaded_at
            
            for row_num, row in enumerate(reader, start=1):
                total_rows += 1
                try:
                    # Handle different column name variations
                    question_text = str(row.get('question_text', '') or row.get('Question', '') or row.get('question', '')).strip()
                    
                    if not question_text:
                        errors.append(f"Row {row_num}: Missing question text")
                        error_count += 1
                        continue
                    
                    # Clean and validate question type
                    question_type = str(row.get('question_type', 'MCQ')).strip()
                    if question_type not in ['MCQ', 'SEQ', 'NOTE']:
                        question_type = 'MCQ'
                    
                    # Handle options with better cleaning
                    option_a = str(row.get('option_a', '') or row.get('option_A', '') or row.get('Option_A', '') or '').strip()
                    option_b = str(row.get('option_b', '') or row.get('option_B', '') or row.get('Option_B', '') or '').strip()
                    option_c = str(row.get('option_c', '') or row.get('option_C', '') or row.get('Option_C', '') or '').strip()
                    option_d = str(row.get('option_d', '') or row.get('option_D', '') or row.get('Option_D', '') or '').strip()
                    option_e = str(row.get('option_e', '') or row.get('option_E', '') or row.get('Option_E', '') or '').strip()
                    
                    # Handle correct answer
                    correct_answer = str(row.get('correct_answer', '') or row.get('correct_option', '') or row.get('Correct_Answer', '') or row.get('answer', '') or '').strip().upper()
                    if correct_answer not in ['A', 'B', 'C', 'D', 'E']:
                        correct_answer = ''
                    
                    # Clean categorization fields
                    degree = str(row.get('degree', 'MBBS')).strip().upper()
                    if degree not in ['MBBS', 'BDS']:
                        degree = 'MBBS'
                    
                    year = str(row.get('year', '1st')).strip()
                    if year not in ['1st', '2nd', '3rd', '4th', '5th']:
                        year = '1st'
                    
                    # Handle difficulty with proper case conversion
                    difficulty_raw = str(row.get('difficulty', 'Medium')).strip()
                    if difficulty_raw.lower() == 'easy':
                        difficulty = 'Easy'
                    elif difficulty_raw.lower() == 'medium':
                        difficulty = 'Medium'
                    elif difficulty_raw.lower() == 'hard':
                        difficulty = 'Hard'
                    elif difficulty_raw in ['Easy', 'Medium', 'Hard']:
                        difficulty = difficulty_raw
                    else:
                        difficulty = 'Medium'
                    
                    # Handle image fields properly (Support both question_image and image)
                    question_image_filename = str(row.get('question_image', '')).strip()
                    explanation_image_filename = str(row.get('image', '')).strip()
                    
                    # ENHANCED DUPLICATE DETECTION
                    is_duplicate, duplicate_reason = enhanced_duplicate_detection_questionbank(
                        question_text, option_a, option_b, option_c, option_d, option_e
                    )
                    
                    if is_duplicate:
                        errors.append(f"Row {row_num}: {duplicate_reason} - '{question_text[:50]}...'")
                        error_count += 1
                        continue
                    
                    # Create question with image fields
                    Question.objects.create(
                        question_text=question_text,
                        question_type=question_type,
                        option_a=option_a or None,
                        option_b=option_b or None,
                        option_c=option_c or None,
                        option_d=option_d or None,
                        option_e=option_e or None,
                        correct_answer=correct_answer or None,
                        degree=degree,
                        year=year,
                        block=str(row.get('block', 'General')).strip() or 'General',
                        module=str(row.get('module', 'General')).strip() or 'General',
                        subject=str(row.get('subject', 'General')).strip() or 'General',
                        topic=str(row.get('topic', 'General')).strip() or 'General',
                        difficulty=difficulty,
                        explanation=str(row.get('explanation', '')).strip() or None,
                        question_image=question_image_filename or None,  # Question image
                        image=explanation_image_filename or None,  # Explanation image
                        created_by=creator,
                        created_on=import_start_time  # Use import time for tracking
                    )
                    question_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    error_count += 1
            
            # Update import record
            import_record.total_rows = total_rows
            import_record.successful_imports = question_count
            import_record.failed_imports = error_count
            import_record.status = 'SUCCESS' if error_count == 0 else ('FAILED' if question_count == 0 else 'SUCCESS')
            import_record.error_details = '\n'.join(errors) if errors else None
            import_record.save()
            
            return JsonResponse({
                'success': True,
                'imported': question_count,
                'failed': error_count,
                'total': total_rows,
                'errors': errors[:10] if errors else []
            })
            
        except Exception as e:
            import_record.status = 'FAILED'
            import_record.error_details = str(e)
            import_record.save()
            
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Invalid form submission'}, status=400)


def import_to_modelpaper(request):
    """Import questions to model paper with image support"""
    if not MODELPAPER_AVAILABLE:
        return JsonResponse({'error': 'Model paper functionality not available'}, status=400)
    
    form = PaperQuestionImportForm(request.POST, request.FILES)
    if form.is_valid():
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'error': 'Please upload a CSV file'}, status=400)
        
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
            
            # Store import start time for tracking imported questions
            import_start_time = import_record.uploaded_at
            
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
                    
                    # Handle image fields (paper_image and image)
                    paper_image_filename = str(row.get('paper_image', '')).strip()
                    explanation_image_filename = str(row.get('image', '')).strip()
                    
                    # Enhanced duplicate detection within same paper name
                    is_duplicate, duplicate_reason = enhanced_duplicate_detection_modelpaper(
                        paper_name, question_text, option_a, option_b, option_c, option_d, option_e
                    )
                    
                    if is_duplicate:
                        errors.append(f"Row {row_num}: {duplicate_reason} - '{question_text[:50]}...'")
                        error_count += 1
                        continue
                    
                    # Create paper question with image fields
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
                        created_by=request.user if request.user.is_authenticated else None,
                        created_at=import_start_time  # Use import time for tracking
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


@require_POST
def delete_csv_record(request, record_id):
    """Delete CSV import record and associated questions"""
    try:
        import_type = request.POST.get('import_type', 'questionbank')
        
        if import_type == 'questionbank':
            return delete_questionbank_csv_record(request, record_id)
        elif import_type == 'modelpaper' and MODELPAPER_AVAILABLE:
            return delete_modelpaper_csv_record(request, record_id)
        else:
            return JsonResponse({'error': 'Invalid import type'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def delete_questionbank_csv_record(request, record_id):
    """Delete questionbank CSV record and its associated questions"""
    try:
        with transaction.atomic():
            # Get the import record
            import_record = get_object_or_404(CSVImportHistory, id=record_id)
            
            # Find questions imported from this CSV
            # We'll use the upload time and user to identify questions from this import
            time_buffer = timedelta(minutes=5)  # 5-minute buffer for import duration
            start_time = import_record.uploaded_at - time_buffer
            end_time = import_record.uploaded_at + time_buffer
            
            questions_to_delete = Question.objects.filter(
                created_on__range=(start_time, end_time),
                created_by=import_record.uploaded_by
            )
            
            # If no user, try to find questions created around the import time
            if not import_record.uploaded_by:
                # Find questions created around the exact import time
                questions_to_delete = Question.objects.filter(
                    created_on__range=(start_time, end_time)
                )
            
            # Count questions to be deleted
            questions_count = questions_to_delete.count()
            
            # Delete the questions
            questions_to_delete.delete()
            
            # Delete the import record
            file_name = import_record.file_name
            import_record.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully deleted CSV record "{file_name}" and {questions_count} associated questions.',
                'deleted_questions': questions_count,
                'deleted_csv': file_name
            })
            
    except Exception as e:
        return JsonResponse({'error': f'Error deleting CSV record: {str(e)}'}, status=500)


def delete_modelpaper_csv_record(request, record_id):
    """Delete model paper CSV record and its associated questions"""
    if not MODELPAPER_AVAILABLE:
        return JsonResponse({'error': 'Model paper functionality not available'}, status=400)
    
    try:
        with transaction.atomic():
            # Get the import record
            import_record = get_object_or_404(PaperCSVImportHistory, id=record_id)
            
            # Find questions imported from this CSV
            time_buffer = timedelta(minutes=5)  # 5-minute buffer for import duration
            start_time = import_record.uploaded_at - time_buffer
            end_time = import_record.uploaded_at + time_buffer
            
            questions_to_delete = PaperQuestion.objects.filter(
                created_at__range=(start_time, end_time),
                created_by=import_record.uploaded_by
            )
            
            # If no user, try to find questions created around the import time
            if not import_record.uploaded_by:
                questions_to_delete = PaperQuestion.objects.filter(
                    created_at__range=(start_time, end_time)
                )
            
            # Count questions to be deleted
            questions_count = questions_to_delete.count()
            
            # Get paper names that will be affected
            affected_papers = list(questions_to_delete.values_list('paper_name', flat=True).distinct())
            
            # Delete the questions
            questions_to_delete.delete()
            
            # Delete the import record
            file_name = import_record.file_name
            import_record.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully deleted CSV record "{file_name}" and {questions_count} associated questions.',
                'deleted_questions': questions_count,
                'deleted_csv': file_name,
                'affected_papers': affected_papers
            })
            
    except Exception as e:
        return JsonResponse({'error': f'Error deleting model paper CSV record: {str(e)}'}, status=500)


def enhanced_duplicate_detection_questionbank(question_text, option_a, option_b, option_c, option_d, option_e=None):
    """Enhanced duplicate detection for questionbank questions"""
    # Clean inputs
    question_text = question_text.strip().lower()
    option_a = option_a.strip().lower() if option_a else ""
    option_b = option_b.strip().lower() if option_b else ""
    option_c = option_c.strip().lower() if option_c else ""
    option_d = option_d.strip().lower() if option_d else ""
    option_e = option_e.strip().lower() if option_e else ""
    
    # Check for exact question text match
    exact_question_matches = Question.objects.filter(
        question_text__iexact=question_text
    )
    
    if exact_question_matches.exists():
        return True, "Exact question text match found"
    
    # Check question text + first two options
    if option_a and option_b:
        mcq_matches = Question.objects.filter(
            question_text__icontains=question_text[:30],  # First 30 chars
            option_a__iexact=option_a,
            option_b__iexact=option_b
        )
        
        if mcq_matches.exists():
            return True, "Similar MCQ found with matching options"
    
    return False, None


def enhanced_duplicate_detection_modelpaper(paper_name, question_text, option_a, option_b, option_c, option_d, option_e=None):
    """Enhanced duplicate detection for paper questions within the same paper name"""
    if not MODELPAPER_AVAILABLE:
        return False, None
    
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


def export_questions(request):
    """View to export questions as CSV - Updated with image fields"""
    # Get filtered questions
    query = request.GET.get('q', '')
    filter_block = request.GET.get('block', '')
    filter_degree = request.GET.get('degree', '')
    filter_difficulty = request.GET.get('difficulty', '')
    filter_type = request.GET.get('type', '')
    
    questions = Question.objects.all().order_by('-created_on')
    
    # Apply search query if provided
    if query:
        questions = questions.filter(
            Q(question_text__icontains=query) |
            Q(block__icontains=query) |
            Q(module__icontains=query) |
            Q(subject__icontains=query) |
            Q(topic__icontains=query)
        )
    
    # Apply filters if provided
    if filter_block:
        questions = questions.filter(block__icontains=filter_block)
    
    if filter_degree:
        questions = questions.filter(degree=filter_degree)
    
    if filter_difficulty:
        questions = questions.filter(difficulty=filter_difficulty)
    
    if filter_type:
        questions = questions.filter(question_type=filter_type)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="pulseprep_questions.csv"'
    
    writer = csv.writer(response)
    
    # CSV headers with image fields
    writer.writerow([
        'question_text', 'question_type', 
        'option_a', 'option_b', 'option_c', 'option_d', 'option_e', 'correct_answer',
        'degree', 'year', 'block', 'module', 'subject', 'topic',
        'difficulty', 'explanation', 'question_image', 'image', 'created_on'
    ])
    
    for question in questions:
        writer.writerow([
            question.question_text, question.question_type,
            question.option_a, question.option_b, question.option_c, question.option_d, question.option_e, question.correct_answer,
            question.degree, question.year, question.block, question.module, question.subject, question.topic,
            question.difficulty, question.explanation, 
            question.question_image or '', question.image or '', question.created_on
        ])
    
    return response


def export_modelpaper_questions(request, paper_name):
    """Export model paper questions by paper name with image support"""
    if not MODELPAPER_AVAILABLE:
        return JsonResponse({'error': 'Model paper functionality not available'}, status=400)
    
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


# Additional utility functions for CSV management

def get_csv_template_data():
    """Generate CSV template data for downloads"""
    templates = {
        'questionbank-basic': {
            'filename': 'questionbank_template_basic.csv',
            'headers': ['question_text', 'question_type', 'degree', 'year', 'block', 'module', 'subject', 'topic', 'difficulty', 'explanation', 'question_image', 'image'],
            'sample_data': [
                ["What is the normal heart rate range for a healthy adult?", "MCQ", "MBBS", "1st", "Cardiovascular", "Physiology", "Cardiology", "Heart Rate", "Easy", "Normal adult heart rate is 60-100 beats per minute at rest.", "heart_rate_diagram.jpg", "heart_rate_explanation.jpg"],
                ["Describe the pathophysiology of myocardial infarction", "SEQ", "MBBS", "3rd", "Cardiovascular", "Pathology", "Cardiology", "Myocardial Infarction", "Hard", "MI occurs due to coronary artery occlusion leading to myocardial cell death.", "", "mi_pathology_detailed.png"],
                ["Anatomy of the human heart chambers", "NOTE", "MBBS", "1st", "Cardiovascular", "Anatomy", "Cardiology", "Heart Anatomy", "Medium", "Study notes on the four chambers of the heart and their functions.", "heart_chambers_labeled.jpg", ""]
            ]
        },
        'questionbank-mcq': {
            'filename': 'questionbank_template_mcq.csv',
            'headers': ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'option_e', 'correct_answer', 'degree', 'year', 'block', 'module', 'subject', 'topic', 'difficulty', 'explanation', 'question_image', 'image'],
            'sample_data': [
                ["What is the normal blood pressure reading for adults?", "120/80 mmHg", "140/90 mmHg", "160/100 mmHg", "100/60 mmHg", "180/110 mmHg", "A", "MBBS", "1st", "Cardiovascular", "Physiology", "Cardiology", "Blood Pressure", "Easy", "Normal blood pressure is approximately 120/80 mmHg for healthy adults.", "bp_measurement_diagram.jpg", "bp_ranges_chart.jpg"],
                ["Which tooth is shown in the radiograph?", "Central Incisor", "Lateral Incisor", "Canine", "First Premolar", "Second Premolar", "C", "BDS", "2nd", "Oral", "Radiology", "Dentistry", "Tooth Identification", "Medium", "Canine teeth have characteristic single pointed crown and long root.", "dental_xray_canine.png", "canine_anatomy.jpg"],
                ["The structure indicated by the arrow is:", "Left Ventricle", "Right Atrium", "Aortic Arch", "Pulmonary Trunk", "Superior Vena Cava", "A", "MBBS", "1st", "Cardiovascular", "Anatomy", "Cardiology", "Heart Anatomy", "Medium", "The left ventricle is the main pumping chamber with thick muscular walls.", "heart_anatomy_labeled.jpg", "ventricle_detail.png"]
            ]
        }
    }
    
    if MODELPAPER_AVAILABLE:
        templates['modelpaper-medical'] = {
            'filename': 'modelpaper_medical_template.csv',
            'headers': ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'option_e', 'correct_answer', 'paper_name', 'degree', 'year', 'module', 'subject', 'topic', 'difficulty', 'explanation', 'paper_image', 'image', 'marks'],
            'sample_data': [
                ["The ECG shown indicates:", "Normal Sinus Rhythm", "Atrial Fibrillation", "Ventricular Tachycardia", "Complete Heart Block", "ST Elevation MI", "E", "MBBS Final Exam 2024", "MBBS", "4th", "Cardiology", "Medicine", "ECG Interpretation", "Hard", "ST elevation in leads II, III, aVF indicates inferior wall MI.", "ecg_stemi_inferior.jpg", "ecg_mi_explanation.png", "2"],
                ["Identify the dental restoration material shown:", "Amalgam", "Composite Resin", "Glass Ionomer", "Gold Inlay", "Ceramic Crown", "B", "BDS Final Exam 2024", "BDS", "4th", "Restorative", "Dentistry", "Dental Materials", "Medium", "Composite resin appears tooth-colored and blends with natural enamel.", "composite_restoration.png", "composite_properties_chart.jpg", "1"],
                ["The radiological finding shows:", "Normal Chest X-ray", "Pneumothorax", "Pleural Effusion", "Pneumonia", "Pulmonary Edema", "C", "MBBS Midterm 2024", "MBBS", "3rd", "Respiratory", "Medicine", "Chest Radiology", "Medium", "Pleural effusion appears as fluid collection in the pleural space.", "chest_xray_effusion.jpg", "pleural_anatomy.png", "2"],
                ["Which periodontal instrument is shown?", "Periodontal Probe", "Curette", "Scaler", "Explorer", "Furcation Probe", "A", "BDS Midterm 2024", "BDS", "3rd", "Periodontics", "Dentistry", "Periodontal Instruments", "Easy", "Periodontal probe is used to measure pocket depths and has millimeter markings.", "perio_probe.jpg", "probe_technique.png", "1"],
                ["The histological section demonstrates:", "Normal Liver Tissue", "Fatty Liver", "Cirrhosis", "Hepatitis", "Liver Cancer", "C", "MBBS Pathology Exam 2024", "MBBS", "2nd", "Pathology", "Medicine", "Liver Pathology", "Hard", "Cirrhosis shows fibrous bands dividing liver into regenerative nodules.", "liver_cirrhosis_histo.jpg", "cirrhosis_stages.png", "3"]
            ]
        }
    
    return templates


def get_import_statistics():
    """Get comprehensive import statistics for both question types"""
    stats = {
        'questionbank': {
            'total_imports': CSVImportHistory.objects.count(),
            'successful_imports': CSVImportHistory.objects.filter(status='SUCCESS').count(),
            'failed_imports': CSVImportHistory.objects.filter(status='FAILED').count(),
            'total_questions': CSVImportHistory.objects.filter(status='SUCCESS').aggregate(
                total=models.Sum('successful_imports')
            )['total'] or 0,
            'recent_imports': CSVImportHistory.objects.filter(
                uploaded_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
        }
    }
    
    if MODELPAPER_AVAILABLE:
        stats['modelpaper'] = {
            'total_imports': PaperCSVImportHistory.objects.count(),
            'successful_imports': PaperCSVImportHistory.objects.filter(status='SUCCESS').count(),
            'failed_imports': PaperCSVImportHistory.objects.filter(status='FAILED').count(),
            'total_questions': PaperCSVImportHistory.objects.filter(status='SUCCESS').aggregate(
                total=models.Sum('successful_imports')
            )['total'] or 0,
            'paper_names': PaperQuestion.objects.values('paper_name').distinct().count(),
            'recent_imports': PaperCSVImportHistory.objects.filter(
                uploaded_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
        }
    else:
        stats['modelpaper'] = {
            'total_imports': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'total_questions': 0,
            'paper_names': 0,
            'recent_imports': 0,
        }
    
    return stats


def validate_csv_structure(csv_file, import_type='questionbank'):
    """Validate CSV structure before processing"""
    try:
        # Read first few lines to check structure
        csv_file.seek(0)
        sample = csv_file.read(1024).decode('utf-8')
        csv_file.seek(0)
        
        # Basic validations
        if not sample:
            return False, "Empty file"
        
        # Check for common CSV issues
        if '\t' in sample and ',' not in sample:
            return False, "File appears to be tab-separated. Please use comma-separated format."
        
        # Try to parse headers
        import io
        sample_io = io.StringIO(sample)
        reader = csv.DictReader(sample_io)
        
        try:
            headers = reader.fieldnames
        except:
            return False, "Could not parse CSV headers"
        
        if not headers:
            return False, "No headers found in CSV"
        
        # Check required fields based on import type
        if import_type == 'questionbank':
            required_fields = ['question_text']
            recommended_fields = ['option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
        else:  # modelpaper
            required_fields = ['question_text', 'paper_name']
            recommended_fields = ['option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
        
        # Check for required fields
        missing_required = []
        for field in required_fields:
            if not any(field.lower() in h.lower() for h in headers):
                missing_required.append(field)
        
        if missing_required:
            return False, f"Missing required fields: {', '.join(missing_required)}"
        
        # Warn about missing recommended fields
        missing_recommended = []
        for field in recommended_fields:
            if not any(field.lower() in h.lower() for h in headers):
                missing_recommended.append(field)
        
        if missing_recommended:
            return True, f"Warning: Missing recommended fields: {', '.join(missing_recommended)}"
        
        return True, "CSV structure looks good"
        
    except Exception as e:
        return False, f"Error validating CSV: {str(e)}"


# API endpoints for CSV management

def get_csv_stats_api(request):
    """API endpoint for CSV statistics"""
    stats = get_import_statistics()
    
    # Add question bank specific stats
    questionbank_total = Question.objects.count()
    questionbank_with_images = Question.objects.exclude(
        Q(question_image__isnull=True) | Q(question_image__exact='') |
        Q(image__isnull=True) | Q(image__exact='')
    ).count()
    
    stats['questionbank']['total_questions_db'] = questionbank_total
    stats['questionbank']['questions_with_images'] = questionbank_with_images
    
    if MODELPAPER_AVAILABLE:
        modelpaper_total = PaperQuestion.objects.count()
        modelpaper_with_images = PaperQuestion.objects.exclude(
            Q(paper_image__isnull=True) | Q(paper_image__exact='') |
            Q(image__isnull=True) | Q(image__exact='')
        ).count()
        
        stats['modelpaper']['total_questions_db'] = modelpaper_total
        stats['modelpaper']['questions_with_images'] = modelpaper_with_images
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'modelpaper_available': MODELPAPER_AVAILABLE,
        'timestamp': timezone.now().isoformat()
    })


def validate_csv_api(request):
    """API endpoint for CSV validation"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    if 'csv_file' not in request.FILES:
        return JsonResponse({'error': 'No CSV file provided'}, status=400)
    
    csv_file = request.FILES['csv_file']
    import_type = request.POST.get('import_type', 'questionbank')
    
    is_valid, message = validate_csv_structure(csv_file, import_type)
    
    return JsonResponse({
        'success': True,
        'is_valid': is_valid,
        'message': message,
        'import_type': import_type
    })


# CSV Import History Management

def get_import_history_api(request):
    """API endpoint for import history"""
    import_type = request.GET.get('type', 'all')
    limit = int(request.GET.get('limit', 20))
    
    history_data = {}
    
    if import_type in ['questionbank', 'all']:
        questionbank_history = CSVImportHistory.objects.all()[:limit]
        history_data['questionbank'] = [
            {
                'id': record.id,
                'file_name': record.file_name,
                'uploaded_at': record.uploaded_at.isoformat(),
                'status': record.status,
                'total_rows': record.total_rows,
                'successful_imports': record.successful_imports,
                'failed_imports': record.failed_imports,
                'file_size': record.file_size,
                'uploaded_by': record.uploaded_by.email if record.uploaded_by else None,
            }
            for record in questionbank_history
        ]
    
    if import_type in ['modelpaper', 'all'] and MODELPAPER_AVAILABLE:
        modelpaper_history = PaperCSVImportHistory.objects.all()[:limit]
        history_data['modelpaper'] = [
            {
                'id': record.id,
                'file_name': record.file_name,
                'uploaded_at': record.uploaded_at.isoformat(),
                'status': record.status,
                'total_rows': record.total_rows,
                'successful_imports': record.successful_imports,
                'failed_imports': record.failed_imports,
                'file_size': record.file_size,
                'uploaded_by': record.uploaded_by.email if record.uploaded_by else None,
                'paper_names': record.imported_paper_names_list,
            }
            for record in modelpaper_history
        ]
    
    return JsonResponse({
        'success': True,
        'history': history_data,
        'modelpaper_available': MODELPAPER_AVAILABLE,
    })


# Error handling for CSV operations

def handle_csv_error(request, error_type, error_message, import_type='unknown'):
    """Centralized error handling for CSV operations"""
    error_context = {
        'error_type': error_type,
        'error_message': error_message,
        'import_type': import_type,
        'user': request.user,
        'timestamp': timezone.now(),
        'request_data': {
            'method': request.method,
            'path': request.path,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
    }
    
    # Log error for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"CSV Error: {error_type} - {error_message}", extra=error_context)
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'success': False,
            'error': error_message,
            'error_type': error_type,
            'import_type': import_type
        }, status=400)
    
    # For non-AJAX requests, redirect with error message
    messages.error(request, f"CSV {error_type}: {error_message}")
    return redirect('manage_csv')


# Cleanup and maintenance functions

def cleanup_failed_imports():
    """Cleanup function to remove old failed import records"""
    cutoff_date = timezone.now() - timezone.timedelta(days=30)
    
    # Clean questionbank import history
    old_questionbank_imports = CSVImportHistory.objects.filter(
        status='FAILED',
        uploaded_at__lt=cutoff_date
    )
    questionbank_count = old_questionbank_imports.count()
    old_questionbank_imports.delete()
    
    modelpaper_count = 0
    if MODELPAPER_AVAILABLE:
        # Clean modelpaper import history
        old_modelpaper_imports = PaperCSVImportHistory.objects.filter(
            status='FAILED',
            uploaded_at__lt=cutoff_date
        )
        modelpaper_count = old_modelpaper_imports.count()
        old_modelpaper_imports.delete()
    
    return {
        'questionbank_cleaned': questionbank_count,
        'modelpaper_cleaned': modelpaper_count,
        'total_cleaned': questionbank_count + modelpaper_count
    }