# managemodule/urls.py - Complete with Notes Support and Missing URLs
from django.urls import path
from . import views

urlpatterns = [
    # Admin URLs (existing)
    path('', views.managemodule, name='managemodule'),
    path('topic-questions/', views.topic_questions, name='topic_questions'),
    
    # Student Practice URLs (existing structure maintained)
    path('student/', views.student_practice_modules, name='student_practice_modules'),
    path('student/practice/', views.start_practice_session, name='start_practice_session'),
    path('student/session/<int:session_id>/', views.practice_session, name='practice_session'),
    path('student/submit-answer/', views.submit_practice_answer, name='submit_practice_answer'),
    path('student/complete-session/', views.complete_practice_session, name='complete_practice_session'),
    path('student/progress/', views.student_practice_progress, name='student_practice_progress'),
    path('student/session/<int:session_id>/result/', views.practice_session_result, name='practice_session_result'),
    
    # REQUIRED - Core Notes Functionality (FIXED - these were missing!)
    path('student/mark-for-review/', views.mark_question_for_review, name='mark_question_for_review'),
    path('student/save-note/', views.save_practice_note, name='save_practice_note'),
    
    # ENHANCED - Notes Checking Functionality (ADD THESE!)
    path('student/check-note/', views.check_question_note, name='check_question_note'),
    
    # AJAX API URLs
    path('api/question-count-by-difficulty/', views.get_question_count_by_difficulty, name='get_question_count_by_difficulty'),
]