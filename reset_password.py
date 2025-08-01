#!/usr/bin/env python
import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salonify.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def reset_admin_password():
    try:
        # Найти пользователя admin
        user = User.objects.filter(username='admin').first()
        
        if user:
            # Установить новый пароль
            user.set_password('admin123456')
            user.save()
            print('✅ Password for admin user has been reset to: admin123456')
        else:
            # Создать нового пользователя admin
            user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123456'
            )
            print('✅ New admin user created with password: admin123456')
            
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    reset_admin_password() 