import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
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
        
        # Get bot instance
        bot = get_or_create_bot(user)
        
        # Parse update
        update_data = json.loads(request.body)
        
        # Process update (this would be handled by the bot's update handler)
        # For now, just log it
        logger.info(f"Received update for user {user.username}: {update_data}")
        
        return JsonResponse({'status': 'ok'})
        
    except User.DoesNotExist:
        logger.error(f"Bot token {bot_token} not found")
        return JsonResponse({'error': 'Bot not found'}, status=404)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JsonResponse({'error': 'Internal error'}, status=500)


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