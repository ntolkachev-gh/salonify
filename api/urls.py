from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    UserViewSet, SalonViewSet, MasterViewSet, ServiceViewSet,
    ClientViewSet, AppointmentViewSet, DocumentViewSet, PostViewSet, EmbeddingViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'salons', SalonViewSet, basename='salon')
router.register(r'masters', MasterViewSet, basename='master')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'posts', PostViewSet, basename='post')
router.register(r'embeddings', EmbeddingViewSet, basename='embedding')

urlpatterns = [
    # JWT Authentication
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # API endpoints
    path('', include(router.urls)),
] 