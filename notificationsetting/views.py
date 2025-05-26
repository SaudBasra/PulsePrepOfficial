from django.shortcuts import render

def notificationsetting(request):
    context = {
        'unread_count': 5,
        'notifications': [
            {'id': 1, 'message': 'New test available', 'date': 'April 19, 2025', 'read': False},
            {'id': 2, 'message': 'Your subscription will expire soon', 'date': 'April 18, 2025', 'read': False},
            {'id': 3, 'message': 'New module added to your course', 'date': 'April 17, 2025', 'read': True},
        ]
    }
    return render(request, 'notificationsetting.html', context)