import json
import logging
import asyncio
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from telegram import Update
from telegram.ext import ContextTypes
from .bot import get_or_create_bot, start_bot_for_user, stop_bot_for_user
from core.models import Salon, UserSession

User = get_user_model()
logger = logging.getLogger(__name__)

def get_user_session(telegram_user_id):
    """Get user session data from database"""
    try:
        session = UserSession.objects.get(user_id=telegram_user_id)
        return session.session_data
    except UserSession.DoesNotExist:
        return {}

def set_user_session(telegram_user_id, data):
    """Set user session data in database"""
    session, created = UserSession.objects.get_or_create(
        user_id=telegram_user_id,
        defaults={'session_data': data}
    )
    if not created:
        session.session_data = data
        session.save()

def clear_user_session(telegram_user_id):
    """Clear user session data from database"""
    UserSession.objects.filter(user_id=telegram_user_id).delete()

def start_salon_registration(telegram_user_id):
    """Start salon registration process"""
    set_user_session(telegram_user_id, {
        'state': 'salon_registration',
        'step': 'name',
        'salon_data': {}
    })

def handle_salon_registration_step(bot, user, chat_id, text, session_data, telegram_user_id):
    """Handle salon registration steps"""
    step = session_data.get('step')
    salon_data = session_data.get('salon_data', {})
    
    logger.info(f"Registration step for telegram_user {telegram_user_id}: step={step}, text='{text}'")
    
    if step == 'name':
        salon_data['name'] = text
        session_data['step'] = 'address'
        session_data['salon_data'] = salon_data
        set_user_session(telegram_user_id, session_data)
        send_message(bot, chat_id, "📍 Введите адрес салона:")
        
    elif step == 'address':
        salon_data['address'] = text
        session_data['step'] = 'phone'
        session_data['salon_data'] = salon_data
        set_user_session(telegram_user_id, session_data)
        send_message(bot, chat_id, "📞 Введите телефон салона:")
        
    elif step == 'phone':
        salon_data['phone'] = text
        session_data['step'] = 'email'
        session_data['salon_data'] = salon_data
        set_user_session(telegram_user_id, session_data)
        send_message(bot, chat_id, "📧 Введите email салона:")
        
    elif step == 'email':
        salon_data['email'] = text
        session_data['step'] = 'working_hours'
        session_data['salon_data'] = salon_data
        set_user_session(telegram_user_id, session_data)
        send_message(bot, chat_id, "🕐 Введите часы работы (например: Пн-Пт 9:00-18:00, Сб 10:00-16:00):")
        
    elif step == 'working_hours':
        salon_data['working_hours'] = text
        session_data['step'] = 'telegram_bot_token'
        session_data['salon_data'] = salon_data
        set_user_session(telegram_user_id, session_data)
        send_message(bot, chat_id, """
🤖 Введите токен Telegram бота для клиентов салона:

📝 Как получить токен:
1. Напишите @BotFather в Telegram
2. Отправьте команду /newbot
3. Следуйте инструкциям
4. Скопируйте полученный токен

Токен выглядит примерно так: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
        """.strip())
        
    elif step == 'telegram_bot_token':
        # Validate telegram bot token format
        if not text or not text.count(':') == 1:
            send_message(bot, chat_id, """
❌ Неверный формат токена!

Токен должен содержать символ ':' и выглядеть примерно так:
123456789:ABCdefGHIjklMNOpqrsTUVwxyz

Попробуйте еще раз:
            """.strip())
            return
        
        salon_data['telegram_bot_token'] = text
        session_data['step'] = 'telegram_bot_username'
        session_data['salon_data'] = salon_data
        set_user_session(telegram_user_id, session_data)
        send_message(bot, chat_id, """
🤖 Введите username Telegram бота (без @):

Например: my_salon_bot
Это имя бота, которое вы указали при создании в @BotFather
        """.strip())
        
    elif step == 'telegram_bot_username':
        # Clean username (remove @ if present)
        username = text.strip().lstrip('@')
        salon_data['telegram_bot_username'] = username
        session_data['step'] = 'openai_api_key'
        session_data['salon_data'] = salon_data
        set_user_session(telegram_user_id, session_data)
        send_message(bot, chat_id, """
🔑 Введите API ключ OpenAI:

📝 Как получить ключ:
1. Зайдите на https://platform.openai.com/api-keys
2. Войдите в аккаунт или зарегистрируйтесь
3. Нажмите 'Create new secret key'
4. Скопируйте ключ

Ключ начинается с 'sk-' и выглядит примерно так:
sk-proj-abc123def456ghi789jkl...
        """.strip())
        
    elif step == 'openai_api_key':
        # Validate OpenAI API key format
        if not text or not text.startswith('sk-'):
            send_message(bot, chat_id, """
❌ Неверный формат API ключа!

Ключ OpenAI должен начинаться с 'sk-'
Например: sk-proj-abc123def456ghi789jkl...

Попробуйте еще раз:
            """.strip())
            return
        
        salon_data['openai_api_key'] = text
        session_data['step'] = 'confirmation'
        session_data['salon_data'] = salon_data
        set_user_session(telegram_user_id, session_data)
        
        # Show summary and ask for confirmation
        summary_message = f"""
📋 Проверьте данные салона:

🏪 Название: {salon_data['name']}
📍 Адрес: {salon_data['address']}
📞 Телефон: {salon_data['phone']}
📧 Email: {salon_data['email']}
🕐 Часы работы: {salon_data['working_hours']}
🤖 Бот: @{salon_data['telegram_bot_username']}
🔑 OpenAI ключ: {salon_data['openai_api_key'][:10]}...

✅ Все верно? Отправьте 'да' для подтверждения или 'нет' для отмены.
        """
        
        send_message(bot, chat_id, summary_message.strip())
        
    elif step == 'confirmation':
        if text.lower() in ['да', 'yes', 'y', 'д']:
            # Create salon and new business user
            try:
                import secrets
                import string
                
                # Generate username based on salon name (transliterate to Latin)
                def transliterate_to_latin(text):
                    """Convert Cyrillic to Latin characters"""
                    cyrillic_to_latin = {
                        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
                        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
                    }
                    result = ''
                    for char in text.lower():
                        if char in cyrillic_to_latin:
                            result += cyrillic_to_latin[char]
                        elif char.isalnum():
                            result += char
                    return result
                
                salon_name_transliterated = transliterate_to_latin(salon_data['name'])
                salon_name_clean = ''.join(c for c in salon_name_transliterated if c.isalnum())
                base_username = f"salon_{salon_name_clean[:15]}" if salon_name_clean else 'salon_business'
                
                # Ensure unique username
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                # Generate secure password
                alphabet = string.ascii_letters + string.digits + '!@#$%&*'
                password = ''.join(secrets.choice(alphabet) for _ in range(16))
                
                # Create new user for the salon
                salon_user = User.objects.create_user(
                    username=username,
                    email=salon_data['email'],
                    password=password,
                    first_name=salon_data['name'][:30],  # Limit length
                    telegram_bot_token=salon_data['telegram_bot_token'],
                    openai_api_token=salon_data['openai_api_key'],
                    is_staff=True  # Даем права персонала для входа в админку
                )
                
                # Даем права на работу с салонами и связанными моделями
                from django.contrib.auth.models import Permission
                from django.contrib.contenttypes.models import ContentType
                from core.models import Master, Service, Client, Appointment, Document, Post
                
                # Модели, на которые нужны права
                models_to_grant = [Salon, Master, Service, Client, Appointment, Document, Post]
                
                for model in models_to_grant:
                    content_type = ContentType.objects.get_for_model(model)
                    permissions = Permission.objects.filter(content_type=content_type)
                    for perm in permissions:
                        salon_user.user_permissions.add(perm)
                
                # Create salon
                salon = Salon.objects.create(
                    user=salon_user,
                    name=salon_data['name'],
                    address=salon_data['address'],
                    phone=salon_data['phone'],
                    email=salon_data['email'],
                    working_hours={'text': salon_data['working_hours']},
                    telegram_bot_token=salon_data['telegram_bot_token'],
                    telegram_bot_username=salon_data['telegram_bot_username'],
                    openai_api_key=salon_data['openai_api_key'],
                    timezone='UTC'
                )
                
                success_message = f"""
✅ Салон успешно зарегистрирован!

🏪 Название: {salon.name}
📍 Адрес: {salon.address}
📞 Телефон: {salon.phone}
📧 Email: {salon.email}
🕐 Часы работы: {salon_data['working_hours']}
🤖 Бот для клиентов: @{salon.telegram_bot_username}

🔐 Данные для входа в веб-админку:
URL: https://salonify-app-3cd2419b7b71.herokuapp.com/admin/
Логин: {username}
Пароль: {password}

⚠️ ВАЖНО: Сохраните эти данные в безопасном месте!
Пароль показывается только один раз.

🎯 Следующие шаги:
1. Войдите в админку по указанным данным
2. Настройте webhook для бота клиентов
3. Добавьте мастеров и услуги
4. Начните принимать записи!

ID салона: {salon.id}
                """
                
                send_message(bot, chat_id, success_message.strip())
                
                # Clear session
                clear_user_session(telegram_user_id)
                
            except Exception as e:
                logger.error(f"Error creating salon: {str(e)}")
                send_message(bot, chat_id, f"❌ Ошибка при создании салона: {str(e)}")
                clear_user_session(telegram_user_id)
        
        elif text.lower() in ['нет', 'no', 'n', 'н']:
            send_message(bot, chat_id, "❌ Регистрация отменена. Используйте /register_salon для повторной попытки.")
            clear_user_session(telegram_user_id)
        
        else:
            send_message(bot, chat_id, "Пожалуйста, ответьте 'да' или 'нет':")


