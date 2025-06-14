from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class UserSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_admin = False  
        if commit:
            user.save()
        return user
