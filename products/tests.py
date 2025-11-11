from django.test import TestCase
from rest_framework.test import APITestCase
from .models import Product, Category, ProductImage
from .serializers import ProductSerializer, CategorySerializer, ProductImageSerializer

class SerializerTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Test Category", description="Test Description")
        self.product = Product.objects.create(
            name="Test Product",
            category=self.category,
            description="Test Product Description",
            price=10.00,
            stock=5
        )
        self.product_image = ProductImage.objects.create(
            product=self.product,
            alt_text="Test Alt Text"
        )

    def test_product_serializer(self):
        serializer = ProductSerializer(self.product)
        data = serializer.data
        self.assertEqual(data['name'], self.product.name)
        self.assertEqual(data['category'], self.product.category.id)
        self.assertEqual(data['description'], self.product.description)
        self.assertEqual(float(data['price']), float(self.product.price))
        self.assertEqual(data['stock'], self.product.stock)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_category_serializer(self):
        serializer = CategorySerializer(self.category)
        data = serializer.data
        self.assertEqual(data['name'], self.category.name)
        self.assertEqual(data['description'], self.category.description)

    def test_product_image_serializer(self):
        serializer = ProductImageSerializer(self.product_image)
        data = serializer.data
        self.assertEqual(data['product'], self.product_image.product.id)
        self.assertEqual(data['alt_text'], self.product_image.alt_text)
        self.assertIn('image', data)
