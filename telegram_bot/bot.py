import logging
import json
import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta
import pytz

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from core.models import Salon, Master, Service, Client, Appointment
from core.tasks import search_embeddings
import openai

User = get_user_model()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot states
SALON_REGISTRATION = 'salon_registration'
APPOINTMENT_BOOKING = 'appointment_booking'
QUESTION_ASKING = 'question_asking'

# User data keys
USER_DATA_STATE = 'state'
USER_DATA_SALON = 'salon_data'
USER_DATA_APPOINTMENT = 'appointment_data'


class SalonifyBot:
    def __init__(self, token: str, user: User):
        self.token = token
        self.user = user
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up bot command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("register_salon", self.register_salon))
        self.application.add_handler(CommandHandler("book_appointment", self.book_appointment))
        self.application.add_handler(CommandHandler("my_appointments", self.my_appointments))
        self.application.add_handler(CommandHandler("cancel_appointment", self.cancel_appointment))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handler for text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Contact handler for phone number sharing
        self.application.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        welcome_message = f"""
👋 Добро пожаловать в Salonify, {user.first_name}!

🏪 Я - административный бот для владельцев салонов красоты.

Я помогу вам:
🏪 Зарегистрировать салон
🤖 Создать персональный бот для клиентов
📊 Управлять салоном
❓ Ответить на ваши вопросы

📝 Для записи клиентов каждый салон получает отдельный бот.
Этот бот предназначен только для владельцев салонов.

Используйте /help для просмотра всех команд.
        """
        
        await update.message.reply_text(welcome_message.strip())
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 Команды для владельцев салонов:

/start - Начать работу с ботом
/help - Показать это сообщение
/register_salon - Зарегистрировать новый салон
/create_bot - Создать бота для клиентов (в разработке)
/my_salons - Мои салоны (в разработке)
/salon_stats - Статистика салона (в разработке)

📝 Этот бот предназначен для владельцев салонов красоты.
Для записи на услуги клиенты должны использовать персональный бот своего салона.

