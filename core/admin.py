from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Salon, Master, Service, Client, Appointment, Document, Post, Embedding


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'created_at')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('telegram_bot_token', 'openai_api_token', 'created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'phone', 'email', 'timezone', 'created_at')
    list_filter = ('timezone', 'created_at', 'user')
    search_fields = ('name', 'address', 'phone', 'email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'name', 'address', 'phone', 'email')
        }),
        ('Настройки', {
            'fields': ('working_hours', 'timezone')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'salon', 'phone', 'specialization', 'is_active', 'created_at')
    list_filter = ('is_active', 'specialization', 'salon', 'created_at')
    search_fields = ('full_name', 'phone', 'specialization', 'telegram_id')
    ordering = ('salon', 'full_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('salon', 'full_name', 'phone', 'specialization')
        }),
        ('Настройки', {
            'fields': ('is_active', 'working_hours', 'telegram_id')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'salon', 'master', 'category', 'price', 'duration_minutes', 'is_active')
    list_filter = ('category', 'is_active', 'salon', 'master', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('salon', 'category', 'name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('salon', 'master', 'name', 'description', 'category')
        }),
        ('Цены и время', {
            'fields': ('price', 'duration_minutes')
        }),
        ('Настройки', {
            'fields': ('is_active',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'salon', 'phone', 'email', 'visits_count', 'total_spent', 'last_visit_date')
    list_filter = ('salon', 'last_visit_date', 'created_at')
    search_fields = ('full_name', 'phone', 'email', 'telegram_id')
    ordering = ('salon', '-last_visit_date')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('salon', 'full_name', 'phone', 'email', 'telegram_id')
        }),
        ('Статистика', {
            'fields': ('visits_count', 'total_spent', 'last_visit_date')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('client', 'service', 'master', 'scheduled_at', 'status', 'price')
    list_filter = ('status', 'salon', 'master', 'service', 'scheduled_at', 'created_at')
    search_fields = ('client__full_name', 'service__name', 'master__full_name', 'notes')
    ordering = ('-scheduled_at',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'scheduled_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('salon', 'client', 'service', 'master', 'scheduled_at')
        }),
        ('Детали записи', {
            'fields': ('status', 'price', 'notes')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'salon', 'doc_type', 'file_size', 'uploaded_at')
    list_filter = ('doc_type', 'salon', 'uploaded_at')
    search_fields = ('name', 'description', 'tags')
    ordering = ('salon', '-uploaded_at')
    readonly_fields = ('uploaded_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('salon', 'name', 'description', 'doc_type')
        }),
        ('Файл', {
            'fields': ('file_path', 'file_size', 'tags')
        }),
        ('Временные метки', {
            'fields': ('uploaded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('salon', 'caption_preview', 'scheduled_at', 'published_at', 'status')
    list_filter = ('status', 'salon', 'scheduled_at', 'published_at')
    search_fields = ('caption', 'error_message')
    ordering = ('-scheduled_at',)
    readonly_fields = ('published_at', 'created_at', 'updated_at')
    date_hierarchy = 'scheduled_at'
    
    def caption_preview(self, obj):
        return obj.caption[:50] + '...' if len(obj.caption) > 50 else obj.caption
    caption_preview.short_description = 'Заголовок'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('salon', 'caption', 'scheduled_at')
        }),
        ('Статус публикации', {
            'fields': ('status', 'published_at', 'error_message')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Embedding)
class EmbeddingAdmin(admin.ModelAdmin):
    list_display = ('document', 'chunk_index', 'content_preview', 'created_at')
    list_filter = ('document__salon', 'document', 'created_at')
    search_fields = ('content_chunk', 'document__name')
    ordering = ('document', 'chunk_index')
    readonly_fields = ('created_at',)
    
    def content_preview(self, obj):
        return obj.content_chunk[:100] + '...' if len(obj.content_chunk) > 100 else obj.content_chunk
    content_preview.short_description = 'Содержимое'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('document', 'chunk_index', 'content_chunk')
        }),
        ('Векторное представление', {
            'fields': ('embedding_vector',),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    ) 