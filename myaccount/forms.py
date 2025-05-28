# myaccount/forms.py
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
        
        # If user is admin, remove degree and year fields
        if user and (user.is_admin or user.is_superuser):
            del self.fields['degree']
            del self.fields['year']
            # Add custom admin-specific fields if needed
            self.fields['first_name'].help_text = 'Administrator first name'
            self.fields['last_name'].help_text = 'Administrator last name'


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

