from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from .models import QuestionImage
import json

@login_required
def manage_images(request):
    """Main image management view"""
    
    # Get search and filter parameters
    query = request.GET.get('q', '')
    
    images = QuestionImage.objects.all()
    
    # Apply search if provided
    if query:
        images = images.filter(filename__icontains=query)
    
    # Pagination
    paginator = Paginator(images, 12)  # Show 12 images per page (grid layout)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get usage statistics
    stats = QuestionImage.get_usage_stats()
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'stats': stats,
        'total_images': images.count(),
    }
    
    return render(request, 'manageimage/manage_images.html', context)

@login_required
@require_POST
def upload_images(request):
    """Handle bulk image upload"""
    uploaded_files = request.FILES.getlist('images')
    
    if not uploaded_files:
        return JsonResponse({'error': 'No files provided'}, status=400)
    
    success_count = 0
    error_count = 0
    errors = []
    
    for file in uploaded_files:
        try:
            # Validate file type
            if not file.content_type.startswith('image/'):
                errors.append(f"{file.name}: Not a valid image file")
                error_count += 1
                continue
            
            # Validate file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                errors.append(f"{file.name}: File too large (max 5MB)")
                error_count += 1
                continue
            
            # Check if filename already exists
            if QuestionImage.objects.filter(filename=file.name).exists():
                errors.append(f"{file.name}: File already exists")
                error_count += 1
                continue
            
            # Create image record
            QuestionImage.objects.create(
                image=file,
                uploaded_by=request.user
            )
            success_count += 1
            
        except Exception as e:
            errors.append(f"{file.name}: {str(e)}")
            error_count += 1
    
    return JsonResponse({
        'success': True,
        'uploaded': success_count,
        'failed': error_count,
        'errors': errors[:10] if errors else []  # Return first 10 errors
    })

@login_required
@require_POST
def delete_image(request, image_id):
    """Delete a single image"""
    try:
        image = get_object_or_404(QuestionImage, id=image_id)
        
        # Check if image is being used
        from questionbank.models import Question
        usage_count = Question.objects.filter(image=image.filename).count()
        
        if usage_count > 0:
            return JsonResponse({
                'error': f'Cannot delete. Image is used in {usage_count} question(s)'
            }, status=400)
        
        filename = image.filename
        image.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Image "{filename}" deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
# Update manageimage/views.py to fix usage detection

@login_required
def get_image_usage(request, image_id):
    """Get usage details for a specific image"""
    try:
        image = get_object_or_404(QuestionImage, id=image_id)
        
        from questionbank.models import Question
        
        # FIX: Match by filename without extension AND with extension
        questions = Question.objects.filter(
            Q(image=image.filename) |  # Exact match
            Q(image=image.filename.rsplit('.', 1)[0]) |  # Without extension
            Q(image__icontains=image.filename.rsplit('.', 1)[0])  # Contains filename
        ).values(
            'id', 'question_text', 'degree', 'year', 'subject', 'topic'
        )
        
        usage_data = []
        for q in questions:
            usage_data.append({
                'id': q['id'],
                'question_preview': q['question_text'][:100] + '...' if len(q['question_text']) > 100 else q['question_text'],
                'degree': q['degree'],
                'year': q['year'],
                'subject': q['subject'],
                'topic': q['topic']
            })
        
        return JsonResponse({
            'filename': image.filename,
            'usage_count': len(usage_data),
            'questions': usage_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@login_required
def get_available_images(request):
    """API endpoint to get list of available images for dropdowns"""
    images = QuestionImage.objects.all().values('id', 'filename', 'uploaded_at')
    
    image_list = []
    for img in images:
        image_list.append({
            'id': img['id'],
            'filename': img['filename'],
            'uploaded_at': img['uploaded_at'].strftime('%Y-%m-%d')
        })
    
    return JsonResponse({'images': image_list})


# Add this debug view to manageimage/views.py

@login_required
def debug_images(request):
    """Debug view to check image loading issues"""
    from .models import QuestionImage
    import os
    from django.conf import settings
    
    debug_info = []
    
    for image in QuestionImage.objects.all():
        file_path = image.image.path if image.image else "No file"
        file_exists = os.path.exists(file_path) if image.image else False
        
        debug_info.append({
            'id': image.id,
            'filename': image.filename,
            'image_field': str(image.image),
            'image_url': image.image.url if image.image else "No URL",
            'file_path': file_path,
            'file_exists': file_exists,
            'media_root': settings.MEDIA_ROOT,
            'media_url': settings.MEDIA_URL,
        })
    
    context = {
        'debug_info': debug_info,
        'media_root': settings.MEDIA_ROOT,
        'media_url': settings.MEDIA_URL,
    }
    
    return render(request, 'manageimage/debug_images.html', context)


@login_required
def test_images(request):
    """Simple test view to check image loading"""
    from .models import QuestionImage
    
    images = QuestionImage.objects.all()[:3]  # First 3 images
    
    return render(request, 'manageimage/test_images.html', {'images': images})