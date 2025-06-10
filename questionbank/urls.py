# questionbank/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('questionbank/', views.questionbank, name='questionbank'),
    path('question/add/', views.question_detail, name='add_question'),
    path('question/<int:pk>/', views.question_detail, name='edit_question'),
    path('question/<int:pk>/delete/', views.delete_question, name='delete_question'),
    path('manage-csv/', views.manage_csv, name='manage_csv'),  # New CSV management page
    path('api/import-questions/', views.import_questions_with_history, name='import_questions'),
    path('api/export-questions/', views.export_questions, name='export_questions'),
   
   
    path('manage-csv/', views.manage_csv, name='manage_csv'),  # Unified CSV management
    path('api/import-questions/', views.import_questions_with_history, name='import_questions_with_history'),
    path('api/export-questions/', views.export_questions, name='export_questions'),    
    
    path('api/import-questions-simple/', views.import_questions, name='import_questions'),
    
    
    path('api/paper-details/<int:paper_id>/', views.get_paper_details, name='get_paper_details'),  # New endpoint

]