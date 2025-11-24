from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'order', 'amount', 'method', 'status', 'transaction_id', 'date_created']
        read_only_fields = ['id', 'date_created']