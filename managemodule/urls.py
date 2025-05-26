# managemodule/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.managemodule, name='managemodule'),
    path('topic-questions/', views.topic_questions, name='topic_questions'),
]