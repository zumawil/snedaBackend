from rest_framework import serializers
from .models import Reviews
from products.models import Product
from users.models import CustomUser as User


class ReviewsSerializer(serializers.ModelSerializer):

    user = serializers.CharField(source='user.email', read_only=True)

    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )

    class Meta:
        model = Reviews
        fields = ['id', 'user', 'product', 'content', 'rating', 'date_created']
        read_only_fields = ['id', 'date_created']

    def create(self, validated_data):
        # attach user to the validated data
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
