# notificationsetting/management/commands/create_default_categories.py
from django.core.management.base import BaseCommand
from notificationsetting.models import NotificationCategory

class Command(BaseCommand):
    help = 'Create default notification categories'

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'system',
                'display_name': 'System Notifications',
                'description': 'System-level notifications and alerts',
                'icon': 'fas fa-cog',
                'color': '#6c757d'
            },
            {
                'name': 'test',
                'display_name': 'Test Notifications',
                'description': 'Mock test related notifications',
                'icon': 'fas fa-clipboard-check',
                'color': '#28a745'
            },
            {
                'name': 'user',
                'display_name': 'User Management',
                'description': 'User registration and approval notifications',
                'icon': 'fas fa-users',
                'color': '#17a2b8'
            },
            {
                'name': 'import',
                'display_name': 'Import Notifications',
                'description': 'CSV import status and results',
                'icon': 'fas fa-file-import',
                'color': '#ffc107'
            },
            {
                'name': 'announcement',
                'display_name': 'Announcements',
                'description': 'General announcements and updates',
                'icon': 'fas fa-bullhorn',
                'color': '#dc3545'
            }
        ]

        for cat_data in categories:
            category, created = NotificationCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category.display_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Category already exists: {category.display_name}')
                )