Просто отправьте мне сообщение с вопросом, и я постараюсь помочь!
        """
        
        await update.message.reply_text(help_text.strip())
    
    async def register_salon(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start salon registration process"""
        context.user_data[USER_DATA_STATE] = SALON_REGISTRATION
        context.user_data[USER_DATA_SALON] = {}
        
        await update.message.reply_text(
            "🏪 Регистрация салона\n\n"
            "Введите название салона:"
        )
    
    async def book_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start appointment booking process"""
        # Get user's salons
        salons = Salon.objects.filter(user=self.user)
        
        if not salons.exists():
            await update.message.reply_text(
                "❌ У вас нет зарегистрированных салонов.\n"
                "Используйте /register_salon для регистрации."
            )
            return
        
        # Create inline keyboard with salons
        keyboard = []
        for salon in salons:
            keyboard.append([InlineKeyboardButton(
                f"🏪 {salon.name}",
                callback_data=f"select_salon_{salon.id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📅 Выберите салон для записи:",
            reply_markup=reply_markup
        )
    
    async def my_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's appointments"""
        user_id = str(update.effective_user.id)
        
        # Find client by telegram_id
        try:
            client = Client.objects.get(telegram_id=user_id)
        except Client.DoesNotExist:
            await update.message.reply_text(
                "❌ Вы не зарегистрированы ни в одном салоне."
            )
            return
        
        # Get upcoming appointments
        upcoming_appointments = client.appointments.filter(
            scheduled_at__gte=timezone.now(),
            status='planned'
        ).order_by('scheduled_at')
        
        if not upcoming_appointments.exists():
            await update.message.reply_text("📅 У вас нет запланированных записей.")
            return
        
        message = "📅 Ваши записи:\n\n"
        
        for appointment in upcoming_appointments:
            message += f"""
🏪 {appointment.salon.name}
💇‍♀️ {appointment.service.name}
👨‍💼 {appointment.master.full_name}
📅 {appointment.scheduled_at.strftime('%d.%m.%Y %H:%M')}
💰 {appointment.price} руб.
---
            """
        
        await update.message.reply_text(message.strip())
    
    async def cancel_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show appointments that can be cancelled"""
        user_id = str(update.effective_user.id)
        
        try:
            client = Client.objects.get(telegram_id=user_id)
        except Client.DoesNotExist:
            await update.message.reply_text(
                "❌ Вы не зарегистрированы ни в одном салоне."
            )
            return
        
        # Get upcoming appointments
        upcoming_appointments = client.appointments.filter(
            scheduled_at__gte=timezone.now(),
            status='planned'
        ).order_by('scheduled_at')
        
        if not upcoming_appointments.exists():
            await update.message.reply_text("📅 У вас нет записей для отмены.")
            return
        
        # Create inline keyboard with appointments
        keyboard = []
        for appointment in upcoming_appointments:
            keyboard.append([InlineKeyboardButton(
                f"{appointment.service.name} - {appointment.scheduled_at.strftime('%d.%m %H:%M')}",
                callback_data=f"cancel_appointment_{appointment.id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ Выберите запись для отмены:",
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith('select_salon_'):
            salon_id = data.split('_')[2]
            await self.handle_salon_selection(query, context, salon_id)
        
        elif data.startswith('select_service_'):
            service_id = data.split('_')[2]
            await self.handle_service_selection(query, context, service_id)
        
        elif data.startswith('select_master_'):
            master_id = data.split('_')[2]
            await self.handle_master_selection(query, context, master_id)
        
        elif data.startswith('cancel_appointment_'):
            appointment_id = data.split('_')[2]
            await self.handle_appointment_cancellation(query, context, appointment_id)
    
    async def handle_salon_selection(self, query, context, salon_id):
        """Handle salon selection for appointment booking"""
        try:
            salon = Salon.objects.get(id=salon_id, user=self.user)
        except Salon.DoesNotExist:
            await query.edit_message_text("❌ Салон не найден.")
            return
        
        context.user_data[USER_DATA_STATE] = APPOINTMENT_BOOKING
        context.user_data[USER_DATA_APPOINTMENT] = {'salon_id': salon_id}
        
        # Get available services
        services = salon.services.filter(is_active=True)
        
        if not services.exists():
            await query.edit_message_text("❌ В салоне нет доступных услуг.")
            return
        
        # Create inline keyboard with services
        keyboard = []
        for service in services:
            keyboard.append([InlineKeyboardButton(
                f"{service.name} - {service.price} руб.",
                callback_data=f"select_service_{service.id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🏪 Салон: {salon.name}\n\n"
            "💇‍♀️ Выберите услугу:",
            reply_markup=reply_markup
        )
    
    async def handle_service_selection(self, query, context, service_id):
        """Handle service selection for appointment booking"""
        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            await query.edit_message_text("❌ Услуга не найдена.")
            return
        
        context.user_data[USER_DATA_APPOINTMENT]['service_id'] = service_id
        
        # Get available masters for this service
        if service.master:
            masters = [service.master]
        else:
            masters = service.salon.masters.filter(is_active=True)
        
        if not masters:
            await query.edit_message_text("❌ Нет доступных мастеров.")
            return
        
        # Create inline keyboard with masters
        keyboard = []
        for master in masters:
            keyboard.append([InlineKeyboardButton(
                f"👨‍💼 {master.full_name}",
                callback_data=f"select_master_{master.id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"💇‍♀️ Услуга: {service.name}\n"
            f"💰 Цена: {service.price} руб.\n"
            f"⏱ Длительность: {service.duration_minutes} мин.\n\n"
            "👨‍💼 Выберите мастера:",
            reply_markup=reply_markup
        )
    
    async def handle_master_selection(self, query, context, master_id):
        """Handle master selection for appointment booking"""
        try:
            master = Master.objects.get(id=master_id)
        except Master.DoesNotExist:
            await query.edit_message_text("❌ Мастер не найден.")
            return
        
        context.user_data[USER_DATA_APPOINTMENT]['master_id'] = master_id
        
        await query.edit_message_text(
            f"👨‍💼 Мастер: {master.full_name}\n\n"
            "📅 Отправьте желаемую дату и время записи в формате:\n"
            "ДД.ММ.ГГГГ ЧЧ:ММ\n\n"
            "Например: 25.12.2023 14:30"
        )
    
    async def handle_appointment_cancellation(self, query, context, appointment_id):
        """Handle appointment cancellation"""
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            appointment.status = 'cancelled'
            appointment.save()
            
            await query.edit_message_text(
                f"✅ Запись отменена:\n\n"
                f"🏪 {appointment.salon.name}\n"
                f"💇‍♀️ {appointment.service.name}\n"
                f"📅 {appointment.scheduled_at.strftime('%d.%m.%Y %H:%M')}"
            )
            
        except Appointment.DoesNotExist:
            await query.edit_message_text("❌ Запись не найдена.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages based on current state"""
        user_state = context.user_data.get(USER_DATA_STATE)
        
        if user_state == SALON_REGISTRATION:
            await self.handle_salon_registration(update, context)
        elif user_state == APPOINTMENT_BOOKING:
            await self.handle_appointment_booking(update, context)
        else:
            # Handle as question
            await self.handle_question(update, context)
    
    async def handle_salon_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle salon registration steps"""
        salon_data = context.user_data[USER_DATA_SALON]
        text = update.message.text
        
        if 'name' not in salon_data:
            salon_data['name'] = text
            await update.message.reply_text("📍 Введите адрес салона:")
        
        elif 'address' not in salon_data:
            salon_data['address'] = text
            await update.message.reply_text("📞 Введите телефон салона:")
        
        elif 'phone' not in salon_data:
            salon_data['phone'] = text
            await update.message.reply_text("📧 Введите email салона:")
        
        elif 'email' not in salon_data:
            salon_data['email'] = text
            await update.message.reply_text("🕐 Введите часы работы (например: Пн-Пт 9:00-18:00, Сб 10:00-16:00):")
        
        elif 'working_hours' not in salon_data:
            salon_data['working_hours'] = text
            await update.message.reply_text(
                "🤖 Введите токен Telegram бота для клиентов салона:\n\n"
                "📝 Как получить токен:\n"
                "1. Напишите @BotFather в Telegram\n"
                "2. Отправьте команду /newbot\n"
                "3. Следуйте инструкциям\n"
                "4. Скопируйте полученный токен\n\n"
                "Токен выглядит примерно так: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
            )
        
        elif 'telegram_bot_token' not in salon_data:
            # Validate telegram bot token format
            if not text or not text.count(':') == 1:
                await update.message.reply_text(
                    "❌ Неверный формат токена!\n\n"
                    "Токен должен содержать символ ':' и выглядеть примерно так:\n"
                    "123456789:ABCdefGHIjklMNOpqrsTUVwxyz\n\n"
                    "Попробуйте еще раз:"
                )
                return
            
            salon_data['telegram_bot_token'] = text
            await update.message.reply_text(
                "🤖 Введите username Telegram бота (без @):\n\n"
                "Например: my_salon_bot\n"
                "Это имя бота, которое вы указали при создании в @BotFather"
            )
        
        elif 'telegram_bot_username' not in salon_data:
            # Clean username (remove @ if present)
            username = text.strip().lstrip('@')
            salon_data['telegram_bot_username'] = username
            await update.message.reply_text(
                "🔑 Введите API ключ OpenAI:\n\n"
                "📝 Как получить ключ:\n"
                "1. Зайдите на https://platform.openai.com/api-keys\n"
                "2. Войдите в аккаунт или зарегистрируйтесь\n"
                "3. Нажмите 'Create new secret key'\n"
                "4. Скопируйте ключ\n\n"
                "Ключ начинается с 'sk-' и выглядит примерно так:\n"
                "sk-proj-abc123def456ghi789jkl..."
            )
        
        elif 'openai_api_key' not in salon_data:
            # Validate OpenAI API key format
            if not text or not text.startswith('sk-'):
                await update.message.reply_text(
                    "❌ Неверный формат API ключа!\n\n"
                    "Ключ OpenAI должен начинаться с 'sk-'\n"
                    "Например: sk-proj-abc123def456ghi789jkl...\n\n"
                    "Попробуйте еще раз:"
                )
                return
            
            salon_data['openai_api_key'] = text
            
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
            
            await update.message.reply_text(summary_message.strip())
        
        elif 'confirmed' not in salon_data:
            if text.lower() in ['да', 'yes', 'y', 'д']:
                salon_data['confirmed'] = True
                
                # Create salon
                try:
                    salon = Salon.objects.create(
                        user=self.user,
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
Логин: {self.user.username}

🎯 Следующие шаги:
1. Настройте webhook для бота клиентов
2. Добавьте мастеров и услуги в админке
3. Начните принимать записи!

ID салона: {salon.id}
                    """
                    
                    await update.message.reply_text(success_message.strip())
                    
                    # Clear state
                    context.user_data.clear()
                    
                except Exception as e:
                    await update.message.reply_text(f"❌ Ошибка при создании салона: {str(e)}")
                    context.user_data.clear()
            
            elif text.lower() in ['нет', 'no', 'n', 'н']:
                await update.message.reply_text("❌ Регистрация отменена. Используйте /register_salon для повторной попытки.")
                context.user_data.clear()
            
            else:
                await update.message.reply_text("Пожалуйста, ответьте 'да' или 'нет':")
    
    async def handle_appointment_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle appointment booking datetime input"""
        appointment_data = context.user_data[USER_DATA_APPOINTMENT]
        text = update.message.text
        
        # Parse datetime
        try:
            dt = datetime.strptime(text, '%d.%m.%Y %H:%M')
            scheduled_at = timezone.make_aware(dt)
            
            # Check if datetime is in the future
            if scheduled_at <= timezone.now():
                await update.message.reply_text("❌ Дата и время должны быть в будущем.")
                return
            
            # Get or create client
            user_id = str(update.effective_user.id)
            user_name = update.effective_user.full_name
            
            salon = Salon.objects.get(id=appointment_data['salon_id'])
            service = Service.objects.get(id=appointment_data['service_id'])
            master = Master.objects.get(id=appointment_data['master_id'])
            
            client, created = Client.objects.get_or_create(
                salon=salon,
                telegram_id=user_id,
                defaults={
                    'full_name': user_name,
                    'phone': 'Не указан'
                }
            )
            
            # Create appointment
            appointment = Appointment.objects.create(
                salon=salon,
                client=client,
                service=service,
                master=master,
                scheduled_at=scheduled_at,
                price=service.price
            )
            
            success_message = f"""
