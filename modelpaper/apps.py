# modelpaper/apps.py
from django.apps import AppConfig

class ModelpaperConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modelpaper'
    verbose_name = 'Model Papers'