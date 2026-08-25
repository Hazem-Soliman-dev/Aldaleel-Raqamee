from rest_framework import viewsets, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from common.permissions import IsAdminOrReadOnly
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products and stock levels (US-001 / TASK-001..TASK-005).
    - Admins (is_staff=True): Full access and can see all products (active + inactive).
    - Customers / Anonymous: Read-only access and ONLY see active products (is_active=True).
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['id', 'name', 'price', 'stock_quantity', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user and (user.is_staff or user.is_superuser):
            return Product.objects.all()
        # Customers and guests only see active products
        return Product.objects.filter(is_active=True)

    def perform_destroy(self, instance):
        """
        Soft-delete product by setting is_active=False (TASK-002 soft delete).
        """
        instance.soft_delete()
