# manageimage/views.py - Complete views with QuestionBank and Model Paper support
# FIXED for Windows Path serialization issues

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from .models import QuestionImage
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def safe_path_to_string(path_obj):
    """Convert any path object to string safely"""
    if isinstance(path_obj, (Path, os.PathLike)):
        return str(path_obj)
    return path_obj

@login_required
def manage_images(request):
    """Main image management view with enhanced statistics and filtering"""
    
    # Get search and filter parameters
    query = request.GET.get('q', '')
    usage_filter = request.GET.get('usage', '')  # 'used', 'unused', 'questionbank', 'modelpaper'
    sort_by = request.GET.get('sort', '-uploaded_at')  # Default sort by newest first
    
    images = QuestionImage.objects.all()
    
    # Apply search if provided
    if query:
        images = images.filter(
            Q(filename__icontains=query) |
            Q(uploaded_by__username__icontains=query)
        )
    
    # Apply usage filter if provided
    if usage_filter:
        filtered_images = []
        for image in images:
            usage_details = image.get_image_usage_details()
            
            if usage_filter == 'used' and usage_details['total_usage'] > 0:
                filtered_images.append(image.id)
            elif usage_filter == 'unused' and usage_details['total_usage'] == 0:
                filtered_images.append(image.id)
            elif usage_filter == 'questionbank' and usage_details['questionbank_count'] > 0:
                filtered_images.append(image.id)
            elif usage_filter == 'modelpaper' and usage_details['modelpaper_count'] > 0:
                filtered_images.append(image.id)
        
        images = images.filter(id__in=filtered_images)
    
    # Apply sorting
    valid_sort_fields = ['filename', 'uploaded_at', 'file_size', '-filename', '-uploaded_at', '-file_size']
    if sort_by in valid_sort_fields:
        images = images.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(images, 12)  # Show 12 images per page (grid layout)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get usage statistics
    stats = QuestionImage.get_usage_stats()
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'usage_filter': usage_filter,
        'sort_by': sort_by,
        'stats': stats,
        'total_images': images.count(),
        'all_images_count': QuestionImage.objects.count(),
    }
    
    return render(request, 'manageimage/manage_images.html', context)

