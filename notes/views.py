# notes/views.py - Updated with Access Control
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils import timezone
from collections import defaultdict

from .models import StudentNote, NoteImage, StudySession, NoteRevision
from questionbank.models import Question
from .forms import StudentNoteForm, QuickNoteForm

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
def notes_dashboard(request):
    """Enhanced main notes dashboard with access control - shows both questions and notes"""
    # Get filter parameters
    query = request.GET.get('q', '')
    filter_degree = request.GET.get('degree', '')
    filter_year = request.GET.get('year', '')
    filter_note_type = request.GET.get('note_type', '')
    
    # Get user's notes for counting and building hierarchy
    user_notes = StudentNote.objects.filter(student=request.user)
    
    # APPLY USER ACCESS FILTER TO USER'S NOTES
    user_notes = apply_user_access_filter(user_notes, request.user)
    
    # Apply search to notes
    if query:
        user_notes = user_notes.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__icontains=query) |
            Q(block__icontains=query) |
            Q(module__icontains=query) |
            Q(subject__icontains=query) |
            Q(topic__icontains=query)
        )
    
    # Apply filters to notes  
    if filter_degree:
        user_notes = user_notes.filter(degree=filter_degree)
    
    if filter_year:
        user_notes = user_notes.filter(year=filter_year)
    
    if filter_note_type:
        user_notes = user_notes.filter(note_type=filter_note_type)
    
    # Get questions for additional hierarchy structure - WITH ACCESS CONTROL
    questions = Question.objects.all()
    questions = apply_user_access_filter(questions, request.user)
    
    if filter_degree:
        questions = questions.filter(degree=filter_degree)
    if filter_year:
        questions = questions.filter(year=filter_year)
    
    # Build hybrid hierarchy structure
    block_module_map = build_hybrid_notes_hierarchy(questions, user_notes)
    
    # Calculate statistics
    stats = calculate_notes_stats(user_notes)
    
    # Get choices for filters
    try:
        degree_choices = Question.DEGREE_CHOICES
        year_choices = Question.YEAR_CHOICES
    except:
        degree_choices = [('MBBS', 'MBBS'), ('BDS', 'BDS')]
        year_choices = [('1st', '1st Year'), ('2nd', '2nd Year'), ('3rd', '3rd Year'), ('4th', '4th Year'), ('5th', '5th Year')]
    
    note_type_choices = StudentNote.NOTE_TYPES
    
    context = {
        'block_module_map': block_module_map,
        'stats': stats,
        'query': query,
        'filter_degree': filter_degree,
        'filter_year': filter_year,
        'filter_note_type': filter_note_type,
        'degree_choices': degree_choices,
        'year_choices': year_choices,
        'note_type_choices': note_type_choices,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'notes/notes_dashboard.html', context)


