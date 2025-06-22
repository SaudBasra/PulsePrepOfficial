# managemodule/models.py - Fixed Complete Practice Session Models
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
    
    PRACTICE_MODE_CHOICES = [
        ('student', 'Student Mode'), 
        ('tutor', 'Tutor Mode')
    ]
    
    practice_mode = models.CharField(
        max_length=10, 
        choices=PRACTICE_MODE_CHOICES, 
        default='student'
    )
    
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
    
    # Results - Fixed: Added accuracy field to store the calculated value
    accuracy = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # Store accuracy as decimal
    questions_attempted = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    
    # Optional fields for enhanced tracking
    current_question_index = models.IntegerField(default=0)  # For session state
    last_activity = models.DateTimeField(auto_now=True)  # For auto-save tracking
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['topic', 'degree', 'year']),
        ]
    
    def __str__(self):
        return f"{self.student.email} - {self.topic} - {self.started_at.strftime('%Y-%m-%d')}"
    
    @property
    def accuracy_percent(self):
        """Calculate accuracy percentage (backward compatibility)"""
        if self.questions_attempted == 0:
            return 0.0
        return round((self.correct_answers / self.questions_attempted) * 100, 1)
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def time_spent_formatted(self):
        if not self.time_spent:
            return "0 seconds"
        
        hours = self.time_spent // 3600
        minutes = (self.time_spent % 3600) // 60
        seconds = self.time_spent % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    
    def update_accuracy(self):
        """Update the stored accuracy field based on current results"""
        if self.questions_attempted > 0:
            calculated_accuracy = (self.correct_answers / self.questions_attempted) * 100
            self.accuracy = round(calculated_accuracy, 1)
        else:
            self.accuracy = 0.0
        self.save(update_fields=['accuracy'])


