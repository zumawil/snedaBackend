from rest_framework import serializers
from .models import Order, OrderItem
from users.serializers import UserSerializer
from products.serializers import ProductSerializer
from utils.paymentConstants import OrderStatus

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id','order', 'product', 'quantity', 'price', 'total_price']

    def get_total_price(self, obj):
        return obj.get_total_price()

class OrderItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating order items with proper OpenAPI schema documentation"""
    
    class Meta:
        model = OrderItem
        fields = ['order', 'product', 'quantity']
        
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

class OrderItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order items with proper OpenAPI schema documentation"""
    
    class Meta:
        model = OrderItem
        fields = ['quantity']
        
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

class OrderSerializer(serializers.ModelSerializer):
    # user = UserSerializer(read_only=True)
    items =  OrderItemSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()
    shipping = serializers.SerializerMethodField()
    fulfillment = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 
                'order_id', 
                'status',
                'total_amount', 
                'created_at', 
                'items', 
                'payment', 
                'shipping', 
                'approved',
                'shipping_address',
                'fulfillment',
                'marked_for_review'
        ]
        read_only_fields = ['total_amount', 'payment', 'created_at', 'marked_for_review']

    def get_shipping(self, obj):
        from shipping.serializers import ShippingSerializer
        shipping = getattr(obj, 'shipping', None)
        # For production-grade, we only return shipping record if it's NOT a pickup
        # and if the record actually exists.
        if shipping and not obj.is_pickup:
            return ShippingSerializer(shipping).data
        return None

    def get_fulfillment(self, obj):
        return {
            "type": obj.fulfillment_type,
            "is_pickup": obj.is_pickup,
            "pickup_location": obj.pickup_location,
            "display_address": obj.fulfillment_display_address
        }

    def get_status(self, obj):
        # expose the effective status derived from shipping when present
        return obj.effective_status

    def get_payment(self, obj):
        from payments.serializers import PaymentSerializer

        payment = obj.get_payment()
        if payment:
            return PaymentSerializer(payment).data.get('status')
        return None

class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order status with proper OpenAPI schema documentation"""
    status = serializers.ChoiceField(
        choices=[OrderStatus.PENDING, OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CANCELLED],
        help_text="New order status"
    )

class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order details with proper OpenAPI schema documentation"""

    """
        returns serialized data for order details
        without the items in the order
    """
    effective_status = serializers.SerializerMethodField()
    # is_cancellable = serializers.SerializerMethodField()
    fulfillment_status = serializers.ReadOnlyField(source='get_fulfillment_status')
    
    payment = serializers.SerializerMethodField()

    def get_payment(self, obj):
        from payments.serializers import PaymentSerializer

        payment = obj.get_payment()
        if payment:
            return PaymentSerializer(payment).data.get('status')
        return None

    def get_effective_status(self, obj):
        return obj.effective_status

    # def get_is_cancellable(self, obj):
    #     return obj.is_cancellable
    
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'order_id', 'total_amount','payment',
         'created_at', 'effective_status', 
                  'user', 'marked_for_review',
                  'fulfillment_status']
        read_only_fields = ['total_amount','payment', 'created_at', 
                            'effective_status', 'user', 'marked_for_review',
                            'fulfillment_status']