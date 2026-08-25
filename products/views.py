from rest_framework import viewsets, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products and stock levels (US-001 / TASK-001..TASK-005).
    Supports listing, creation, retrieval, full/partial update, and soft deletion.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['id', 'name', 'price', 'stock_quantity', 'created_at']
    ordering = ['-created_at']

    def perform_destroy(self, instance):
        """
        Soft-delete product by setting is_active=False (TASK-002 soft delete).
        """
        instance.soft_delete()
