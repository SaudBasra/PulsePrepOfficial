from django.shortcuts import render

def analytics_report(request):
    context = {
        'user_growth': 15,  # percentage
        'test_completion_rate': 78,  # percentage
        'average_score': 72,  # percentage
        'active_users': 3200,
    }
    return render(request, 'analytics_report.html', context)