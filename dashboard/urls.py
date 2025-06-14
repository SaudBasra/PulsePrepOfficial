
# dashboard/urls.p

from django.urls import path
from . import views

urlpatterns = [
    # Student Dashboard URLs
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/progress/', views.unified_progress, name='unified_progress'),
    
    # Admin Dashboard URLs  
    path('', views.dashboard, name='dashboard'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Legacy redirect URLs for backward compatibility
    path('manage-questions/', views.manage_questions, name='manage_questions'),
    path('manage-modules/', views.manage_modules, name='manage_modules'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('mock-test/', views.mock_test, name='mock_test'),
    path('analytics-reports/', views.analytics_reports, name='analytics_reports'),
    path('my-account/', views.my_account, name='my_account'),
    path('notification/', views.notification, name='notification'),
    path('settings/', views.settings, name='settings'),
    path('logout/', views.logout_view, name='logout'),
    path('all-notifications/', views.all_notifications, name='all_notifications'),
]