# modelpaper/models.py - UPDATED: Added image support

from django.db import models
from django.utils import timezone
from django.conf import settings
from django.db.models import Q

class PaperQuestion(models.Model):
    """Independent storage for all paper questions from CSV uploads - With image support"""
    CORRECT_ANSWER_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    
    DEGREE_CHOICES = [
        ('MBBS', 'MBBS'),
        ('BDS', 'BDS'),
    ]
    
    YEAR_CHOICES = [
        ('1st', '1st'),
        ('2nd', '2nd'),
        ('3rd', '3rd'),
        ('4th', '4th'),
        ('5th', '5th'),
    ]
    
    # Question content
    question_text = models.TextField()
    option_a = models.TextField()
    option_b = models.TextField()
    option_c = models.TextField()
    option_d = models.TextField()
    option_e = models.TextField(blank=True, null=True)
    correct_answer = models.CharField(max_length=1, choices=CORRECT_ANSWER_CHOICES)
    
    # Paper classification - paper_name is the key field
    paper_name = models.CharField(max_length=200)  # e.g., "MBBS Final 2024"
    degree = models.CharField(max_length=4, choices=DEGREE_CHOICES, blank=True)
    year = models.CharField(max_length=3, choices=YEAR_CHOICES, blank=True)
    module = models.CharField(max_length=100, blank=True)
    subject = models.CharField(max_length=100, blank=True)
    topic = models.CharField(max_length=100, blank=True)
    
    # Question metadata
    difficulty = models.CharField(max_length=6, choices=DIFFICULTY_CHOICES, default='Medium')
    explanation = models.TextField(blank=True, null=True)
    marks = models.IntegerField(default=1)
    
    # Image fields - Added for compatibility with question bank
    paper_image = models.CharField(max_length=255, blank=True, null=True, 
                                  help_text="Image to display with the question (filename only)")
    image = models.CharField(max_length=255, blank=True, null=True, 
                           help_text="Image to display with explanation (filename only)")
    
    # Import tracking
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['paper_name', 'id']
        
    def __str__(self):
        return f"{self.paper_name} - {self.question_text[:50]}..."
    
    @property
    def has_paper_image(self):
        """Check if question has a paper image"""
        return bool(self.paper_image and self.paper_image.strip())
    
    @property
    def has_explanation_image(self):
        """Check if explanation has an image"""
        return bool(self.image and self.image.strip())
    
    @property
    def paper_image_url(self):
        """Get URL for paper image if it exists"""
        if self.has_paper_image:
            from django.conf import settings
            return f"{settings.MEDIA_URL}question_images/{self.paper_image}"
        return None
    
    @property
    def explanation_image_url(self):
        """Get URL for explanation image if it exists"""
        if self.has_explanation_image:
            from django.conf import settings
            return f"{settings.MEDIA_URL}question_images/{self.image}"
        return None
    
    @classmethod
    def get_available_paper_names(cls):
        """Get list of available paper names from uploaded questions"""
        return cls.objects.values_list('paper_name', flat=True).distinct().order_by('paper_name')
    
    @classmethod
    def get_filtered_questions(cls, paper_name, degree=None, year=None, module=None, subject=None, topic=None):
        """Get questions filtered by paper_name and optional criteria"""
        questions = cls.objects.filter(paper_name=paper_name)
        
        if degree:
            questions = questions.filter(degree=degree)
        if year:
            questions = questions.filter(year=year)
        if module:
            questions = questions.filter(module__icontains=module)
        if subject:
            questions = questions.filter(subject__icontains=subject)
        if topic:
            questions = questions.filter(topic__icontains=topic)
            
        return questions
    
    @classmethod
    def get_paper_filter_options(cls, paper_name):
        """Get available filter options for a specific paper"""
        questions = cls.objects.filter(paper_name=paper_name)
        
        return {
            'degrees': list(questions.values_list('degree', flat=True).distinct().exclude(degree='')),
            'years': list(questions.values_list('year', flat=True).distinct().exclude(year='')),
            'modules': list(questions.values_list('module', flat=True).distinct().exclude(module='')),
            'subjects': list(questions.values_list('subject', flat=True).distinct().exclude(subject='')),
            'topics': list(questions.values_list('topic', flat=True).distinct().exclude(topic=''))
        }
    
    @classmethod
    def get_stats(cls):
        """Get basic statistics for paper questions"""
        total_questions = cls.objects.count()
        
        stats = {
            'total_questions': total_questions,
            'by_degree': {},
            'by_difficulty': {},
            'recent_count': cls.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
            'with_paper_images': cls.objects.exclude(
                Q(paper_image__isnull=True) | Q(paper_image__exact='')
            ).count(),
            'with_explanation_images': cls.objects.exclude(
                Q(image__isnull=True) | Q(image__exact='')
            ).count(),
            'paper_names_count': cls.objects.values('paper_name').distinct().count(),
        }
        
        # Count by degree
        for degree, _ in cls.DEGREE_CHOICES:
            stats['by_degree'][degree] = cls.objects.filter(degree=degree).count()
        
        # Count by difficulty
        for difficulty, _ in cls.DIFFICULTY_CHOICES:
            stats['by_difficulty'][difficulty] = cls.objects.filter(difficulty=difficulty).count()
        
        return stats


