import csv
import io
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
                    # Create question from CSV row
                    Question.objects.create(
                        question_text=row.get('question_text', ''),
                        question_type=row.get('question_type', 'MCQ'),
                        option_a=row.get('option_a', ''),
                        option_b=row.get('option_b', ''),
                        option_c=row.get('option_c', ''),
                        option_d=row.get('option_d', ''),
                        option_e=row.get('option_e', ''),  # Added Option E
                        correct_answer=row.get('correct_answer', ''),
                        degree=row.get('degree', 'MBBS'),
                        year=row.get('year', '1st'),
                        block=row.get('block', ''),
                        module=row.get('module', ''),
                        subject=row.get('subject', ''),
                        topic=row.get('topic', ''),
                        difficulty=row.get('difficulty', 'Medium'),
                        explanation=row.get('explanation', ''),
                        created_by=creator
                    )
                    question_count += 1
                
                return JsonResponse({'count': question_count})
                
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
        else:
            return JsonResponse({'error': 'Invalid form submission'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# New CSV Management page
def manage_csv(request):
    """View for CSV management page"""
    # Get import history
    import_history = CSVImportHistory.objects.all()[:10]  # Last 10 imports
    
    # Get CSV statistics
    total_imports = CSVImportHistory.objects.count()
    successful_imports = CSVImportHistory.objects.filter(status='SUCCESS').count()
    failed_imports = CSVImportHistory.objects.filter(status='FAILED').count()
    total_questions_imported = CSVImportHistory.objects.filter(status='SUCCESS').aggregate(
        total=models.Sum('successful_imports')
    )['total'] or 0
    
    context = {
        'import_history': import_history,
        'csv_stats': {
            'total_imports': total_imports,
            'successful_imports': successful_imports,
            'failed_imports': failed_imports,
            'total_questions_imported': total_questions_imported,
            'success_rate': round((successful_imports / total_imports * 100), 1) if total_imports > 0 else 0
        }
    }
    
    return render(request, 'questionbank/manage_csv.html', context)

# Updated import function with encoding detection
def import_questions_with_history(request):
    """Enhanced CSV import with history tracking and encoding detection"""
    if request.method == 'POST':
        form = QuestionImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Check if file is CSV
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
                
                # List of encodings to try
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
                        question_text = (
                            str(row.get('question_text', '') or 
                                row.get('Question', '') or 
                                row.get('question', '')).strip()
                        )
                        
                        if not question_text:
                            errors.append(f"Row {row_num}: Missing question text")
                            error_count += 1
                            continue
                        
                        # Clean and validate question type
                        question_type = str(row.get('question_type', 'MCQ')).strip()
                        if question_type not in ['MCQ', 'SEQ', 'NOTE']:
                            question_type = 'MCQ'
                        
                        # Handle different option column name variations
                        option_a = str(
                            row.get('option_a', '') or 
                            row.get('option_A', '') or 
                            row.get('Option_A', '') or ''
                        ).strip()
                        
                        option_b = str(
                            row.get('option_b', '') or 
                            row.get('option_B', '') or 
                            row.get('Option_B', '') or ''
                        ).strip()
                        
                        option_c = str(
                            row.get('option_c', '') or 
                            row.get('option_C', '') or 
                            row.get('Option_C', '') or ''
                        ).strip()
                        
                        option_d = str(
                            row.get('option_d', '') or 
                            row.get('option_D', '') or 
                            row.get('Option_D', '') or ''
                        ).strip()
                        
                        option_e = str(
                            row.get('option_e', '') or 
                            row.get('option_E', '') or 
                            row.get('Option_E', '') or ''
                        ).strip()
                        
                        # Handle different correct answer column variations
                        correct_answer = str(
                            row.get('correct_answer', '') or 
                            row.get('correct_option', '') or 
                            row.get('Correct_Answer', '') or 
                            row.get('answer', '') or ''
                        ).strip().upper()
                        
                        if correct_answer not in ['A', 'B', 'C', 'D', 'E']:
                            correct_answer = ''
                        
                        # Clean categorization fields
                        degree = str(row.get('degree', 'MBBS')).strip().upper()
                        if degree not in ['MBBS', 'BDS']:
                            degree = 'MBBS'
                        
                        year = str(row.get('year', '1st')).strip()
                        if year not in ['1st', '2nd', '3rd', '4th', '5th']:
                            year = '1st'
                        
                        # FIXED DIFFICULTY HANDLING - Handle both cases
                        difficulty_raw = str(row.get('difficulty', 'Medium')).strip()
                        
                        # Convert to proper case format
                        if difficulty_raw.lower() == 'easy':
                            difficulty = 'Easy'
                        elif difficulty_raw.lower() == 'medium':
                            difficulty = 'Medium'
                        elif difficulty_raw.lower() == 'hard':
                            difficulty = 'Hard'
                        elif difficulty_raw in ['Easy', 'Medium', 'Hard']:  # Already proper case
                            difficulty = difficulty_raw
                        else:
                            difficulty = 'Medium'  # Default fallback
                        
                        # DUPLICATE DETECTION - Check for exact duplicate
                        duplicate_exists = Question.objects.filter(
                            question_text__iexact=question_text.strip()
                        ).exists()
                        
                        if duplicate_exists:
                            errors.append(f"Row {row_num}: Duplicate question found - '{question_text[:50]}...'")
                            error_count += 1
                            continue
                        
                        # For MCQ questions, also check option similarity
                        if question_type == 'MCQ' and option_a and option_b:
                            similar_mcq = Question.objects.filter(
                                question_type='MCQ',
                                option_a__iexact=option_a,
                                option_b__iexact=option_b,
                                question_text__icontains=question_text[:20]  # First 20 characters
                            ).exists()
                            
                            if similar_mcq:
                                errors.append(f"Row {row_num}: Similar MCQ found - '{question_text[:50]}...'")
                                error_count += 1
                                continue
                        
                        # Create question from CSV row
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
                    'errors': errors[:10] if errors else []  # Return first 10 errors
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

# Remove login_required for development/testing
def export_questions(request):
    """View to export questions as CSV"""
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
    writer.writerow([
        'question_text', 'question_type', 
        'option_a', 'option_b', 'option_c', 'option_d', 'option_e', 'correct_answer',  # Added option_e
        'degree', 'year', 'block', 'module', 'subject', 'topic',
        'difficulty', 'explanation', 'created_on'
    ])
    
    for question in questions:
        writer.writerow([
            question.question_text, question.question_type,
            question.option_a, question.option_b, question.option_c, question.option_d, question.option_e, question.correct_answer,  # Added option_e
            question.degree, question.year, question.block, question.module, question.subject, question.topic,
            question.difficulty, question.explanation, question.created_on
        ])
    
    return response