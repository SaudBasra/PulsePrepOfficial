# questionbank/urls.py - Updated with CSV deletion functionality
from django.urls import path
from . import views

urlpatterns = [
    path('questionbank/', views.questionbank, name='questionbank'),
    path('question/add/', views.question_detail, name='add_question'),
    path('question/<int:pk>/', views.question_detail, name='edit_question'),
    path('question/<int:pk>/delete/', views.delete_question, name='delete_question'),
    path('manage-csv/', views.manage_csv, name='manage_csv'),  # Unified CSV management
    path('api/import-questions/', views.import_questions_with_history, name='import_questions_with_history'),
    path('api/export-questions/', views.export_questions, name='export_questions'),    
    path('api/import-questions-simple/', views.import_questions, name='import_questions'),
    
    # NEW: CSV deletion endpoints
    path('api/delete-csv/<int:record_id>/', views.delete_csv_record, name='delete_csv_record'),
    
    # API endpoints for CSV management
    path('api/csv-stats/', views.get_csv_stats_api, name='csv_stats_api'),
    path('api/validate-csv/', views.validate_csv_api, name='validate_csv_api'),
    path('api/import-history/', views.get_import_history_api, name='import_history_api'),
]