# Keep the rest of the models exactly the same...
class ModelPaper(models.Model):
    """Model paper configuration that uses PaperQuestion as source"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('completed', 'Completed'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Paper Selection and Filtering
    selected_paper_name = models.CharField(max_length=200)  # Selected from PaperQuestion.paper_name
    filter_degree = models.CharField(max_length=4, choices=PaperQuestion.DEGREE_CHOICES, blank=True)
    filter_year = models.CharField(max_length=3, choices=PaperQuestion.YEAR_CHOICES, blank=True)
    filter_module = models.CharField(max_length=100, blank=True)
    filter_subject = models.CharField(max_length=100, blank=True)
    filter_topic = models.CharField(max_length=100, blank=True)
    
    # Test Configuration
    duration_minutes = models.IntegerField(default=60)
    total_questions = models.IntegerField(default=0)  # Auto-calculated from filtered results
    passing_percentage = models.IntegerField(default=40)
    max_attempts = models.IntegerField(default=1)
    
    # Test Settings
    randomize_questions = models.BooleanField(default=True)
    randomize_options = models.BooleanField(default=True)
    show_explanations = models.BooleanField(default=True)
    
    # Schedule
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    # Status and Metadata
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_papers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def is_active(self):
        now = timezone.now()
        return self.status == 'live' and self.start_datetime <= now <= self.end_datetime
    
    @property
    def total_marks(self):
        return sum(q.marks for q in self.get_questions())
    
    @property
    def passing_marks(self):
        return int((self.passing_percentage / 100) * self.total_marks)
    
    def get_questions(self):
        """Get questions for this model paper based on filters"""
        return PaperQuestion.get_filtered_questions(
            paper_name=self.selected_paper_name,
            degree=self.filter_degree,
            year=self.filter_year,
            module=self.filter_module,
            subject=self.filter_subject,
            topic=self.filter_topic
        )
    
    def update_total_questions(self):
        """Update total_questions based on current filters"""
        self.total_questions = self.get_questions().count()
        self.save(update_fields=['total_questions'])


class ModelPaperAttempt(models.Model):
    """Student's attempt at a model paper"""
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]
    
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='paper_attempts')
    model_paper = models.ForeignKey(ModelPaper, on_delete=models.CASCADE, related_name='attempts')
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    score = models.IntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    warning_count = models.IntegerField(default=0)
    time_taken = models.IntegerField(default=0)  # in seconds
    
    class Meta:
        ordering = ['-started_at']
        unique_together = ['student', 'model_paper', 'started_at']
    
    def __str__(self):
        return f"{self.student.email} - {self.model_paper.title}"
    
    @property
    def passed(self):
        return self.percentage >= self.model_paper.passing_percentage
    
    @property
    def remaining_time(self):
        if self.status != 'in_progress':
            return 0
        elapsed = (timezone.now() - self.started_at).total_seconds()
        total_seconds = self.model_paper.duration_minutes * 60
        return max(0, int(total_seconds - elapsed))
    
    @property
    def time_taken_formatted(self):
        """Return formatted time taken in human readable format"""
        if not self.time_taken:
            return "0 seconds"
        
        seconds = self.time_taken
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds == 0:
                return f"{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                return f"{minutes}m {remaining_seconds}s"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            remaining_seconds = seconds % 60
            
            result = f"{hours}h"
            if remaining_minutes > 0:
                result += f" {remaining_minutes}m"
            if remaining_seconds > 0:
                result += f" {remaining_seconds}s"
            
            return result
    
    @property
    def time_taken_display(self):
        """Return time in MM:SS format for displays"""
        if not self.time_taken:
            return "00:00"
        
        minutes = self.time_taken // 60
        seconds = self.time_taken % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def time_taken_minutes(self):
        """Return time taken in minutes (for calculations)"""
        if not self.time_taken:
            return 0
        return round(self.time_taken / 60, 1)


class ModelPaperResponse(models.Model):
    """Student's response to a specific question in a paper attempt"""
    attempt = models.ForeignKey(ModelPaperAttempt, on_delete=models.CASCADE, related_name='responses')
    paper_question = models.ForeignKey(PaperQuestion, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=1, choices=PaperQuestion.CORRECT_ANSWER_CHOICES, blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    marked_for_review = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['attempt', 'paper_question']
    
    def __str__(self):
        return f"{self.attempt} - Q{self.paper_question.id} - {self.selected_answer or 'No Answer'}"
    
    def check_answer(self):
        """Check if the selected answer is correct"""
        if self.selected_answer and self.paper_question.correct_answer:
            self.is_correct = self.selected_answer == self.paper_question.correct_answer
        else:
            self.is_correct = False
        return self.is_correct


class PaperCSVImportHistory(models.Model):
    """Model to track CSV import history for paper questions"""
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PROCESSING', 'Processing'),
    ]
    
    file_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PROCESSING')
    total_rows = models.IntegerField(default=0)
    successful_imports = models.IntegerField(default=0)
    failed_imports = models.IntegerField(default=0)
    error_details = models.TextField(blank=True, null=True)
    file_size = models.BigIntegerField(default=0)  # in bytes
    paper_names_imported = models.TextField(blank=True, null=True)  # JSON list of paper names
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Paper CSV Import History"
        verbose_name_plural = "Paper CSV Import Histories"
    
    def __str__(self):
        return f"{self.file_name} - {self.status} ({self.uploaded_at})"
    
    @property
    def success_rate(self):
        if self.total_rows == 0:
            return 0
        return round((self.successful_imports / self.total_rows) * 100, 1)
    
    @property
    def imported_paper_names_list(self):
        """Get list of imported paper names from JSON"""
        if not self.paper_names_imported:
            return []
        try:
            import json
            return json.loads(self.paper_names_imported)
        except:
            return []