# modelpaper/urls.py - Updated with all necessary URLs + Debug URLs

from django.urls import path
from . import views

urlpatterns = [
    # ==================== DEBUG URLS (for testing image issues) ====================
#    path('debug-images/', views.debug_model_paper_images, name='debug_model_paper_images'),
 #   path('quick-image-test/', views.quick_image_test, name='quick_image_test'),
  #  path('test-specific-image/', views.test_specific_image, name='test_specific_image'),
    
    # ==================== EXISTING ADMIN URLS - Model Paper Management ====================
    path('', views.modelpaper_list, name='modelpaper_list'),
    path('create/', views.create_paper, name='create_paper'),
    path('delete/<int:paper_id>/', views.delete_paper, name='delete_paper'),
    path('preview/<int:paper_id>/', views.preview_paper, name='preview_paper'),
    path('export/<int:paper_id>/', views.export_paper_questions, name='export_paper_questions'),
    path('questions/<path:paper_name>/', views.view_paper_questions, name='view_paper_questions'),
    
    # ==================== CSV IMPORT URLS ====================
    path('import-questions/', views.import_paper_questions, name='import_paper_questions'),
        path('export-questions/<path:paper_name>/', views.export_modelpaper_questions, name='export_modelpaper_questions'),

    # ==================== API URLS FOR FILTERING ====================
    path('api/paper-counts/', views.get_paper_question_counts, name='get_paper_question_counts'),
    path('api/filtered-count/', views.get_filtered_question_count, name='get_filtered_question_count'),
    path('api/paper-hierarchy-data/', views.get_paper_hierarchy_data, name='get_paper_hierarchy_data'),
    
    # ==================== EXISTING STUDENT URLS - Taking Papers ====================
    path('student/', views.student_model_papers, name='student_model_papers'),
    path('take/<int:paper_id>/', views.take_paper, name='take_paper'),  # Handles mode selection
    path('submit-answer/', views.submit_paper_answer, name='submit_paper_answer'),
    path('submit-paper/', views.submit_paper, name='submit_paper'),
    path('result/<int:attempt_id>/', views.paper_result, name='paper_result'),
    path('report-warning/', views.report_warning, name='report_paper_warning'),
    path('progress/', views.student_paper_progress, name='student_paper_progress'),
    path('delete-paper-questions/', views.delete_paper_questions, name='delete_paper_questions'),

    # ==================== ADMIN IMPORT HISTORY (optional) ====================
    # Uncomment these if you want import history views
    # path('admin/import-history/', views.import_history, name='modelpaper_import_history'),
    # path('admin/import-detail/<int:import_id>/', views.import_detail, name='modelpaper_import_detail'),
]