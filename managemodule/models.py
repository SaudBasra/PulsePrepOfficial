# managemodule/models.py - Practice Session Models
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class PracticeSession(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]
    
    # Student and topic information
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='practice_sessions')
    degree = models.CharField(max_length=10)
    year = models.CharField(max_length=3)
    block = models.CharField(max_length=100)
    module = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=100)
    
    # Session configuration
    difficulty_filter = models.CharField(max_length=20, blank=True, null=True)
    total_questions = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    show_explanations = models.BooleanField(default=True)
    timed_practice = models.BooleanField(default=False)
    time_per_question = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(10), MaxValueValidator(300)])  # seconds
    randomize_questions = models.BooleanField(default=True)
    
    # Session tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent = models.IntegerField(default=0)  # total seconds
    
    # Results
    questions_attempted = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.student.email} - {self.topic} - {self.started_at.strftime('%Y-%m-%d')}"
    
    @property
    def accuracy(self):
        if self.questions_attempted == 0:
            return 0
        return round((self.correct_answers / self.questions_attempted) * 100, 1)
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def time_spent_formatted(self):
        if not self.time_spent:
            return "0 seconds"
        
        minutes = self.time_spent // 60
        seconds = self.time_spent % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


class PracticeResponse(models.Model):
    session = models.ForeignKey(PracticeSession, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey('questionbank.Question', on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=1, choices=[
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E')
    ], blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    time_spent = models.IntegerField(default=0)  # seconds spent on this question
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['session', 'question']
        ordering = ['answered_at']
    
    def __str__(self):
        return f"{self.session} - Q{self.question.id}"
    
    def check_answer(self):
        if self.selected_answer and self.question.correct_answer:
            self.is_correct = self.selected_answer == self.question.correct_answer
        else:
            self.is_correct = False
        return self.is_correct


class StudentProgress(models.Model):
    MASTERY_LEVELS = [
        ('Not Started', 'Not Started'),
        ('Getting Started', 'Getting Started'),
        ('Needs Practice', 'Needs Practice'),
        ('Fair', 'Fair'),
        ('Good', 'Good'),
        ('Mastered', 'Mastered'),
    ]
    
    # Student and topic identification
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='topic_progress')
    degree = models.CharField(max_length=10)
    year = models.CharField(max_length=3)
    block = models.CharField(max_length=100)
    module = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=100)
    
    # Progress tracking
    total_sessions = models.IntegerField(default=0)
    total_questions_attempted = models.IntegerField(default=0)
    total_correct_answers = models.IntegerField(default=0)
    best_accuracy = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    average_accuracy = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    mastery_level = models.CharField(max_length=20, choices=MASTERY_LEVELS, default='Not Started')
    
    # Timestamps
    first_practiced = models.DateTimeField(auto_now_add=True)
    last_practiced = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'degree', 'year', 'block', 'module', 'subject', 'topic']
        ordering = ['-last_practiced']
    
    def __str__(self):
        return f"{self.student.email} - {self.topic} ({self.mastery_level})"
    
    @property
    def overall_accuracy(self):
        return self.average_accuracy
    
    def update_progress(self, session):
        """Update progress based on completed session"""
        self.total_sessions += 1
        self.total_questions_attempted += session.questions_attempted
        self.total_correct_answers += session.correct_answers
        
        # Update best accuracy
        session_accuracy = session.accuracy
        if session_accuracy > self.best_accuracy:
            self.best_accuracy = session_accuracy
        
        # Calculate average accuracy
        if self.total_questions_attempted > 0:
            self.average_accuracy = (self.total_correct_answers / self.total_questions_attempted) * 100
        
        # Update mastery level based on performance
        self.update_mastery_level()
        
        self.save()
    
    def update_mastery_level(self):
        """Determine mastery level based on performance metrics"""
        if self.total_sessions == 0:
            self.mastery_level = 'Not Started'
        elif self.total_sessions == 1:
            self.mastery_level = 'Getting Started'
        elif self.average_accuracy < 50:
            self.mastery_level = 'Needs Practice'
        elif self.average_accuracy < 70:
            self.mastery_level = 'Fair'
        elif self.average_accuracy < 85:
            self.mastery_level = 'Good'
        else:
            self.mastery_level = 'Mastered'