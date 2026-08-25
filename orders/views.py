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
    - Admins: See all orders across all customers.
    - Authenticated Customers: Automatically isolated to ONLY see their own orders.
    - Guests / Anonymous: Can view their created order details or filter by customer_name.
    """
    serializer_class = OrderDetailSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['customer_name', 'id']
    ordering_fields = ['id', 'created_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.prefetch_related('items__product')
        if user and (user.is_staff or user.is_superuser):
            # Admins see all orders
            return queryset.all()
        elif user and user.is_authenticated:
            # Customers only see their own orders
            names = [user.username]
            if user.get_full_name():
                names.append(user.get_full_name())
            return queryset.filter(customer_name__in=names)
        
        # Guest / anonymous filtering
        customer_name = self.request.query_params.get('customer_name')
        if customer_name:
            return queryset.filter(customer_name=customer_name)
        return queryset.all()

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