def build_hybrid_notes_hierarchy(questions, user_notes):
    """Enhanced hierarchy builder with access control - comprehensive coverage"""
    from collections import defaultdict
    
    # Step 1: Build hierarchy paths from both questions AND notes (both already filtered by access control)
    all_paths = set()
    
    # Add paths from questions
    for question in questions:
        path = (
            question.block or 'General',
            question.module or 'Miscellaneous', 
            question.subject or 'General',
            question.topic or 'General Topics',
            question.degree or 'MBBS',
            question.year or '1st'
        )
        all_paths.add(path)
    
    # Add paths from notes (this ensures notes-only paths are included)
    for note in user_notes:
        path = (
            note.block or 'General Notes',
            note.module or 'Miscellaneous',
            note.subject or 'General', 
            note.topic or 'General Topics',
            note.degree or 'MBBS',
            note.year or '1st'
        )
        all_paths.add(path)
    
    # Step 2: Group notes by their hierarchy
    note_counts = {}
    for note in user_notes:
        key = f"{note.block}|{note.module}|{note.subject}|{note.topic}"
        if key not in note_counts:
            note_counts[key] = {
                'total_notes': 0,
                'favorite_notes': 0,
                'notes_list': [],
                'last_updated': None
            }
        note_counts[key]['total_notes'] += 1
        if note.is_favorite:
            note_counts[key]['favorite_notes'] += 1
        note_counts[key]['notes_list'].append(note)
        if not note_counts[key]['last_updated'] or note.updated_at > note_counts[key]['last_updated']:
            note_counts[key]['last_updated'] = note.updated_at
    
    # Step 3: Group question counts by hierarchy  
    question_counts = {}
    for question in questions:
        key = f"{question.block}|{question.module}|{question.subject}|{question.topic}"
        if key not in question_counts:
            question_counts[key] = 0
        question_counts[key] += 1
    
    # Step 4: Build the nested structure
    hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
        'paths': set(),
        'notes': [],
        'questions_count': 0
    }))))
    
    # Populate the hierarchy with all paths
    for block, module, subject, topic, degree, year in all_paths:
        hierarchy[block][module][subject][topic]['paths'].add((degree, year))
        
        # Add note data
        notes_key = f"{block}|{module}|{subject}|{topic}"
        if notes_key in note_counts:
            hierarchy[block][module][subject][topic]['notes'] = note_counts[notes_key]['notes_list']
            hierarchy[block][module][subject][topic]['note_count'] = note_counts[notes_key]['total_notes']
            hierarchy[block][module][subject][topic]['favorite_count'] = note_counts[notes_key]['favorite_notes']
            hierarchy[block][module][subject][topic]['last_updated'] = note_counts[notes_key]['last_updated']
        else:
            hierarchy[block][module][subject][topic]['note_count'] = 0
            hierarchy[block][module][subject][topic]['favorite_count'] = 0
            hierarchy[block][module][subject][topic]['last_updated'] = None
            
        # Add question count
        if notes_key in question_counts:
            hierarchy[block][module][subject][topic]['questions_count'] = question_counts[notes_key]
    
    # Step 5: Convert to template format
    block_module_map = []
    
    for block_name, modules in hierarchy.items():
        block_data = {
            'block': block_name,
            'modules': []
        }
        
        for module_name, subjects in modules.items():
            # Group by degree/year combinations
            degree_year_groups = defaultdict(list)
            
            for subject_name, topics in subjects.items():
                for topic_name, topic_data in topics.items():
                    # Create a topic for each degree/year combination
                    for degree, year in topic_data['paths']:
                        degree_year_groups[(degree, year)].append({
                            'subject_name': subject_name,
                            'topic_name': topic_name,
                            'topic_data': topic_data
                        })
            
            # Create module entries for each degree/year
            for (degree, year), topic_groups in degree_year_groups.items():
                # Group topics by subject
                subjects_dict = defaultdict(list)
                for item in topic_groups:
                    subjects_dict[item['subject_name']].append({
                        'name': item['topic_name'],
                        'block': block_name,
                        'module': module_name,
                        'subject': item['subject_name'],
                        'degree': degree,
                        'year': year,
                        'questions_count': item['topic_data']['questions_count'],
                        'notes_count': item['topic_data']['note_count'],
                        'favorite_count': item['topic_data']['favorite_count'],
                        'notes': item['topic_data']['notes'][:3],  # Show first 3 notes for preview
                        'last_updated': item['topic_data']['last_updated'],
                    })
                
                # Build subjects list
                subject_list = []
                total_module_notes = 0
                total_module_topics = 0
                
                for subject_name, topics_list in subjects_dict.items():
                    subject_notes_count = sum(t['notes_count'] for t in topics_list)
                    subject_list.append({
                        'name': subject_name,
                        'topics': topics_list,
                        'topics_count': len(topics_list),
                        'notes_count': subject_notes_count,
                    })
                    total_module_notes += subject_notes_count
                    total_module_topics += len(topics_list)
                
                if subject_list:  # Only add if there are subjects
                    module_data = {
                        'name': module_name,
                        'degree': degree,
                        'year': year,
                        'subjects': subject_list,
                        'subjects_count': len(subject_list),
                        'topics_count': total_module_topics,
                        'notes_count': total_module_notes,
                    }
                    block_data['modules'].append(module_data)
        
        if block_data['modules']:  # Only add block if it has modules
            block_module_map.append(block_data)
    
    return block_module_map


