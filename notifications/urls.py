# notifications/urls.py - Enhanced with AJAX endpoints
from django.urls import path
from . import views

urlpatterns = [
    # ====================================================================
    # ADMIN NOTIFICATION URLs
    # ====================================================================
    path('', views.notification_center, name='notification_center'),
    path('mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    
    # Delete functionality
    path('delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    
    # Reset functionality (Admin only)
    path('reset-all/', views.reset_all_notifications, name='reset_all_notifications'),
    
    # ====================================================================
    # STUDENT NOTIFICATION URLs
    # ====================================================================
    path('student/', views.student_notifications, name='student_notifications'),
    path('student/mark-read/<int:notification_id>/', views.student_mark_notification_read, name='student_mark_notification_read'),
    path('student/mark-all-read/', views.student_mark_all_read, name='student_mark_all_read'),
    
    # ====================================================================
    # AJAX/API URLs
    # ====================================================================
    path('ajax/mark-read/<int:notification_id>/', views.ajax_mark_read, name='ajax_mark_read'),
    path('ajax/delete/<int:notification_id>/', views.ajax_delete_notification, name='ajax_delete_notification'),
    
    # NEW: AJAX endpoint for getting user count based on filters
    path('ajax/get-user-count/', views.get_user_count, name='get_user_count'),
]