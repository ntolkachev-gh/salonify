from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Salon
from telegram_bot.views import process_salon_client_update
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Test client bot processing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--salon-id',
            type=int,
            default=2,
            help='Salon ID to test (default: 2)'
        )

    def handle(self, *args, **options):
        salon_id = options.get('salon_id', 2)
        
        try:
            salon = Salon.objects.get(id=salon_id)
        except Salon.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Salon with ID {salon_id} not found')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Testing salon: {salon.name}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Bot token: {salon.telegram_bot_token[:20]}...')
        )
        
        # Create test update data
        test_update_data = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 123456789,
                    "is_bot": False,
                    "first_name": "Test",
                    "last_name": "User",
                    "username": "testuser",
                    "language_code": "ru"
                },
                "chat": {
                    "id": 123456789,
                    "first_name": "Test",
                    "last_name": "User",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1640995200,
                "text": "/start"
            }
        }
        
        # Test different commands
        commands = ["/start", "/help", "/services", "/book", "/contact"]
        
        for command in commands:
            self.stdout.write(f'\nTesting command: {command}')
            test_update_data["message"]["text"] = command
            
            try:
                process_salon_client_update(salon, test_update_data)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {command} processed successfully')
                )
            except Exception as e:
                if "Chat not found" in str(e):
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ {command} processed successfully (Chat not found is expected for test)')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'❌ {command} failed: {str(e)}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Client bot test completed!')
        ) 