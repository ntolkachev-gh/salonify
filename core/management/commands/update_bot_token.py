from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Update bot token for admin user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--token',
            type=str,
            help='Telegram bot token',
        )
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username to update (default: admin)',
        )

    def handle(self, *args, **options):
        token = options.get('token')
        username = options.get('username')
        
        if not token:
            self.stdout.write(
                self.style.ERROR('Token is required. Use --token argument.')
            )
            return
        
        try:
            user = User.objects.get(username=username)
            user.telegram_bot_token = token
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Updated user {user.username} with bot token')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Bot token: {user.telegram_bot_token[:20]}...')
            )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User {username} not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {e}')
            ) 