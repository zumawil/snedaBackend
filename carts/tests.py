from django.test import TestCase
from rest_framework.test import APITestCase
from .models import Cart, CartItem
from .serializer import CartSerializer, CartItemSerializer
from users.models import CustomUser
from products.models import Product, Category

class CartModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email="test@example.com", password="password")
        self.category = Category.objects.create(name="Test Category", description="Test Description")
        self.product = Product.objects.create(
            name="Test Product",
            category=self.category,
            description="Test Product Description",
            price=10.00,
            stock=5
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )

    def test_cart_str(self):
        self.assertEqual(str(self.cart), f"Cart of {self.user.email}")

    def test_cart_total_items(self):
        self.assertEqual(self.cart.total_items(), 2)

    def test_cart_item_str(self):
        self.assertEqual(str(self.cart_item), f"2 of {self.product.name} in cart of {self.user.email}")

    def test_cart_item_get_total_price(self):
        self.assertEqual(self.cart_item.get_total_price(), 20.00)

class SerializerTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email="test@example.com", password="password")
        self.category = Category.objects.create(name="Test Category", description="Test Description")
        self.product = Product.objects.create(
            name="Test Product",
            category=self.category,
            description="Test Product Description",
            price=10.00,
            stock=5
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )

    def test_cart_serializer(self):
        serializer = CartSerializer(self.cart)
        data = serializer.data
        self.assertEqual(data['id'], self.cart.id)
        self.assertIn('created_at', data)
        self.assertEqual(data['user']['email'], self.user.email)

    def test_cart_item_serializer(self):
        serializer = CartItemSerializer(self.cart_item)
        data = serializer.data
        self.assertEqual(data['id'], self.cart_item.id)
        self.assertEqual(data['quantity'], 2)
        self.assertEqual(data['product']['id'], self.product.id)
        self.assertEqual(data['id'], self.cart.id)
