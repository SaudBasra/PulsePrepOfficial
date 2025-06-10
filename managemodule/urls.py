# managemodule/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.managemodule, name='managemodule'),
    path('topic-questions/', views.topic_questions, name='topic_questions'),
    path('api/topic-image-count/', views.get_topic_image_count, name='get_topic_image_count'),

]