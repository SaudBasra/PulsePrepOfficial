# ===============================================
# myaccount/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.my_profile, name='my_profile'),
    path('profile/', views.my_profile, name='myaccount'),  # For backward compatibility
    path('change-password/', views.change_password, name='change_password'),
    path('settings/', views.account_settings, name='account_settings'),
    # In myaccount/urls.py - ADD these two lines:
path('reset-records/', views.reset_all_records, name='reset_all_records'),
path('reset-preview/', views.get_reset_preview, name='reset_preview'),
]
