from celery import shared_task
from django.utils import timezone
from django.conf import settings
import openai
import logging
from datetime import timedelta
import json
import requests
from typing import List, Dict

from .models import Document, Embedding, Appointment, Post, Salon, Client

logger = logging.getLogger(__name__)


@shared_task
def generate_document_embeddings(document_id: str):
    """Generate embeddings for a document using OpenAI API"""
    try:
        document = Document.objects.get(id=document_id)
        salon = document.salon
        
        # Get OpenAI API key from user settings
        openai_api_key = salon.user.openai_api_token
        if not openai_api_key:
            logger.error(f"No OpenAI API key found for user {salon.user.username}")
            return
        
        # Configure OpenAI client
        openai.api_key = openai_api_key
        
        # Read document content
        content = read_document_content(document)
        if not content:
            logger.error(f"Could not read content from document {document.id}")
            return
        
        # Split content into chunks (max 8000 characters per chunk)
        chunks = split_text_into_chunks(content, max_length=8000)
        
        # Delete existing embeddings for this document
        Embedding.objects.filter(document=document).delete()
        
        # Generate embeddings for each chunk
        for index, chunk in enumerate(chunks):
            try:
                response = openai.Embedding.create(
                    model="text-embedding-ada-002",
                    input=chunk
                )
                
                embedding_vector = response['data'][0]['embedding']
                
                # Save embedding to database
                Embedding.objects.create(
                    document=document,
                    content_chunk=chunk,
                    embedding_vector=embedding_vector,
                    chunk_index=index
                )
                
                logger.info(f"Generated embedding for chunk {index} of document {document.id}")
                
            except Exception as e:
                logger.error(f"Error generating embedding for chunk {index}: {str(e)}")
                continue
        
        logger.info(f"Completed embedding generation for document {document.id}")
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
    except Exception as e:
        logger.error(f"Error in generate_document_embeddings: {str(e)}")


@shared_task
def send_appointment_reminders():
    """Send appointment reminders to clients"""
    try:
        # Get appointments scheduled for the next hour
        now = timezone.now()
        one_hour_later = now + timedelta(hours=1)
        
        appointments = Appointment.objects.filter(
            scheduled_at__gte=now,
            scheduled_at__lte=one_hour_later,
            status='planned'
        ).select_related('client', 'service', 'master', 'salon')
        
        for appointment in appointments:
            try:
                send_telegram_reminder(appointment)
                logger.info(f"Sent reminder for appointment {appointment.id}")
            except Exception as e:
                logger.error(f"Error sending reminder for appointment {appointment.id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in send_appointment_reminders: {str(e)}")


@shared_task
def send_post(post_id: str):
    """Send a scheduled post"""
    try:
        post = Post.objects.get(id=post_id)
        salon = post.salon
        
        # Get bot token from user settings
        bot_token = salon.user.telegram_bot_token
        if not bot_token:
            post.status = 'error'
            post.error_message = 'No Telegram bot token configured'
            post.save()
            return
        
        # Send post via Telegram bot
        success = send_telegram_post(bot_token, post)
        
        if success:
            post.status = 'sent'
            post.published_at = timezone.now()
            post.error_message = ''
        else:
            post.status = 'error'
            post.error_message = 'Failed to send post'
        
        post.save()
        logger.info(f"Processed post {post.id} with status {post.status}")
        
    except Post.DoesNotExist:
        logger.error(f"Post {post_id} not found")
    except Exception as e:
        logger.error(f"Error in send_post: {str(e)}")


@shared_task
def process_scheduled_posts():
    """Process all scheduled posts that are due"""
    try:
        now = timezone.now()
        
        # Get posts scheduled for now or earlier
        posts = Post.objects.filter(
            scheduled_at__lte=now,
            status='scheduled'
        )
        
        for post in posts:
            send_post.delay(str(post.id))
            
        logger.info(f"Queued {posts.count()} posts for processing")
        
    except Exception as e:
        logger.error(f"Error in process_scheduled_posts: {str(e)}")


