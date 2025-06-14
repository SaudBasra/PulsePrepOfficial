# notes/apps.py
from django.apps import AppConfig


class NotesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notes'
    verbose_name = 'Student Notes'

    def ready(self):
        # Import signal handlers if any
        pass
