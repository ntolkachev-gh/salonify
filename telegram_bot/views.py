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

User = get_user_model()
logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def webhook(request, bot_token):
    """Handle Telegram webhook updates"""
    try:
        # Find user by bot token
        user = get_object_or_404(User, telegram_bot_token=bot_token)
        
        # Parse update
        update_data = json.loads(request.body)
        logger.info(f"Received update for user {user.username}: {update_data}")
        
        # Process update synchronously
        process_telegram_update(user, update_data)
        
        return JsonResponse({'status': 'ok'})
        
    except User.DoesNotExist:
        logger.error(f"Bot token {bot_token} not found")
        return JsonResponse({'error': 'Bot not found'}, status=404)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JsonResponse({'error': 'Internal error'}, status=500)


def process_telegram_update(user, update_data):
    """Process Telegram update synchronously"""
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


def handle_message_sync(bot, update, user):
    """Handle message synchronously"""
    try:
        message = update.message
        text = message.text
        chat_id = message.chat.id
        
        # Handle commands
        if text == '/start':
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
            send_message(bot, chat_id, """
🏪 Регистрация салона

Введите название вашего салона:
            """.strip())
            
        elif text == '/create_bot':
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
            send_message(bot, chat_id, f"""
❓ Вы написали: {text}

Этот бот предназначен для владельцев салонов красоты.
Используйте /help для просмотра доступных команд.

Если вы клиент салона, обратитесь к администратору за ссылкой на бот вашего салона.
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