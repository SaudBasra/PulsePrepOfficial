from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
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
    path('setting/', include('setting.urls')),
    path('analytics-report/', include('analytics_report.urls')),
    path('notification/', include('notifications.urls')),
    path('modelpaper/', include('modelpaper.urls')),
    path('images/', include('manageimage.urls')),
    path('notes/', include('notes.urls')),



]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)