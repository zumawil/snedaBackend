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

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    items =  OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = ['id','user', 'status','total_amount', 'created_at', 'items']
        read_only_fields = ['total_amount']

