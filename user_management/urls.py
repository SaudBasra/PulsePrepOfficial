# user_management/urls.py - Complete URLs with Email Activation Routes
from django.urls import path
from . import views

app_name = 'user_management'

urlpatterns = [
    # Authentication Routes
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Email Activation Routes
    path('activate/<str:token>/', views.activate_account, name='activate_account'),
    
    # Admin User Management Routes
    path('manage-users/', views.manage_users, name='manage_users'),
    path('user-details/<int:user_id>/', views.user_details, name='user_details'),
    
    # API Routes for User Management
    path('api/users/', views.get_users, name='get_users'),
    path('api/users/<int:user_id>/status/', views.change_user_status, name='change_user_status'),
    path('api/users/add/', views.add_user, name='add_user'),
    path('api/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    
    # API Routes for Email Management
    path('api/bulk-send-activation/', views.bulk_send_activation_emails, name='bulk_send_activation'),
    path('api/users/<int:user_id>/resend-activation/', views.resend_activation_email, name='resend_activation'),
    path('api/users/<int:user_id>/manual-activate/', views.manual_activate_account, name='manual_activate'),
    path('api/retry-failed-emails/', views.retry_failed_emails, name='retry_failed_emails'),
    path('api/test-email/', views.test_email_config, name='test_email'),
    
    # Email Logs and Export Routes
    path('email-logs/', views.email_logs_view, name='email_logs'),
    path('export-csv/', views.export_users_csv, name='export_users_csv'),
    
    # User Profile Routes
    path('profile/', views.profile_view, name='profile'),
    path('request-activation-resend/', views.request_activation_resend, name='request_activation_resend'),
    
    # Dashboard Route
]