def calculate_notes_stats(user_notes):
    """Calculate statistics for notes dashboard with access control"""
    total_notes = user_notes.count()
    
    # Count unique hierarchy levels from user's accessible notes
    modules_count = user_notes.values('module').distinct().count()
    subjects_count = user_notes.values('subject').distinct().count()
    topics_count = user_notes.values('topic').distinct().count()
    
    # Additional stats
    favorite_notes = user_notes.filter(is_favorite=True).count()
    recent_notes = user_notes.filter(created_at__gte=timezone.now() - timezone.timedelta(days=7)).count()
    
    # Notes by type
    notes_by_type = {}
    for note_type, label in StudentNote.NOTE_TYPES:
        count = user_notes.filter(note_type=note_type).count()
        notes_by_type[note_type] = {'count': count, 'label': label}
    
    return {
        'total_notes': total_notes,
        'modules_count': modules_count,
        'subjects_count': subjects_count,
        'topics_count': topics_count,
        'favorite_notes': favorite_notes,
        'recent_notes': recent_notes,
        'notes_by_type': notes_by_type,
    }


@content_access_required
def topic_notes(request):
    """Enhanced view notes for a specific topic with access control"""
    # Get filter parameters
    block = request.GET.get('block')
    module = request.GET.get('module')
    subject = request.GET.get('subject')
    topic = request.GET.get('topic')
    degree = request.GET.get('degree')
    year = request.GET.get('year')
    
    # Build filter query
    notes_filter = Q(student=request.user)
    
    if block:
        notes_filter &= Q(block=block)
    if module:
        notes_filter &= Q(module=module)
    if subject:
        notes_filter &= Q(subject=subject)
    if topic:
        notes_filter &= Q(topic=topic)
    if degree:
        notes_filter &= Q(degree=degree)
    if year:
        notes_filter &= Q(year=year)
    
    notes = StudentNote.objects.filter(notes_filter).order_by('-updated_at')
    
    # APPLY USER ACCESS FILTER
    notes = apply_user_access_filter(notes, request.user)
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        notes = notes.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(tags__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(notes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Build breadcrumb
    breadcrumb_parts = []
    if block:
        breadcrumb_parts.append(block)
    if module:
        breadcrumb_parts.append(module)
    if subject:
        breadcrumb_parts.append(subject)
    if topic:
        breadcrumb_parts.append(topic)
    
    # Get related questions for this topic (with access control)
    if block and module and subject and topic and degree and year:
        related_questions = Question.objects.filter(
            block=block,
            module=module,
            subject=subject,
            topic=topic,
            degree=degree,
            year=year
        )
        related_questions = apply_user_access_filter(related_questions, request.user)
        related_questions_count = related_questions.count()
    else:
        related_questions_count = 0
    
    context = {
        'notes': page_obj,
        'total_notes': notes.count(),
        'breadcrumb': ' > '.join(breadcrumb_parts) if breadcrumb_parts else 'All Notes',
        'current_filters': {
            'block': block,
            'module': module,
            'subject': subject,
            'topic': topic,
            'degree': degree,
            'year': year,
        },
        'search_query': search_query,
        'related_questions_count': related_questions_count,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'notes/topic_notes.html', context)


@content_access_required
def add_note(request):
    """Enhanced add note with access control"""
    if request.method == 'POST':
        form = StudentNoteForm(request.POST, request.FILES)
        if form.is_valid():
            note = form.save(commit=False)
            note.student = request.user
            
            # APPLY USER ACCESS FILTER TO NOTE DATA
            user_access = get_user_access_info(request.user)
            if user_access['level'] == 'student':
                # Ensure student can only create notes for their degree/year
                filter_params = user_access.get('filter_params', {})
                if filter_params.get('degree'):
                    note.degree = filter_params['degree']
                if filter_params.get('year'):
                    note.year = filter_params['year']
            
            note.save()
            
            # Handle multiple image uploads
            files = request.FILES.getlist('images')
            for file in files:
                if file:
                    NoteImage.objects.create(note=note, image=file)
            
            messages.success(request, 'Note added successfully!')
            return redirect('notes_dashboard')
    else:
        # Pre-populate with URL parameters if coming from question/topic
        initial_data = {}
        for field in ['degree', 'year', 'block', 'module', 'subject', 'topic']:
            value = request.GET.get(field)
            if value:
                initial_data[field] = value
        
        question_id = request.GET.get('question_id')
        if question_id:
            try:
                question = Question.objects.get(id=question_id)
                
                # ACCESS CONTROL: Check if user can access this question
                if not check_object_access(question, request.user):
                    messages.error(request, "You don't have access to create notes for this question.")
                    return redirect('notes_dashboard')
                
                initial_data.update({
                    'question': question,
                    'degree': question.degree,
                    'year': question.year,
                    'block': question.block,
                    'module': question.module,
                    'subject': question.subject,
                    'topic': question.topic,
                    'title': f"Note for: {question.question_text[:50]}...",
                    'note_type': 'question_note'
                })
            except Question.DoesNotExist:
                pass
        
        form = StudentNoteForm(initial=initial_data)
    
    context = {
        'form': form,
        'is_edit': False,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'notes/add_edit_note.html', context)


@content_access_required
def edit_note(request, note_id):
    """Enhanced edit note with access control"""
    note = get_object_or_404(StudentNote, id=note_id, student=request.user)
    
    # ACCESS CONTROL: Check if note content is still accessible
    if not check_object_access(note, request.user):
        messages.error(request, "You no longer have access to edit this note.")
        return redirect('notes_dashboard')
    
    if request.method == 'POST':
        # Create revision before editing
        NoteRevision.objects.create(
            note=note,
            content_snapshot=note.content,
            revision_reason=request.POST.get('revision_reason', 'Manual edit')
        )
        
        form = StudentNoteForm(request.POST, request.FILES, instance=note)
        if form.is_valid():
            updated_note = form.save(commit=False)
            
            # APPLY USER ACCESS FILTER TO UPDATED NOTE DATA
            user_access = get_user_access_info(request.user)
            if user_access['level'] == 'student':
                # Ensure student can only edit notes within their access level
                filter_params = user_access.get('filter_params', {})
                if filter_params.get('degree'):
                    updated_note.degree = filter_params['degree']
                if filter_params.get('year'):
                    updated_note.year = filter_params['year']
            
            updated_note.save()
            
            # Handle new image uploads
            files = request.FILES.getlist('images')
            for file in files:
                if file:
                    NoteImage.objects.create(note=note, image=file)
            
            messages.success(request, 'Note updated successfully!')
            return redirect('notes_dashboard')
    else:
        form = StudentNoteForm(instance=note)
    
    context = {
        'form': form,
        'note': note,
        'is_edit': True,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'notes/add_edit_note.html', context)


@content_access_required
def delete_note(request, note_id):
    """Enhanced delete note with access control"""
    note = get_object_or_404(StudentNote, id=note_id, student=request.user)
    
    # ACCESS CONTROL: Ensure user owns this note and can still access it
    if not check_object_access(note, request.user):
        messages.error(request, "You no longer have access to this note.")
        return redirect('notes_dashboard')
    
    if request.method == 'POST':
        note_title = note.title
        note.delete()
        messages.success(request, f'Note "{note_title}" deleted successfully!')
        return redirect('notes_dashboard')
    
    context = {
        'note': note,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'notes/confirm_delete.html', context)


@require_POST
@content_access_required
def quick_add_note(request):
    """Enhanced quick add note via AJAX with access control - FIXED VERSION"""
    question_id = request.POST.get('question_id')
    content = request.POST.get('content')
    title = request.POST.get('title', 'Quick Note')
    note_type = request.POST.get('note_type', 'general_note')
    
    if not content:
        return JsonResponse({'error': 'Content is required'}, status=400)
    
    try:
        note_data = {
            'title': title or 'Quick Note',
            'content': content,
            'student': request.user,
            'note_type': note_type
        }
        
        # Try to get question if question_id is valid and populate hierarchy
        if question_id and question_id != 'undefined' and question_id != 'null' and question_id.strip() and question_id.isdigit():
            try:
                question = Question.objects.get(id=int(question_id))
                
                # ACCESS CONTROL: Check if user can access this question
                if not check_object_access(question, request.user):
                    return JsonResponse({
                        'error': 'You don\'t have access to create notes for this question'
                    }, status=403)
                
                # FIXED: Properly populate ALL hierarchy fields from the question
                note_data.update({
                    'question': question,
                    'degree': question.degree or 'MBBS',  # Use question's degree or default
                    'year': question.year or '1st',      # Use question's year or default
                    'block': question.block or '',       # Use question's block
                    'module': question.module or '',     # Use question's module
                    'subject': question.subject or '',   # Use question's subject
                    'topic': question.topic or '',       # Use question's topic
                    'note_type': 'question_note'         # Set as question note when linked to question
                })
                
                # If title wasn't provided, create one based on question
                if not title or title == 'Quick Note':
                    note_data['title'] = f"Note for: {question.question_text[:50]}..."
                    
            except Question.DoesNotExist:
                # If question doesn't exist, continue without question link but log it
                print(f"Warning: Question with ID {question_id} not found")
                pass
        else:
            # For general notes without question link, use user's default values with access control
            user_access = get_user_access_info(request.user)
            if user_access['level'] == 'student':
                filter_params = user_access.get('filter_params', {})
                note_data.update({
                    'degree': filter_params.get('degree', 'MBBS'),
                    'year': filter_params.get('year', '1st'),
                    'block': '',       # Empty block for general notes
                    'module': '',      # Empty module for general notes
                    'subject': '',     # Empty subject for general notes
                    'topic': '',       # Empty topic for general notes
                })
            else:
                # Admin default
                note_data.update({
                    'degree': 'MBBS',
                    'year': '1st',
                    'block': '',
                    'module': '',
                    'subject': '',
                    'topic': '',
                })
        
        # Create the note with all populated data
        note = StudentNote.objects.create(**note_data)
        
        return JsonResponse({
            'success': True,
            'note_id': note.id,
            'message': 'Note saved successfully!',
            'note_details': {
                'title': note.title,
                'degree': note.degree,
                'year': note.year,
                'block': note.block,
                'module': note.module,
                'subject': note.subject,
                'topic': note.topic,
                'note_type': note.note_type,
                'hierarchy_path': note.hierarchy_path
            },
            'user_access_level': get_user_access_info(request.user).get('level', 'student')
        })
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error in quick_add_note: {str(e)}")
        return JsonResponse({'error': f'Error saving note: {str(e)}'}, status=500)


@require_POST
@content_access_required
def toggle_favorite(request, note_id):
    """Enhanced toggle favorite with access control"""
    note = get_object_or_404(StudentNote, id=note_id, student=request.user)
    
    # ACCESS CONTROL: Check if note is still accessible
    if not check_object_access(note, request.user):
        return JsonResponse({
            'success': False,
            'error': 'You no longer have access to this note'
        }, status=403)
    
    note.is_favorite = not note.is_favorite
    note.save()
    
    return JsonResponse({
        'success': True,
        'is_favorite': note.is_favorite,
        'user_access_level': get_user_access_info(request.user).get('level', 'student')
    })


@content_access_required
def note_detail(request, note_id):
    """Enhanced note detail with access control"""
    note = get_object_or_404(StudentNote, id=note_id, student=request.user)
    
    # ACCESS CONTROL: Check if note is still accessible
    if not check_object_access(note, request.user):
        messages.error(request, "You no longer have access to this note.")
        return redirect('notes_dashboard')
    
    revisions = note.revisions.all()[:5]  # Show last 5 revisions
    
    # Get related notes with access control
    related_notes = StudentNote.objects.filter(
        student=request.user,
        subject=note.subject,
        topic=note.topic
    ).exclude(id=note.id)
    
    # APPLY ACCESS FILTER TO RELATED NOTES
    related_notes = apply_user_access_filter(related_notes, request.user)[:5]
    
    context = {
        'note': note,
        'revisions': revisions,
        'related_notes': related_notes,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'notes/note_detail.html', context)


@content_access_required
def study_session_start(request):
    """Enhanced start study session with access control"""
    session = StudySession.objects.create(student=request.user)
    request.session['current_study_session'] = session.id
    
    return JsonResponse({
        'success': True,
        'session_id': session.id,
        'user_access_level': get_user_access_info(request.user).get('level', 'student')
    })


@content_access_required
def study_session_end(request):
    """Enhanced end study session with access control"""
    session_id = request.session.get('current_study_session')
    if session_id:
        try:
            session = StudySession.objects.get(id=session_id, student=request.user)
            session.ended_at = timezone.now()
            
            if session.started_at:
                duration = (session.ended_at - session.started_at).total_seconds() / 60
                session.duration_minutes = int(duration)
            
            session.save()
            del request.session['current_study_session']
            
            return JsonResponse({
                'success': True,
                'duration_minutes': session.duration_minutes,
                'user_access_level': get_user_access_info(request.user).get('level', 'student')
            })
        except StudySession.DoesNotExist:
            pass
    
    return JsonResponse({
        'success': False,
        'user_access_level': get_user_access_info(request.user).get('level', 'student')
    })


@content_access_required
def search_notes(request):
    """Enhanced search notes with access control"""
    query = request.GET.get('q', '')
    notes = StudentNote.objects.filter(student=request.user)
    
    # APPLY USER ACCESS FILTER
    notes = apply_user_access_filter(notes, request.user)
    
    if query:
        notes = notes.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__icontains=query)
        )
    
    # Apply additional filters
    for filter_field in ['degree', 'year', 'block', 'module', 'subject', 'topic', 'note_type']:
        filter_value = request.GET.get(filter_field)
        if filter_value:
            filter_kwargs = {filter_field: filter_value}
            notes = notes.filter(**filter_kwargs)
    
    # Pagination
    paginator = Paginator(notes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'notes': page_obj,
        'query': query,
        'total_results': notes.count(),
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'notes/search_results.html', context)


