from rest_framework import serializers
from .models import Shipping

class ShippingSerializer(serializers.ModelSerializer):
    order_id = serializers.SerializerMethodField()

    def get_order_id(self, obj):
        return obj.order.id if obj.order else None

    class Meta:
        model = Shipping
        fields = [
            "pk",
            "order_id",
            "status",
            "tracking_number",
            "address",
            "date_created",
            "pickup",
            "pickup_location",
        ]

    