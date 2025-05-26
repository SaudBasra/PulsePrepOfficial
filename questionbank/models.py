# questionbank/models.py
from django.db import models
from django.utils import timezone
from django.conf import settings

class CSVImportHistory(models.Model):
    """Model to track CSV import history"""
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
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "CSV Import History"
        verbose_name_plural = "CSV Import Histories"
    
    def __str__(self):
        return f"{self.file_name} - {self.status} ({self.uploaded_at})"
    
    @property
    def success_rate(self):
        if self.total_rows == 0:
            return 0
        return round((self.successful_imports / self.total_rows) * 100, 1)

class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('MCQ', 'Multiple Choice'),
        ('SEQ', 'Short Essay Question'),
        ('NOTE', 'Notes'),
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
    
    CORRECT_ANSWER_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'),  # Added Option E
    ]
    
    # Basic question details
    question_text = models.TextField()
    question_type = models.CharField(max_length=4, choices=QUESTION_TYPE_CHOICES, default='MCQ')
    created_on = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    # MCQ specific fields
    option_a = models.TextField(blank=True, null=True)
    option_b = models.TextField(blank=True, null=True)
    option_c = models.TextField(blank=True, null=True)
    option_d = models.TextField(blank=True, null=True)
    option_e = models.TextField(blank=True, null=True)  # Added Option E
    correct_answer = models.CharField(max_length=1, choices=CORRECT_ANSWER_CHOICES, blank=True, null=True)
    
    # Categorization - adding default values to fix migration issues
    degree = models.CharField(max_length=4, choices=DEGREE_CHOICES, default='MBBS')
    year = models.CharField(max_length=3, choices=YEAR_CHOICES, default='1st')
    block = models.CharField(max_length=100, default='General')
    module = models.CharField(max_length=100, default='General')
    subject = models.CharField(max_length=100, default='General')
    topic = models.CharField(max_length=100, default='General')
    
    # Additional info
    difficulty = models.CharField(max_length=6, choices=DIFFICULTY_CHOICES, default='Medium')
    explanation = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.question_text[:50]
    
    # Analytics helper methods
    @classmethod
    def get_stats(cls):
        """Get basic statistics for questions"""
        from django.contrib.auth import get_user_model  # Import here instead
        
        total_questions = cls.objects.count()
        
        stats = {
            'total_questions': total_questions,
            'by_degree': {},
            'by_difficulty': {},
            'by_type': {},
            'recent_count': cls.objects.filter(
                created_on__gte=timezone.now() - timezone.timedelta(days=7)
            ).count()
        }
        
        # Count by degree
        for degree, _ in cls.DEGREE_CHOICES:
            stats['by_degree'][degree] = cls.objects.filter(degree=degree).count()
        
        # Count by difficulty
        for difficulty, _ in cls.DIFFICULTY_CHOICES:
            stats['by_difficulty'][difficulty] = cls.objects.filter(difficulty=difficulty).count()
        
        # Count by type
        for q_type, _ in cls.QUESTION_TYPE_CHOICES:
            stats['by_type'][q_type] = cls.objects.filter(question_type=q_type).count()
        
        return stats