# ADMIN VIEWS WITH ACCESS CONTROL

@admin_required
def admin_notes_overview(request):
    """Admin overview of all student notes"""
    # Get all notes
    all_notes = StudentNote.objects.all().select_related('student')
    
    # Calculate statistics
    total_notes = all_notes.count()
    total_students_with_notes = all_notes.values('student').distinct().count()
    
    # Notes by degree/year
    degree_stats = {}
    for note in all_notes:
        key = f"{note.degree} - {note.year}"
        if key not in degree_stats:
            degree_stats[key] = {'notes': 0, 'students': set()}
        degree_stats[key]['notes'] += 1
        degree_stats[key]['students'].add(note.student.id)
    
    # Calculate unique students per degree/year
    for key in degree_stats:
        degree_stats[key]['unique_students'] = len(degree_stats[key]['students'])
        del degree_stats[key]['students']  # Remove set for template
    
    # Most active note-takers
    active_students = all_notes.values('student__first_name', 'student__last_name', 'student__email').annotate(
        note_count=Count('id')
    ).order_by('-note_count')[:10]
    
    # Notes by type
    notes_by_type = {}
    for note_type, label in StudentNote.NOTE_TYPES:
        count = all_notes.filter(note_type=note_type).count()
        notes_by_type[note_type] = {'count': count, 'label': label}
    
    context = {
        'total_notes': total_notes,
        'total_students_with_notes': total_students_with_notes,
        'degree_stats': degree_stats,
        'active_students': active_students,
        'notes_by_type': notes_by_type,
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'notes/admin_notes_overview.html', context)


