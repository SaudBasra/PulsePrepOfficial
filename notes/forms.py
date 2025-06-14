# notes/forms.py
from django import forms
from .models import StudentNote, NoteImage


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget for multiple file upload"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Custom field for handling multiple files"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class StudentNoteForm(forms.ModelForm):
    """Form for creating and editing student notes"""
    
    images = MultipleFileField(
        required=False,
        help_text="Upload multiple images for your note (optional)"
    )
    
    class Meta:
        model = StudentNote
        fields = [
            'title', 'content', 'note_type', 'degree', 'year', 
            'block', 'module', 'subject', 'topic', 'tags', 
            'difficulty_level', 'is_favorite'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter note title...'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Write your note content here...'
            }),
            'note_type': forms.Select(attrs={
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
                'placeholder': 'e.g., Cardiovascular'
            }),
            'module': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Physiology'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Cardiology'
            }),
            'topic': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Heart Rate'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tags separated by commas...'
            }),
            'difficulty_level': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_favorite': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class QuickNoteForm(forms.Form):
    """Quick note form for use during question practice"""
    title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Note title (optional)'
        })
    )
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Write your note here...'
        })
    )
    
    note_type = forms.ChoiceField(
        choices=StudentNote.NOTE_TYPES,
        initial='question_note',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )


class NoteSearchForm(forms.Form):
    """Advanced search form for notes"""
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search notes, tags, content...'
        })
    )
    
    degree = forms.ChoiceField(
        choices=[('', 'All Degrees')] + [('MBBS', 'MBBS'), ('BDS', 'BDS')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    year = forms.ChoiceField(
        choices=[('', 'All Years')] + [
            ('1st', '1st Year'), ('2nd', '2nd Year'), ('3rd', '3rd Year'), 
            ('4th', '4th Year'), ('5th', '5th Year')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    note_type = forms.ChoiceField(
        choices=[('', 'All Types')] + StudentNote.NOTE_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    block = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Block name...'
        })
    )
    
    module = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Module name...'
        })
    )
    
    subject = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject name...'
        })
    )
    
    topic = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Topic name...'
        })
    )
    
    is_favorite = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    difficulty_level = forms.ChoiceField(
        choices=[('', 'All Difficulties')] + [
            ('easy', 'Easy'),
            ('medium', 'Medium'),
            ('hard', 'Hard')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )