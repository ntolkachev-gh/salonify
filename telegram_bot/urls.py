from django.urls import path
from . import views

urlpatterns = [
    path('webhook/<str:bot_token>/', views.webhook, name='telegram_webhook'),
    path('start_bot/', views.start_bot, name='start_bot'),
    path('stop_bot/', views.stop_bot, name='stop_bot'),
] 