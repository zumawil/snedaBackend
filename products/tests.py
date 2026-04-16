from django.test import TestCase
from rest_framework.test import APITestCase
from .models import (
    Product, Category, ProductImage, 
    ProductGroup, HSCode, Brand
)
from .serializers import (
    ProductSerializer, CategorySerializer, 
    ProductImageSerializer
)

class SerializerTests(APITestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Test Brand")
        self.group = ProductGroup.objects.create(name="Test Group")
        self.hscode = HSCode.objects.create(code="123456")
        self.category = Category.objects.create(name="Test Category")
        
        self.product = Product.objects.create(
            item_no="TEST-001",
            product_group=self.group,
            category=self.category,
            hs_code=self.hscode,
            brand=self.brand,
            inventory_qty=10,
            gross_price=100.00
        )
        self.product_image = ProductImage.objects.create(
            product=self.product,
            url="http://example.com/image.jpg",
            alt_text="Test Alt Text"
        )

    def test_product_serializer(self):
        serializer = ProductSerializer(self.product)
        data = serializer.data
        self.assertEqual(data['item_no'], self.product.item_no)
        self.assertIn('category', data)
        self.assertIn('product_group', data)
        self.assertIn('hs_code', data)
        self.assertIn('brand', data)
        self.assertEqual(float(data['gross_price']), float(self.product.gross_price))
        self.assertEqual(data['inventory_qty'], self.product.inventory_qty)
        self.assertEqual(data['available_stock'], self.product.available_stock)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
        self.assertIn('available_stock', data)

    def test_category_serializer(self):
        serializer = CategorySerializer(self.category)
        data = serializer.data
        self.assertEqual(data['name'], self.category.name)

    def test_product_image_serializer(self):
        serializer = ProductImageSerializer(self.product_image)
        data = serializer.data
        self.assertEqual(data['product'], self.product_image.product.item_no)
        self.assertEqual(data['alt_text'], self.product_image.alt_text)
        self.assertEqual(data['url'], self.product_image.url)
