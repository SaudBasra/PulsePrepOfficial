# manageimage/models.py - Complete support for both QuestionBank and Model Paper

from django.db import models
from django.conf import settings
from django.db.models import Q
import os
import logging

logger = logging.getLogger(__name__)

class QuestionImage(models.Model):
    """Model to manage question images for both QuestionBank and Model Papers"""
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
                try:
                    os.remove(self.image.path)
                except Exception as e:
                    logger.warning(f"Could not delete file {self.image.path}: {e}")
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
        """Get detailed usage information for both QuestionBank and Model Paper"""
        from questionbank.models import Question
        
        # Try to import Model Paper models
        try:
            from modelpaper.models import PaperQuestion
            MODELPAPER_AVAILABLE = True
        except ImportError:
            PaperQuestion = None
            MODELPAPER_AVAILABLE = False
        
        filename = self.filename
        filename_no_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # Initialize usage details
        usage_details = {
            'total_usage': 0,
            'questionbank_count': 0,
            'modelpaper_count': 0,
            'questionbank_questions': [],
            'modelpaper_questions': [],
            'usage_tags': [],
            'question_image_usage': 0,  # Used in question_image/paper_image fields
            'explanation_image_usage': 0,  # Used in image fields (explanations)
            'questionbank_question_usage': 0,  # QB question_image usage
            'questionbank_explanation_usage': 0,  # QB image usage
            'modelpaper_question_usage': 0,  # MP paper_image usage
            'modelpaper_explanation_usage': 0,  # MP image usage
            'modelpaper_available': MODELPAPER_AVAILABLE
        }
        
        # === CHECK QUESTIONBANK USAGE ===
        questionbank_questions = Question.objects.filter(
            Q(question_image=filename) |
            Q(question_image=filename_no_ext) |
            Q(question_image__iexact=filename) |
            Q(question_image__iexact=filename_no_ext) |
            Q(question_image__icontains=filename_no_ext) |
            Q(image=filename) |
            Q(image=filename_no_ext) |
            Q(image__iexact=filename) |
            Q(image__iexact=filename_no_ext) |
            Q(image__icontains=filename_no_ext)
        ).exclude(
            Q(question_image__isnull=True) & Q(image__isnull=True) |
            Q(question_image__exact='') & Q(image__exact='')
        )
        
        for q in questionbank_questions:
            # Determine which field(s) match
            question_image_match = False
            explanation_image_match = False
            
            # Check question_image field
            if q.question_image and self._matches_filename(q.question_image, filename, filename_no_ext):
                question_image_match = True
                usage_details['questionbank_question_usage'] += 1
            
            # Check explanation image field
            if q.image and self._matches_filename(q.image, filename, filename_no_ext):
                explanation_image_match = True
                usage_details['questionbank_explanation_usage'] += 1
            
            # Add to questions list with usage type information
            usage_type = []
            if question_image_match:
                usage_type.append('Question')
            if explanation_image_match:
                usage_type.append('Explanation')
            
            if usage_type:  # Only add if there's a match
                usage_details['questionbank_questions'].append({
                    'id': q.id,
                    'question_text': q.question_text,
                    'degree': q.degree,
                    'year': q.year,
                    'subject': q.subject,
                    'topic': q.topic,
                    'block': q.block,
                    'module': q.module,
                    'usage_type': ', '.join(usage_type),
                    'question_image': q.question_image,
                    'explanation_image': q.image
                })
        
        usage_details['questionbank_count'] = len(usage_details['questionbank_questions'])
        
        # === CHECK MODEL PAPER USAGE ===
        if MODELPAPER_AVAILABLE:
            # Check if PaperQuestion has image fields (assuming paper_image and image)
            model_fields = [f.name for f in PaperQuestion._meta.get_fields()]
            has_paper_image = 'paper_image' in model_fields
            has_image = 'image' in model_fields
            
            if has_paper_image or has_image:
                # Build query based on available fields
                query_conditions = []
                
                if has_paper_image:
                    query_conditions.extend([
                        Q(paper_image=filename),
                        Q(paper_image=filename_no_ext),
                        Q(paper_image__iexact=filename),
                        Q(paper_image__iexact=filename_no_ext),
                        Q(paper_image__icontains=filename_no_ext)
                    ])
                
                if has_image:
                    query_conditions.extend([
                        Q(image=filename),
                        Q(image=filename_no_ext),
                        Q(image__iexact=filename),
                        Q(image__iexact=filename_no_ext),
                        Q(image__icontains=filename_no_ext)
                    ])
                
                if query_conditions:
                    modelpaper_questions = PaperQuestion.objects.filter(
                        *query_conditions, _connector=Q.OR
                    )
                    
                    # Exclude empty records
                    exclude_conditions = Q()
                    if has_paper_image and has_image:
                        exclude_conditions = (Q(paper_image__isnull=True) & Q(image__isnull=True)) | (Q(paper_image__exact='') & Q(image__exact=''))
                    elif has_paper_image:
                        exclude_conditions = Q(paper_image__isnull=True) | Q(paper_image__exact='')
                    elif has_image:
                        exclude_conditions = Q(image__isnull=True) | Q(image__exact='')
                    
                    modelpaper_questions = modelpaper_questions.exclude(exclude_conditions)
                    
                    for q in modelpaper_questions:
                        # Determine which field(s) match
                        paper_image_match = False
                        explanation_image_match = False
                        
                        # Check paper_image field if it exists
                        if has_paper_image and hasattr(q, 'paper_image') and q.paper_image:
                            if self._matches_filename(q.paper_image, filename, filename_no_ext):
                                paper_image_match = True
                                usage_details['modelpaper_question_usage'] += 1
                        
                        # Check explanation image field if it exists
                        if has_image and hasattr(q, 'image') and q.image:
                            if self._matches_filename(q.image, filename, filename_no_ext):
                                explanation_image_match = True
                                usage_details['modelpaper_explanation_usage'] += 1
                        
                        # Add to questions list with usage type information
                        usage_type = []
                        if paper_image_match:
                            usage_type.append('Question')
                        if explanation_image_match:
                            usage_type.append('Explanation')
                        
                        if usage_type:  # Only add if there's a match
                            usage_details['modelpaper_questions'].append({
                                'id': q.id,
                                'question_text': q.question_text,
                                'paper_name': q.paper_name,
                                'degree': q.degree,
                                'year': q.year,
                                'subject': q.subject,
                                'topic': q.topic,
                                'module': q.module,
                                'usage_type': ', '.join(usage_type),
                                'paper_image': getattr(q, 'paper_image', None),
                                'explanation_image': getattr(q, 'image', None)
                            })
                
                usage_details['modelpaper_count'] = len(usage_details['modelpaper_questions'])
        
        # Calculate totals
        usage_details['total_usage'] = usage_details['questionbank_count'] + usage_details['modelpaper_count']
        usage_details['question_image_usage'] = usage_details['questionbank_question_usage'] + usage_details['modelpaper_question_usage']
        usage_details['explanation_image_usage'] = usage_details['questionbank_explanation_usage'] + usage_details['modelpaper_explanation_usage']
        
        # Create detailed usage tags
        tag_parts = []
        
        # QuestionBank tags
        if usage_details['questionbank_count'] > 0:
            qb_parts = []
            if usage_details['questionbank_question_usage'] > 0:
                qb_parts.append(f"Q({usage_details['questionbank_question_usage']})")
            if usage_details['questionbank_explanation_usage'] > 0:
                qb_parts.append(f"E({usage_details['questionbank_explanation_usage']})")
            
            if qb_parts:
                tag_parts.append(f"QB({'/'.join(qb_parts)})")
        
        # Model Paper tags
        if usage_details['modelpaper_count'] > 0:
            mp_parts = []
            if usage_details['modelpaper_question_usage'] > 0:
                mp_parts.append(f"Q({usage_details['modelpaper_question_usage']})")
            if usage_details['modelpaper_explanation_usage'] > 0:
                mp_parts.append(f"E({usage_details['modelpaper_explanation_usage']})")
            
            if mp_parts:
                tag_parts.append(f"MP({'/'.join(mp_parts)})")
        
        usage_details['usage_tags'] = tag_parts
        
        return usage_details

    def _matches_filename(self, field_value, filename, filename_no_ext):
        """Helper method to check if a field value matches the image filename"""
        if not field_value:
            return False
        
        return (
            filename == field_value or
            filename_no_ext == field_value or
            filename.lower() == field_value.lower() or
            filename_no_ext.lower() == field_value.lower() or
            (len(filename_no_ext) > 3 and filename_no_ext.lower() in field_value.lower())
        )

    @classmethod
    def get_usage_stats(cls):
        """Usage statistics for both QuestionBank and Model Paper"""
        from questionbank.models import Question
        
        # Try to import Model Paper models
        try:
            from modelpaper.models import PaperQuestion
            MODELPAPER_AVAILABLE = True
        except ImportError:
            PaperQuestion = None
            MODELPAPER_AVAILABLE = False

        total_images = cls.objects.count()

        if total_images == 0:
            return {
                'total_images': 0,
                'used_images': 0,
                'unused_images': 0,
                'usage_percentage': 0,
                'questionbank_usage': 0,
                'modelpaper_usage': 0,
                'question_image_usage': 0,
                'explanation_image_usage': 0,
                'modelpaper_available': MODELPAPER_AVAILABLE
            }

        # Get all images referenced in QuestionBank
        questionbank_images = set()
        question_image_refs = Question.objects.exclude(
            Q(question_image__isnull=True) | Q(question_image__exact='')
        ).values_list('question_image', flat=True)

        for img_name in question_image_refs:
            if img_name and img_name.strip():
                clean_name = img_name.strip()
                questionbank_images.add(clean_name)
                if '.' in clean_name:
                    questionbank_images.add(clean_name.rsplit('.', 1)[0])

        explanation_image_refs = Question.objects.exclude(
            Q(image__isnull=True) | Q(image__exact='')
        ).values_list('image', flat=True)

        for img_name in explanation_image_refs:
            if img_name and img_name.strip():
                clean_name = img_name.strip()
                questionbank_images.add(clean_name)
                if '.' in clean_name:
                    questionbank_images.add(clean_name.rsplit('.', 1)[0])

        # Get all images referenced in Model Papers
        modelpaper_images = set()
        if MODELPAPER_AVAILABLE:
            model_fields = [f.name for f in PaperQuestion._meta.get_fields()]
            
            if 'paper_image' in model_fields:
                paper_image_refs = PaperQuestion.objects.exclude(
                    Q(paper_image__isnull=True) | Q(paper_image__exact='')
                ).values_list('paper_image', flat=True)

                for img_name in paper_image_refs:
                    if img_name and img_name.strip():
                        clean_name = img_name.strip()
                        modelpaper_images.add(clean_name)
                        if '.' in clean_name:
                            modelpaper_images.add(clean_name.rsplit('.', 1)[0])

            if 'image' in model_fields:
                mp_explanation_refs = PaperQuestion.objects.exclude(
                    Q(image__isnull=True) | Q(image__exact='')
                ).values_list('image', flat=True)

                for img_name in mp_explanation_refs:
                    if img_name and img_name.strip():
                        clean_name = img_name.strip()
                        modelpaper_images.add(clean_name)
                        if '.' in clean_name:
                            modelpaper_images.add(clean_name.rsplit('.', 1)[0])

        # Combine all referenced images
        all_referenced_images = questionbank_images.union(modelpaper_images)

        # Count how many of our uploaded images are actually used
        used_images = 0
        questionbank_usage_count = 0
        modelpaper_usage_count = 0
        question_image_usage_count = 0
        explanation_image_usage_count = 0

        for uploaded_img in cls.objects.all():
            filename = uploaded_img.filename
            filename_no_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename

            # Check if image is used
            is_used_in_questionbank = (
                filename in questionbank_images or
                filename_no_ext in questionbank_images or
                any(filename.lower() == used_name.lower() for used_name in questionbank_images) or
                any(filename_no_ext.lower() == used_name.lower() for used_name in questionbank_images)
            )

            is_used_in_modelpaper = (
                filename in modelpaper_images or
                filename_no_ext in modelpaper_images or
                any(filename.lower() == used_name.lower() for used_name in modelpaper_images) or
                any(filename_no_ext.lower() == used_name.lower() for used_name in modelpaper_images)
            )

            is_used_anywhere = is_used_in_questionbank or is_used_in_modelpaper

            if is_used_anywhere:
                used_images += 1
                
                if is_used_in_questionbank:
                    questionbank_usage_count += 1
                if is_used_in_modelpaper:
                    modelpaper_usage_count += 1

        return {
            'total_images': total_images,
            'used_images': used_images,
            'unused_images': total_images - used_images,
            'usage_percentage': round((used_images / total_images * 100), 1) if total_images > 0 else 0,
            'questionbank_usage': questionbank_usage_count,
            'modelpaper_usage': modelpaper_usage_count,
            'question_image_usage': question_image_usage_count,
            'explanation_image_usage': explanation_image_usage_count,
            'modelpaper_available': MODELPAPER_AVAILABLE
        }