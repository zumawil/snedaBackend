from .models import Product, Category, ProductImage
from rest_framework import serializers 

class ProductImageSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ProductImage
        fields = ['image', 'product', 'alt_text']



class ProductSerializer(serializers.ModelSerializer):

    images = ProductImageSerializer(many=True, read_only=True)
    category = serializers.SlugRelatedField(
        read_only="true",
        slug_field ='name'
    )
    
    class Meta:
        model = Product
        fields = ['name', 'category', 'description',
                  'price', 'stock', 'created_at', 'updated_at',
                  'images']
        
    

class CategorySerializer(serializers.ModelSerializer):

    products = ProductSerializer(read_only=True, many=True)
    class Meta:
        model = Category
        fields = ['name', 'description', 'products']