@login_required
@require_POST
def upload_images(request):
    """Handle bulk image upload with comprehensive error handling"""
    
    try:
        # Log the request details for debugging
        logger.info(f"Upload request from user: {request.user.username}")
        logger.info(f"Request FILES keys: {list(request.FILES.keys())}")
        logger.info(f"Request POST keys: {list(request.POST.keys())}")
        
        uploaded_files = request.FILES.getlist('images')
        
        if not uploaded_files:
            logger.warning("No files provided in upload request")
            return JsonResponse({
                'success': False,
                'error': 'No files provided. Please select images to upload.'
            }, status=400)
        
        logger.info(f"Processing {len(uploaded_files)} files")
        
        success_count = 0
        error_count = 0
        errors = []
        successful_files = []
        
        # Check if media directory exists and is writable
        media_path = os.path.join(settings.MEDIA_ROOT, 'question_images')
        if not os.path.exists(media_path):
            try:
                os.makedirs(media_path, exist_ok=True)
                logger.info(f"Created media directory: {media_path}")
            except Exception as e:
                logger.error(f"Failed to create media directory: {e}")
                return JsonResponse({
                    'success': False,
                    'error': f'Media directory setup failed: {str(e)}'
                }, status=500)
        
        for file in uploaded_files:
            try:
                logger.info(f"Processing file: {file.name}, size: {file.size}, type: {file.content_type}")
                
                # Validate file type
                allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
                if file.content_type not in allowed_types:
                    error_msg = f"{file.name}: Invalid file type ({file.content_type}). Allowed: JPG, PNG, GIF, WebP"
                    errors.append(error_msg)
                    error_count += 1
                    logger.warning(error_msg)
                    continue
                
                # Validate file size (max 5MB)
                max_size = 5 * 1024 * 1024  # 5MB
                if file.size > max_size:
                    error_msg = f"{file.name}: File too large ({file.size:,} bytes). Maximum allowed: {max_size:,} bytes (5MB)"
                    errors.append(error_msg)
                    error_count += 1
                    logger.warning(error_msg)
                    continue
                
                # Validate filename
                if not file.name or len(file.name) > 255:
                    error_msg = f"{file.name}: Invalid filename length"
                    errors.append(error_msg)
                    error_count += 1
                    logger.warning(error_msg)
                    continue
                
                # Check if filename already exists
                existing_image = QuestionImage.objects.filter(filename=file.name).first()
                if existing_image:
                    uploaded_by_name = existing_image.uploaded_by.username if existing_image.uploaded_by else 'unknown'
                    uploaded_date = existing_image.uploaded_at.strftime('%Y-%m-%d')
                    error_msg = f"{file.name}: File with this name already exists (uploaded by {uploaded_by_name} on {uploaded_date})"
                    errors.append(error_msg)
                    error_count += 1
                    logger.warning(error_msg)
                    continue
                
                # Create image record
                try:
                    image_obj = QuestionImage.objects.create(
                        image=file,
                        uploaded_by=request.user
                    )
                    successful_files.append({
                        'id': image_obj.id,
                        'filename': image_obj.filename,
                        'size': image_obj.file_size_formatted,
                        'url': str(image_obj.image.url) if image_obj.image else None  # Convert to string
                    })
                    success_count += 1
                    logger.info(f"Successfully created image: {image_obj.filename} (ID: {image_obj.id})")
                    
                except Exception as e:
                    error_msg = f"{file.name}: Database error - {str(e)}"
                    errors.append(error_msg)
                    error_count += 1
                    logger.error(f"Database error for file {file.name}: {str(e)}", exc_info=True)
                
            except Exception as e:
                error_msg = f"{file.name}: Processing error - {str(e)}"
                errors.append(error_msg)
                error_count += 1
                logger.error(f"Processing error for file {file.name}: {str(e)}", exc_info=True)
        
        # Prepare response
        response_data = {
            'success': success_count > 0,
            'uploaded': success_count,
            'failed': error_count,
            'total_processed': len(uploaded_files),
            'errors': errors[:20] if errors else [],  # Return first 20 errors
            'successful_files': successful_files,
            'message': f'Upload completed: {success_count} successful, {error_count} failed'
        }
        
        logger.info(f"Upload completed: {success_count} successful, {error_count} failed")
        
        # Return appropriate status code
        if success_count > 0 and error_count == 0:
            status_code = 200  # All successful
        elif success_count > 0 and error_count > 0:
            status_code = 206  # Partial success
        else:
            status_code = 400  # All failed
            response_data['success'] = False
        
        return JsonResponse(response_data, status=status_code)
        
    except Exception as e:
        logger.error(f"Critical error in upload_images: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Server error during upload: {str(e)}',
            'uploaded': 0,
            'failed': 0
        }, status=500)

@login_required
@require_POST
def delete_image(request, image_id):
    """Delete a single image with comprehensive usage checking"""
    try:
        logger.info(f"Delete request for image {image_id} from user {request.user.username}")
        
        image = get_object_or_404(QuestionImage, id=image_id)
        
        # Get comprehensive usage information
        usage_details = image.get_image_usage_details()
        total_usage = usage_details['total_usage']
        
        if total_usage > 0:
            # Create detailed error message
            usage_parts = []
            if usage_details['questionbank_count'] > 0:
                qb_details = []
                if usage_details['questionbank_question_usage'] > 0:
                    qb_details.append(f"{usage_details['questionbank_question_usage']} question image(s)")
                if usage_details['questionbank_explanation_usage'] > 0:
                    qb_details.append(f"{usage_details['questionbank_explanation_usage']} explanation image(s)")
                usage_parts.append(f"QuestionBank: {', '.join(qb_details)}")
            
            if usage_details['modelpaper_count'] > 0:
                mp_details = []
                if usage_details['modelpaper_question_usage'] > 0:
                    mp_details.append(f"{usage_details['modelpaper_question_usage']} question image(s)")
                if usage_details['modelpaper_explanation_usage'] > 0:
                    mp_details.append(f"{usage_details['modelpaper_explanation_usage']} explanation image(s)")
                usage_parts.append(f"Model Papers: {', '.join(mp_details)}")
            
            usage_message = "; ".join(usage_parts)
            error_msg = f'Cannot delete "{image.filename}". Image is currently used in: {usage_message}'
            
            logger.warning(f"Delete blocked for image {image_id}: {error_msg}")
            return JsonResponse({
                'success': False,
                'error': error_msg,
                'usage_count': total_usage
            }, status=400)
        
        # Image is not used, safe to delete
        filename = image.filename
        
        # Get file path as string to avoid WindowsPath serialization issues
        file_path_str = str(image.image.path) if image.image else None
        
        # Delete the database record (this will also delete the file via model's delete method)
        image.delete()
        
        # Double-check file deletion
        if file_path_str and os.path.exists(file_path_str):
            try:
                os.remove(file_path_str)
                logger.info(f"Manually removed orphaned file: {file_path_str}")
            except Exception as e:
                logger.warning(f"Could not remove file {file_path_str}: {e}")
        
        logger.info(f"Successfully deleted image: {filename}")
        return JsonResponse({
            'success': True,
            'message': f'Image "{filename}" deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting image {image_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Delete failed: {str(e)}'
        }, status=500)

