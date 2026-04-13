from rest_framework import serializers
from .models import Cart, CartItem
from users.serializers import UserSerializer, CartUserSerializer
from products.serializers import ProductSerializer

class CartItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()
    # product = ProductSerializer(read_only=True)
    product_item_no = serializers.CharField(
        source='product.item_no', 
        read_only=True
    )
    gross_price = serializers.DecimalField(
        source='product.gross_price',
        read_only=True,
        max_digits=10,
        decimal_places=2
    )
    available_stock = serializers.IntegerField(
        source='product.inventory_qty',
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = ['id', 
                  'quantity', 
                  'product_item_no', 
                  'gross_price',
                  'available_stock', 
                  'total_price']

    def get_total_price(self, obj):
        return obj.get_total_price()

class CartItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating cart items with proper OpenAPI schema documentation"""
    
    class Meta:
        model = CartItem
        fields = ['product', 'quantity']
        
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

class CartSerializer(serializers.ModelSerializer):
    user = CartUserSerializer(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    class Meta:
        model = Cart
        fields = ['id', 'created_at', 'user', 'items']

class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout request with proper OpenAPI schema documentation"""
    address = serializers.CharField(max_length=255, required=True, help_text="Shipping address")
    pickup = serializers.BooleanField(default=False, help_text="Whether this is a pickup order")
    
    def validate_address(self, value):
        if not value.strip():
            raise serializers.ValidationError("Address cannot be empty.")
        return value

class CheckoutResponseSerializer(serializers.Serializer):
    """Serializer for checkout response"""
    order = serializers.DictField()
    payment = serializers.DictField(required=False)
    payment_url = serializers.URLField(required=False)