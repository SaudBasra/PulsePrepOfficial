# analytics_report/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.analytics_report, name='analytics_report'),
    path('export/', views.export_analytics_report, name='export_analytics_report'),
    path('api/', views.analytics_api, name='analytics_api'),
    path('subject/<str:subject_name>/', views.subject_analytics, name='subject_analytics'),
]