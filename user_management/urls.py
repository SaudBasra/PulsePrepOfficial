# user_management/urls.py
from django.urls import path
from . import views

app_name = 'user_management'

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('api/users/', views.get_users, name='get_users'),
    path('api/users/<int:user_id>/status/', views.change_user_status, name='change_user_status'),
    path('api/users/add/', views.add_user, name='add_user'),
]