@csrf_exempt
@require_http_methods(["POST"])
def webhook(request, bot_token):
    """Handle Telegram webhook updates"""
    try:
        # Parse update
        update_data = json.loads(request.body)
        logger.info(f"Received update for bot_token {bot_token}: {update_data}")
        
        # Try to find admin user by bot token first
        try:
            user = User.objects.get(telegram_bot_token=bot_token)
            logger.info(f"Found admin user {user.username} for token")
            process_telegram_update(user, update_data)
            return JsonResponse({'status': 'ok'})
        except User.DoesNotExist:
            pass
        
        # Try to find salon by bot token
        try:
            salon = Salon.objects.get(telegram_bot_token=bot_token)
            logger.info(f"Found salon {salon.name} for token")
            process_salon_client_update(salon, update_data)
            return JsonResponse({'status': 'ok'})
        except Salon.DoesNotExist:
            pass
        
        logger.error(f"Bot token {bot_token} not found in users or salons")
        return JsonResponse({'error': 'Bot not found'}, status=404)
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JsonResponse({'error': 'Internal error'}, status=500)


def process_telegram_update(user, update_data):
    """Process Telegram update synchronously for admin bots"""
    try:
        from .bot import SalonifyBot
        
        # Create bot instance
        bot = SalonifyBot(user.telegram_bot_token, user)
        
        # Create Update object
        update = Update.de_json(update_data, bot.application.bot)
        
        # Handle different types of updates
        if update.message:
            handle_message_sync(bot, update, user)
        elif update.callback_query:
            handle_callback_query_sync(bot, update, user)
            
    except Exception as e:
        logger.error(f"Error processing update: {str(e)}")


