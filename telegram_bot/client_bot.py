import logging
import json
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
BOOKING_PROCESS = 'booking_process'
ASKING_QUESTION = 'asking_question'

# User data keys
USER_DATA_STATE = 'state'
USER_DATA_BOOKING = 'booking_data'


class SalonClientBot:
    """Бот для клиентов салона"""
    
    def __init__(self, salon: Salon):
        self.salon = salon
        self.token = salon.telegram_bot_token
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up bot command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("services", self.show_services))
        self.application.add_handler(CommandHandler("book", self.book_appointment))
        self.application.add_handler(CommandHandler("my_appointments", self.my_appointments))
        self.application.add_handler(CommandHandler("cancel", self.cancel_appointment))
        self.application.add_handler(CommandHandler("contact", self.contact_info))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handler for text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Contact handler for phone number sharing
        self.application.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Get or create client
        client, created = Client.objects.get_or_create(
            salon=self.salon,
            telegram_id=str(user.id),
            defaults={
                'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
                'phone': '',
                'email': ''
            }
        )
        
        if created:
            welcome_message = f"""
👋 Добро пожаловать в {self.salon.name}, {user.first_name}!

🏪 Я - бот для записи в салон красоты.

Что я умею:
📅 Записать вас на услуги
📋 Показать доступные услуги
👥 Показать наших мастеров
📞 Предоставить контактную информацию
❓ Ответить на ваши вопросы

Используйте /help для просмотра всех команд или просто напишите мне!
            """
        else:
            welcome_message = f"""
👋 С возвращением, {user.first_name}!

🏪 Добро пожаловать в {self.salon.name}!

Чем могу помочь сегодня?
📅 Записаться на услугу - /book
📋 Посмотреть услуги - /services
📞 Контакты - /contact
            """
        
        await update.message.reply_text(welcome_message.strip())
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = f"""
🤖 Команды бота {self.salon.name}:

📅 /book - Записаться на услугу
📋 /services - Посмотреть все услуги
👥 /my_appointments - Мои записи
❌ /cancel - Отменить запись
📞 /contact - Контактная информация
❓ /help - Показать это сообщение

💬 Также вы можете просто написать мне вопрос, и я постараюсь помочь!

📍 Адрес: {self.salon.address}
📞 Телефон: {self.salon.phone}
        """
        
        await update.message.reply_text(help_text.strip())
    
    async def show_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show available services"""
        services = Service.objects.filter(salon=self.salon, is_active=True)
        
        if not services.exists():
            await update.message.reply_text("❌ В данный момент нет доступных услуг.")
            return
        
        services_text = f"💇‍♀️ Услуги салона {self.salon.name}:\n\n"
        
        # Group services by category
        categories = {}
        for service in services:
            category = service.get_category_display()
            if category not in categories:
                categories[category] = []
            categories[category].append(service)
        
        for category, category_services in categories.items():
            services_text += f"📂 {category}:\n"
            for service in category_services:
                master_info = f" (мастер: {service.master.full_name})" if service.master else ""
                services_text += f"• {service.name}{master_info}\n"
                services_text += f"  💰 {service.price} руб. | ⏱ {service.duration_minutes} мин.\n"
                if service.description:
                    services_text += f"  📝 {service.description}\n"
                services_text += "\n"
        
        services_text += "📅 Для записи используйте команду /book"
        
        await update.message.reply_text(services_text)
    
    async def book_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start booking process"""
        services = Service.objects.filter(salon=self.salon, is_active=True)
        
        if not services.exists():
            await update.message.reply_text("❌ В данный момент нет доступных услуг.")
            return
        
        # Create inline keyboard with services
        keyboard = []
        for service in services:
            master_info = f" ({service.master.full_name})" if service.master else ""
            keyboard.append([InlineKeyboardButton(
                f"{service.name}{master_info} - {service.price} руб.",
                callback_data=f"book_service_{service.id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"💇‍♀️ Выберите услугу в {self.salon.name}:",
            reply_markup=reply_markup
        )
    
    async def my_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's appointments"""
        user_id = str(update.effective_user.id)
        
        try:
            client = Client.objects.get(salon=self.salon, telegram_id=user_id)
        except Client.DoesNotExist:
            await update.message.reply_text("❌ Вы не зарегистрированы в системе. Используйте /start")
            return
        
        appointments = Appointment.objects.filter(
            client=client,
            scheduled_at__gte=timezone.now()
        ).order_by('scheduled_at')
        
        if not appointments.exists():
            await update.message.reply_text("📅 У вас нет предстоящих записей.")
            return
        
        appointments_text = f"📅 Ваши записи в {self.salon.name}:\n\n"
        
        for appointment in appointments:
            status_emoji = {
                'scheduled': '⏰',
                'confirmed': '✅',
                'in_progress': '🔄',
                'completed': '✅',
                'cancelled': '❌',
                'no_show': '❌'
            }.get(appointment.status, '❓')
            
            appointments_text += f"{status_emoji} {appointment.service.name}\n"
            appointments_text += f"👨‍💼 Мастер: {appointment.master.full_name}\n"
            appointments_text += f"📅 Дата: {appointment.scheduled_at.strftime('%d.%m.%Y')}\n"
            appointments_text += f"🕐 Время: {appointment.scheduled_at.strftime('%H:%M')}\n"
            appointments_text += f"💰 Цена: {appointment.price} руб.\n"
            appointments_text += f"📊 Статус: {appointment.get_status_display()}\n"
            if appointment.notes:
                appointments_text += f"📝 Примечания: {appointment.notes}\n"
            appointments_text += "\n"
        
        appointments_text += "❌ Для отмены записи используйте /cancel"
        
        await update.message.reply_text(appointments_text)
    
    async def cancel_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel appointment"""
        user_id = str(update.effective_user.id)
        
        try:
            client = Client.objects.get(salon=self.salon, telegram_id=user_id)
        except Client.DoesNotExist:
            await update.message.reply_text("❌ Вы не зарегистрированы в системе. Используйте /start")
            return
        
        appointments = Appointment.objects.filter(
            client=client,
            scheduled_at__gte=timezone.now(),
            status__in=['scheduled', 'confirmed']
        ).order_by('scheduled_at')
        
        if not appointments.exists():
            await update.message.reply_text("📅 У вас нет записей для отмены.")
            return
        
        # Create inline keyboard with appointments
        keyboard = []
        for appointment in appointments:
            keyboard.append([InlineKeyboardButton(
                f"{appointment.service.name} - {appointment.scheduled_at.strftime('%d.%m %H:%M')}",
                callback_data=f"cancel_appointment_{appointment.id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ Выберите запись для отмены:",
            reply_markup=reply_markup
        )
    
    async def contact_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show contact information"""
        contact_text = f"""
📞 Контактная информация

🏪 {self.salon.name}
📍 Адрес: {self.salon.address}
📞 Телефон: {self.salon.phone}
        """
        
        if self.salon.email:
            contact_text += f"📧 Email: {self.salon.email}\n"
        
        if self.salon.working_hours:
            hours_text = self.salon.working_hours.get('text', '')
            if hours_text:
                contact_text += f"🕐 Часы работы: {hours_text}\n"
        
        contact_text += "\n📅 Для записи используйте /book"
        
        await update.message.reply_text(contact_text.strip())
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith('book_service_'):
            service_id = data.split('_')[2]
            await self.handle_service_booking(query, context, service_id)
        
        elif data.startswith('book_master_'):
            master_id = data.split('_')[2]
            await self.handle_master_selection(query, context, master_id)
        
        elif data.startswith('cancel_appointment_'):
            appointment_id = data.split('_')[2]
            await self.handle_appointment_cancellation(query, context, appointment_id)
    
    async def handle_service_booking(self, query, context, service_id):
        """Handle service booking"""
        try:
            service = Service.objects.get(id=service_id, salon=self.salon)
        except Service.DoesNotExist:
            await query.edit_message_text("❌ Услуга не найдена.")
            return
        
        # Store booking data
        context.user_data[USER_DATA_STATE] = BOOKING_PROCESS
        context.user_data[USER_DATA_BOOKING] = {
            'service_id': service_id,
            'step': 'select_master'
        }
        
        # Get available masters
        if service.master:
            # Service has specific master
            masters = [service.master]
        else:
            # Service can be done by any master
            masters = Master.objects.filter(salon=self.salon, is_active=True)
        
        if not masters:
            await query.edit_message_text("❌ Нет доступных мастеров для этой услуги.")
            return
        
        # Create keyboard with masters
        keyboard = []
        for master in masters:
            keyboard.append([InlineKeyboardButton(
                f"👨‍💼 {master.full_name}",
                callback_data=f"book_master_{master.id}"
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
        """Handle master selection"""
        try:
            master = Master.objects.get(id=master_id, salon=self.salon)
        except Master.DoesNotExist:
            await query.edit_message_text("❌ Мастер не найден.")
            return
        
        booking_data = context.user_data.get(USER_DATA_BOOKING, {})
        booking_data['master_id'] = master_id
        booking_data['step'] = 'select_date'
        context.user_data[USER_DATA_BOOKING] = booking_data
        
        await query.edit_message_text(
            f"👨‍💼 Мастер: {master.full_name}\n\n"
            "📅 Выберите удобную дату и время:\n\n"
            "📝 Напишите желаемую дату и время в формате:\n"
            "ДД.ММ.ГГГГ ЧЧ:ММ\n\n"
            "Например: 25.12.2024 14:30"
        )
    
    async def handle_appointment_cancellation(self, query, context, appointment_id):
        """Handle appointment cancellation"""
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            await query.edit_message_text("❌ Запись не найдена.")
            return
        
        # Cancel appointment
        appointment.status = 'cancelled'
        appointment.save()
        
        await query.edit_message_text(
            f"✅ Запись отменена:\n\n"
            f"💇‍♀️ Услуга: {appointment.service.name}\n"
            f"👨‍💼 Мастер: {appointment.master.full_name}\n"
            f"📅 Дата: {appointment.scheduled_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            "📞 При необходимости свяжитесь с нами для уточнения деталей."
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user_state = context.user_data.get(USER_DATA_STATE)
        
        if user_state == BOOKING_PROCESS:
            await self.handle_booking_process(update, context)
        else:
            # Handle as question
            await self.handle_question(update, context)
    
    async def handle_booking_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle booking process steps"""
        booking_data = context.user_data.get(USER_DATA_BOOKING, {})
        step = booking_data.get('step')
        text = update.message.text
        
        if step == 'select_date':
            # Parse date and time
            try:
                # Expected format: DD.MM.YYYY HH:MM
                appointment_datetime = datetime.strptime(text, '%d.%m.%Y %H:%M')
                appointment_datetime = timezone.make_aware(appointment_datetime)
                
                # Check if date is in the future
                if appointment_datetime <= timezone.now():
                    await update.message.reply_text(
                        "❌ Дата и время должны быть в будущем. Попробуйте еще раз:"
                    )
                    return
                
                # Create appointment
                user_id = str(update.effective_user.id)
                client = Client.objects.get(salon=self.salon, telegram_id=user_id)
                service = Service.objects.get(id=booking_data['service_id'])
                master = Master.objects.get(id=booking_data['master_id'])
                
                appointment = Appointment.objects.create(
                    salon=self.salon,
                    client=client,
                    service=service,
                    master=master,
                    scheduled_at=appointment_datetime,
                    price=service.price,
                    status='scheduled'
                )
                
                success_message = f"""
✅ Запись успешно создана!

🏪 Салон: {self.salon.name}
💇‍♀️ Услуга: {service.name}
👨‍💼 Мастер: {master.full_name}
📅 Дата: {appointment_datetime.strftime('%d.%m.%Y')}
🕐 Время: {appointment_datetime.strftime('%H:%M')}
💰 Цена: {service.price} руб.
⏱ Длительность: {service.duration_minutes} мин.

📞 Контакты салона:
📍 {self.salon.address}
📞 {self.salon.phone}

❗️ Пожалуйста, приходите вовремя!
                """
                
                await update.message.reply_text(success_message.strip())
                
                # Clear booking data
                context.user_data.clear()
                
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат даты и времени!\n\n"
                    "Используйте формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
                    "Например: 25.12.2024 14:30"
                )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Ошибка при создании записи: {str(e)}"
                )
                context.user_data.clear()
    
    async def handle_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user questions using OpenAI"""
        user_question = update.message.text
        
        # Simple responses for common questions
        if any(word in user_question.lower() for word in ['цена', 'стоимость', 'сколько']):
            await self.show_services(update, context)
            return
        
        if any(word in user_question.lower() for word in ['адрес', 'где', 'находится']):
            await self.contact_info(update, context)
            return
        
        if any(word in user_question.lower() for word in ['время', 'часы', 'работа']):
            await self.contact_info(update, context)
            return
        
        if any(word in user_question.lower() for word in ['записаться', 'запись', 'записать']):
            await self.book_appointment(update, context)
            return
        
        # Default response
        await update.message.reply_text(
            f"Спасибо за ваш вопрос! 😊\n\n"
            f"Я могу помочь вам:\n"
            f"📅 Записаться на услугу - /book\n"
            f"📋 Посмотреть услуги - /services\n"
            f"📞 Узнать контакты - /contact\n\n"
            f"Если у вас есть специальные вопросы, свяжитесь с нами по телефону:\n"
            f"📞 {self.salon.phone}"
        )
    
    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle contact sharing"""
        contact = update.message.contact
        user_id = str(update.effective_user.id)
        
        try:
            client = Client.objects.get(salon=self.salon, telegram_id=user_id)
            client.phone = contact.phone_number
            client.save()
            
            await update.message.reply_text(
                f"✅ Номер телефона обновлен: {contact.phone_number}\n\n"
                f"Теперь мы сможем связаться с вами по поводу записей."
            )
        except Client.DoesNotExist:
            await update.message.reply_text(
                "❌ Ошибка обновления номера телефона. Используйте /start для регистрации."
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


# Global client bot instances
client_bot_instances: Dict[str, SalonClientBot] = {}


def get_or_create_client_bot(salon: Salon) -> SalonClientBot:
    """Get or create client bot instance for salon"""
    if not salon.telegram_bot_token:
        raise ValueError("Salon has no Telegram bot token")
    
    salon_id = str(salon.id)
    
    if salon_id not in client_bot_instances:
        client_bot_instances[salon_id] = SalonClientBot(salon)
    
    return client_bot_instances[salon_id]


async def start_client_bot_for_salon(salon: Salon):
    """Start client bot for a specific salon"""
    try:
        bot = get_or_create_client_bot(salon)
        await bot.run()
        logger.info(f"Started client bot for salon {salon.name}")
    except Exception as e:
        logger.error(f"Error starting client bot for salon {salon.name}: {str(e)}")


async def stop_client_bot_for_salon(salon: Salon):
    """Stop client bot for a specific salon"""
    try:
        salon_id = str(salon.id)
        if salon_id in client_bot_instances:
            bot = client_bot_instances[salon_id]
            await bot.stop()
            del client_bot_instances[salon_id]
            logger.info(f"Stopped client bot for salon {salon.name}")
    except Exception as e:
        logger.error(f"Error stopping client bot for salon {salon.name}: {str(e)}")


async def start_all_client_bots():
    """Start client bots for all salons with tokens"""
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def get_salons():
        return list(Salon.objects.exclude(telegram_bot_token__isnull=True).exclude(telegram_bot_token=''))
    
    salons = await get_salons()
    
    for salon in salons:
        try:
            await start_client_bot_for_salon(salon)
        except Exception as e:
            logger.error(f"Error starting client bot for salon {salon.name}: {str(e)}") 