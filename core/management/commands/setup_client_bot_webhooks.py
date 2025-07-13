from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Salon
import requests
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Setup webhooks for salon client bots'

    def add_arguments(self, parser):
        parser.add_argument(
            '--salon-id',
            type=int,
            help='Setup webhook for specific salon ID'
        )
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Remove webhooks instead of setting them'
        )

    def handle(self, *args, **options):
        salon_id = options.get('salon_id')
        remove = options.get('remove', False)
        
        if salon_id:
            try:
                salon = Salon.objects.get(id=salon_id)
                salons = [salon]
            except Salon.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Salon with ID {salon_id} not found')
                )
                return
        else:
            salons = Salon.objects.exclude(
                telegram_bot_token__isnull=True
            ).exclude(telegram_bot_token='')
        
        for salon in salons:
            if remove:
                self.remove_webhook(salon)
            else:
                self.setup_webhook(salon)

    def setup_webhook(self, salon):
        """Setup webhook for salon client bot"""
        if not salon.telegram_bot_token:
            self.stdout.write(
                self.style.WARNING(f'Salon {salon.name} has no bot token')
            )
            return
        
        webhook_url = f"https://salonify-app-3cd2419b7b71.herokuapp.com/telegram/webhook/{salon.telegram_bot_token}/"
        
        url = f"https://api.telegram.org/bot{salon.telegram_bot_token}/setWebhook"
        data = {
            'url': webhook_url,
            'allowed_updates': ['message', 'callback_query']
        }
        
        try:
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get('ok'):
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Webhook set for salon {salon.name}: {webhook_url}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to set webhook for salon {salon.name}: {result.get("description")}'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error setting webhook for salon {salon.name}: {str(e)}'
                )
            )

    def remove_webhook(self, salon):
        """Remove webhook for salon client bot"""
        if not salon.telegram_bot_token:
            self.stdout.write(
                self.style.WARNING(f'Salon {salon.name} has no bot token')
            )
            return
        
        url = f"https://api.telegram.org/bot{salon.telegram_bot_token}/deleteWebhook"
        
        try:
            response = requests.post(url)
            result = response.json()
            
            if result.get('ok'):
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Webhook removed for salon {salon.name}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to remove webhook for salon {salon.name}: {result.get("description")}'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error removing webhook for salon {salon.name}: {str(e)}'
                )
            ) 