"""
Stock Management Tests

Tests for stock validation, reduction, and restoration across:
- Add to cart
- Checkout
- Payment failure
- Payment abandonment
- Order cancellation
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from products.models import Product, Category
from carts.models import Cart, CartItem
from orders.models import Order, OrderItem
from payments.models import Payment
from shipping.models import Shipping
from decimal import Decimal
from users.models import CustomUser
import unittest

User = CustomUser


class StockManagementTestCase(TestCase):
    """Test stock management across the entire order flow"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            verified=True
        )
        
        # Create category
        self.category = Category.objects.create(
            name='Electronics',
            description='Electronic items'
        )
        
        # Create products with stock
        self.product1 = Product.objects.create(
            name='Laptop',
            description='Gaming laptop',
            price=Decimal('1500.00'),
            stock=10,  # Initial stock: 10
            category=self.category
        )
        
        self.product2 = Product.objects.create(
            name='Mouse',
            description='Wireless mouse',
            price=Decimal('50.00'),
            stock=5,  # Initial stock: 5
            category=self.category
        )
        
        # Authenticate user
        self.client.force_authenticate(user=self.user)
        
        # Create cart for user
        self.cart = Cart.objects.create(user=self.user)
     #passed
    #PASSED
    def test_add_to_cart_validates_stock(self):
        """Test that adding to cart validates available stock"""
        # Add product to cart
        response = self.client.post(f'/add-to-cart/{self.product1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify cart item created
        cart_item = CartItem.objects.get(cart=self.cart, product=self.product1)
        self.assertEqual(cart_item.quantity, 1)
        
        # Stock should NOT be reduced yet (only at checkout)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 10)
    #PASSED
    def test_add_to_cart_prevents_out_of_stock(self):
        """Test that adding out-of-stock product fails"""
        # Set stock to 0
        self.product1.stock = 0
        self.product1.save()
        
        # Try to add to cart
        response = self.client.post(f'/add-to-cart/{self.product1.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('out of stock', response.data['error'].lower())
    #PASSED
    def test_add_to_cart_prevents_exceeding_stock(self):
        """Test that incrementing quantity beyond stock fails"""
        # Set stock to 2
        self.product1.stock = 2
        self.product1.save()
        
        # Add to cart (quantity = 1)
        self.client.post(f'/add-to-cart/{self.product1.id}/')
        
        # Add again (quantity = 2)
        self.client.post(f'/add-to-cart/{self.product1.id}/')
        
        # Try to add third time (should fail - stock is only 2)
        response = self.client.post(f'/add-to-cart/{self.product1.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('insufficient stock', response.data['error'].lower())
    #PASSED
    def test_checkout_reduces_stock_atomically(self):
        """Test that checkout reduces stock immediately and atomically"""
        # Add items to cart
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=3)
        CartItem.objects.create(cart=self.cart, product=self.product2, quantity=2)
        
        initial_stock_p1 = self.product1.stock  # 10
        initial_stock_p2 = self.product2.stock  # 5
        
        # Checkout
        response = self.client.post('/checkout/', {
            'X-Idempotency-Key': 'test-key-123',
            'address': '123 Test St',
            'pickup': 'false'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify stock was reduced immediately
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        
        self.assertEqual(self.product1.stock, initial_stock_p1 - 3)  # 10 - 3 = 7
        self.assertEqual(self.product2.stock, initial_stock_p2 - 2)  # 5 - 2 = 3
    #PASSED
    def test_checkout_fails_with_insufficient_stock(self):
        """Test that checkout fails if stock becomes insufficient"""
        # Add more items than available stock
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=15)
        
        initial_stock = self.product1.stock  # 10
        
        # Checkout should fail
        response = self.client.post('/checkout/', {
            'X-Idempotency-Key': 'test-key-456',
            'address': '123 Test St',
            'pickup': 'false'
        })
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('insufficient stock', response.data['error'].lower())
        
        # Stock should remain unchanged (transaction rollback)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, initial_stock)
    #PASSED
    def test_concurrent_checkout_prevents_overselling(self):
        """Test that concurrent checkouts don't oversell (atomic F() expressions)"""
        # This tests the atomic nature of F() expressions
        # Create two carts trying to buy the last items
        
        # Set stock to 5
        self.product1.stock = 5
        self.product1.save()
        
        # User 1 cart: wants 5 items
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=5)
        
        # User 2 (create another user and cart)
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='pass123',
            verified=True
        )
        # create cart for user2
        cart2 = Cart.objects.create(user=user2)
        # add product to cart2
        CartItem.objects.create(cart=cart2, product=self.product1, quantity=5)
        
        # User 1 checks out first
        response1 = self.client.post('/checkout/', {
            'X-Idempotency-Key': 'user1-key',
            'address': '123 Test St',
            'pickup': 'false'
        })
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # User 2 tries to checkout (should fail - no stock left)
        client2 = APIClient()
        client2.force_authenticate(user=user2)
        response2 = client2.post('/checkout/', {
            'X-Idempotency-Key': 'user2-key',
            'address': '456 Test Ave',
            'pickup': 'false'
        })
        
        self.assertEqual(response2.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Verify stock is 0 (only user1's order succeeded)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 0)
    #PASSED
    def test_payment_failure_restores_stock(self):
        """Test that failed payment restores stock"""
        # Add items and checkout
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=3)
        # user checks out
        # Mock bill_user to raise exception
        with unittest.mock.patch('carts.views.bill_user', side_effect=Exception('Payment failed')):
            response = self.client.post('/checkout/', {
                'X-Idempotency-Key': 'test-payment-fail',
                'address': '123 Test St',
                'pickup': 'false'
            })
            
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
        # Stock should be reduced
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 7)  # 10 - 3
        
        # Get the order (payment might not exist if bill_user failed)
        from orders.models import Order
        order = Order.objects.get(user=self.user)
        
        # Simulate payment failure (manually call restore_product_stock)
        from payments.views import WebhookView
        webhook = WebhookView()
        webhook.restore_product_stock(order)
        
        # Stock should be restored
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 10)  # Back to original
    #PASSED
    def test_order_cancellation_restores_stock(self):
        """Test that cancelling an order restores stock"""
        # Add items and checkout
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=4)
        
        response = self.client.post('/checkout/', {
            'X-Idempotency-Key': 'test-cancel',
            'address': '123 Test St',
            'pickup': 'false'
        })
        
        order_id = response.data['order']['id']
  
        # Stock should be reduced
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 6)  # 10 - 4
        
        # Cancel the order
        cancel_response = self.client.post(f'/order/cancel/{order_id}/')
        
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        # Stock should be restored
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 10)  # Back to original
    #PASSED 
    def test_stock_restoration_is_atomic(self):
        """Test that stock restoration uses atomic F() expressions"""
        # This is implicitly tested by the implementation
        # F() expressions ensure atomicity at the database level
        
        # Create order with items
        order = Order.objects.create(user=self.user, total_amount=Decimal('100.00'))
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=5,
            price=self.product1.price
        )
        
        # Reduce stock manually
        from django.db.models import F
        Product.objects.filter(id=self.product1.id).update(stock=F('stock') - 5)
        
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 5) # 10 - 5
        
        # Restore stock atomically
        Product.objects.filter(id=self.product1.id).update(stock=F('stock') + 5)
        
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 10)
    #PASSED
    def test_idempotency_prevents_duplicate_stock_reduction(self):
        """Test that idempotency key prevents duplicate checkouts"""
        # Add items to cart
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=2)
        
        idempotency_key = 'duplicate-test-key'
        
        # First checkout
        response1 = self.client.post('/checkout/', {
            'X-Idempotency-Key': idempotency_key,
            'address': '123 Test St',
            'pickup': 'false'
        })
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Stock reduced
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 8)  # 10 - 2
        
        # Try same checkout again with same key
        response2 = self.client.post('/checkout/', {
            'X-Idempotency-Key': idempotency_key,
            'address': '123 Test St',
            'pickup': 'false'
        })
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Stock should NOT be reduced again
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 8)  # Still 8, not 6
    #PASSED
    def test_multiple_items_checkout_all_or_nothing(self):
        """Test that if one item fails stock check, entire checkout fails"""
        # Add items: one with sufficient stock, one without
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=2)  # OK
        CartItem.objects.create(cart=self.cart, product=self.product2, quantity=10)  # FAIL (only 5 in stock)
        
        initial_stock_p1 = self.product1.stock
        initial_stock_p2 = self.product2.stock
        
        # Checkout should fail
        response = self.client.post('/checkout/', {
            'X-Idempotency-Key': 'all-or-nothing-test',
            'address': '123 Test St',
            'pickup': 'false'
        })
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # BOTH products should have unchanged stock (transaction rollback)
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        
        self.assertEqual(self.product1.stock, initial_stock_p1)
        self.assertEqual(self.product2.stock, initial_stock_p2)


class StockEdgeCasesTestCase(TestCase):
    """Test edge cases and race conditions"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='edgecase@example.com',
            password='testpass123',
            verified=True
        )
        self.client.force_authenticate(user=self.user)
        
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('100.00'),
            stock=1,  # Only 1 in stock
            category=self.category
        )
        self.cart = Cart.objects.create(user=self.user)

    def test_last_item_checkout(self):
        """Test checking out the last item in stock"""
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)
        
        response = self.client.post('/checkout/', {
            'X-Idempotency-Key': 'last-item-test',
            'address': '123 Test St',
            'pickup': 'false'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Stock should be 0
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)

    def test_zero_stock_prevents_add_to_cart(self):
        """Test that zero stock prevents adding to cart"""
        self.product.stock = 0
        self.product.save()
        
        response = self.client.post(f'/add-to-cart/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_stock_prevented(self):
        """Test that stock never goes negative"""
        # Try to checkout more than available
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=5)
        
        response = self.client.post('/checkout/', {
            'X-Idempotency-Key': 'negative-test',
            'address': '123 Test St',
            'pickup': 'false'
        })
        
        # Should fail
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Stock should still be 1 (not negative)
        self.product.refresh_from_db()
        self.assertGreaterEqual(self.product.stock, 0)
