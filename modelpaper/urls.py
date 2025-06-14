# modelpaper/urls.py - Updated with all necessary URLs
from django.urls import path
from . import views

urlpatterns = [
    # Admin URLs - Model Paper Management
    path('', views.modelpaper_list, name='modelpaper_list'),
    path('create/', views.create_paper, name='create_paper'),
    path('delete/<int:paper_id>/', views.delete_paper, name='delete_paper'),
    path('preview/<int:paper_id>/', views.preview_paper, name='preview_paper'),
    path('export/<int:paper_id>/', views.export_paper_questions, name='export_paper_questions'),
    path('questions/<path:paper_name>/', views.view_paper_questions, name='view_paper_questions'),
    
    # CSV Import URLs
    path('import-questions/', views.import_paper_questions, name='import_paper_questions'),
    
    # API URLs for filtering
    path('api/paper-counts/', views.get_paper_question_counts, name='get_paper_question_counts'),
    path('api/filtered-count/', views.get_filtered_question_count, name='get_filtered_question_count'),
    
    # Student URLs - Taking Papers
    path('student/', views.student_model_papers, name='student_model_papers'),
    path('take/<int:paper_id>/', views.take_paper, name='take_paper'),
    path('submit-answer/', views.submit_answer, name='submit_paper_answer'),
    path('submit-paper/', views.submit_paper, name='submit_paper'),
    path('result/<int:attempt_id>/', views.paper_result, name='paper_result'),
    path('report-warning/', views.report_warning, name='report_paper_warning'),
    path('progress/', views.student_paper_progress, name='student_paper_progress'),
]