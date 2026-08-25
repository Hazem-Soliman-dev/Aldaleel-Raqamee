from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Order
from .serializers import OrderCreateSerializer, OrderDetailSerializer
from .services import OrderService

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing Orders and Stock Reservations.
    - POST /api/orders/ : Create order and reserve stock atomically (Customers & Admins)
    - GET  /api/orders/ : List all orders with pagination & filters
    - GET  /api/orders/{id}/ : Retrieve order details and items
    - POST /api/orders/{id}/cancel/ : Cancel order and release reserved stock
    """
    queryset = Order.objects.prefetch_related('items__product').all()
    serializer_class = OrderDetailSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['customer_name', 'id']
    ordering_fields = ['id', 'created_at', 'status']
    ordering = ['-created_at']

    def create(self, request, *args, **kwargs):
        """
        Create order and reserve stock atomically (US-002).
        If customer is logged in and customer_name is omitted, defaults to username.
        """
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if not data.get('customer_name') and request.user and request.user.is_authenticated:
            data['customer_name'] = request.user.get_full_name() or request.user.username

        serializer = OrderCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        order = OrderService.create_order(
            customer_name=serializer.validated_data['customer_name'],
            items_data=serializer.validated_data['items']
        )

        order_detailed = Order.objects.prefetch_related('items__product').get(id=order.id)
        output_serializer = OrderDetailSerializer(order_detailed)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        Cancel a PENDING order and safely release reserved stock (US-003).
        """
        order = OrderService.cancel_order(order_id=pk)
        order_detailed = Order.objects.prefetch_related('items__product').get(id=order.id)
        output_serializer = OrderDetailSerializer(order_detailed)
        return Response(output_serializer.data, status=status.HTTP_200_OK)
