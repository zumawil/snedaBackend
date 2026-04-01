from django.test import TestCase
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal

from users.models import CustomUser as User
from products.models import Product, ProductGroup, Category, HSCode, Brand
from carts.models import Cart, CartItem, CheckoutAttempt
from orders.models import Order, OrderItem, PickupFulfillment, Reservation
from shipping.models import Shipping


class OrderCheckoutFlowTestCase(TestCase):
    """
    Test suite to verify the new split between Order, Shipping, and PickupFulfillment models.
    
    WHY: After separating address/location from Order model, we need to ensure:
    1. Orders are created without address data during checkout
    2. CheckoutAttempt temporarily stores address/location for post-payment use
    3. Shipping/PickupFulfillment are created after payment with correct data
    4. All fulfillment data flows correctly through the system
    """

    def setUp(self):
        """Create test user, product, and cart for reuse across tests"""
        # Create test user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            verified=True
        )
        
        # Create required ForeignKey objects for Product
        self.product_group = ProductGroup.objects.create(name='Test Group')
        self.category = Category.objects.create(name='Test Category')
        self.hs_code = HSCode.objects.create(code='1234567890')
        self.brand = Brand.objects.create(name='Test Brand')
        
        # Create test product 
        self.product = Product.objects.create(
            item_no='SKU001',
            product_group=self.product_group,
            category=self.category,
            hs_code=self.hs_code,
            brand=self.brand,
            gross_price=Decimal('100.00'),
            inventory_qty=100,
            weight=1.5
        )
        
        # Create cart with items
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )

    def test_order_created_without_address_fields(self):
        """
        TEST: Order model no longer stores address or pickup_location
        WHY: Separates business logic (Order) from fulfillment details (Shipping/PickupFulfillment)
        
        This verifies that Order only stores is_pickup flag, and doesn't have address/location fields.
        """
        order = Order.objects.create(
            user=self.user,
            status='pending',
            is_pickup=False
        )
        
        # Order should only have these fields set
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.is_pickup, False)
        self.assertEqual(order.status, 'pending')
        
        # Order should NOT have address/location attributes
        self.assertFalse(hasattr(order, 'address'))
        self.assertFalse(hasattr(order, 'pickup_location'))
        
        print("✓ Order created without address/location fields")

    def test_checkout_attempt_stores_delivery_address(self):
        """
        TEST: CheckoutAttempt stores delivery address for later use
        WHY: Address is needed AFTER payment succeeds to create Shipping record.
        We store it in CheckoutAttempt during checkout, then retrieve it during fulfillment.
        
        This prevents needing to ask user for address twice and decouples checkout from fulfillment.
        """
        # Create order during checkout
        order = Order.objects.create(
            user=self.user,
            status='pending',
            is_pickup=False
        )
        
        # Store checkout attempt with delivery address
        delivery_address = "123 Main Street, Accra, Ghana"
        checkout_attempt = CheckoutAttempt.objects.create(
            key='test-idempotency-key-1',
            order=order,
            address=delivery_address,  # Address stored here for delivery orders
            pickup_location=None       # No pickup location for delivery
        )
        
        # Verify data is stored correctly
        self.assertEqual(checkout_attempt.address, delivery_address)
        self.assertIsNone(checkout_attempt.pickup_location)
        self.assertEqual(checkout_attempt.order, order)
        
        print("CheckoutAttempt correctly stored delivery address")

    def test_checkout_attempt_stores_pickup_location(self):
        """
        TEST: CheckoutAttempt stores pickup location choice for later use
        WHY: Pickup location is needed AFTER payment succeeds to create PickupFulfillment record.
        We store it in CheckoutAttempt during checkout, then retrieve it during fulfillment.
        
        This prevents needing to ask user for location twice and decouples checkout from fulfillment.
        """
        # Create order during checkout
        order = Order.objects.create(
            user=self.user,
            status='pending',
            is_pickup=True  # Mark as pickup order
        )
        
        # Store checkout attempt with pickup location
        pickup_location = "SPINTEX"
        checkout_attempt = CheckoutAttempt.objects.create(
            key='test-idempotency-key-2',
            order=order,
            address=None,                  # No address for pickup orders
            pickup_location=pickup_location  # Location stored here for pickup
        )
        
        # Verify data is stored correctly
        self.assertIsNone(checkout_attempt.address)
        self.assertEqual(checkout_attempt.pickup_location, pickup_location)
        self.assertEqual(checkout_attempt.order, order)
        
        print("✓ CheckoutAttempt correctly stored pickup location")

    def test_shipping_created_from_checkout_attempt_data(self):
        """
        TEST: Shipping record is created using data from CheckoutAttempt
        WHY: After payment succeeds, fulfillment_service reads address from CheckoutAttempt
        and creates Shipping record. This is the post-payment fulfillment creation.
        
        Simulates: Payment webhook -> fulfillment_service.handle_post_payment() -> 
                   ShippingService.create_shipping_from_order()
        """
        # 1. Create order during checkout
        order = Order.objects.create(
            user=self.user,
            status='pending',
            is_pickup=False
        )
        
        # 2. Store delivery address in CheckoutAttempt
        delivery_address = "456 Market Street, Kumasi, Ghana"
        checkout_attempt = CheckoutAttempt.objects.create(
            key='test-checkout-1',
            order=order,
            address=delivery_address
        )
        
        # 3. After payment succeeds, create Shipping from CheckoutAttempt data
        # (This is what fulfillment_service does)
        shipping = Shipping.objects.create(
            order=order,
            address=checkout_attempt.address,  # Gets address from CheckoutAttempt
            status='pending'
        )
        
        # Verify Shipping is created correctly
        self.assertEqual(shipping.order, order)
        self.assertEqual(shipping.address, delivery_address)
        self.assertEqual(shipping.status, 'pending')
        
        # Verify Order now has Shipping related object
        self.assertTrue(hasattr(order, 'shipping'))
        self.assertEqual(order.shipping, shipping)
        
        print("✓ Shipping record created correctly from CheckoutAttempt data")

    def test_pickup_fulfillment_created_from_checkout_attempt_data(self):
        """
        TEST: PickupFulfillment record is created using data from CheckoutAttempt
        WHY: After payment succeeds, fulfillment_service reads pickup_location from CheckoutAttempt
        and creates PickupFulfillment record. This is the post-payment fulfillment creation for pickups.
        
        Simulates: Payment webhook -> fulfillment_service.handle_post_payment() -> 
                   ShippingService.create_shipping_from_order()
        """
        # 1. Create pickup order during checkout
        order = Order.objects.create(
            user=self.user,
            status='pending',
            is_pickup=True  # Flag as pickup
        )
        
        # 2. Store pickup location in CheckoutAttempt (use valid location choice)
        pickup_location = "SPINTEX"
        checkout_attempt = CheckoutAttempt.objects.create(
            key='test-checkout-2',
            order=order,
            pickup_location=pickup_location
        )
        
        # 3. After payment succeeds, create PickupFulfillment from CheckoutAttempt data
        # (This is what fulfillment_service does)
        pickup_fulfillment = PickupFulfillment.objects.create(
            order=order,
            location=checkout_attempt.pickup_location,  # Gets location from CheckoutAttempt
            status='pending'
        )
        
        # Verify PickupFulfillment is created correctly
        self.assertEqual(pickup_fulfillment.order, order)
        self.assertEqual(pickup_fulfillment.location, pickup_location)
        self.assertEqual(pickup_fulfillment.status, 'pending')
        
        # Verify Order now has PickupFulfillment related object
        self.assertTrue(hasattr(order, 'pickup_fulfillment'))
        self.assertEqual(order.pickup_fulfillment, pickup_fulfillment)
        
        print("✓ PickupFulfillment record created correctly from CheckoutAttempt data")

    def test_order_fulfillment_property_delivery(self):
        """
        TEST: Order.fulfillment property returns correct dict for delivery orders
        WHY: Frontend/serializers call order.fulfillment to get fulfillment details.
        The property must return the right structure regardless of fulfillment type.
        
        This is used in OrderSerializer to populate response data.
        """
        # Create delivery order with shipping
        order = Order.objects.create(
            user=self.user,
            status='paid',
            is_pickup=False
        )
        
        shipping = Shipping.objects.create(
            order=order,
            address="789 King Street, Tema, Ghana",
            status='pending',
            tracking_number='TRACK123'
        )
        
        # Call fulfillment property
        fulfillment = order.fulfillment
        
        # Verify it returns a dict with delivery details
        self.assertIsNotNone(fulfillment)
        self.assertEqual(fulfillment['type'], 'delivery')
        self.assertEqual(fulfillment['status'], 'pending')
        self.assertEqual(fulfillment['address'], "789 King Street, Tema, Ghana")
        self.assertEqual(fulfillment['tracking_number'], 'TRACK123')
        
        print("✓ Order.fulfillment returns correct delivery dict")

    def test_order_fulfillment_property_pickup(self):
        """
        TEST: Order.fulfillment property returns correct dict for pickup orders
        WHY: Frontend/serializers call order.fulfillment to get fulfillment details.
        The property must return the right structure regardless of fulfillment type.
        
        This is used in OrderSerializer to populate response data.
        """
        # Create pickup order with fulfillment
        order = Order.objects.create(
            user=self.user,
            status='paid',
            is_pickup=True
        )
        
        pickup_fulfillment = PickupFulfillment.objects.create(
            order=order,
            location='SPINTEX',
            status='pending'
        )
        
        # Call fulfillment property
        fulfillment = order.fulfillment
        
        # Verify it returns a dict with pickup details
        self.assertIsNotNone(fulfillment)
        self.assertEqual(fulfillment['type'], 'pickup')
        self.assertEqual(fulfillment['status'], 'pending')
        self.assertEqual(fulfillment['location'], 'SPINTEX')
        
        print("✓ Order.fulfillment returns correct pickup dict")

    def test_order_effective_status_from_shipping(self):
        """
        TEST: Order.effective_status returns status from Shipping (not Order.status)
        WHY: For delivery orders, the real fulfillment status comes from Shipping model.
        Order.status is for payment/business state only. The user cares about shipment status.
        
        Example: Order.status='paid' but Shipping.status='shipped' -> 
                 effective_status should be 'shipped'
        """
        # Create delivery order
        order = Order.objects.create(
            user=self.user,
            status='paid',  # Payment completed
            is_pickup=False
        )
        
        shipping = Shipping.objects.create(
            order=order,
            address="123 Main Street, Accra, Ghana",
            status='shipped'  # But shipment is already in transit
        )
        
        # Effective status should come from Shipping, not Order
        self.assertEqual(order.effective_status, 'shipped')
        # Not equal to order.status
        self.assertNotEqual(order.effective_status, order.status)
        
        print("✓ Order.effective_status correctly returns Shipping status")

    def test_order_effective_status_from_pickup(self):
        """
        TEST: Order.effective_status returns status from PickupFulfillment (not Order.status)
        WHY: For pickup orders, the real fulfillment status comes from PickupFulfillment model.
        Order.status is for payment/business state only. The user cares about pickup readiness.
        
        Example: Order.status='paid' but PickupFulfillment.status='ready' -> 
                 effective_status should be 'ready'
        """
        # Create pickup order
        order = Order.objects.create(
            user=self.user,
            status='paid',  # Payment completed
            is_pickup=True
        )
        
        pickup_fulfillment = PickupFulfillment.objects.create(
            order=order,
            location='SPINTEX',
            status='ready'  # But order is ready to pickup
        )
        
        # Effective status should come from PickupFulfillment, not Order
        self.assertEqual(order.effective_status, 'ready')
        # Not equal to order.status
        self.assertNotEqual(order.effective_status, order.status)
        
        print("✓ Order.effective_status correctly returns PickupFulfillment status")

    def test_order_validation_prevents_both_shipping_and_pickup(self):
        """
        TEST: Order.clean() prevents having both Shipping and PickupFulfillment
        WHY: An order must be EITHER delivery OR pickup, never both.
        This validation ensures data consistency in the database.
        
        Expected behavior:
        - delivery order (is_pickup=False) MUST have Shipping, NOT PickupFulfillment
        - pickup order (is_pickup=True) MUST have PickupFulfillment, NOT Shipping
        """
        # Create a delivery order (is_pickup=False)
        order = Order.objects.create(
            user=self.user,
            status='pending',
            is_pickup=False
        )
        
        # Create Shipping for delivery
        shipping = Shipping.objects.create(
            order=order,
            address="123 Main Street, Accra, Ghana",
            status='pending'
        )
        
        # Verify setup: order has shipping but not pickup yet
        self.assertEqual(order.shipping, shipping)
        self.assertFalse(hasattr(order, 'pickup_fulfillment'))

        # Try to also create PickupFulfillment - should raise ValidationError
        # because the order is NOT marked as pickup and already has shipping.
        pickup = PickupFulfillment(
            order=order,
            location='SPINTEX',
            status='pending'
        )
        
        # Trigger model validation (PickupFulfillment.clean() and Order.clean())
        with self.assertRaises(ValidationError):
            pickup.full_clean()
        
        print("✓ Order validation prevents conflicting fulfillment types (Shipping and PickupFulfillment)")

    def test_complete_checkout_to_fulfillment_flow(self):
        """
        TEST: Complete end-to-end flow from checkout to fulfillment
        WHY: Integration test to verify the entire process works together.
        Tests the real workflow: checkout -> payment -> fulfillment creation
        
        This is the main flow that end users experience.
        """
        # STEP 1: User adds items to cart (already done in setUp)
        self.assertEqual(self.cart.total_items(), 2)
        
        # STEP 2: Checkout - create Order and CheckoutAttempt with address
        idempotency_key = 'test-complete-flow-key'
        order = Order.objects.create(
            user=self.user,
            status='pending',
            is_pickup=False  # Delivery order
        )
        
        delivery_address = "999 Prosperity Avenue, Accra, Ghana"
        checkout_attempt = CheckoutAttempt.objects.create(
            key=idempotency_key,
            order=order,
            address=delivery_address
        )
        
        # STEP 3: Payment succeeds (webhook triggered)
        order.status = 'paid'
        order.save()
        
        # STEP 4: Fulfillment service creates Shipping from CheckoutAttempt data
        shipping = Shipping.objects.create(
            order=order,
            address=checkout_attempt.address,  # Uses CheckoutAttempt data
            status='pending',
            tracking_number='GHLK1234567890'
        )
        
        # STEP 5: Admin marks as picked
        shipping.status = 'picked'
        shipping.save()
        
        # STEP 6: Verify final state
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.effective_status, 'picked')  # User sees picked status
        self.assertEqual(shipping.address, delivery_address)
        self.assertFalse(order.is_closed)  # Order not closed until delivered
        
        # STEP 7: Mark as delivered (order closed)
        shipping.status = 'delivered'
        shipping.save()
        
        self.assertTrue(order.is_closed)  # Now order is closed
        
        print("✓ Complete checkout-to-fulfillment flow works correctly")