# UTILITY FUNCTIONS WITH ACCESS CONTROL

@content_access_required
def get_notes_hierarchy_data(request):
    """AJAX endpoint for notes hierarchy data with access control"""
    field = request.GET.get('field')
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    
    # Get user's notes
    notes = StudentNote.objects.filter(student=request.user)
    
    # APPLY USER ACCESS FILTER
    notes = apply_user_access_filter(notes, request.user)
    
    if degree:
        notes = notes.filter(degree=degree)
    if year:
        notes = notes.filter(year=year)
    if block:
        notes = notes.filter(block=block)
    if module:
        notes = notes.filter(module=module)
    if subject:
        notes = notes.filter(subject=subject)
    
    if field == 'blocks':
        data = list(notes.values_list('block', flat=True).distinct().order_by('block'))
    elif field == 'modules':
        data = list(notes.values_list('module', flat=True).distinct().order_by('module'))
    elif field == 'subjects':
        data = list(notes.values_list('subject', flat=True).distinct().order_by('subject'))
    elif field == 'topics':
        data = list(notes.values_list('topic', flat=True).distinct().order_by('topic'))
    else:
        data = []
    
    # Remove empty values
    data = [item for item in data if item and item.strip()]
    
    user_access = get_user_access_info(request.user)
    
    return JsonResponse({
        'data': data,
        'count': len(data),
        'user_access_level': user_access.get('level', 'student'),
        'filter_applied': user_access.get('level') == 'student'
    })