class PracticeResponse(models.Model):
    ANSWER_CHOICES = [
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E')
    ]
    
    session = models.ForeignKey(PracticeSession, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey('questionbank.Question', on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=1, choices=ANSWER_CHOICES, blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    time_spent = models.IntegerField(default=0)  # seconds spent on this question
    answered_at = models.DateTimeField(auto_now_add=True)
    
    # Additional tracking fields
    marked_for_review = models.BooleanField(default=False)  # For review functionality
    attempt_count = models.IntegerField(default=1)  # For future multi-attempt support
    
    class Meta:
        unique_together = ['session', 'question']
        ordering = ['answered_at']
        indexes = [
            models.Index(fields=['session', 'is_correct']),
            models.Index(fields=['question', 'is_correct']),
        ]
    
    def __str__(self):
        return f"{self.session} - Q{self.question.id} - {self.selected_answer or 'No Answer'}"
    
    def check_answer(self):
        """Check if the selected answer is correct"""
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
    
    # Enhanced tracking fields
    total_time_spent = models.IntegerField(default=0)  # total seconds across all sessions
    consecutive_correct = models.IntegerField(default=0)  # current streak
    longest_streak = models.IntegerField(default=0)  # best streak ever
    
    # Timestamps
    first_practiced = models.DateTimeField(auto_now_add=True)
    last_practiced = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'degree', 'year', 'block', 'module', 'subject', 'topic']
        ordering = ['-last_practiced']
        indexes = [
            models.Index(fields=['student', 'mastery_level']),
            models.Index(fields=['student', 'best_accuracy']),
            models.Index(fields=['topic', 'mastery_level']),
        ]
    
    def __str__(self):
        return f"{self.student.email} - {self.topic} ({self.mastery_level})"
    
    @property
    def overall_accuracy(self):
        return self.average_accuracy
    
    @property
    def improvement_rate(self):
        """Calculate improvement rate based on recent sessions"""
        if self.total_sessions < 2:
            return 0.0
        
        # Get recent sessions for this topic
        recent_sessions = PracticeSession.objects.filter(
            student=self.student,
            topic=self.topic,
            status='completed'
        ).order_by('-completed_at')[:5]
        
        if len(recent_sessions) < 2:
            return 0.0
        
        # Calculate trend
        recent_accuracy = float(recent_sessions[0].accuracy)
        older_accuracy = float(recent_sessions[-1].accuracy)
        
        return recent_accuracy - older_accuracy
    
    def update_progress(self, session):
        """Update progress based on completed session"""
        self.total_sessions += 1
        self.total_questions_attempted += session.questions_attempted
        self.total_correct_answers += session.correct_answers
        self.total_time_spent += session.time_spent
        
        # Update best accuracy - use the stored accuracy field
        session_accuracy = float(session.accuracy) if hasattr(session, 'accuracy') else session.accuracy_percent
        if session_accuracy > self.best_accuracy:
            self.best_accuracy = session_accuracy
        
        # Calculate average accuracy
        if self.total_questions_attempted > 0:
            self.average_accuracy = (self.total_correct_answers / self.total_questions_attempted) * 100
        
        # Update streak tracking
        if session_accuracy == 100.0:
            self.consecutive_correct += 1
            self.longest_streak = max(self.longest_streak, self.consecutive_correct)
        else:
            self.consecutive_correct = 0
        
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
            # Additional criteria for mastery
            if self.best_accuracy >= 90 and self.total_sessions >= 3:
                self.mastery_level = 'Mastered'
            else:
                self.mastery_level = 'Good'


class StudyPlan(models.Model):
    """Model for structured study planning"""
    PLAN_STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='study_plans'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Plan configuration
    target_topics = models.JSONField(default=list)  # List of topic identifiers
    daily_target = models.IntegerField(default=10)  # Questions per day
    target_accuracy = models.FloatField(default=80.0)  # Target accuracy percentage
    
    # Plan tracking
    status = models.CharField(max_length=20, choices=PLAN_STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Progress tracking
    total_questions_completed = models.IntegerField(default=0)
    total_correct_answers = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.email} - {self.name}"
    
    @property
    def current_accuracy(self):
        if self.total_questions_completed == 0:
            return 0.0
        return (self.total_correct_answers / self.total_questions_completed) * 100
    
    @property
    def is_on_track(self):
        """Check if student is on track with daily targets"""
        from datetime import date
        days_elapsed = (date.today() - self.start_date).days + 1
        target_questions = days_elapsed * self.daily_target
        return self.total_questions_completed >= target_questions


class TopicRecommendation(models.Model):
    """Model for AI-powered topic recommendations"""
    RECOMMENDATION_TYPES = [
        ('review', 'Review'),
        ('practice', 'Practice'),
        ('master', 'Master'),
        ('catch_up', 'Catch Up'),
    ]
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='topic_recommendations'
    )
    
    # Topic identification
    degree = models.CharField(max_length=10)
    year = models.CharField(max_length=3)
    block = models.CharField(max_length=100)
    module = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=100)
    
    # Recommendation details
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    priority_score = models.FloatField(default=0.0)  # Higher score = higher priority
    reason = models.TextField()  # Explanation for the recommendation
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    is_viewed = models.BooleanField(default=False)
    is_acted_upon = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-priority_score', '-created_at']
        indexes = [
            models.Index(fields=['student', 'is_viewed']),
            models.Index(fields=['recommendation_type', 'priority_score']),
        ]
    
    def __str__(self):
        return f"{self.student.email} - {self.topic} ({self.recommendation_type})"


class PracticeSessionNote(models.Model):
    """Model for storing notes during practice sessions"""
    session = models.ForeignKey(PracticeSession, on_delete=models.CASCADE, related_name='session_notes')
    question = models.ForeignKey('questionbank.Question', on_delete=models.CASCADE)
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['session', 'question']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note for Q{self.question.id} in {self.session}"


class TopicPerformanceSummary(models.Model):
    """Aggregated performance data for analytics"""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    topic = models.CharField(max_length=100)
    degree = models.CharField(max_length=10)
    year = models.CharField(max_length=3)
    
    # Weekly aggregated data
    week_start = models.DateField()
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    total_time = models.IntegerField(default=0)  # seconds
    sessions_count = models.IntegerField(default=0)
    
    # Performance metrics
    weekly_accuracy = models.FloatField(default=0.0)
    average_time_per_question = models.FloatField(default=0.0)  # seconds
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'topic', 'week_start']
        ordering = ['-week_start']
    
    def __str__(self):
        return f"{self.student.email} - {self.topic} - Week {self.week_start}"