def process_salon_client_update(salon, update_data):
    """Process Telegram update synchronously for salon client bots"""
    try:
        from .client_bot import SalonClientBot
        
        # Create client bot instance
        bot = SalonClientBot(salon)
        
        # Create Update object
        update = Update.de_json(update_data, bot.application.bot)
        
        # Handle different types of updates
        if update.message:
            handle_client_message_sync(bot, update, salon)
        elif update.callback_query:
            handle_client_callback_query_sync(bot, update, salon)
            
    except Exception as e:
        logger.error(f"Error processing salon client update: {str(e)}")


def handle_message_sync(bot, update, user):
    """Handle message synchronously"""
    try:
        message = update.message
        text = message.text
        chat_id = message.chat.id
        
        # Get or create user session data using Telegram user ID
        telegram_user_id = message.from_user.id
        session_data = get_user_session(telegram_user_id)
        
        # Handle commands
        if text == '/start':
            clear_user_session(telegram_user_id)
            send_message(bot, chat_id, f"""
👋 Добро пожаловать в Salonify Admin Bot, {message.from_user.first_name}!

🏪 Этот бот предназначен для ВЛАДЕЛЬЦЕВ салонов красоты.

Я помогу вам:
• Зарегистрировать ваш салон
• Создать персональный бот для ваших клиентов
• Управлять записями и услугами
• Настроить автоматические уведомления

Используйте /help для просмотра всех команд.
            """.strip())
            
        elif text == '/help':
            send_message(bot, chat_id, """
🤖 Команды для владельцев салонов:

/start - Начать работу с ботом
/help - Показать это сообщение
/register_salon - Зарегистрировать новый салон
/create_bot - Создать бота для клиентов
/my_salons - Мои салоны
/salon_stats - Статистика салона

📝 Примечание: Этот бот только для владельцев салонов.
Ваши клиенты будут использовать отдельный персональный бот для записей.
            """.strip())
            
        elif text == '/register_salon':
            start_salon_registration(telegram_user_id)
            send_message(bot, chat_id, """
🏪 Регистрация салона

Введите название вашего салона:
            """.strip())
            
        elif session_data.get('state') == 'salon_registration':
            handle_salon_registration_step(bot, user, chat_id, text, session_data, telegram_user_id)
            
        elif text == '/create_bot':
            clear_user_session(telegram_user_id)  # Clear any existing session
            send_message(bot, chat_id, """
🤖 Создание бота для клиентов

Эта функция позволит создать персональный бот для ваших клиентов.
Через этот бот клиенты смогут:
• Записываться на услуги
• Просматривать свои записи
• Отменять записи
• Задавать вопросы о салоне

Функция находится в разработке. Скоро будет доступна!
            """.strip())
            
        elif text == '/my_salons':
            clear_user_session(telegram_user_id)  # Clear any existing session
            send_message(bot, chat_id, """
🏪 Мои салоны

Функция просмотра ваших салонов находится в разработке.
Скоро вы сможете:
• Просматривать список салонов
• Редактировать информацию
• Управлять услугами и мастерами
• Настраивать расписание
            """.strip())
            
        elif text == '/salon_stats':
            clear_user_session(telegram_user_id)  # Clear any existing session
            send_message(bot, chat_id, """
📊 Статистика салона

Функция статистики находится в разработке.
Скоро вы сможете просматривать:
• Количество записей
• Популярные услуги
• Доходы по периодам
• Активность клиентов
            """.strip())
            
        else:
            # Don't clear session for unknown commands - user might be in registration process
            if not session_data.get('state'):
                send_message(bot, chat_id, f"""
❓ Вы написали: {text}

Этот бот предназначен для владельцев салонов красоты.
Используйте /help для просмотра доступных команд.

Если вы клиент салона, обратитесь к администратору за ссылкой на бот вашего салона.
                """.strip())
            else:
                # User is in some process, let them know
                send_message(bot, chat_id, f"""
❓ Неизвестная команда: {text}

Вы находитесь в процессе регистрации салона.
Пожалуйста, ответьте на текущий вопрос или используйте /start для начала заново.
                """.strip())
            
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")


