from rest_framework import serializers
from .models import Order, OrderItem, PickupFulfillment, Reservation
from utils.paymentConstants import OrderStatus
from users.serializers import UserSerializer
from products.serializers import ProductSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for displaying order items"""
    product = ProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product', 'quantity', 'price', 'total_price']
        read_only_fields = ['id', 'total_price']

    def get_total_price(self, obj):
        return obj.get_total_price()

class OrderItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating order items"""
    
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price']
        
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value


class OrderItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order items"""
    
    class Meta:
        model = OrderItem
        fields = ['quantity']
        
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value


class ReservationSerializer(serializers.ModelSerializer):
    """Serializer for order reservations"""
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'product', 'quantity', 'status', 'expires_at', 'created_at']
        read_only_fields = ['id', 'created_at', 'expires_at']


class PickupFulfillmentSerializer(serializers.ModelSerializer):
    """Serializer for pickup fulfillment"""
    picked_by = UserSerializer(read_only=True)
    completed_by = UserSerializer(read_only=True)
    display_address = serializers.SerializerMethodField()

    class Meta:
        model = PickupFulfillment
        fields = [
            'id',
            'order',
            'location',
            'display_address',
            'status',
            'picked_at',
            'picked_by',
            'completed_at',
            'completed_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'picked_at',
            'picked_by',
            'completed_at',
            'completed_by',
        ]

    def get_display_address(self, obj):
        return obj.get_display_address()


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for displaying orders with full details"""
    user = UserSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    # reservations = ReservationSerializer(many=True, read_only=True)
    payment = serializers.SerializerMethodField()
    effective_status = serializers.SerializerMethodField()
    fulfillment_type = serializers.SerializerMethodField()
    fulfillment = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'order_id',
            'user',
            'status',
            'effective_status',
            'total_amount',
            'created_at',
            'items',
            # 'reservations',
            'payment',
            'approved',
            'is_pickup',
            'fulfillment_type',
            'fulfillment',
            'marked_for_review',
        ]
        read_only_fields = [
            'id',
            'order_id',
            'status',
            'effective_status',
            'total_amount',
            'created_at',
            'payment',
            'fulfillment_type',
            'fulfillment',
        ]

    def get_payment(self, obj):
        from payments.serializers import PaymentSerializer
        payment = obj.get_payment()
        if payment:
            return PaymentSerializer(payment).data
        return None

    def get_effective_status(self, obj):
        return obj.effective_status

    def get_fulfillment_type(self, obj):
        return obj.fulfillment_type

    def get_fulfillment(self, obj):
        return obj.fulfillment


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed order information"""
    user = UserSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    #reservations = ReservationSerializer(many=True, read_only=True)
    payment = serializers.SerializerMethodField()
    effective_status = serializers.SerializerMethodField()
    fulfillment_type = serializers.SerializerMethodField()
    fulfillment = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'order_id',
            'user',
            'status',
            'effective_status',
            'total_amount',
            'created_at',
            'items',
            #reservations',
            'payment',
            'approved',
            'is_pickup',
            'fulfillment_type',
            'fulfillment',
            'marked_for_review',
        ]
        read_only_fields = [
            'id',
            'order_id',
            'user',
            'status',
            'effective_status',
            'total_amount',
            'created_at',
            'payment',
            'fulfillment_type',
            'fulfillment',
            'marked_for_review',
        ]

    def get_payment(self, obj):
        from payments.serializers import PaymentSerializer
        payment = obj.get_payment()
        if payment:
            return PaymentSerializer(payment).data
        return None

    def get_effective_status(self, obj):
        return obj.effective_status

    def get_fulfillment_type(self, obj):
        return obj.fulfillment_type

    def get_fulfillment(self, obj):
        return obj.fulfillment


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order status (Fulfillment status)"""
    def get_combined_choices():
        # Combined choices for both delivery and pickup fulfillments
        delivery_choices = [
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("picked", "Picked"),
            ("shipped", "Shipped"),
            ("delivered", "Delivered"),
            ('cancelled', 'Cancelled'),
        ]
        pickup_choices = [
            ('ready', 'Ready for Pickup'),
            ('completed', 'Completed'),
        ]
        # Use a dict to ensure unique keys
        all_choices = {k: v for k, v in delivery_choices + pickup_choices}
        return list(all_choices.items())

    status = serializers.ChoiceField(
        choices=get_combined_choices(),
        help_text="New fulfillment status"
    )


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new orders"""
    
    class Meta:
        model = Order
        fields = ['is_pickup', 'approved']
        read_only_fields = ['approved']
