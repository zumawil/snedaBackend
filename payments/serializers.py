from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'order', 
                'amount', 'method', 'status',
                'date_created']
        read_only_fields = ['id', 'date_created']

class PaymentRetrySerializer(serializers.Serializer):
    """Serializer for payment retry requests with proper OpenAPI schema documentation"""
    order_id = serializers.IntegerField(help_text="ID of the order to retry payment for")
    
    def validate_order_id(self, value):
        from orders.models import Order
        try:
            order = Order.objects.get(id=value)
            # Check if order belongs to user
            if order.user != self.context['request'].user:
                raise serializers.ValidationError("You can only retry payments for your own orders.")
            return value
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")