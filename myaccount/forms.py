# myaccount/forms.py - Updated with Readonly Degree/Year for Students
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from user_management.models import CustomUser
from django.core.exceptions import ValidationError

class UserProfileForm(forms.ModelForm):
    """Form for updating user profile information"""
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'degree', 'year', 'profile_image']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name'
            }),
            'degree': forms.Select(attrs={
                'class': 'form-control'
            }),
            'year': forms.Select(attrs={
                'class': 'form-control'
            }),
            'profile_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'degree': 'Degree Program',
            'year': 'Academic Year',
            'profile_image': 'Profile Picture',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        
        # Make degree and year readonly for students (non-admin users)
        if user and not (user.is_admin or user.is_superuser):
            # Make degree field readonly for students
            self.fields['degree'].widget = forms.TextInput(attrs={
                'class': 'form-control readonly-field',
                'readonly': True,
                'value': user.get_degree_display() if user.degree else 'Not Set'
            })
            self.fields['degree'].help_text = "Contact administrator to change degree program"
            
            # Make year field readonly for students  
            self.fields['year'].widget = forms.TextInput(attrs={
                'class': 'form-control readonly-field',
                'readonly': True,
                'value': user.get_year_display() if user.year else 'Not Set'
            })
            self.fields['year'].help_text = "Contact administrator to change academic year"
            
            # Remove from form processing
            self.fields['degree'].disabled = True
            self.fields['year'].disabled = True
        else:
            # For admins, keep them editable but add help text
            self.fields['degree'].help_text = 'Administrator can edit degree program'
            self.fields['year'].help_text = 'Administrator can edit academic year'

    def clean_degree(self):
        """Prevent students from changing degree"""
        if self.instance and not (self.instance.is_admin or self.instance.is_superuser):
            # Return the original value for students
            return self.instance.degree
        return self.cleaned_data.get('degree')
    
    def clean_year(self):
        """Prevent students from changing year"""
        if self.instance and not (self.instance.is_admin or self.instance.is_superuser):
            # Return the original value for students
            return self.instance.year
        return self.cleaned_data.get('year')


class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with better styling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes and placeholders
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your current password'
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your new password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your new password'
        })
        
        # Update labels
        self.fields['old_password'].label = 'Current Password'
        self.fields['new_password1'].label = 'New Password'
        self.fields['new_password2'].label = 'Confirm New Password'