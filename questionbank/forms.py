# questionbank/forms.py
from django import forms
from .models import Question

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'question_text', 'question_type', 'option_a', 'option_b', 
            'option_c', 'option_d', 'option_e', 'correct_answer',  # Added option_e
            'degree', 'year', 'block', 'module', 'subject', 'topic',
            'difficulty', 'explanation'
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter your question here...'
            }),
            'question_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'option_a': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Option A'
            }),
            'option_b': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Option B'
            }),
            'option_c': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Option C'
            }),
            'option_d': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Option D'
            }),
            'option_e': forms.Textarea(attrs={  # Added Option E widget
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Option E'
            }),
            'correct_answer': forms.Select(attrs={
                'class': 'form-control'
            }),
            'degree': forms.Select(attrs={
                'class': 'form-control'
            }),
            'year': forms.Select(attrs={
                'class': 'form-control'
            }),
            'block': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Block name'
            }),
            'module': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Module name'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject name'
            }),
            'topic': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Topic name'
            }),
            'difficulty': forms.Select(attrs={
                'class': 'form-control'
            }),
            'explanation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional explanation for the correct answer...'
            }),
        }

class QuestionImportForm(forms.Form):
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'form-control'
        })
    )