# managemodule/views.py
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from questionbank.models import Question

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
                    
                    topic_list.append({
                        'name': topic_name,
                        'questions_count': topic_questions_count,
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
    """Display questions for a specific topic"""
    # Get topic parameters from URL
    block = request.GET.get('block', '')
    module = request.GET.get('module', '')
    subject = request.GET.get('subject', '')
    topic = request.GET.get('topic', '')
    degree = request.GET.get('degree', '')
    year = request.GET.get('year', '')
    
    # Get search parameter
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
    
    context = {
        'page_obj': page_obj,
        'breadcrumb': breadcrumb,
        'query': query,
        'total_questions': questions.count(),
    }
    
    return render(request, 'managemodule/topic_questions.html', context)