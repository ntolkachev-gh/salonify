import asyncio
import threading
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from telegram_bot.bot import start_all_bots

User = get_user_model()


class Command(BaseCommand):
    help = 'Запускает всех Telegram ботов'

    def handle(self, *args, **options):
        def run_bots():
            try:
                asyncio.run(start_all_bots())
                self.stdout.write(
                    self.style.SUCCESS('Все боты запущены успешно')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Ошибка запуска ботов: {str(e)}')
                )
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=run_bots)
        thread.daemon = True
        thread.start()
        thread.join()
        
        self.stdout.write('Команда завершена') 