@content_access_required
def get_notes_statistics(request):
    """AJAX endpoint for notes statistics with access control"""
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    
    # Get user's notes
    notes = StudentNote.objects.filter(student=request.user)
    
    # APPLY USER ACCESS FILTER
    notes = apply_user_access_filter(notes, request.user)
    
    if degree:
        notes = notes.filter(degree=degree)
    if year:
        notes = notes.filter(year=year)
    if subject:
        notes = notes.filter(subject=subject)
    if topic:
        notes = notes.filter(topic=topic)
    
    # Calculate statistics
    total_notes = notes.count()
    favorite_notes = notes.filter(is_favorite=True).count()
    recent_notes = notes.filter(created_at__gte=timezone.now() - timezone.timedelta(days=7)).count()
    
    # Notes by type for the filtered set
    notes_by_type = {}
    for note_type, label in StudentNote.NOTE_TYPES:
        count = notes.filter(note_type=note_type).count()
        notes_by_type[note_type] = {'count': count, 'label': label}
    
    user_access = get_user_access_info(request.user)
    
    return JsonResponse({
        'total_notes': total_notes,
        'favorite_notes': favorite_notes,
        'recent_notes': recent_notes,
        'notes_by_type': notes_by_type,
        'user_access_level': user_access.get('level', 'student'),
        'filter_applied': user_access.get('level') == 'student'
    })


