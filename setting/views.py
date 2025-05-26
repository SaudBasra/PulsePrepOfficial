from django.shortcuts import render

def setting(request):
    context = {
        'current_theme': 'Light',
        'current_language': 'English',
    }
    return render(request, 'setting.html', context)