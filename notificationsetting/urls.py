from django.urls import path
from . import views

urlpatterns = [
    path('', views.notificationsetting, name='notificationsetting'),
]