✅ Запись создана!

🏪 Салон: {salon.name}
💇‍♀️ Услуга: {service.name}
👨‍💼 Мастер: {master.full_name}
📅 Дата и время: {scheduled_at.strftime('%d.%m.%Y %H:%M')}
💰 Цена: {service.price} руб.
⏱ Длительность: {service.duration_minutes} мин.

Мы пришлем напоминание за час до записи!
            """
            
            await update.message.reply_text(success_message.strip())
            
            # Clear state
            context.user_data.clear()
            
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат даты и времени.\n"
                "Используйте формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
                "Например: 25.12.2023 14:30"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при создании записи: {str(e)}")
            context.user_data.clear()
    
    async def handle_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle questions using AI and knowledge base"""
        question = update.message.text
        
        # For now, send a simple response
        # In a real implementation, this would:
        # 1. Search embeddings for relevant information
        # 2. Use OpenAI to generate a response based on context
        # 3. Fall back to general salon information
        
        await update.message.reply_text(
            f"❓ Вы спросили: {question}\n\n"
            "Я пока учусь отвечать на вопросы. Скоро буду умнее! 🤖\n\n"
            "Используйте /help для просмотра доступных команд."
        )
    
    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle contact sharing"""
        contact = update.message.contact
        user_id = str(update.effective_user.id)
        
        # Update client phone number if exists
        try:
            client = Client.objects.get(telegram_id=user_id)
            client.phone = contact.phone_number
            client.save()
            
            await update.message.reply_text(
                f"✅ Номер телефона обновлен: {contact.phone_number}"
            )
        except Client.DoesNotExist:
            await update.message.reply_text(
                "ℹ️ Номер телефона сохранен для будущих записей."
            )
    
    async def run(self):
        """Run the bot"""
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
    
    async def stop(self):
        """Stop the bot"""
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()


# Global bot instances
bot_instances: Dict[str, SalonifyBot] = {}


def get_or_create_bot(user: User) -> SalonifyBot:
    """Get or create bot instance for user"""
    if not user.telegram_bot_token:
        raise ValueError("User has no Telegram bot token")
    
    user_id = str(user.id)
    
    if user_id not in bot_instances:
        bot_instances[user_id] = SalonifyBot(user.telegram_bot_token, user)
    
    return bot_instances[user_id]


async def start_bot_for_user(user: User):
    """Start bot for a specific user"""
    try:
        bot = get_or_create_bot(user)
        await bot.run()
        logger.info(f"Started bot for user {user.username}")
    except Exception as e:
        logger.error(f"Error starting bot for user {user.username}: {str(e)}")


async def stop_bot_for_user(user: User):
    """Stop bot for a specific user"""
    try:
        user_id = str(user.id)
        if user_id in bot_instances:
            bot = bot_instances[user_id]
            await bot.stop()
            del bot_instances[user_id]
            logger.info(f"Stopped bot for user {user.username}")
    except Exception as e:
        logger.error(f"Error stopping bot for user {user.username}: {str(e)}")


async def start_all_bots():
    """Start bots for all users with tokens"""
    from asgiref.sync import sync_to_async
    
    # Получаем пользователей синхронно
    @sync_to_async
    def get_users():
        return list(User.objects.exclude(telegram_bot_token__isnull=True).exclude(telegram_bot_token=''))
    
    users = await get_users()
    
    for user in users:
        try:
            await start_bot_for_user(user)
        except Exception as e:
            logger.error(f"Error starting bot for user {user.username}: {str(e)}")


async def stop_all_bots():
    """Stop all running bots"""
    for user_id, bot in list(bot_instances.items()):
        try:
            await bot.stop()
        except Exception as e:
            logger.error(f"Error stopping bot {user_id}: {str(e)}")
    
    bot_instances.clear() 