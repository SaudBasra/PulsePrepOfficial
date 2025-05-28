# notifications/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Admin notification URLs
    path('', views.notification_center, name='notification_center'),
    path('mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    
    # Student notification URLs
    path('student/', views.student_notifications, name='student_notifications'),
    path('student/mark-read/<int:notification_id>/', views.student_mark_notification_read, name='student_mark_notification_read'),
    path('student/mark-all-read/', views.student_mark_all_read, name='student_mark_all_read'),
]