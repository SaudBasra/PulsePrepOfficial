# manageimage/models.py - Updated with question_image support

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

    def get_image_usage_details(self):
        """Get detailed usage information including both question_image and image fields"""
        from questionbank.models import Question
        
        filename = self.filename
        filename_no_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # Initialize counters and lists
        usage_details = {
            'total_usage': 0,
            'questionbank_count': 0,
            'questionbank_questions': [],
            'usage_tags': [],
            'question_image_usage': 0,  # NEW: Track question image usage
            'explanation_image_usage': 0  # NEW: Track explanation image usage
        }
        
        print(f"DEBUG: Checking usage for image: {filename} (no ext: {filename_no_ext})")
        
        # Check both question_image and image fields
        questionbank_questions = Question.objects.filter(
            Q(question_image=filename) |  # Exact match for question images
            Q(question_image=filename_no_ext) |  # Without extension for question images
            Q(question_image__iexact=filename) |  # Case insensitive for question images
            Q(question_image__iexact=filename_no_ext) |  # Case insensitive without extension for question images
            Q(question_image__icontains=filename_no_ext) |  # Contains filename for question images
            Q(image=filename) |  # Exact match for explanation images
            Q(image=filename_no_ext) |  # Without extension for explanation images
            Q(image__iexact=filename) |  # Case insensitive for explanation images
            Q(image__iexact=filename_no_ext) |  # Case insensitive without extension for explanation images
            Q(image__icontains=filename_no_ext)  # Contains filename for explanation images
        ).exclude(
            Q(question_image__isnull=True) & Q(image__isnull=True) |
            Q(question_image__exact='') & Q(image__exact='')
        )
        
        print(f"DEBUG: Found {questionbank_questions.count()} QuestionBank matches")
        
        for q in questionbank_questions:
            print(f"DEBUG: QB Question {q.id} - question_image: '{q.question_image}', explanation_image: '{q.image}'")
            
            # Determine which field(s) match
            question_image_match = False
            explanation_image_match = False
            
            # Check question_image field
            if q.question_image:
                if (filename == q.question_image or 
                    filename_no_ext == q.question_image or
                    filename.lower() == q.question_image.lower() or
                    filename_no_ext.lower() == q.question_image.lower() or
                    (len(filename_no_ext) > 3 and filename_no_ext.lower() in q.question_image.lower())):
                    question_image_match = True
                    usage_details['question_image_usage'] += 1
            
            # Check explanation image field
            if q.image:
                if (filename == q.image or 
                    filename_no_ext == q.image or
                    filename.lower() == q.image.lower() or
                    filename_no_ext.lower() == q.image.lower() or
                    (len(filename_no_ext) > 3 and filename_no_ext.lower() in q.image.lower())):
                    explanation_image_match = True
                    usage_details['explanation_image_usage'] += 1
            
            # Add to questions list with usage type information
            usage_type = []
            if question_image_match:
                usage_type.append('Question')
            if explanation_image_match:
                usage_type.append('Explanation')
            
            usage_details['questionbank_questions'].append({
                'id': q.id,
                'question_text': q.question_text,
                'degree': q.degree,
                'year': q.year,
                'subject': q.subject,
                'topic': q.topic,
                'usage_type': ', '.join(usage_type),  # NEW: Show where image is used
                'question_image': q.question_image,
                'explanation_image': q.image
            })
        
        usage_details['questionbank_count'] = len(usage_details['questionbank_questions'])
        
        # Calculate total usage
        usage_details['total_usage'] = usage_details['questionbank_count']
        
        # Create usage tags with more detail
        tag_parts = []
        if usage_details['question_image_usage'] > 0:
            tag_parts.append(f"Q({usage_details['question_image_usage']})")
        if usage_details['explanation_image_usage'] > 0:
            tag_parts.append(f"E({usage_details['explanation_image_usage']})")
        
        if tag_parts:
            usage_details['usage_tags'].append(f"QB({'/'.join(tag_parts)})")
        
        print(f"DEBUG: Total usage for {filename}: {usage_details['total_usage']} (QB: {usage_details['questionbank_count']}, Q: {usage_details['question_image_usage']}, E: {usage_details['explanation_image_usage']})")
        
        return usage_details

    @classmethod
    def get_usage_stats(cls):
        """Usage statistics including both question_image and image fields"""
        from questionbank.models import Question

        total_images = cls.objects.count()

        if total_images == 0:
            return {
                'total_images': 0,
                'used_images': 0,
                'unused_images': 0,
                'usage_percentage': 0,
                'question_image_usage': 0,
                'explanation_image_usage': 0
            }

        print(f"DEBUG: Calculating usage stats for {total_images} images")

        # Get all images referenced in questions (both fields)
        questionbank_question_images = set()
        questionbank_explanation_images = set()
        
        # Get question images
        question_image_refs = Question.objects.exclude(
            Q(question_image__isnull=True) | Q(question_image__exact='')
        ).values_list('question_image', flat=True)

        for img_name in question_image_refs:
            if img_name and img_name.strip():
                clean_name = img_name.strip()
                questionbank_question_images.add(clean_name)
                if '.' in clean_name:
                    name_no_ext = clean_name.rsplit('.', 1)[0]
                    questionbank_question_images.add(name_no_ext)

        # Get explanation images
        explanation_image_refs = Question.objects.exclude(
            Q(image__isnull=True) | Q(image__exact='')
        ).values_list('image', flat=True)

        for img_name in explanation_image_refs:
            if img_name and img_name.strip():
                clean_name = img_name.strip()
                questionbank_explanation_images.add(clean_name)
                if '.' in clean_name:
                    name_no_ext = clean_name.rsplit('.', 1)[0]
                    questionbank_explanation_images.add(name_no_ext)

        # Combine all referenced images
        all_referenced_images = questionbank_question_images.union(questionbank_explanation_images)

        print(f"DEBUG: Found {len(questionbank_question_images)} unique question image refs")
        print(f"DEBUG: Found {len(questionbank_explanation_images)} unique explanation image refs")
        print(f"DEBUG: Total unique image references: {len(all_referenced_images)}")

        # Count how many of our uploaded images are actually used
        used_images = 0
        question_image_usage_count = 0
        explanation_image_usage_count = 0
        all_images = cls.objects.all()

        for uploaded_img in all_images:
            filename = uploaded_img.filename
            filename_no_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename

            # Enhanced matching strategies
            is_used_in_questions = (
                filename in questionbank_question_images or
                filename_no_ext in questionbank_question_images or
                any(filename.lower() == used_name.lower() for used_name in questionbank_question_images) or
                any(filename_no_ext.lower() == used_name.lower() for used_name in questionbank_question_images) or
                any(filename_no_ext.lower() in used_name.lower() for used_name in questionbank_question_images if len(filename_no_ext) > 3) or
                any(used_name.lower() in filename.lower() for used_name in questionbank_question_images if len(used_name) > 3)
            )

            is_used_in_explanations = (
                filename in questionbank_explanation_images or
                filename_no_ext in questionbank_explanation_images or
                any(filename.lower() == used_name.lower() for used_name in questionbank_explanation_images) or
                any(filename_no_ext.lower() == used_name.lower() for used_name in questionbank_explanation_images) or
                any(filename_no_ext.lower() in used_name.lower() for used_name in questionbank_explanation_images if len(filename_no_ext) > 3) or
                any(used_name.lower() in filename.lower() for used_name in questionbank_explanation_images if len(used_name) > 3)
            )

            if is_used_in_questions or is_used_in_explanations:
                used_images += 1
                if is_used_in_questions:
                    question_image_usage_count += 1
                if is_used_in_explanations:
                    explanation_image_usage_count += 1
                print(f"DEBUG: Image {filename} is USED (Q: {is_used_in_questions}, E: {is_used_in_explanations})")
            else:
                print(f"DEBUG: Image {filename} is UNUSED")

        print(f"DEBUG: Final stats - Total: {total_images}, Used: {used_images}, Question: {question_image_usage_count}, Explanation: {explanation_image_usage_count}")

        return {
            'total_images': total_images,
            'used_images': used_images,
            'unused_images': total_images - used_images,
            'usage_percentage': round((used_images / total_images * 100), 1) if total_images > 0 else 0,
            'question_image_usage': question_image_usage_count,
            'explanation_image_usage': explanation_image_usage_count
        }