@content_access_required
def export_notes(request):
    """Export notes to CSV with access control"""
    # Get user's notes
    notes = StudentNote.objects.filter(student=request.user)
    
    # APPLY USER ACCESS FILTER
    notes = apply_user_access_filter(notes, request.user)
    
    # Apply filters if provided
    subject = request.GET.get('subject')
    note_type = request.GET.get('note_type')
    
    if subject:
        notes = notes.filter(subject__icontains=subject)
    
    if note_type:
        notes = notes.filter(note_type=note_type)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="my_notes.csv"'
    
    import csv
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Title', 'Content', 'Note Type', 'Degree', 'Year', 'Block', 
        'Module', 'Subject', 'Topic', 'Tags', 'Is Favorite', 
        'Created At', 'Updated At'
    ])
    
    # Write data
    for note in notes:
        writer.writerow([
            note.title,
            note.content,
            note.get_note_type_display(),
            note.degree,
            note.year,
            note.block,
            note.module,
            note.subject,
            note.topic,
            note.tags,
            'Yes' if note.is_favorite else 'No',
            note.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            note.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response


# ADDITIONAL USEFUL VIEWS WITH ACCESS CONTROL

@content_access_required
def notes_by_subject(request):
    """View notes grouped by subject with access control"""
    user_notes = StudentNote.objects.filter(student=request.user)
    user_notes = apply_user_access_filter(user_notes, request.user)
    
    # Group notes by subject
    subjects = {}
    for note in user_notes:
        subject = note.subject or 'Uncategorized'
        if subject not in subjects:
            subjects[subject] = {
                'notes': [],
                'count': 0,
                'favorite_count': 0,
                'recent_count': 0
            }
        subjects[subject]['notes'].append(note)
        subjects[subject]['count'] += 1
        if note.is_favorite:
            subjects[subject]['favorite_count'] += 1
        if note.created_at >= timezone.now() - timezone.timedelta(days=7):
            subjects[subject]['recent_count'] += 1
    
    context = {
        'subjects': subjects,
        'total_subjects': len(subjects),
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'notes/notes_by_subject.html', context)


@content_access_required
def favorite_notes(request):
    """View only favorite notes with access control"""
    user_notes = StudentNote.objects.filter(student=request.user, is_favorite=True)
    user_notes = apply_user_access_filter(user_notes, request.user)
    
    # Apply search if provided
    query = request.GET.get('q', '')
    if query:
        user_notes = user_notes.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__icontains=query)
        )
    
    # Pagination
    paginator = Paginator(user_notes, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'notes': page_obj,
        'query': query,
        'total_favorites': user_notes.count(),
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'notes/favorite_notes.html', context)