@login_required
def get_image_usage(request, image_id):
    """Get detailed usage information for both QuestionBank and Model Paper"""
    try:
        image = get_object_or_404(QuestionImage, id=image_id)
        
        # Get comprehensive usage information
        usage_details = image.get_image_usage_details()
        
        # Convert image URL to string to avoid path serialization issues
        image_url = str(image.image.url) if image.image else None
        
        # Format response data with detailed breakdown
        response_data = {
            'success': True,
            'filename': image.filename,
            'image_url': image_url,
            'file_size': image.file_size_formatted,
            'uploaded_at': image.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
            'uploaded_by': image.uploaded_by.username if image.uploaded_by else 'Unknown',
            'usage_count': usage_details['total_usage'],
            'questionbank_count': usage_details['questionbank_count'],
            'modelpaper_count': usage_details['modelpaper_count'],
            'question_image_usage': usage_details['question_image_usage'],
            'explanation_image_usage': usage_details['explanation_image_usage'],
            'usage_tags': usage_details['usage_tags'],
            'usage_breakdown': {
                'questionbank_question_usage': usage_details['questionbank_question_usage'],
                'questionbank_explanation_usage': usage_details['questionbank_explanation_usage'],
                'modelpaper_question_usage': usage_details['modelpaper_question_usage'],
                'modelpaper_explanation_usage': usage_details['modelpaper_explanation_usage'],
            },
            'questions': []
        }
        
        # Add QuestionBank questions with detailed information
        for q in usage_details['questionbank_questions']:
            question_info = {
                'id': q['id'],
                'question_preview': q['question_text'][:150] + '...' if len(q['question_text']) > 150 else q['question_text'],
                'degree': q['degree'],
                'year': q['year'],
                'subject': q['subject'],
                'topic': q['topic'],
                'block': q['block'],
                'module': q['module'],
                'usage_type': q['usage_type'],
                'source': 'QuestionBank',
                'source_tag': 'QB',
                'edit_url': f'/questionbank/question/{q["id"]}/',
                'question_image': q.get('question_image'),
                'explanation_image': q.get('explanation_image')
            }
            response_data['questions'].append(question_info)
        
        # Add Model Paper questions with detailed information
        for q in usage_details['modelpaper_questions']:
            question_info = {
                'id': q['id'],
                'question_preview': q['question_text'][:150] + '...' if len(q['question_text']) > 150 else q['question_text'],
                'paper_name': q['paper_name'],
                'degree': q['degree'],
                'year': q['year'],
                'subject': q['subject'],
                'topic': q['topic'],
                'module': q['module'],
                'usage_type': q['usage_type'],
                'source': 'Model Paper',
                'source_tag': 'MP',
                'edit_url': f'/modelpaper/questions/{q["paper_name"]}/',
                'paper_image': q.get('paper_image'),
                'explanation_image': q.get('explanation_image')
            }
            response_data['questions'].append(question_info)
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error getting usage details for image {image_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to get usage details: {str(e)}'
        }, status=500)

