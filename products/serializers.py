from .models import (
    Product, Category, 
    ProductImage, HSCode, 
    ProductGroup, Brand, ProductDescription)
from rest_framework import serializers 
from reviews.serializers import ReviewsSerializer

class HSCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HSCode
        fields = ['id', 'code']

class ProductGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductGroup
        fields = ['id', 'name']

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name']

class ProductDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDescription
        fields = ['id', 'description']

class ProductImageSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ProductImage 
        fields = ['id','image', 'product', 'alt_text']

class ProductImageCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductImage
        fields = ['image', 'product', 'alt_text']

# serializer for creating and updating products
class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    images = ProductImageCreateSerializer(many=True, read_only=True)
    product_group = ProductGroupSerializer(read_only=True)
    description = ProductDescriptionSerializer(read_only=True)
    hs_code = HSCodeSerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    class Meta:
        model = Product
        fields = [
                    'item_no', 
                    'product_group', 'description',
                    'hs_code', 'gtin', 'height',
                    'width', 'length', 'weight',
                    'box_qty', 'inventory_qty', 
                    'gross_price', 'brand', 
                    'images'
                ]

#  serializer for retrieving product details
class ProductSerializer(serializers.ModelSerializer):
    reviews = ReviewsSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    product_group = ProductGroupSerializer(read_only=True)
    description = ProductDescriptionSerializer(read_only=True)
    hs_code = HSCodeSerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    class Meta:
        model = Product
        fields = ['id','item_no', 'product_group', 'description',
                  'hs_code', 'gtin', 'height', 'width', 'length', 'weight',
                  'box_qty', 'inventory_qty', 'gross_price', 'brand',
                  'created_at', 'updated_at',
                  'images', 'reviews']
    

class ProductImageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['image', 'product', 'alt_text']

class ProductCreateUpdateSerializer(serializers.ModelSerializer):   

    class Meta:
        model = Product
        fields = ['name', 'category', 'description',
                  'price', 'stock']
    
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

    