@content_access_required
def recent_notes(request):
    """View recent notes (last 30 days) with access control"""
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    user_notes = StudentNote.objects.filter(
        student=request.user,
        created_at__gte=thirty_days_ago
    ).order_by('-created_at')
    
    user_notes = apply_user_access_filter(user_notes, request.user)
    
    # Pagination
    paginator = Paginator(user_notes, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'notes': page_obj,
        'total_recent': user_notes.count(),
        'user_access': get_user_access_info(request.user),
    }
    
    return render(request, 'notes/recent_notes.html', context)


@require_POST
@content_access_required
def bulk_delete_notes(request):
    """Bulk delete notes with access control"""
    note_ids = request.POST.getlist('note_ids')
    
    if not note_ids:
        return JsonResponse({'error': 'No notes selected'}, status=400)
    
    # Get notes that belong to user
    notes = StudentNote.objects.filter(id__in=note_ids, student=request.user)
    
    # Apply access control
    accessible_notes = []
    for note in notes:
        if check_object_access(note, request.user):
            accessible_notes.append(note)
    
    if not accessible_notes:
        return JsonResponse({'error': 'No accessible notes to delete'}, status=403)
    
    # Delete accessible notes
    deleted_count = len(accessible_notes)
    for note in accessible_notes:
        note.delete()
    
    return JsonResponse({
        'success': True,
        'deleted_count': deleted_count,
        'message': f'{deleted_count} notes deleted successfully',
        'user_access_level': get_user_access_info(request.user).get('level', 'student')
    })


@require_POST
@content_access_required
def bulk_favorite_notes(request):
    """Bulk toggle favorite status with access control"""
    note_ids = request.POST.getlist('note_ids')
    action = request.POST.get('action', 'add')  # 'add' or 'remove'
    
    if not note_ids:
        return JsonResponse({'error': 'No notes selected'}, status=400)
    
    # Get notes that belong to user
    notes = StudentNote.objects.filter(id__in=note_ids, student=request.user)
    
    # Apply access control
    accessible_notes = []
    for note in notes:
        if check_object_access(note, request.user):
            accessible_notes.append(note)
    
    if not accessible_notes:
        return JsonResponse({'error': 'No accessible notes to modify'}, status=403)
    
    # Update favorite status
    updated_count = 0
    for note in accessible_notes:
        if action == 'add':
            note.is_favorite = True
        else:
            note.is_favorite = False
        note.save()
        updated_count += 1
    
    action_text = 'added to' if action == 'add' else 'removed from'
    
    return JsonResponse({
        'success': True,
        'updated_count': updated_count,
        'message': f'{updated_count} notes {action_text} favorites',
        'user_access_level': get_user_access_info(request.user).get('level', 'student')
    })