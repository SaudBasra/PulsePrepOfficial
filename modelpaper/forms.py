# modelpaper/forms.py
from django import forms
from django.utils import timezone
from .models import ModelPaper, PaperQuestion

class ModelPaperForm(forms.ModelForm):
    # Dynamic field for paper name selection
    selected_paper_name = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'paper-name-select'}),
        help_text="Select from available paper names in uploaded questions"
    )
    
    class Meta:
        model = ModelPaper
        fields = [
            'title', 'description', 'selected_paper_name',
            'filter_degree', 'filter_year', 'filter_module', 'filter_subject', 'filter_topic',
            'duration_minutes', 'passing_percentage', 'max_attempts',
            'randomize_questions', 'randomize_options', 'show_explanations',
            'start_datetime', 'end_datetime', 'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter model paper title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'filter_degree': forms.Select(attrs={'class': 'form-control'}),
            'filter_year': forms.Select(attrs={'class': 'form-control'}),
            'filter_module': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Module filter (optional)'}),
            'filter_subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject filter (optional)'}),
            'filter_topic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Topic filter (optional)'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 5}),
            'passing_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'max_attempts': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'selected_paper_name': 'Paper Name',
            'filter_degree': 'Filter by Degree (optional)',
            'filter_year': 'Filter by Year (optional)',
            'filter_module': 'Filter by Module (optional)',
            'filter_subject': 'Filter by Subject (optional)',
            'filter_topic': 'Filter by Topic (optional)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate paper name choices from uploaded questions
        paper_names = PaperQuestion.get_available_paper_names()
        choices = [('', 'Select a paper name...')]
        choices.extend([(name, name) for name in paper_names])
        self.fields['selected_paper_name'].choices = choices
        
        # If no paper names available, show helpful message
        if not paper_names:
            self.fields['selected_paper_name'].help_text = "No paper questions uploaded yet. Upload CSV with paper questions first."
            self.fields['selected_paper_name'].widget.attrs['disabled'] = True
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate datetime
        start = cleaned_data.get('start_datetime')
        end = cleaned_data.get('end_datetime')
        
        if start and end and start >= end:
            raise forms.ValidationError("End datetime must be after start datetime")
        
        # Validate paper name selection
        selected_paper_name = cleaned_data.get('selected_paper_name')
        if not selected_paper_name:
            raise forms.ValidationError("Please select a paper name")
        
        # Check if paper name has questions
        questions_count = PaperQuestion.get_filtered_questions(
            paper_name=selected_paper_name,
            degree=cleaned_data.get('filter_degree'),
            year=cleaned_data.get('filter_year'),
            module=cleaned_data.get('filter_module'),
            subject=cleaned_data.get('filter_subject'),
            topic=cleaned_data.get('filter_topic')
        ).count()
        
        if questions_count == 0:
            raise forms.ValidationError(
                "No questions found for the selected paper name with current filters. "
                "Please adjust filters or upload more questions."
            )
        
        return cleaned_data


class PaperQuestionImportForm(forms.Form):
    """Simple form for CSV upload - no paper selection needed"""
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'form-control'
        }),
        help_text="Upload CSV file with paper questions. Can contain multiple paper names."
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        if not csv_file.name.lower().endswith('.csv'):
            raise forms.ValidationError("Please upload a CSV file.")
        
        if csv_file.size > 10 * 1024 * 1024:  # 10MB limit
            raise forms.ValidationError("File size must be less than 10MB.")
        
        return csv_file