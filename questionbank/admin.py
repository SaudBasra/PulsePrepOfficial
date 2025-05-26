# questionbank/admin.py
"""
from django.contrib import admin
from .models import Question, CSVImportHistory

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'question_type', 'degree', 'year', 'block', 'module', 'subject', 'difficulty', 'created_on')
    list_filter = ('question_type', 'degree', 'year', 'difficulty', 'block')
    search_fields = ('question_text', 'module', 'subject', 'topic')
    date_hierarchy = 'created_on'
    fieldsets = (
        ('Basic Information', {
            'fields': ('question_text', 'question_type', 'created_on', 'created_by')
        }),
        ('MCQ Options', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'option_e', 'correct_answer'),  # Added option_e
            'classes': ('collapse',),
            'description': 'Options for Multiple Choice Questions (A-E)'
        }),
        ('Categorization', {
            'fields': ('degree', 'year', 'block', 'module', 'subject', 'topic')
        }),
        ('Additional Information', {
            'fields': ('difficulty', 'explanation')
        }),
    )

@admin.register(CSVImportHistory)
class CSVImportHistoryAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'uploaded_by', 'uploaded_at', 'status', 'total_rows', 'successful_imports', 'failed_imports', 'success_rate')
    list_filter = ('status', 'uploaded_at')
    search_fields = ('file_name', 'uploaded_by__email')
    readonly_fields = ('uploaded_at', 'success_rate')
    
    def success_rate(self, obj):
        return f"{obj.success_rate}%"
    success_rate.short_description = 'Success Rate'
    """