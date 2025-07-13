import asyncio
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from telegram_bot.bot import start_all_bots

User = get_user_model()


class Command(BaseCommand):
    help = 'Start all Telegram bots for users with bot tokens'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting all Telegram bots...'))
        
        try:
            # Run the async function
            asyncio.run(start_all_bots())
            self.stdout.write(self.style.SUCCESS('All bots started successfully'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error starting bots: {str(e)}')
            ) 