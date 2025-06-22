
from django.views.decorators.http import require_GET
# Add JSON import for model paper functionality

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
from django.db import models
from django.contrib.auth import get_user_model

from .models import Question, CSVImportHistory
from .forms import QuestionForm, QuestionImportForm

# Get the custom user model
User = get_user_model()


# Remove login_required for development/testing
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

# Remove login_required for development/testing
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

# Remove login_required for development/testing
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

# Remove login_required for development/testing
def import_questions(request):
    """View to handle CSV import"""
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
                    # FIXED: Move image_filename inside the loop
                    image_filename = str(row.get('image', '')).strip()
                    
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
                        image=image_filename or None,  # FIXED: Use the correct variable
                        created_by=creator
                    )
                    question_count += 1
                
                return JsonResponse({'count': question_count})
                
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
        else:
            return JsonResponse({'error': 'Invalid form submission'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def enhanced_duplicate_detection_questionbank(question_text, option_a, option_b, option_c, option_d, option_e=None):
    """
    Enhanced duplicate detection for questionbank questions
    """
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


# Enhanced manage_csv view with model paper integration
def manage_csv(request):
    """Enhanced CSV management view with both questionbank and modelpaper support"""
    
    # Get questionbank statistics
    questionbank_total_imports = CSVImportHistory.objects.count()
    questionbank_successful_imports = CSVImportHistory.objects.filter(status='SUCCESS').count()
    questionbank_failed_imports = CSVImportHistory.objects.filter(status='FAILED').count()
    questionbank_total_questions_imported = CSVImportHistory.objects.filter(status='SUCCESS').aggregate(
        total=models.Sum('successful_imports')
    )['total'] or 0
    
    # Get modelpaper statistics
    try:
        from modelpaper.models import PaperCSVImportHistory, PaperQuestion
        modelpaper_total_imports = PaperCSVImportHistory.objects.count()
        modelpaper_successful_imports = PaperCSVImportHistory.objects.filter(status='SUCCESS').count()
        modelpaper_failed_imports = PaperCSVImportHistory.objects.filter(status='FAILED').count()
        modelpaper_total_questions_imported = PaperCSVImportHistory.objects.filter(status='SUCCESS').aggregate(
            total=models.Sum('successful_imports')
        )['total'] or 0
        
        # Get model paper statistics
        paper_names = PaperQuestion.get_available_paper_names()
        paper_stats = []
        for paper_name in paper_names:
            count = PaperQuestion.objects.filter(paper_name=paper_name).count()
            paper_stats.append({
                'name': paper_name,
                'question_count': count
            })
        
        # Get import histories
        modelpaper_history = PaperCSVImportHistory.objects.all()[:10]
        
        # Get available papers for dropdown - not needed since we have independent storage
        available_papers = []
        
    except ImportError:
        # If modelpaper app not installed
        modelpaper_total_imports = 0
        modelpaper_successful_imports = 0
        modelpaper_failed_imports = 0
        modelpaper_total_questions_imported = 0
        paper_stats = []
        modelpaper_history = []
        available_papers = []
    
    # Get questionbank import history
    questionbank_history = CSVImportHistory.objects.all()[:10]
    
    context = {
        'questionbank_stats': {
            'total_imports': questionbank_total_imports,
            'successful_imports': questionbank_successful_imports,
            'failed_imports': questionbank_failed_imports,
            'total_questions_imported': questionbank_total_questions_imported,
            'success_rate': round((questionbank_successful_imports / questionbank_total_imports * 100), 1) if questionbank_total_imports > 0 else 0
        },
        'modelpaper_stats': {
            'total_imports': modelpaper_total_imports,
            'successful_imports': modelpaper_successful_imports,
            'failed_imports': modelpaper_failed_imports,
            'total_questions_imported': modelpaper_total_questions_imported,
            'success_rate': round((modelpaper_successful_imports / modelpaper_total_imports * 100), 1) if modelpaper_total_imports > 0 else 0,
            'total_paper_names': len(paper_stats),
            'avg_questions_per_paper': sum(p['question_count'] for p in paper_stats) / len(paper_stats) if paper_stats else 0
        },
        'paper_stats': paper_stats,
        'questionbank_history': questionbank_history,
        'modelpaper_history': modelpaper_history,
        'available_papers': available_papers,
    }
    
    return render(request, 'questionbank/manage_csv.html', context)


def import_questions_with_history(request):
    """Enhanced CSV import supporting both questionbank and model papers"""
    if request.method == 'POST':
        import_type = request.POST.get('import_type', 'questionbank')
        
        if import_type == 'modelpaper':
            # Import to model paper system
            return import_to_model_paper(request)
        else:
            return import_to_questionbank(request)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# Replace the entire import_to_questionbank function in questionbank/views.py:

def import_to_questionbank(request):
    """Import questions to questionbank (existing logic)"""
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
                    
                    # FIXED: Handle image field properly
                    image_filename = str(row.get('image', '')).strip()
                    
                    # ENHANCED DUPLICATE DETECTION
                    is_duplicate, duplicate_reason = enhanced_duplicate_detection_questionbank(
                        question_text, option_a, option_b, option_c, option_d, option_e
                    )
                    
                    if is_duplicate:
                        errors.append(f"Row {row_num}: {duplicate_reason} - '{question_text[:50]}...'")
                        error_count += 1
                        continue
                    
                    # Create question
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
                        image=image_filename or None,  # FIXED: Use the correct variable
                        created_by=creator
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

def import_to_model_paper(request):
    """Import questions to model paper system - integrated version"""
    try:
        from modelpaper.models import PaperQuestion, PaperCSVImportHistory
        from modelpaper.views import enhanced_duplicate_detection
    except ImportError:
        return JsonResponse({'error': 'Model paper system not available'}, status=400)
    
    csv_file = request.FILES.get('csv_file')
    
    if not csv_file:
        return JsonResponse({'error': 'No CSV file provided'}, status=400)
    
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
        import_record.paper_names_imported = json.dumps(list(paper_names_imported)) if paper_names_imported else None
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

# Update the export_questions function in questionbank/views.py

def export_questions(request):
    """View to export questions as CSV - Updated with image field"""
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
    
    # UPDATED: Added image field after explanation
    writer.writerow([
        'question_text', 'question_type', 
        'option_a', 'option_b', 'option_c', 'option_d', 'option_e', 'correct_answer',
        'degree', 'year', 'block', 'module', 'subject', 'topic',
        'difficulty', 'explanation', 'image', 'created_on'  # Added image field
    ])
    
    for question in questions:
        writer.writerow([
            question.question_text, question.question_type,
            question.option_a, question.option_b, question.option_c, question.option_d, question.option_e, question.correct_answer,
            question.degree, question.year, question.block, question.module, question.subject, question.topic,
            question.difficulty, question.explanation, question.image or '', question.created_on  # Added image field
        ])
    
    return response

@require_GET
def get_paper_details(request, paper_id):
    """
    API endpoint to get details for a specific paper.
    This is a placeholder implementation. Adjust as needed.
    """
    try:
        from modelpaper.models import PaperQuestion
        questions = PaperQuestion.objects.filter(paper_name=paper_id)
        data = []
        for q in questions:
            data.append({
                'id': q.id,
                'question_text': q.question_text,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'option_e': q.option_e,
                'correct_answer': q.correct_answer,
                # Add more fields as needed
            })
        return JsonResponse({'questions': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)