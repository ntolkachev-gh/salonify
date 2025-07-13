from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models import Salon, Master, Service, Client, Appointment, Document, Post, Embedding

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'telegram_bot_token', 'openai_api_token', 'created_at', 'updated_at']
        read_only_fields = ['id', 'username', 'created_at', 'updated_at']


class SalonSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    masters_count = serializers.SerializerMethodField()
    services_count = serializers.SerializerMethodField()
    clients_count = serializers.SerializerMethodField()

    class Meta:
        model = Salon
        fields = ['id', 'user', 'name', 'address', 'phone', 'email', 'working_hours', 
                 'timezone', 'masters_count', 'services_count', 'clients_count', 
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_masters_count(self, obj):
        return obj.masters.filter(is_active=True).count()

    def get_services_count(self, obj):
        return obj.services.filter(is_active=True).count()

    def get_clients_count(self, obj):
        return obj.clients.count()


class MasterSerializer(serializers.ModelSerializer):
    salon = SalonSerializer(read_only=True)
    salon_id = serializers.UUIDField(write_only=True)
    services_count = serializers.SerializerMethodField()

    class Meta:
        model = Master
        fields = ['id', 'salon', 'salon_id', 'full_name', 'phone', 'telegram_id', 
                 'specialization', 'working_hours', 'is_active', 'services_count',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'salon', 'created_at', 'updated_at']

    def get_services_count(self, obj):
        return obj.services.filter(is_active=True).count()


class ServiceSerializer(serializers.ModelSerializer):
    salon = SalonSerializer(read_only=True)
    salon_id = serializers.UUIDField(write_only=True)
    master = MasterSerializer(read_only=True)
    master_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Service
        fields = ['id', 'salon', 'salon_id', 'master', 'master_id', 'name', 'description', 
                 'price', 'duration_minutes', 'category', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'salon', 'master', 'created_at', 'updated_at']

    def validate_master_id(self, value):
        if value:
            salon_id = self.initial_data.get('salon_id')
            if salon_id and not Master.objects.filter(id=value, salon_id=salon_id).exists():
                raise serializers.ValidationError("Master must belong to the same salon")
        return value


class ClientSerializer(serializers.ModelSerializer):
    salon = SalonSerializer(read_only=True)
    salon_id = serializers.UUIDField(write_only=True)
    upcoming_appointments = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['id', 'salon', 'salon_id', 'full_name', 'phone', 'telegram_id', 
                 'email', 'visits_count', 'last_visit_date', 'total_spent', 
                 'upcoming_appointments', 'created_at', 'updated_at']
        read_only_fields = ['id', 'salon', 'visits_count', 'last_visit_date', 
                           'total_spent', 'created_at', 'updated_at']

    def get_upcoming_appointments(self, obj):
        from django.utils import timezone
        upcoming = obj.appointments.filter(
            scheduled_at__gte=timezone.now(),
            status='planned'
        ).count()
        return upcoming


class AppointmentSerializer(serializers.ModelSerializer):
    salon = SalonSerializer(read_only=True)
    salon_id = serializers.UUIDField(write_only=True)
    client = ClientSerializer(read_only=True)
    client_id = serializers.UUIDField(write_only=True)
    service = ServiceSerializer(read_only=True)
    service_id = serializers.UUIDField(write_only=True)
    master = MasterSerializer(read_only=True)
    master_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'salon', 'salon_id', 'client', 'client_id', 'service', 'service_id', 
                 'master', 'master_id', 'scheduled_at', 'status', 'price', 'notes', 
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'salon', 'client', 'service', 'master', 'price', 
                           'created_at', 'updated_at']

    def validate(self, attrs):
        salon_id = attrs.get('salon_id')
        client_id = attrs.get('client_id')
        service_id = attrs.get('service_id')
        master_id = attrs.get('master_id')

        # Validate all entities belong to the same salon
        if not Client.objects.filter(id=client_id, salon_id=salon_id).exists():
            raise serializers.ValidationError("Client must belong to the same salon")
        
        if not Service.objects.filter(id=service_id, salon_id=salon_id).exists():
            raise serializers.ValidationError("Service must belong to the same salon")
        
        if not Master.objects.filter(id=master_id, salon_id=salon_id).exists():
            raise serializers.ValidationError("Master must belong to the same salon")

        return attrs


class DocumentSerializer(serializers.ModelSerializer):
    salon = SalonSerializer(read_only=True)
    salon_id = serializers.UUIDField(write_only=True)
    embeddings_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'salon', 'salon_id', 'name', 'doc_type', 'path_or_url', 
                 'description', 'tags', 'file_size', 'embeddings_count',
                 'uploaded_at', 'updated_at']
        read_only_fields = ['id', 'salon', 'uploaded_at', 'updated_at']

    def get_embeddings_count(self, obj):
        return obj.embeddings.count()

    def validate_salon_id(self, value):
        # Check document count limit
        if not self.instance:  # Only for new documents
            existing_count = Document.objects.filter(salon_id=value).count()
            from django.conf import settings
            if existing_count >= settings.MAX_DOCUMENTS_PER_SALON:
                raise serializers.ValidationError(
                    f"Maximum {settings.MAX_DOCUMENTS_PER_SALON} documents allowed per salon"
                )
        return value


class PostSerializer(serializers.ModelSerializer):
    salon = SalonSerializer(read_only=True)
    salon_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Post
        fields = ['id', 'salon', 'salon_id', 'caption', 'image_url', 'scheduled_at', 
                 'published_at', 'status', 'error_message', 'created_at', 'updated_at']
        read_only_fields = ['id', 'salon', 'published_at', 'status', 'error_message', 
                           'created_at', 'updated_at']

    def validate_scheduled_at(self, value):
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future")
        return value


class EmbeddingSerializer(serializers.ModelSerializer):
    document = DocumentSerializer(read_only=True)
    document_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Embedding
        fields = ['id', 'document', 'document_id', 'content_chunk', 'embedding_vector', 
                 'chunk_index', 'created_at']
        read_only_fields = ['id', 'document', 'created_at'] 