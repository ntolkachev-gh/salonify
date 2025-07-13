from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin
from .models import User, Master, Client, Salon, Service, Appointment, Document, Post, Embedding


# Создаем кастомные группы моделей для лучшей организации
class CustomAdminSite(admin.AdminSite):
    site_header = 'Администрирование Salonify'
    site_title = 'Salonify Admin'
    index_title = 'Добро пожаловать в админку Salonify'

    def get_app_list(self, request):
        """
        Кастомная группировка моделей в админке
        """
        app_list = super().get_app_list(request)
        
        # Создаем новую структуру приложений
        custom_app_list = []
        
        # Группа "Аутентификация и авторизация"
        auth_models = []
        
        # Группа "Основное"
        core_models = []
        
        # Перебираем все приложения
        for app in app_list:
            if app['app_label'] == 'auth':
                # Добавляем стандартные модели аутентификации
                auth_models.extend(app['models'])
            elif app['app_label'] == 'core':
                # Разделяем модели core на две группы
                for model in app['models']:
                    model_name = model['object_name'].lower()
                    if model_name in ['user', 'master', 'client']:
                        # Перемещаем в группу аутентификации
                        auth_models.append(model)
                    else:
                        # Оставляем в основной группе
                        core_models.append(model)
        
        # Создаем группу "Аутентификация и авторизация"
        if auth_models:
            custom_app_list.append({
                'name': 'Аутентификация и авторизация',
                'app_label': 'auth',
                'app_url': '/admin/auth/',
                'has_module_perms': True,
                'models': auth_models
            })
        
        # Создаем группу "Основное"
        if core_models:
            custom_app_list.append({
                'name': 'Основное',
                'app_label': 'core',
                'app_url': '/admin/core/',
                'has_module_perms': True,
                'models': core_models
            })
        
        # Добавляем остальные приложения
        for app in app_list:
            if app['app_label'] not in ['auth', 'core']:
                custom_app_list.append(app)
        
        return custom_app_list


# Создаем экземпляр кастомного админ-сайта
admin_site = CustomAdminSite(name='custom_admin')

# Регистрируем все модели в кастомном админ-сайте
from .admin import (
    UserAdmin, SalonAdmin, MasterAdmin, ServiceAdmin, 
    ClientAdmin, AppointmentAdmin, DocumentAdmin, PostAdmin, EmbeddingAdmin
)

admin_site.register(User, UserAdmin)
admin_site.register(Salon, SalonAdmin)
admin_site.register(Master, MasterAdmin)
admin_site.register(Service, ServiceAdmin)
admin_site.register(Client, ClientAdmin)
admin_site.register(Appointment, AppointmentAdmin)
admin_site.register(Document, DocumentAdmin)
admin_site.register(Post, PostAdmin)
admin_site.register(Embedding, EmbeddingAdmin)

# Регистрируем стандартные модели аутентификации
admin_site.register(Group, GroupAdmin) 