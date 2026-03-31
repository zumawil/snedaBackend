from rest_framework import serializers
from .models import Shipping
from users.models import CustomUser as User

class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]

class ShippingSerializer(serializers.ModelSerializer):
    order_id = serializers.SerializerMethodField()
    picked_by = UserMinimalSerializer(read_only=True)
    delivered_by = UserMinimalSerializer(read_only=True)

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
            "updated_at",
            "picked_at",
            "picked_by",
            "delivered_at",
            "delivered_by",
        ]
        read_only_fields = [
            "date_created",
            "updated_at",
            "picked_at",
            "picked_by",
            "delivered_at",
            "delivered_by",
        ]

    