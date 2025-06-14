# mocktest/urls.py - Updated version
from django.urls import path
from . import views

urlpatterns = [
    # Admin URLs - Mock Test Management
    path('', views.mocktest_list, name='mocktest_list'),
    path('create/', views.create_test, name='create_test'),
    path('delete/<int:test_id>/', views.delete_test, name='delete_test'),
    path('preview/<int:test_id>/', views.preview_test, name='preview_test'),
    path('get-questions/', views.get_filtered_questions, name='get_filtered_questions'),
    path('save-manual-questions/', views.save_manual_questions, name='save_manual_questions'),
    path('get-hierarchy/', views.get_hierarchy_data, name='get_hierarchy_data'),
    
    # NEW: Enhanced question availability checking
    path('check-availability/', views.check_question_availability, name='check_question_availability'),
         
    # Test taking URLs
    path('student/', views.student_mock_tests, name='student_mock_tests'),
    path('take/<int:test_id>/', views.take_test, name='take_test'),
    path('submit-answer/', views.submit_answer, name='submit_answer'),
    path('submit-test/', views.submit_test, name='submit_test'),
    path('result/<int:attempt_id>/', views.test_result, name='test_result'),
    path('report-warning/', views.report_warning, name='report_warning'),
    path('progress/', views.mock_test_progress, name='mock_test_progress'),
]


