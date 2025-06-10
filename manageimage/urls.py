from django.urls import path
from . import views

urlpatterns = [
    path('', views.manage_images, name='manage_images'),
    path('upload/', views.upload_images, name='upload_images'),
    path('delete/<int:image_id>/', views.delete_image, name='delete_image'),
    path('usage/<int:image_id>/', views.get_image_usage, name='get_image_usage'),
    path('api/available/', views.get_available_images, name='get_available_images'),
    path('debug/', views.debug_images, name='debug_images'),  # ADD THIS
    path('test/', views.test_images, name='test_images'),  # ADD THIS

]