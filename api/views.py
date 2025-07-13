from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q

from core.models import Salon, Master, Service, Client, Appointment, Document, Post, Embedding
from .serializers import (
    UserSerializer, UserCreateSerializer, UserProfileSerializer,
    SalonSerializer, MasterSerializer, ServiceSerializer, ClientSerializer,
    AppointmentSerializer, DocumentSerializer, PostSerializer, EmbeddingSerializer
)
from .permissions import IsOwnerOrReadOnly, IsSalonOwner

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['retrieve', 'update', 'partial_update'] and self.get_object() == self.request.user:
            return UserProfileSerializer
        return UserSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get', 'put', 'patch'])
    def profile(self, request):
        """Get or update current user profile"""
        if request.method == 'GET':
            serializer = UserProfileSerializer(request.user)
            return Response(serializer.data)
        else:
            serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SalonViewSet(viewsets.ModelViewSet):
    serializer_class = SalonSerializer
    permission_classes = [IsAuthenticated, IsSalonOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['timezone']
    search_fields = ['name', 'address', 'phone', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Salon.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get salon statistics"""
        salon = self.get_object()
        today = timezone.now().date()
        
        stats = {
            'total_masters': salon.masters.filter(is_active=True).count(),
            'total_services': salon.services.filter(is_active=True).count(),
            'total_clients': salon.clients.count(),
            'total_appointments': salon.appointments.count(),
            'today_appointments': salon.appointments.filter(
                scheduled_at__date=today,
                status='planned'
            ).count(),
            'pending_appointments': salon.appointments.filter(
                status='planned',
                scheduled_at__gte=timezone.now()
            ).count(),
            'completed_appointments': salon.appointments.filter(status='completed').count(),
            'total_revenue': sum(
                appointment.price for appointment in salon.appointments.filter(status='completed')
            ),
            'documents_count': salon.documents.count(),
            'scheduled_posts': salon.posts.filter(status='scheduled').count(),
        }
        return Response(stats)


class MasterViewSet(viewsets.ModelViewSet):
    serializer_class = MasterSerializer
    permission_classes = [IsAuthenticated, IsSalonOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['salon', 'is_active', 'specialization']
    search_fields = ['full_name', 'phone', 'specialization']
    ordering_fields = ['full_name', 'specialization', 'created_at']
    ordering = ['full_name']

    def get_queryset(self):
        return Master.objects.filter(salon__user=self.request.user)

    def perform_create(self, serializer):
        salon_id = self.request.data.get('salon_id')
        salon = Salon.objects.get(id=salon_id, user=self.request.user)
        serializer.save(salon=salon)


class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated, IsSalonOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['salon', 'master', 'category', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'duration_minutes', 'created_at']
    ordering = ['category', 'name']

    def get_queryset(self):
        return Service.objects.filter(salon__user=self.request.user)

    def perform_create(self, serializer):
        salon_id = self.request.data.get('salon_id')
        salon = Salon.objects.get(id=salon_id, user=self.request.user)
        master_id = self.request.data.get('master_id')
        master = None
        if master_id:
            master = Master.objects.get(id=master_id, salon=salon)
        serializer.save(salon=salon, master=master)


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsSalonOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['salon']
    search_fields = ['full_name', 'phone', 'email']
    ordering_fields = ['full_name', 'last_visit_date', 'total_spent', 'created_at']
    ordering = ['-last_visit_date']

    def get_queryset(self):
        return Client.objects.filter(salon__user=self.request.user)

    def perform_create(self, serializer):
        salon_id = self.request.data.get('salon_id')
        salon = Salon.objects.get(id=salon_id, user=self.request.user)
        serializer.save(salon=salon)

    @action(detail=True, methods=['get'])
    def appointments(self, request, pk=None):
        """Get client's appointment history"""
        client = self.get_object()
        appointments = client.appointments.all().order_by('-scheduled_at')
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsSalonOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['salon', 'client', 'service', 'master', 'status']
    search_fields = ['client__full_name', 'service__name', 'master__full_name', 'notes']
    ordering_fields = ['scheduled_at', 'created_at']
    ordering = ['-scheduled_at']

    def get_queryset(self):
        return Appointment.objects.filter(salon__user=self.request.user)

    def perform_create(self, serializer):
        salon_id = self.request.data.get('salon_id')
        salon = Salon.objects.get(id=salon_id, user=self.request.user)
        client = Client.objects.get(id=self.request.data.get('client_id'), salon=salon)
        service = Service.objects.get(id=self.request.data.get('service_id'), salon=salon)
        master = Master.objects.get(id=self.request.data.get('master_id'), salon=salon)
        serializer.save(salon=salon, client=client, service=service, master=master)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark appointment as completed"""
        appointment = self.get_object()
        appointment.status = 'completed'
        appointment.save()
        
        # Update client statistics
        client = appointment.client
        client.visits_count += 1
        client.last_visit_date = timezone.now()
        client.total_spent += appointment.price
        client.save()
        
        return Response({'status': 'completed'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel appointment"""
        appointment = self.get_object()
        appointment.status = 'cancelled'
        appointment.save()
        return Response({'status': 'cancelled'})


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, IsSalonOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['salon', 'doc_type']
    search_fields = ['name', 'description', 'tags']
    ordering_fields = ['name', 'uploaded_at']
    ordering = ['-uploaded_at']

    def get_queryset(self):
        return Document.objects.filter(salon__user=self.request.user)

    def perform_create(self, serializer):
        salon_id = self.request.data.get('salon_id')
        salon = Salon.objects.get(id=salon_id, user=self.request.user)
        serializer.save(salon=salon)

    @action(detail=True, methods=['post'])
    def generate_embeddings(self, request, pk=None):
        """Generate embeddings for document"""
        document = self.get_object()
        # This will be handled by Celery task
        from core.tasks import generate_document_embeddings
        generate_document_embeddings.delay(document.id)
        return Response({'status': 'embeddings_generation_started'})


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated, IsSalonOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['salon', 'status']
    search_fields = ['caption']
    ordering_fields = ['scheduled_at', 'created_at']
    ordering = ['-scheduled_at']

    def get_queryset(self):
        return Post.objects.filter(salon__user=self.request.user)

    def perform_create(self, serializer):
        salon_id = self.request.data.get('salon_id')
        salon = Salon.objects.get(id=salon_id, user=self.request.user)
        serializer.save(salon=salon)

    @action(detail=True, methods=['post'])
    def send_now(self, request, pk=None):
        """Send post immediately"""
        post = self.get_object()
        # This will be handled by Celery task
        from core.tasks import send_post
        send_post.delay(post.id)
        return Response({'status': 'post_sending_started'})


class EmbeddingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmbeddingSerializer
    permission_classes = [IsAuthenticated, IsSalonOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['document', 'document__salon']
    search_fields = ['content_chunk']
    ordering_fields = ['chunk_index', 'created_at']
    ordering = ['document', 'chunk_index']

    def get_queryset(self):
        return Embedding.objects.filter(document__salon__user=self.request.user)

    @action(detail=False, methods=['post'])
    def search(self, request):
        """Search embeddings by similarity"""
        query = request.data.get('query')
        salon_id = request.data.get('salon_id')
        
        if not query or not salon_id:
            return Response(
                {'error': 'query and salon_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # This would implement vector similarity search
        # For now, return text-based search
        embeddings = self.get_queryset().filter(
            document__salon_id=salon_id,
            content_chunk__icontains=query
        )[:10]
        
        serializer = self.get_serializer(embeddings, many=True)
        return Response(serializer.data) 