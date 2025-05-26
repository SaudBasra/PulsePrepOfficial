from django.shortcuts import render

def myaccount(request):
    context = {
        'user_since': 'Jan 15, 2023',
        'subscription_status': 'Active',
        'subscription_plan': 'Premium',
        'renewal_date': 'Dec 15, 2025',
    }
    return render(request, 'myaccount.html', context)