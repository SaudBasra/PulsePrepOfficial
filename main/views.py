from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

def signup_view(request):
    # This should redirect to the user_management signup
    return redirect('user_management:signup')

def login_view(request):
    # This should redirect to the user_management login
    return redirect('user_management:login')

def logout_view(request):
    logout(request)
    return redirect('home')

def home(request):
    return render(request, 'main/home.html')

def about(request):
    return render(request, 'main/about.html')

def faqs(request):
    return render(request, 'main/faqs.html')

def contact(request):
    return render(request, 'main/contact.html')