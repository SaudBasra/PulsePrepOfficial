from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('user_management.urls')),
    path('', include('main.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('questionbank/', include('questionbank.urls')),
    path('managemodule/', include('managemodule.urls')),
    path('mocktest/', include('mocktest.urls')),
    path('analytics-report/', include('analytics_report.urls')),
    path('myaccount/', include('myaccount.urls')),
    path('notificationsetting/', include('notificationsetting.urls')),
    path('setting/', include('setting.urls')),
    path('analytics-report/', include('analytics_report.urls')),
    path('notification/', include('notificationsetting.urls')),

]