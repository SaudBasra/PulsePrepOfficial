# manageimage/urls.py - Simple URL configuration matching your existing pattern

from django.urls import path
from . import views

urlpatterns = [
    # Main image management
    path('', views.manage_images, name='manage_images'),
    
    # Upload and delete operations
    path('upload/', views.upload_images, name='upload_images'),
    path('delete/<int:image_id>/', views.delete_image, name='delete_image'),
    
    # Usage information
    path('usage/<int:image_id>/', views.get_image_usage, name='get_image_usage'),
    path('usage-summary/<int:image_id>/', views.get_image_usage_summary, name='get_image_usage_summary'),
    
    # API endpoints
    path('api/available/', views.get_available_images, name='get_available_images'),
    
    # Debug and testing
    path('debug/', views.debug_images, name='debug_images'),
    path('test/', views.test_images, name='test_images'),
]