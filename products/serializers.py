from .models import Product, Category, ProductImage
from rest_framework import serializers 
from reviews.serializers import ReviewsSerializer

class ProductImageSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ProductImage
        fields = ['id','image', 'product', 'alt_text']



class ProductSerializer(serializers.ModelSerializer):

    reviews = ReviewsSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    category = serializers.SlugRelatedField(
        read_only="true",
        slug_field ='name'
    )
    
    class Meta:
        model = Product
        fields = ['id','name', 'category', 'description',
                  'price', 'stock', 'created_at', 'updated_at',
                  'images', 'reviews']
        
    

class CategorySerializer(serializers.ModelSerializer):
    # 
    # products = ProductSerializer(read_only=True, many=True)

    products_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Category
        fields = ['id','name', 'description','products_count']

    

