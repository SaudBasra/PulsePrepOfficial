# notes/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Main notes dashboard
    path('', views.notes_dashboard, name='notes_dashboard'),
    
    # Topic-specific notes (similar to topic_questions)
    path('topic-notes/', views.topic_notes, name='topic_notes'),
    
    # CRUD operations
    path('add/', views.add_note, name='add_note'),
    path('edit/<int:note_id>/', views.edit_note, name='edit_note'),
    path('delete/<int:note_id>/', views.delete_note, name='delete_note'),
    path('detail/<int:note_id>/', views.note_detail, name='note_detail'),
    
    # AJAX operations
    path('quick-add/', views.quick_add_note, name='quick_add_note'),
    path('toggle-favorite/<int:note_id>/', views.toggle_favorite, name='toggle_favorite'),
    
    # Study sessions
    path('study-session/start/', views.study_session_start, name='study_session_start'),
    path('study-session/end/', views.study_session_end, name='study_session_end'),
    
    # Search
    path('search/', views.search_notes, name='search_notes'),
]