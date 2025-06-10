from django.db import models
from django.utils import timezone
from django.conf import settings
from questionbank.models import Question

class MockTest(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('completed', 'Completed'),
    ]
    
    SELECTION_TYPE_CHOICES = [
        ('random', 'Random Selection'),
        ('manual', 'Manual Selection'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Removed instructions field - will handle at frontend
    
    # Test Classification (all optional for flexible filtering)
    degree = models.CharField(max_length=4, choices=Question.DEGREE_CHOICES, blank=True)
    year = models.CharField(max_length=3, choices=Question.YEAR_CHOICES, blank=True)
    block = models.CharField(max_length=100, blank=True)
    module = models.CharField(max_length=100, blank=True)
    subject = models.CharField(max_length=100, blank=True)
    topic = models.CharField(max_length=100, blank=True)
    
    # Test Configuration
    duration_minutes = models.IntegerField(default=60)
    total_questions = models.IntegerField(default=50)
    passing_percentage = models.IntegerField(default=40)
    max_attempts = models.IntegerField(default=1)
    
    # Question Selection
    selection_type = models.CharField(max_length=10, choices=SELECTION_TYPE_CHOICES, default='random')
    easy_percentage = models.IntegerField(default=30)  # For random selection
    medium_percentage = models.IntegerField(default=50)
    hard_percentage = models.IntegerField(default=20)
    
    # Test Settings
    randomize_questions = models.BooleanField(default=True)
    randomize_options = models.BooleanField(default=True)
    show_explanations = models.BooleanField(default=True)
    
    # Schedule
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    # Status and Metadata
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Questions
    questions = models.ManyToManyField(Question, through='TestQuestion')
    
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
        return self.total_questions  # Since each question is 1 mark
    
    @property
    def passing_marks(self):
        return int((self.passing_percentage / 100) * self.total_marks)
    



class TestQuestion(models.Model):
    mock_test = models.ForeignKey(MockTest, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    question_order = models.IntegerField(default=0)
    marks = models.IntegerField(default=1)
    
    class Meta:
        ordering = ['question_order']
        unique_together = ['mock_test', 'question']
    
    def __str__(self):
        return f"{self.mock_test.title} - Q{self.question_order}"

# Add these properties to your existing TestAttempt model in mocktest/models.py
# Just add the @property methods to your current model - no migration needed!

class TestAttempt(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]
    
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='test_attempts')
    mock_test = models.ForeignKey(MockTest, on_delete=models.CASCADE, related_name='attempts')
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    score = models.IntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    warning_count = models.IntegerField(default=0)
    time_taken = models.IntegerField(default=0)  # in seconds
    
    class Meta:
        ordering = ['-started_at']
        unique_together = ['student', 'mock_test', 'started_at']
    
    def __str__(self):
        return f"{self.student.email} - {self.mock_test.title}"
    
    @property
    def passed(self):
        return self.percentage >= self.mock_test.passing_percentage
    
    @property
    def remaining_time(self):
        if self.status != 'in_progress':
            return 0
        elapsed = (timezone.now() - self.started_at).total_seconds()
        total_seconds = self.mock_test.duration_minutes * 60
        return max(0, int(total_seconds - elapsed))

    # ADD THESE NEW PROPERTIES - NO MIGRATION NEEDED
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


class TestResponse(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=1, choices=Question.CORRECT_ANSWER_CHOICES, blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    marked_for_review = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"{self.attempt} - {self.question.id}"
    
    def check_answer(self):
        if self.selected_answer and self.question.correct_answer:
            self.is_correct = self.selected_answer == self.question.correct_answer
        else:
            self.is_correct = False
        return self.is_correct