from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Reset admin password to a known value'

    def handle(self, *args, **options):
        try:
            # Найти пользователя admin
            user = User.objects.filter(username='admin').first()
            
            if user:
                # Установить новый пароль
                user.set_password('admin123456')
                user.save()
                self.stdout.write(
                    self.style.SUCCESS('Password for admin user has been reset to: admin123456')
                )
            else:
                # Создать нового пользователя admin
                user = User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='admin123456'
                )
                self.stdout.write(
                    self.style.SUCCESS('New admin user created with password: admin123456')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            ) 