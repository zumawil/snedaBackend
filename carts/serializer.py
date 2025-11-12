from rest_framework import serializers
from .models import Cart, CartItem
from users.serializers import UserSerializer
from products.serializers import ProductSerializer

class CartItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()
    product = ProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'quantity', 'product', 'total_price']

    def get_total_price(self, obj):
        return obj.get_total_price()

class CartSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    class Meta:
        model = Cart
        fields = ['id', 'created_at', 'user', 'items']