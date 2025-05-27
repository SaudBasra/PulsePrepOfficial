
# notificationsetting/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.notificationsetting, name='notificationsetting'),
    path('preferences/', views.notification_preferences, name='notification_preferences'),
    path('admin/', views.admin_notifications, name='admin_notifications'),
    path('api/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('api/archive/', views.archive_notification, name='archive_notification'),
    path('api/count/', views.get_notification_count, name='get_notification_count'),
    path('api/create/', views.create_notification, name='create_notification'),
]