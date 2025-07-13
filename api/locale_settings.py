# Настройки локализации для API
from django.utils.translation import gettext_lazy as _

# Сообщения для API
API_MESSAGES = {
    'created': _('Успешно создано'),
    'updated': _('Успешно обновлено'),
    'deleted': _('Успешно удалено'),
    'not_found': _('Объект не найден'),
    'permission_denied': _('Доступ запрещен'),
    'invalid_data': _('Неверные данные'),
    'authentication_failed': _('Ошибка аутентификации'),
    'token_expired': _('Токен истек'),
    'token_invalid': _('Неверный токен'),
    'validation_error': _('Ошибка валидации'),
    'server_error': _('Ошибка сервера'),
    'bad_request': _('Неверный запрос'),
    'unauthorized': _('Не авторизован'),
    'forbidden': _('Запрещено'),
    'method_not_allowed': _('Метод не разрешен'),
    'not_acceptable': _('Неприемлемо'),
    'conflict': _('Конфликт'),
    'gone': _('Удалено'),
    'unsupported_media_type': _('Неподдерживаемый тип медиа'),
    'throttled': _('Слишком много запросов'),
    'service_unavailable': _('Сервис недоступен'),
}

# Поля модели
FIELD_NAMES = {
    'name': _('Название'),
    'description': _('Описание'),
    'price': _('Цена'),
    'phone': _('Телефон'),
    'email': _('Email'),
    'address': _('Адрес'),
    'created_at': _('Дата создания'),
    'updated_at': _('Дата обновления'),
    'is_active': _('Активно'),
    'status': _('Статус'),
    'category': _('Категория'),
    'duration': _('Длительность'),
    'date': _('Дата'),
    'time': _('Время'),
    'salon': _('Салон'),
    'master': _('Мастер'),
    'client': _('Клиент'),
    'service': _('Услуга'),
    'appointment': _('Запись'),
    'user': _('Пользователь'),
    'full_name': _('Полное имя'),
    'specialization': _('Специализация'),
    'working_hours': _('Часы работы'),
    'timezone': _('Часовой пояс'),
    'telegram_id': _('Telegram ID'),
    'visits_count': _('Количество визитов'),
    'total_spent': _('Общая сумма'),
    'last_visit_date': _('Дата последнего визита'),
    'scheduled_at': _('Запланировано на'),
    'notes': _('Заметки'),
    'doc_type': _('Тип документа'),
    'file_size': _('Размер файла'),
    'tags': _('Теги'),
    'caption': _('Заголовок'),
    'image_url': _('URL изображения'),
    'published_at': _('Опубликовано'),
    'error_message': _('Сообщение об ошибке'),
}

# Статусы
STATUS_CHOICES = {
    'planned': _('Запланирована'),
    'cancelled': _('Отменена'),
    'completed': _('Выполнена'),
    'scheduled': _('Запланирован'),
    'sent': _('Отправлен'),
    'error': _('Ошибка'),
}

# Категории услуг
SERVICE_CATEGORIES = {
    'haircut': _('Стрижка'),
    'coloring': _('Окрашивание'),
    'styling': _('Укладка'),
    'manicure': _('Маникюр'),
    'pedicure': _('Педикюр'),
    'facial': _('Уход за лицом'),
    'massage': _('Массаж'),
    'other': _('Другое'),
}

# Типы документов
DOCUMENT_TYPES = {
    'DOCX': _('Файл DOCX'),
    'TXT': _('Текстовый файл'),
    'GOOGLE_DOC': _('Google Документ'),
} 