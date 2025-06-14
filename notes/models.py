# notes/models.py
from django.db import models
from django.conf import settings
from questionbank.models import Question

class StudentNote(models.Model):
    """Model to store student notes for specific questions or topics"""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_notes')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=True, blank=True, related_name='student_notes')
    
    # Hierarchy fields (can be filled even without a specific question)
    degree = models.CharField(max_length=10, choices=[('MBBS', 'MBBS'), ('BDS', 'BDS')], default='MBBS')
    year = models.CharField(max_length=10, choices=[
        ('1st', '1st Year'), ('2nd', '2nd Year'), ('3rd', '3rd Year'), 
        ('4th', '4th Year'), ('5th', '5th Year')
    ], default='1st')
    block = models.CharField(max_length=100, blank=True)
    module = models.CharField(max_length=100, blank=True)
    subject = models.CharField(max_length=100, blank=True)
    topic = models.CharField(max_length=100, blank=True)
    
    # Note content
    title = models.CharField(max_length=200, help_text="Note title or brief description")
    content = models.TextField(help_text="Your note content")
    
    # Note type
    NOTE_TYPES = [
        ('question_note', 'Question Note'),
        ('topic_note', 'Topic Note'),
        ('general_note', 'General Note'),
        ('revision_note', 'Revision Note'),
    ]
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default='general_note')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_favorite = models.BooleanField(default=False)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    
    # Study metadata
    difficulty_level = models.CharField(max_length=10, choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ], blank=True)
    
    class Meta:
        ordering = ['-updated_at', '-created_at']
    
    def __str__(self):
        if self.question:
            return f"{self.student.email} - Note for Question {self.question.id}"
        return f"{self.student.email} - {self.title}"
    
    @property
    def tag_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    @property
    def hierarchy_path(self):
        """Return the full hierarchy path"""
        parts = []
        if self.block:
            parts.append(self.block)
        if self.module:
            parts.append(self.module)
        if self.subject:
            parts.append(self.subject)
        if self.topic:
            parts.append(self.topic)
        return ' > '.join(parts) if parts else 'General Notes'


class NoteImage(models.Model):
    """Model to store images attached to notes"""
    note = models.ForeignKey(StudentNote, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='note_images/', help_text="Upload images for your notes")
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"Image for {self.note.title}"


class StudySession(models.Model):
    """Track study sessions when students review their notes"""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_sessions')
    notes_reviewed = models.ManyToManyField(StudentNote, related_name='study_sessions')
    
    # Session details
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    
    # Focus area
    focus_degree = models.CharField(max_length=10, choices=[('MBBS', 'MBBS'), ('BDS', 'BDS')], blank=True)
    focus_year = models.CharField(max_length=10, blank=True)
    focus_subject = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.student.email} - Study Session on {self.started_at.date()}"


class NoteRevision(models.Model):
    """Track revisions and versions of notes"""
    note = models.ForeignKey(StudentNote, on_delete=models.CASCADE, related_name='revisions')
    content_snapshot = models.TextField()
    revision_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Revision of {self.note.title} at {self.created_at}"