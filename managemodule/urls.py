# managemodule/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Admin URLs (existing)
    path('', views.managemodule, name='managemodule'),
    path('topic-questions/', views.topic_questions, name='topic_questions'),
    path('api/topic-image-count/', views.get_topic_image_count, name='get_topic_image_count'),
    
    # Student Practice URLs (existing structure maintained)
    path('student/', views.student_practice_modules, name='student_practice_modules'),
    path('student/practice/', views.start_practice_session, name='start_practice_session'),
    path('student/session/<int:session_id>/', views.practice_session, name='practice_session'),
    path('student/submit-answer/', views.submit_practice_answer, name='submit_practice_answer'),
    path('student/complete-session/', views.complete_practice_session, name='complete_practice_session'),
    path('student/progress/', views.student_practice_progress, name='student_practice_progress'),
    path('student/session/<int:session_id>/result/', views.practice_session_result, name='practice_session_result'),
    
    # New AJAX API for dynamic question counting
    path('api/question-count-by-difficulty/', views.get_question_count_by_difficulty, name='get_question_count_by_difficulty'),
]