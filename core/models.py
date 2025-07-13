from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import RegexValidator


class User(AbstractUser):
    """Пользователь системы"""
    telegram_bot_token = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name='Токен Telegram бота',
        help_text='Токен для интеграции с Telegram ботом'
    )
    openai_api_token = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name='API токен OpenAI',
        help_text='Токен для интеграции с OpenAI API'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.username} ({self.first_name} {self.last_name})"


class Salon(models.Model):
    """Салон красоты"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        verbose_name='Владелец',
        help_text='Пользователь-владелец салона'
    )
    name = models.CharField(
        max_length=200, 
        verbose_name='Название салона'
    )
    address = models.TextField(
        verbose_name='Адрес',
        help_text='Полный адрес салона'
    )
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Номер телефона должен быть в формате: '+999999999'. До 15 цифр."
        )],
        verbose_name='Телефон'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email'
    )
    working_hours = models.JSONField(
        default=dict,
        verbose_name='Часы работы',
        help_text='Расписание работы салона в формате JSON'
    )
    timezone = models.CharField(
        max_length=50,
        default='Europe/Moscow',
        verbose_name='Часовой пояс'
    )
    telegram_bot_token = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name='Токен Telegram бота салона',
        help_text='Токен персонального бота для клиентов салона'
    )
    telegram_bot_username = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Username Telegram бота',
        help_text='Username бота для клиентов (без @)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Салон'
        verbose_name_plural = 'Салоны'

    def __str__(self):
        return self.name


class Master(models.Model):
    """Мастер в салоне"""
    salon = models.ForeignKey(
        Salon, 
        on_delete=models.CASCADE, 
        verbose_name='Салон'
    )
    full_name = models.CharField(
        max_length=200, 
        verbose_name='Полное имя'
    )
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Номер телефона должен быть в формате: '+999999999'. До 15 цифр."
        )],
        verbose_name='Телефон'
    )
    specialization = models.CharField(
        max_length=200, 
        verbose_name='Специализация',
        help_text='Основная специализация мастера'
    )
    working_hours = models.JSONField(
        default=dict,
        verbose_name='Часы работы',
        help_text='Расписание работы мастера в формате JSON'
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Активен',
        help_text='Активен ли мастер для записи'
    )
    telegram_id = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name='Telegram ID'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Мастер'
        verbose_name_plural = 'Мастера'

    def __str__(self):
        return f"{self.full_name} ({self.salon.name})"


class Service(models.Model):
    """Услуга салона"""
    CATEGORY_CHOICES = [
        ('hair', 'Волосы'),
        ('nails', 'Ногти'),
        ('face', 'Лицо'),
        ('body', 'Тело'),
        ('massage', 'Массаж'),
        ('other', 'Другое'),
    ]
    
    salon = models.ForeignKey(
        Salon, 
        on_delete=models.CASCADE, 
        verbose_name='Салон'
    )
    master = models.ForeignKey(
        Master, 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True,
        verbose_name='Мастер',
        help_text='Мастер, который выполняет услугу (необязательно)'
    )
    name = models.CharField(
        max_length=200, 
        verbose_name='Название услуги'
    )
    description = models.TextField(
        blank=True, 
        verbose_name='Описание'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name='Категория'
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Цена'
    )
    duration_minutes = models.PositiveIntegerField(
        verbose_name='Длительность (минуты)'
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Активна',
        help_text='Доступна ли услуга для записи'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'

    def __str__(self):
        return f"{self.name} ({self.salon.name})"


class Client(models.Model):
    """Клиент салона"""
    salon = models.ForeignKey(
        Salon, 
        on_delete=models.CASCADE, 
        verbose_name='Салон'
    )
    full_name = models.CharField(
        max_length=200, 
        verbose_name='Полное имя'
    )
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Номер телефона должен быть в формате: '+999999999'. До 15 цифр."
        )],
        verbose_name='Телефон'
    )
    email = models.EmailField(
        blank=True, 
        verbose_name='Email'
    )
    telegram_id = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name='Telegram ID'
    )
    visits_count = models.PositiveIntegerField(
        default=0, 
        verbose_name='Количество визитов'
    )
    total_spent = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name='Общая сумма потрачено'
    )
    last_visit_date = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='Дата последнего визита'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'

    def __str__(self):
        return f"{self.full_name} ({self.salon.name})"


class Appointment(models.Model):
    """Запись на прием"""
    STATUS_CHOICES = [
        ('scheduled', 'Запланирована'),
        ('confirmed', 'Подтверждена'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
        ('no_show', 'Не явился'),
    ]
    
    salon = models.ForeignKey(
        Salon, 
        on_delete=models.CASCADE, 
        verbose_name='Салон'
    )
    client = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        verbose_name='Клиент'
    )
    service = models.ForeignKey(
        Service, 
        on_delete=models.CASCADE, 
        verbose_name='Услуга'
    )
    master = models.ForeignKey(
        Master, 
        on_delete=models.CASCADE, 
        verbose_name='Мастер'
    )
    scheduled_at = models.DateTimeField(
        verbose_name='Время записи'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name='Статус'
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Цена'
    )
    notes = models.TextField(
        blank=True, 
        verbose_name='Заметки'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Запись'
        verbose_name_plural = 'Записи'

    def __str__(self):
        return f"{self.client.full_name} - {self.service.name} ({self.scheduled_at})"


class Document(models.Model):
    """Документ"""
    DOC_TYPE_CHOICES = [
        ('policy', 'Политика'),
        ('price_list', 'Прайс-лист'),
        ('instruction', 'Инструкция'),
        ('contract', 'Договор'),
        ('other', 'Другое'),
    ]
    
    salon = models.ForeignKey(
        Salon, 
        on_delete=models.CASCADE, 
        verbose_name='Салон'
    )
    name = models.CharField(
        max_length=200, 
        verbose_name='Название документа'
    )
    description = models.TextField(
        blank=True, 
        verbose_name='Описание'
    )
    doc_type = models.CharField(
        max_length=20,
        choices=DOC_TYPE_CHOICES,
        default='other',
        verbose_name='Тип документа'
    )
    file_path = models.CharField(
        max_length=500, 
        verbose_name='Путь к файлу',
        default='',
        blank=True
    )
    file_size = models.PositiveIntegerField(
        verbose_name='Размер файла (байты)'
    )
    tags = models.CharField(
        max_length=500, 
        blank=True, 
        verbose_name='Теги',
        help_text='Теги для поиска, разделенные запятыми'
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата загрузки'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'

    def __str__(self):
        return f"{self.name} ({self.salon.name})"


class Post(models.Model):
    """Пост для публикации"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('scheduled', 'Запланирован'),
        ('published', 'Опубликован'),
        ('failed', 'Ошибка публикации'),
    ]
    
    salon = models.ForeignKey(
        Salon, 
        on_delete=models.CASCADE, 
        verbose_name='Салон'
    )
    caption = models.TextField(
        verbose_name='Заголовок поста'
    )
    image_url = models.URLField(
        blank=True, 
        verbose_name='URL изображения'
    )
    scheduled_at = models.DateTimeField(
        verbose_name='Время публикации'
    )
    published_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='Фактическое время публикации'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Статус'
    )
    error_message = models.TextField(
        blank=True, 
        verbose_name='Сообщение об ошибке'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        return f"{self.salon.name} - {self.caption[:50]}..."


class Embedding(models.Model):
    """Векторное представление документа"""
    document = models.ForeignKey(
        Document, 
        on_delete=models.CASCADE, 
        verbose_name='Документ'
    )
    chunk_index = models.PositiveIntegerField(
        verbose_name='Индекс части'
    )
    content_chunk = models.TextField(
        verbose_name='Часть содержимого'
    )
    embedding_vector = models.JSONField(
        verbose_name='Векторное представление'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Векторное представление'
        verbose_name_plural = 'Векторные представления'
        unique_together = ['document', 'chunk_index']

    def __str__(self):
        return f"{self.document.name} - часть {self.chunk_index}" 