def handle_callback_query_sync(bot, update, user):
    """Handle callback query synchronously"""
    try:
        query = update.callback_query
        send_message(bot, query.message.chat.id, "Callback queries не реализованы пока")
    except Exception as e:
        logger.error(f"Error handling callback query: {str(e)}")


def handle_client_message_sync(bot, update, salon):
    """Handle message synchronously for client bots"""
    try:
        import asyncio
        from telegram.ext import ContextTypes
        
        # Create a simple context
        context = ContextTypes.DEFAULT_TYPE()
        
        # Run the async method synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def handle_async():
            await bot.handle_message(update, context)
        
        loop.run_until_complete(handle_async())
        loop.close()
        
    except Exception as e:
        logger.error(f"Error handling client message: {str(e)}")


def handle_client_callback_query_sync(bot, update, salon):
    """Handle callback query synchronously for client bots"""
    try:
        import asyncio
        from telegram.ext import ContextTypes
        
        # Create a simple context
        context = ContextTypes.DEFAULT_TYPE()
        
        # Run the async method synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def handle_async():
            await bot.button_callback(update, context)
        
        loop.run_until_complete(handle_async())
        loop.close()
        
    except Exception as e:
        logger.error(f"Error handling client callback query: {str(e)}")


def send_message(bot, chat_id, text):
    """Send message using requests"""
    import requests
    
    url = f"https://api.telegram.org/bot{bot.token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            logger.info(f"Message sent successfully to chat {chat_id}")
        else:
            logger.error(f"Failed to send message: {response.text}")
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")


@login_required
@require_http_methods(["POST"])
def start_bot(request):
    """Start bot for current user"""
    try:
        user = request.user
        
        if not user.telegram_bot_token:
            return JsonResponse({'error': 'No bot token configured'}, status=400)
        
        # Start bot (this would be handled by a management command or background task)
        # For now, just return success
        logger.info(f"Starting bot for user {user.username}")
        
        return JsonResponse({'status': 'Bot started'})
        
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        return JsonResponse({'error': 'Failed to start bot'}, status=500)


@login_required
@require_http_methods(["POST"])
def stop_bot(request):
    """Stop bot for current user"""
    try:
        user = request.user
        
        # Stop bot (this would be handled by a management command or background task)
        # For now, just return success
        logger.info(f"Stopping bot for user {user.username}")
        
        return JsonResponse({'status': 'Bot stopped'})
        
    except Exception as e:
        logger.error(f"Error stopping bot: {str(e)}")
        return JsonResponse({'error': 'Failed to stop bot'}, status=500) 