from rest_framework import serializers
from .models import Reviews
from products.models import Product
from users.models import CustomUser as User


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name"]


class ReviewsSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = Reviews
        fields = ["id", "user", "product", "content", "rating", "date_created"]
        read_only_fields = ["id", "date_created"]

    def create(self, validated_data):
        # attach user to the validated data
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
