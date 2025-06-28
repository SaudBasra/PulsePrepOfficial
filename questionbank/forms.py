# questionbank/forms.py - Updated with question_image field

from django import forms
from .models import Question

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'question_text', 'question_type', 'option_a', 'option_b', 'option_c', 
            'option_d', 'option_e', 'correct_answer', 'degree', 'year', 'block', 
            'module', 'subject', 'topic', 'difficulty', 'explanation', 
            'question_image', 'image'  # Added question_image field
        ]
        
        widgets = {
            'question_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter the complete question text...'
            }),
            'question_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'option_a': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter option A...'
            }),
            'option_b': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter option B...'
            }),
            'option_c': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter option C...'
            }),
            'option_d': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter option D...'
            }),
            'option_e': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter option E...'
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
                'placeholder': 'e.g., Cardiovascular System'
            }),
            'module': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Anatomy'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Human Anatomy'
            }),
            'topic': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Heart Structure'
            }),
            'difficulty': forms.Select(attrs={
                'class': 'form-control'
            }),
            'explanation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Provide explanation for the correct answer...'
            }),
            'question_image': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., heart_anatomy.jpg (optional)',
                'title': 'Image filename to display with the question'
            }),
            'image': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., heart_explanation.jpg (optional)',
                'title': 'Image filename to display with the explanation'
            })
        }
        
        labels = {
            'question_text': 'Question Text',
            'question_type': 'Question Type',
            'option_a': 'Option A',
            'option_b': 'Option B', 
            'option_c': 'Option C',
            'option_d': 'Option D',
            'option_e': 'Option E',
            'correct_answer': 'Correct Answer',
            'degree': 'Degree Program',
            'year': 'Academic Year',
            'block': 'Block/System',
            'module': 'Module',
            'subject': 'Subject',
            'topic': 'Topic',
            'difficulty': 'Difficulty Level',
            'explanation': 'Answer Explanation',
            'question_image': 'Question Image',  # NEW
            'image': 'Explanation Image'  # Updated label for clarity
        }
        
        help_texts = {
            'question_text': 'Enter the complete question that will be shown to students.',
            'question_type': 'Select the type of question (MCQ for multiple choice).',
            'correct_answer': 'Select which option (A, B, C, D, or E) is the correct answer.',
            'difficulty': 'Rate the difficulty level of this question.',
            'explanation': 'Provide a detailed explanation of why the correct answer is right.',
            'question_image': 'Filename of image to display with the question (e.g., diagram.jpg)',  # NEW
            'image': 'Filename of image to display with the explanation (e.g., solution.jpg)'  # Updated
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make certain fields required for MCQ questions
        self.fields['question_text'].required = True
        
        # Add custom validation messages
        self.fields['question_text'].error_messages = {
            'required': 'Question text is required.'
        }

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get('question_type')
        
        # Custom validation for MCQ questions
        if question_type == 'MCQ':
            required_mcq_fields = ['option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
            for field in required_mcq_fields:
                if not cleaned_data.get(field):
                    if field == 'correct_answer':
                        self.add_error(field, 'Please select the correct answer for MCQ questions.')
                    else:
                        field_label = self.fields[field].label
                        self.add_error(field, f'{field_label} is required for MCQ questions.')
            
            # Validate correct answer matches available options
            correct_answer = cleaned_data.get('correct_answer')
            if correct_answer:
                option_field = f'option_{correct_answer.lower()}'
                if not cleaned_data.get(option_field):
                    self.add_error('correct_answer', 
                                 f'Option {correct_answer} must have content if selected as correct answer.')
        
        # Validate image filenames if provided
        question_image = cleaned_data.get('question_image')
        if question_image and question_image.strip():
            # Basic filename validation
            if not self._is_valid_image_filename(question_image.strip()):
                self.add_error('question_image', 
                             'Please provide a valid image filename (e.g., image.jpg)')
        
        explanation_image = cleaned_data.get('image')
        if explanation_image and explanation_image.strip():
            if not self._is_valid_image_filename(explanation_image.strip()):
                self.add_error('image', 
                             'Please provide a valid image filename (e.g., image.jpg)')
        
        return cleaned_data
    
    def _is_valid_image_filename(self, filename):
        """Basic validation for image filename"""
        if not filename:
            return True
        
        # Check for valid image extensions
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        filename_lower = filename.lower()
        
        # Must have a valid extension
        has_valid_extension = any(filename_lower.endswith(ext) for ext in valid_extensions)
        
        # Must not contain invalid characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        has_invalid_chars = any(char in filename for char in invalid_chars)
        
        return has_valid_extension and not has_invalid_chars


class QuestionImportForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file with question data. Maximum file size: 10MB',
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': '.csv'
        })
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        if csv_file:
            # Check file extension
            if not csv_file.name.lower().endswith('.csv'):
                raise forms.ValidationError('Please upload a CSV file.')
            
            # Check file size (10MB limit)
            if csv_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size must be less than 10MB.')
        
        return csv_file


class QuestionFilterForm(forms.Form):
    """Form for filtering questions in the question bank"""
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search questions, blocks, modules, subjects, topics...'
        }),
        label='Search'
    )
    
    block = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by block...'
        }),
        label='Block'
    )
    
    degree = forms.ChoiceField(
        choices=[('', 'All Degrees')] + Question.DEGREE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Degree'
    )
    
    difficulty = forms.ChoiceField(
        choices=[('', 'All Difficulties')] + Question.DIFFICULTY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Difficulty'
    )
    
    question_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Question.QUESTION_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Question Type'
    )