from django import forms
from django.utils import timezone
from .models import MockTest, TestQuestion
from questionbank.models import Question

class MockTestForm(forms.ModelForm):
    class Meta:
        model = MockTest
        fields = [
            'title', 'description',
            'degree', 'year', 'block', 'module', 'subject', 'topic',
            'duration_minutes', 'total_questions', 'passing_percentage',
            'max_attempts', 'selection_type',
            'easy_percentage', 'medium_percentage', 'hard_percentage',
            'randomize_questions', 'randomize_options', 'show_explanations',
            'start_datetime', 'end_datetime', 'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter test title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'degree': forms.Select(attrs={'class': 'form-control'}),
            'year': forms.Select(attrs={'class': 'form-control'}),
            'block': forms.TextInput(attrs={'class': 'form-control'}),
            'module': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'topic': forms.TextInput(attrs={'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 5}),
            'total_questions': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'passing_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'max_attempts': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'selection_type': forms.RadioSelect(),
            'easy_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'medium_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'hard_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate percentages sum to 100
        if cleaned_data.get('selection_type') == 'random':
            easy = cleaned_data.get('easy_percentage', 0)
            medium = cleaned_data.get('medium_percentage', 0)
            hard = cleaned_data.get('hard_percentage', 0)
            
            if easy + medium + hard != 100:
                raise forms.ValidationError("Difficulty percentages must sum to 100%")
        
        # Validate datetime
        start = cleaned_data.get('start_datetime')
        end = cleaned_data.get('end_datetime')
        
        if start and end and start >= end:
            raise forms.ValidationError("End datetime must be after start datetime")
        
        return cleaned_data