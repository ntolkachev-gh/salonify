import requests
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup webhook for Telegram bot'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username (default: admin)',
        )
        parser.add_argument(
            '--url',
            type=str,
            default='https://salonify-app-3cd2419b7b71.herokuapp.com',
            help='Base URL for webhook',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        base_url = options.get('url')
        
        try:
            user = User.objects.get(username=username)
            
            if not user.telegram_bot_token:
                self.stdout.write(
                    self.style.ERROR(f'❌ User {username} has no bot token')
                )
                return
            
            # Setup webhook
            token = user.telegram_bot_token
            webhook_url = f"{base_url}/telegram/webhook/{token}/"
            
            # Set webhook
            api_url = f"https://api.telegram.org/bot{token}/setWebhook"
            data = {
                'url': webhook_url,
                'max_connections': 40,
                'allowed_updates': ['message', 'callback_query']
            }
            
            response = requests.post(api_url, json=data)
            result = response.json()
            
            if result.get('ok'):
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Webhook set successfully!')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Webhook URL: {webhook_url}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to set webhook: {result.get("description")}')
                )
            
            # Get bot info
            info_url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(info_url)
            result = response.json()
            
            if result.get('ok'):
                bot_info = result.get('result')
                self.stdout.write(
                    self.style.SUCCESS(f'🤖 Bot info:')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'   Name: {bot_info.get("first_name")}')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'   Username: @{bot_info.get("username")}')
                )
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User {username} not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {e}')
            ) 