@login_required
def get_available_images(request):
    """API endpoint to get list of available images for dropdowns/autocomplete"""
    try:
        search_query = request.GET.get('q', '')
        limit = int(request.GET.get('limit', 50))
        
        images = QuestionImage.objects.all()
        
        if search_query:
            images = images.filter(filename__icontains=search_query)
        
        images = images.order_by('-uploaded_at')[:limit]
        
        image_list = []
        for img in images:
            # Convert image URL to string to avoid path serialization issues
            image_url = str(img.image.url) if img.image else None
            
            image_list.append({
                'id': img.id,
                'filename': img.filename,
                'url': image_url,
                'uploaded_at': img.uploaded_at.strftime('%Y-%m-%d'),
                'file_size': img.file_size_formatted,
                'uploaded_by': img.uploaded_by.username if img.uploaded_by else 'Unknown'
            })
        
        return JsonResponse({
            'success': True,
            'images': image_list,
            'total_found': len(image_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting available images: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def get_image_usage_summary(request, image_id):
    """Get quick usage summary for display in image cards"""
    try:
        image = get_object_or_404(QuestionImage, id=image_id)
        usage_details = image.get_image_usage_details()
        
        return JsonResponse({
            'success': True,
            'total_usage': usage_details['total_usage'],
            'usage_tags': usage_details['usage_tags'],
            'questionbank_count': usage_details['questionbank_count'],
            'modelpaper_count': usage_details['modelpaper_count'],
            'breakdown': {
                'questionbank_question': usage_details['questionbank_question_usage'],
                'questionbank_explanation': usage_details['questionbank_explanation_usage'],
                'modelpaper_question': usage_details['modelpaper_question_usage'],
                'modelpaper_explanation': usage_details['modelpaper_explanation_usage'],
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting usage summary for image {image_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def bulk_delete_images(request):
    """Handle bulk deletion of images with comprehensive usage checking"""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        image_ids = data.get('image_ids', [])
        
        if not image_ids:
            return JsonResponse({
                'success': False,
                'error': 'No images selected for deletion'
            }, status=400)
        
        logger.info(f"Bulk delete request for {len(image_ids)} images from user {request.user.username}")
        
        # Check usage for all selected images
        used_images = []
        can_delete = []
        not_found = []
        
        for image_id in image_ids:
            try:
                image = QuestionImage.objects.get(id=image_id)
                usage_details = image.get_image_usage_details()
                
                if usage_details['total_usage'] > 0:
                    used_images.append({
                        'id': image_id,
                        'filename': image.filename,
                        'usage_count': usage_details['total_usage'],
                        'questionbank_count': usage_details['questionbank_count'],
                        'modelpaper_count': usage_details['modelpaper_count'],
                        'usage_tags': usage_details['usage_tags']
                    })
                else:
                    can_delete.append(image)
                    
            except QuestionImage.DoesNotExist:
                not_found.append(image_id)
                continue
        
        # Delete images that can be deleted
        deleted_count = 0
        deleted_filenames = []
        delete_errors = []
        
        for image in can_delete:
            try:
                deleted_filenames.append(image.filename)
                image.delete()
                deleted_count += 1
                logger.info(f"Bulk deleted image: {image.filename}")
            except Exception as e:
                delete_errors.append(f"Failed to delete {image.filename}: {str(e)}")
                logger.error(f"Error deleting image {image.filename}: {str(e)}")
        
        response_data = {
            'success': True,
            'deleted_count': deleted_count,
            'deleted_filenames': deleted_filenames,
            'used_images_count': len(used_images),
            'used_images': used_images[:10],  # Return first 10 used images
            'not_found_count': len(not_found),
            'delete_errors': delete_errors,
            'message': f'Bulk deletion completed: {deleted_count} deleted, {len(used_images)} skipped (in use), {len(not_found)} not found'
        }
        
        if used_images:
            response_data['warning'] = f'{len(used_images)} image(s) could not be deleted because they are currently in use'
        
        if delete_errors:
            response_data['warning'] = f'{len(delete_errors)} image(s) encountered errors during deletion'
        
        logger.info(f"Bulk delete completed: {response_data}")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Critical error in bulk_delete_images: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Bulk delete failed: {str(e)}'
        }, status=500)

@login_required
def get_usage_statistics(request):
    """Get comprehensive usage statistics for dashboard"""
    try:
        stats = QuestionImage.get_usage_stats()
        
        # Add additional statistics
        total_images = QuestionImage.objects.count()
        
        # Get breakdown by usage type
        usage_breakdown = {
            'question_only': 0,
            'explanation_only': 0,
            'both': 0,
            'unused': 0
        }
        
        # Get file size statistics
        file_sizes = QuestionImage.objects.exclude(file_size__isnull=True).values_list('file_size', flat=True)
        total_size = sum(file_sizes) if file_sizes else 0
        avg_size = total_size / len(file_sizes) if file_sizes else 0
        
        # Calculate usage breakdown
        for image in QuestionImage.objects.all():
            usage_details = image.get_image_usage_details()
            
            if usage_details['total_usage'] == 0:
                usage_breakdown['unused'] += 1
            elif usage_details['question_image_usage'] > 0 and usage_details['explanation_image_usage'] > 0:
                usage_breakdown['both'] += 1
            elif usage_details['question_image_usage'] > 0:
                usage_breakdown['question_only'] += 1
            elif usage_details['explanation_image_usage'] > 0:
                usage_breakdown['explanation_only'] += 1
        
        # Enhanced statistics
        enhanced_stats = {
            **stats,
            'usage_breakdown': usage_breakdown,
            'file_statistics': {
                'total_size_bytes': total_size,
                'total_size_formatted': format_file_size(total_size),
                'average_size_bytes': int(avg_size),
                'average_size_formatted': format_file_size(avg_size),
                'largest_file': max(file_sizes) if file_sizes else 0,
                'smallest_file': min(file_sizes) if file_sizes else 0
            },
            'recent_uploads': list(QuestionImage.objects.order_by('-uploaded_at')[:5].values(
                'id', 'filename', 'uploaded_at', 'uploaded_by__username'
            ))
        }
        
        return JsonResponse(enhanced_stats)
        
    except Exception as e:
        logger.error(f"Error getting usage statistics: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if not size_bytes:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

@login_required
def get_image_by_filename(request):
    """API endpoint to search for images by filename (for form autocomplete)"""
    try:
        query = request.GET.get('q', '')
        exact_match = request.GET.get('exact', 'false').lower() == 'true'
        
        if not query or len(query) < 2:
            return JsonResponse({
                'success': True,
                'images': []
            })
        
        if exact_match:
            images = QuestionImage.objects.filter(filename__iexact=query)
        else:
            images = QuestionImage.objects.filter(filename__icontains=query)
        
        images = images.order_by('filename')[:10]
        
        image_list = []
        for img in images:
            image_list.append({
                'id': img.id,
                'filename': img.filename,
                'uploaded_at': img.uploaded_at.strftime('%Y-%m-%d'),
                'url': str(img.image.url) if img.image else None,  # Convert to string
                'file_size': img.file_size_formatted
            })
        
        return JsonResponse({
            'success': True,
            'images': image_list
        })
        
    except Exception as e:
        logger.error(f"Error searching images by filename: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def cleanup_unused_images(request):
    """Admin tool to identify and optionally remove unused images"""
    try:
        # Check admin permissions
        if not (request.user.is_admin or request.user.is_superuser):
            return JsonResponse({
                'success': False,
                'error': 'Admin access required'
            }, status=403)
        
        if request.method == 'POST':
            # Actually delete unused images
            deleted_count = 0
            deleted_files = []
            errors = []
            
            for image in QuestionImage.objects.all():
                try:
                    usage_details = image.get_image_usage_details()
                    if usage_details['total_usage'] == 0:
                        deleted_files.append({
                            'filename': image.filename,
                            'size': image.file_size_formatted,
                            'uploaded_at': image.uploaded_at.strftime('%Y-%m-%d')
                        })
                        image.delete()
                        deleted_count += 1
                except Exception as e:
                    errors.append(f"Error deleting {image.filename}: {str(e)}")
            
            logger.info(f"Cleanup completed by {request.user.username}: {deleted_count} images deleted")
            
            return JsonResponse({
                'success': True,
                'deleted_count': deleted_count,
                'deleted_files': deleted_files[:50],  # Return first 50 filenames
                'errors': errors
            })
        
        else:
            # Just identify unused images
            unused_images = []
            total_unused_size = 0
            
            for image in QuestionImage.objects.all():
                usage_details = image.get_image_usage_details()
                if usage_details['total_usage'] == 0:
                    image_info = {
                        'id': image.id,
                        'filename': image.filename,
                        'uploaded_at': image.uploaded_at.strftime('%Y-%m-%d'),
                        'file_size': image.file_size_formatted,
                        'file_size_bytes': image.file_size or 0,
                        'uploaded_by': image.uploaded_by.username if image.uploaded_by else 'Unknown'
                    }
                    unused_images.append(image_info)
                    total_unused_size += image.file_size or 0
            
            return JsonResponse({
                'success': True,
                'unused_images': unused_images,
                'count': len(unused_images),
                'total_size_bytes': total_unused_size,
                'total_size_formatted': format_file_size(total_unused_size)
            })
            
    except Exception as e:
        logger.error(f"Error in cleanup_unused_images: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def debug_images(request):
    """Debug view to check image loading issues with enhanced Model Paper support"""
    try:
        debug_info = []
        
        for image in QuestionImage.objects.all()[:10]:  # Limit to first 10 for debugging
            file_path = str(image.image.path) if image.image else "No file"
            file_exists = os.path.exists(file_path) if image.image else False
            
            # Get usage details
            usage_details = image.get_image_usage_details()
            
            debug_info.append({
                'id': image.id,
                'filename': image.filename,
                'image_field': str(image.image),
                'image_url': str(image.image.url) if image.image else "No URL",
                'file_path': file_path,
                'file_exists': file_exists,
                'total_usage': usage_details['total_usage'],
                'questionbank_usage': usage_details['questionbank_count'],
                'modelpaper_usage': usage_details['modelpaper_count'],
                'usage_tags': usage_details['usage_tags'],
                'file_size': image.file_size_formatted,
                'uploaded_by': image.uploaded_by.username if image.uploaded_by else 'Unknown'
            })
        
        context = {
            'debug_info': debug_info,
            'media_root': str(settings.MEDIA_ROOT),  # Convert to string
            'media_url': settings.MEDIA_URL,
            'stats': QuestionImage.get_usage_stats(),
            'total_images': QuestionImage.objects.count()
        }
        
        return render(request, 'manageimage/debug_images.html', context)
        
    except Exception as e:
        logger.error(f"Error in debug_images: {str(e)}")
        return render(request, 'manageimage/debug_images.html', {
            'error': str(e),
            'debug_info': [],
            'stats': {}
        })

@login_required
def test_images(request):
    """Simple test view to check image loading with usage information"""
    try:
        images_data = []
        for image in QuestionImage.objects.all()[:5]:  # First 5 images
            usage_details = image.get_image_usage_details()
            images_data.append({
                'image': image,
                'usage_details': usage_details,
                'can_delete': usage_details['total_usage'] == 0
            })
        
        return render(request, 'manageimage/test_images.html', {
            'images_data': images_data,
            'stats': QuestionImage.get_usage_stats()
        })
        
    except Exception as e:
        logger.error(f"Error in test_images: {str(e)}")
        return render(request, 'manageimage/test_images.html', {
            'error': str(e),
            'images_data': [],
            'stats': {}
        })

@login_required
def debug_upload(request):
    """Debug view to test upload functionality and server configuration"""
    try:
        # Convert all paths to strings to avoid WindowsPath serialization issues
        media_root_str = str(settings.MEDIA_ROOT)
        question_images_path = os.path.join(media_root_str, 'question_images')
        
        debug_data = {
            'method': request.method,
            'user': str(request.user),
            'user_authenticated': request.user.is_authenticated,
            'csrf_token_in_cookies': 'csrftoken' in request.COOKIES,
            'media_root': media_root_str,  # Convert to string
            'media_url': settings.MEDIA_URL,
            'media_root_exists': os.path.exists(media_root_str),
            'question_images_dir_exists': os.path.exists(question_images_path),
            'timestamp': timezone.now().isoformat(),
            'platform': os.name,
            'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}"
        }
        
        if request.method == 'POST':
            debug_data.update({
                'files_received': list(request.FILES.keys()),
                'post_data_keys': list(request.POST.keys()),
                'csrf_token_in_post': 'csrfmiddlewaretoken' in request.POST,
                'content_type': request.content_type,
                'content_length': request.META.get('CONTENT_LENGTH', 'Not provided')
            })
            
            # Test file processing
            if 'images' in request.FILES:
                files = request.FILES.getlist('images')
                debug_data['test_files'] = []
                
                for file in files[:3]:  # Test first 3 files
                    debug_data['test_files'].append({
                        'name': file.name,
                        'size': file.size,
                        'content_type': file.content_type,
                        'valid_type': file.content_type.startswith('image/'),
                        'valid_size': file.size <= 5 * 1024 * 1024
                    })
            
            debug_data['success'] = True
            debug_data['message'] = 'Debug upload endpoint working correctly'
        
        return JsonResponse(debug_data)
        
    except Exception as e:
        logger.error(f"Error in debug_upload: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'method': request.method,
            'user': str(request.user) if hasattr(request, 'user') else 'No user'
        }, status=500)

@login_required
def export_image_list(request):
    """Export list of images with usage information to CSV"""
    try:
        import csv
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="images_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'ID', 'Filename', 'File Size', 'Uploaded At', 'Uploaded By',
            'Total Usage', 'QuestionBank Usage', 'Model Paper Usage',
            'Question Image Usage', 'Explanation Image Usage', 'Usage Tags'
        ])
        
        # Write data
        for image in QuestionImage.objects.all().order_by('-uploaded_at'):
            usage_details = image.get_image_usage_details()
            
            writer.writerow([
                image.id,
                image.filename,
                image.file_size_formatted,
                image.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                image.uploaded_by.username if image.uploaded_by else 'Unknown',
                usage_details['total_usage'],
                usage_details['questionbank_count'],
                usage_details['modelpaper_count'],
                usage_details['question_image_usage'],
                usage_details['explanation_image_usage'],
                ', '.join(usage_details['usage_tags'])
            ])
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting image list: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Export failed: {str(e)}'
        }, status=500)

@login_required
def image_search_api(request):
    """Advanced API for image searching with multiple filters"""
    try:
        # Get parameters
        query = request.GET.get('q', '')
        usage_type = request.GET.get('usage_type', '')  # 'used', 'unused', 'questionbank', 'modelpaper'
        file_type = request.GET.get('file_type', '')  # 'jpg', 'png', 'gif', etc.
        uploaded_by = request.GET.get('uploaded_by', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        sort_by = request.GET.get('sort', 'filename')
        limit = min(int(request.GET.get('limit', 50)), 100)  # Max 100 results
        
        images = QuestionImage.objects.all()
        
        # Apply filters
        if query:
            images = images.filter(filename__icontains=query)
        
        if file_type:
            images = images.filter(filename__iendswith=f'.{file_type}')
        
        if uploaded_by:
            images = images.filter(uploaded_by__username__icontains=uploaded_by)
        
        if date_from:
            from django.utils.dateparse import parse_date
            date_from_parsed = parse_date(date_from)
            if date_from_parsed:
                images = images.filter(uploaded_at__date__gte=date_from_parsed)
        
        if date_to:
            from django.utils.dateparse import parse_date
            date_to_parsed = parse_date(date_to)
            if date_to_parsed:
                images = images.filter(uploaded_at__date__lte=date_to_parsed)
        
        # Apply usage filtering
        if usage_type:
            filtered_ids = []
            for image in images:
                usage_details = image.get_image_usage_details()
                
                if (usage_type == 'used' and usage_details['total_usage'] > 0) or \
                   (usage_type == 'unused' and usage_details['total_usage'] == 0) or \
                   (usage_type == 'questionbank' and usage_details['questionbank_count'] > 0) or \
                   (usage_type == 'modelpaper' and usage_details['modelpaper_count'] > 0):
                    filtered_ids.append(image.id)
            
            images = images.filter(id__in=filtered_ids)
        
        # Apply sorting
        valid_sorts = ['filename', '-filename', 'uploaded_at', '-uploaded_at', 'file_size', '-file_size']
        if sort_by in valid_sorts:
            images = images.order_by(sort_by)
        
        # Limit results
        images = images[:limit]
        
        # Format response
        results = []
        for image in images:
            usage_details = image.get_image_usage_details()
            
            results.append({
                'id': image.id,
                'filename': image.filename,
                'url': str(image.image.url) if image.image else None,  # Convert to string
                'file_size': image.file_size_formatted,
                'uploaded_at': image.uploaded_at.isoformat(),
                'uploaded_by': image.uploaded_by.username if image.uploaded_by else 'Unknown',
                'usage_summary': {
                    'total': usage_details['total_usage'],
                    'questionbank': usage_details['questionbank_count'],
                    'modelpaper': usage_details['modelpaper_count'],
                    'tags': usage_details['usage_tags']
                }
            })
        
        return JsonResponse({
            'success': True,
            'results': results,
            'count': len(results),
            'total_available': QuestionImage.objects.count(),
            'filters_applied': {
                'query': query,
                'usage_type': usage_type,
                'file_type': file_type,
                'uploaded_by': uploaded_by,
                'date_range': f"{date_from} to {date_to}" if date_from or date_to else None,
                'sort_by': sort_by
            }
        })
        
    except Exception as e:
        logger.error(f"Error in image_search_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def batch_update_images(request):
    """Batch update image metadata or properties"""
    try:
        if request.method != 'POST':
            return JsonResponse({
                'success': False,
                'error': 'POST method required'
            }, status=405)
        
        # Check admin permissions
        if not (request.user.is_admin or request.user.is_superuser):
            return JsonResponse({
                'success': False,
                'error': 'Admin access required'
            }, status=403)
        
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        image_ids = data.get('image_ids', [])
        operation = data.get('operation', '')
        
        if not image_ids:
            return JsonResponse({
                'success': False,
                'error': 'No images selected'
            }, status=400)
        
        updated_count = 0
        errors = []
        
        if operation == 'recalculate_file_sizes':
            # Recalculate file sizes for selected images
            for image_id in image_ids:
                try:
                    image = QuestionImage.objects.get(id=image_id)
                    if image.image and os.path.exists(str(image.image.path)):
                        image.file_size = image.image.size
                        image.save()
                        updated_count += 1
                except QuestionImage.DoesNotExist:
                    errors.append(f"Image {image_id} not found")
                except Exception as e:
                    errors.append(f"Error updating image {image_id}: {str(e)}")
        
        elif operation == 'verify_files':
            # Verify that image files exist on disk
            missing_files = []
            for image_id in image_ids:
                try:
                    image = QuestionImage.objects.get(id=image_id)
                    file_path = str(image.image.path) if image.image else None
                    if not image.image or not os.path.exists(file_path):
                        missing_files.append({
                            'id': image.id,
                            'filename': image.filename,
                            'path': file_path or 'No path'
                        })
                except QuestionImage.DoesNotExist:
                    errors.append(f"Image {image_id} not found")
            
            return JsonResponse({
                'success': True,
                'operation': 'verify_files',
                'missing_files': missing_files,
                'missing_count': len(missing_files),
                'errors': errors
            })
        
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unknown operation: {operation}'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'operation': operation,
            'updated_count': updated_count,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error in batch_update_images: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# Error handler for common image-related errors
def handle_image_error(request, error_type='general', error_message='An error occurred'):
    """Centralized error handling for image operations"""
    
    if request.headers.get('Accept') == 'application/json' or 'api' in request.path:
        return JsonResponse({
            'success': False,
            'error': error_message,
            'error_type': error_type,
            'timestamp': timezone.now().isoformat()
        }, status=400)
    
    context = {
        'error_type': error_type,
        'error_message': error_message,
        'user': request.user,
        'timestamp': timezone.now()
    }
    
    return render(request, 'manageimage/error.html', context)

# Simple connection test view
@login_required
def test_connection(request):
    """Simple test view to verify URL routing"""
    return JsonResponse({
        'success': True,
        'message': 'manageimage URLs are working',
        'user': str(request.user),
        'method': request.method,
        'timestamp': timezone.now().isoformat()
    })