@shared_task
def update_client_statistics():
    """Update client statistics based on completed appointments"""
    try:
        # Get all clients
        clients = Client.objects.all()
        
        for client in clients:
            completed_appointments = client.appointments.filter(status='completed')
            
            # Update statistics
            client.visits_count = completed_appointments.count()
            client.total_spent = sum(app.price for app in completed_appointments)
            
            # Update last visit date
            last_appointment = completed_appointments.order_by('-scheduled_at').first()
            if last_appointment:
                client.last_visit_date = last_appointment.scheduled_at
            
            client.save()
            
        logger.info(f"Updated statistics for {clients.count()} clients")
        
    except Exception as e:
        logger.error(f"Error in update_client_statistics: {str(e)}")


def read_document_content(document: Document) -> str:
    """Read content from document based on its type"""
    try:
        if document.doc_type == 'TXT':
            with open(document.path_or_url, 'r', encoding='utf-8') as file:
                return file.read()
        
        elif document.doc_type == 'DOCX':
            from docx import Document as DocxDocument
            doc = DocxDocument(document.path_or_url)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        
        elif document.doc_type == 'GOOGLE_DOC':
            # For Google Docs, we would need to implement Google Docs API integration
            # For now, return empty string
            logger.warning(f"Google Docs integration not implemented for document {document.id}")
            return ""
        
        return ""
        
    except Exception as e:
        logger.error(f"Error reading document {document.id}: {str(e)}")
        return ""


def split_text_into_chunks(text: str, max_length: int = 8000) -> List[str]:
    """Split text into chunks of specified maximum length"""
    chunks = []
    current_chunk = ""
    
    sentences = text.split('. ')
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 2 <= max_length:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def send_telegram_reminder(appointment: Appointment):
    """Send Telegram reminder to client"""
    try:
        bot_token = appointment.salon.user.telegram_bot_token
        if not bot_token or not appointment.client.telegram_id:
            return
        
        message = f"""
🔔 Напоминание о записи

Салон: {appointment.salon.name}
Услуга: {appointment.service.name}
Мастер: {appointment.master.full_name}
Время: {appointment.scheduled_at.strftime('%d.%m.%Y %H:%M')}
Цена: {appointment.price} руб.

Ждем вас!
        """.strip()
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': appointment.client.telegram_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=data)
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error sending Telegram reminder: {str(e)}")
        return False


def send_telegram_post(bot_token: str, post: Post) -> bool:
    """Send post via Telegram bot"""
    try:
        # This would send to a channel or group
        # For now, we'll just log it
        logger.info(f"Sending post: {post.caption}")
        
        # In a real implementation, you would:
        # 1. Send to a Telegram channel
        # 2. Or send to subscribers
        # 3. Handle image uploads if image_url is provided
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending Telegram post: {str(e)}")
        return False


@shared_task
def search_embeddings(query: str, salon_id: str, limit: int = 10) -> List[Dict]:
    """Search for similar embeddings using vector similarity"""
    try:
        salon = Salon.objects.get(id=salon_id)
        openai_api_key = salon.user.openai_api_token
        
        if not openai_api_key:
            logger.error(f"No OpenAI API key found for salon {salon_id}")
            return []
        
        # Configure OpenAI
        openai.api_key = openai_api_key
        
        # Generate embedding for query
        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=query
        )
        
        query_embedding = response['data'][0]['embedding']
        
        # Get all embeddings for this salon
        embeddings = Embedding.objects.filter(
            document__salon=salon
        ).select_related('document')
        
        # Calculate similarity scores
        results = []
        for embedding in embeddings:
            similarity = calculate_cosine_similarity(query_embedding, embedding.embedding_vector)
            results.append({
                'embedding_id': str(embedding.id),
                'document_name': embedding.document.name,
                'content_chunk': embedding.content_chunk,
                'similarity': similarity
            })
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:limit]
        
    except Exception as e:
        logger.error(f"Error in search_embeddings: {str(e)}")
        return []


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    import math
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(a * a for a in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0
    
    return dot_product / (magnitude1 * magnitude2) 