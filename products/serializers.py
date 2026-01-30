from .models import (
    Product, Category, 
    ProductImage, HSCode, 
    ProductGroup, Brand)
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

class ProductImageSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ProductImage 
        fields = ['id','url', 'product', 'alt_text']
        extra_kwargs = {'product': {'required': False}}

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class ProductCreateUpdateSerializer(serializers.ModelSerializer):   
    # For write operations, accept IDs
    product_group = serializers.PrimaryKeyRelatedField(
        queryset=ProductGroup.objects.all(),
        required=True
    )
   
    # Images are handled separately
    images = ProductImageSerializer(many=True, required=False)
    
    class Meta:
        model = Product
        fields = ['item_no', 'gtin', 'height',
                      'width', 'length', 'weight',
                  'box_qty', 'inventory_qty', 
                  'gross_price', 'brand', 
                  'images', 'category', 'product_group', 'hs_code']
    
    def create(self, validated_data):
        # Extract images if present
        images_data = validated_data.pop('images', [])
        
        # Create the product
        product = Product.objects.create(**validated_data)
        
        # Create product images
        for image_data in images_data:
            ProductImage.objects.create(
                product=product,
                url=image_data.get('url'),
                alt_text=image_data.get('alt_text', f"Image for {product.item_no}")
            )
        
        return product
    
    
    def to_representation(self, instance):
        # For read operations, return nested objects
        representation = super().to_representation(instance)
        representation['product_group'] = ProductGroupSerializer(instance.product_group).data
        representation['category'] = CategorySerializer(instance.category).data
        representation['hs_code'] = HSCodeSerializer(instance.hs_code).data
        representation['brand'] = BrandSerializer(instance.brand).data
        representation['images'] = ProductImageSerializer(instance.images.all(), many=True).data
        return representation

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', [])

        # Update scalar fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Add new images if provided
        for image_data in images_data:
            ProductImage.objects.create(
                product=instance,
                url=image_data.get('url'),
                alt_text=image_data.get('alt_text', f"Image for {instance.item_no}")
            )

        return instance


class ProductImageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['url', 'product', 'alt_text']

    def create(self, validated_data):
        return ProductImage.objects.create(**validated_data)


#  serializer for retrieving product details
class ProductSerializer(serializers.ModelSerializer):
    reviews = ReviewsSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    product_group = ProductGroupSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    hs_code = HSCodeSerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    
    class Meta:
        model = Product
        fields = ['item_no', 'product_group', 'category',
                  'hs_code', 'gtin', 'height', 'width', 'length', 'weight',
                  'box_qty', 'inventory_qty', 'gross_price', 'brand',
                  'created_at', 'updated_at',
                  'images', 'reviews']
