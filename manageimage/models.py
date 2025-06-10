from django.db import models
from django.conf import settings
from django.db.models import Q
import os

class QuestionImage(models.Model):
    """Model to manage question images"""
    filename = models.CharField(max_length=255, unique=True)
    image = models.ImageField(upload_to='question_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    file_size = models.IntegerField(null=True, blank=True)  # in bytes
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Question Image'
        verbose_name_plural = 'Question Images'
    
    def __str__(self):
        return self.filename
    
    def save(self, *args, **kwargs):
        if self.image:
            self.filename = os.path.basename(self.image.name)
            self.file_size = self.image.size
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Delete the actual file when model is deleted
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        super().delete(*args, **kwargs)
    
    @property
    def file_size_formatted(self):
        """Return human readable file size"""
        if not self.file_size:
            return "Unknown"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @classmethod
    def get_usage_stats(cls):
        """Get image usage statistics"""
        from questionbank.models import Question
        
        total_images = cls.objects.count()
        
        if total_images == 0:
            return {
                'total_images': 0,
                'used_images': 0,
                'unused_images': 0,
                'usage_percentage': 0
            }
        
        # Get all questions that have images
        questions_with_images = Question.objects.exclude(
            Q(image__isnull=True) | Q(image__exact='')
        ).values_list('image', flat=True)
        
        # Get unique image names used in questions
        used_image_names = set()
        
        for img_name in questions_with_images:
            if img_name:
                used_image_names.add(img_name.strip())
        
        # Count how many of our uploaded images are actually used
        used_images = 0
        all_images = cls.objects.all()
        
        for uploaded_img in all_images:
            filename = uploaded_img.filename
            filename_no_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            
            # Check if this uploaded image is used (with various matching strategies)
            is_used = (
                filename in used_image_names or
                filename_no_ext in used_image_names or
                any(filename_no_ext.lower() in used_name.lower() for used_name in used_image_names) or
                any(used_name.lower() in filename.lower() for used_name in used_image_names)
            )
            
            if is_used:
                used_images += 1
        
        return {
            'total_images': total_images,
            'used_images': used_images,
            'unused_images': total_images - used_images,
            'usage_percentage': round((used_images / total_images * 100), 1) if total_images > 0 else 0
        }