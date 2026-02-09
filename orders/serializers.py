from rest_framework import serializers
from .models import Order, OrderItem
from users.serializers import UserSerializer
from products.serializers import ProductSerializer

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

    class Meta:
        model = Order
        fields = ['id', 'status','total_amount', 'created_at', 'items', 'payment', 'shipping']
        read_only_fields = ['total_amount', 'payment', 'created_at']

    def get_shipping(self, obj):
        from shipping.serializers import ShippingSerializer
        shipping = getattr(obj, 'shipping', None)
        if shipping:
            return ShippingSerializer(shipping).data
        return None

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
        choices=['pending', 'shipped', 'delivered', 'cancelled'],
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
        fields = ['id', 'total_amount','payment',
         'created_at', 'effective_status', 
                  'user',
                  'fulfillment_status']
        read_only_fields = ['total_amount','payment', 'created_at', 
                            'effective_status', 'user', 
                            'fulfillment_status']