from .models import Product, Category, ProductImage
from rest_framework.serializers import ModelSerializer

class ProductSerializer(ModelSerializer):
    
    class Meta:
        model = Product
        fields = "__all__"

class CategorySerializer(ModelSerializer):
    
    class Meta:
        model = Category
        fields = "__all__"


class ProductImageSerializer(ModelSerializer):
    
    class Meta:
        model = ProductImage
        fields = "__all__"

