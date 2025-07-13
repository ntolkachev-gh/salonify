import requests
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Test Telegram bot'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username (default: admin)',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        
        try:
            user = User.objects.get(username=username)
            
            if not user.telegram_bot_token:
                self.stdout.write(
                    self.style.ERROR(f'❌ User {username} has no bot token')
                )
                return
            
            token = user.telegram_bot_token
            
            # Get bot info
            info_url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(info_url)
            result = response.json()
            
            if result.get('ok'):
                bot_info = result.get('result')
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Bot is working!')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'🤖 Bot info:')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'   Name: {bot_info.get("first_name")}')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'   Username: @{bot_info.get("username")}')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'   ID: {bot_info.get("id")}')
                )
                
                # Get webhook info
                webhook_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
                response = requests.get(webhook_url)
                result = response.json()
                
                if result.get('ok'):
                    webhook_info = result.get('result')
                    self.stdout.write(
                        self.style.SUCCESS(f'🔗 Webhook info:')
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'   URL: {webhook_info.get("url")}')
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'   Has custom certificate: {webhook_info.get("has_custom_certificate")}')
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'   Pending update count: {webhook_info.get("pending_update_count")}')
                    )
                    
                    if webhook_info.get("last_error_date"):
                        self.stdout.write(
                            self.style.WARNING(f'⚠️ Last error: {webhook_info.get("last_error_message")}')
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(f'\n📱 To test the bot, go to: https://t.me/{bot_info.get("username")}')
                )
                
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Bot error: {result.get("description")}')
                )
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User {username} not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {e}')
            ) 