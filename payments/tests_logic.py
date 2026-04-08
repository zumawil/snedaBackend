from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.test import TransactionTestCase

from orders.models import Order, Reservation, OrderItem
from shipping.models import Shipping
from products.models import Product
from payments.models import Payment
from payments.webhook_handlers import handle_payment_success
from utils.paymentConstants import PaymentStatus, OrderStatus

class PaymentLogicTest(TransactionTestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from carts.models import Cart
        User = get_user_model()
        self.user = User.objects.create_user(email='test@test.com', password='password')
        self.cart = Cart.objects.create(user=self.user)

        from products.models import ProductGroup, Category, HSCode, Brand
        pg, _ = ProductGroup.objects.get_or_create(name="Test Group")
        cat, _ = Category.objects.get_or_create(name="Test Category")
        hs, _ = HSCode.objects.get_or_create(code="12345678")
        br, _ = Brand.objects.get_or_create(name="Test Brand")

        # Create a product
        self.product = Product.objects.create(
            item_no="TEST-001",
            product_group=pg,
            category=cat,
            hs_code=hs,
            brand=br,
            inventory_qty=10,
            gross_price=Decimal("100.00")
        )
        
        # Create an order
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("100.00"),
            status=OrderStatus.PENDING
        )
        
        # Create a reservation
        self.reservation = Reservation.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            expires_at=timezone.now() + timedelta(minutes=15),
            status=Reservation.Status.ACTIVE
        )

    @patch('services.fulfillment_service.FulfillmentService.handle_post_payment')
    @patch('payments.tasks.send_confirmation_email_task.delay')
    def test_payment_success_deducts_stock(self, mock_delay, mock_fulfillment):
        """Test that payment success correctly deducts inventory_qty."""
        mock_delay.return_value.id = "fake-task-id" # Prevent FieldError in update()
        
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("100.00"),
            paystack_reference="REF-001",
            status=PaymentStatus.PENDING,
            is_processed=False
        )
        
        handle_payment_success("REF-001", self.order.id)
        
        # Refresh from DB
        self.product.refresh_from_db()
        self.reservation.refresh_from_db()
        self.order.refresh_from_db()
        payment.refresh_from_db()
        
        self.assertEqual(self.product.inventory_qty, 8)
        self.assertEqual(self.reservation.status, Reservation.Status.CONFIRMED)
        self.assertEqual(self.order.status, OrderStatus.PAID)
        self.assertTrue(payment.is_processed)

    @patch('services.fulfillment_service.FulfillmentService.handle_post_payment')
    @patch('payments.tasks.send_confirmation_email_task.delay')
    def test_payment_success_with_expired_but_available_stock(self, mock_delay, mock_fulfillment):
        """Test success after expiration but stock is still available (grace period)."""
        mock_delay.return_value.id = "fake-task-id"
        self.reservation.expires_at = timezone.now() - timedelta(minutes=1)
        self.reservation.save()
        
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("100.00"),
            paystack_reference="REF-EXPIRED",
            is_processed=False
        )
        
        handle_payment_success("REF-EXPIRED", self.order.id)
        
        self.product.refresh_from_db()
        self.reservation.refresh_from_db()
        self.assertEqual(self.product.inventory_qty, 8)
        self.assertEqual(self.reservation.status, Reservation.Status.CONFIRMED)

    @patch('services.fulfillment_service.FulfillmentService.handle_post_payment')
    @patch('payments.tasks.send_confirmation_email_task.delay')
    def test_payment_success_with_expired_and_no_stock(self, mock_delay, mock_fulfillment):
        """Test that we DON'T deduct stock if expired and others took the stock."""
        mock_delay.return_value.id = "fake-task-id"
        # Expire the reservation - 20 mins is past the 2 min grace window
        self.reservation.expires_at = timezone.now() - timedelta(minutes=20)
        self.reservation.save()
        
        # Someone else takes the stock
        self.product.inventory_qty = 1
        self.product.save()
        
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("100.00"),
            paystack_reference="REF-OVERSOLD",
            is_processed=False
        )
        
        handle_payment_success("REF-OVERSOLD", self.order.id)
        
        self.product.refresh_from_db()
        self.reservation.refresh_from_db()
        
        # Stock should NOT have been deducted further
        self.assertEqual(self.product.inventory_qty, 1)
        # It stayed ACTIVE because our atomic block skipped it and raised ValueError (which we logged)
        self.assertEqual(self.reservation.status, Reservation.Status.ACTIVE) 
        
        # Order should be marked for review
        self.order.refresh_from_db()
        self.assertTrue(self.order.marked_for_review)
        self.assertEqual(self.order.status, OrderStatus.PAID)

    @patch('services.fulfillment_service.FulfillmentService.handle_post_payment')
    @patch('payments.tasks.send_confirmation_email_task.delay')
    def test_atomic_order_deduction_failure(self, mock_delay, mock_fulfillment):
        """If one item in order is unavailable, NO items should be deducted."""
        mock_delay.return_value.id = "fake-task-id"
        from products.models import ProductGroup, Category, HSCode, Brand
        pg = ProductGroup.objects.first()
        cat = Category.objects.first()
        hs = HSCode.objects.first()
        br = Brand.objects.first()
        
        p2 = Product.objects.create(
            item_no="TEST-002", 
            inventory_qty=0,
            product_group=pg,
            category=cat,
            hs_code=hs,
            brand=br,
            gross_price=Decimal("50.00")
        )
        res2 = Reservation.objects.create(
            order=self.order, 
            product=p2, 
            quantity=1, 
            status=Reservation.Status.ACTIVE,
            expires_at=timezone.now() - timedelta(minutes=20)
        )
        
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("100.00"),
            paystack_reference="REF-ATOMIC",
            is_processed=False
        )
        
        handle_payment_success("REF-ATOMIC", self.order.id)
        
        self.product.refresh_from_db()
        p2.refresh_from_db()
        
        # Physical stock should NOT have changed for either because the whole block rolled back
        self.assertEqual(self.product.inventory_qty, 10)
        self.assertEqual(p2.inventory_qty, 0)

    def test_restore_stock_cancelled_order(self):
        """Test restore_stock() increments inventory_qty if previously PAID."""
        # Simulate a PAID order with confirmed stock
        self.order.status = OrderStatus.PAID
        self.order.save()
        self.reservation.status = Reservation.Status.CONFIRMED
        self.product.inventory_qty = 8
        self.product.save()
        self.reservation.save()
        
        self.order.restore_stock(trigger_refund=False)
        
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.inventory_qty, 10)
        self.assertEqual(self.order.status, OrderStatus.CANCELLED)

    def test_restore_stock_already_shipped(self):
        """Verify we DON'T restore stock if it's already shipped."""
        shipping = Shipping.objects.create(
            order=self.order,
            status='shipped',
            address="123 Test St, Accra"
        )
        
        self.order.status = OrderStatus.PAID
        self.order.save()
        self.reservation.status = Reservation.Status.CONFIRMED
        self.product.inventory_qty = 8
        self.product.save()
        self.reservation.save()
        
        self.order.restore_stock(trigger_refund=False)
        
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        shipping.refresh_from_db()
        # Stock stays 8 because it's shipped!
        self.assertEqual(self.product.inventory_qty, 8)
        self.assertEqual(self.order.status, OrderStatus.CANCELLED)
        self.assertEqual(shipping.status, 'shipped')

    @patch('utils.payment_helpers.initiate_paystack_refund')
    def test_restore_stock_with_refund(self, mock_refund):
        """Verify cancelling a PAID order triggers external refund and sets status to REFUNDED."""
        mock_refund.return_value = (True, "Refund processed successfully")
        
        self.order.status = OrderStatus.PAID
        self.order.save()
        self.reservation.status = Reservation.Status.CONFIRMED
        self.product.inventory_qty = 8
        self.product.save()
        self.reservation.save()
        
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("100.00"),
            paystack_reference="REF-TO-REFUND",
            status='success',
            is_processed=True
        )
        
        self.order.restore_stock(trigger_refund=True)
        
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        
        self.assertEqual(self.order.status, OrderStatus.REFUNDED)
        self.assertEqual(self.product.inventory_qty, 10)
        mock_refund.assert_called_once_with("REF-TO-REFUND", Decimal("100.00"))

    def test_cancel_unpaid_orders_task(self):
        """Verify the background task zeroes out abandoned orders correctly."""
        from orders.tasks import cancel_unpaid_orders
        
        # Old abandoned order
        abandoned_order = Order.objects.create(
            user=self.user, 
            status=OrderStatus.PENDING, 
            total_amount=Decimal("50.00")
        )
        # Manually force created_at using update to bypass auto_now_add
        Order.objects.filter(id=abandoned_order.id).update(created_at=timezone.now() - timedelta(minutes=40))
        
        # Fresh pending order (should be ignored)
        fresh_order = Order.objects.create(
            user=self.user, 
            status=OrderStatus.PENDING, 
            total_amount=Decimal("50.00")
        )
        Order.objects.filter(id=fresh_order.id).update(created_at=timezone.now() - timedelta(minutes=10))
        
        # Old paid order (should be ignored)
        paid_order = Order.objects.create(
            user=self.user, 
            status=OrderStatus.PAID, 
            total_amount=Decimal("50.00")
        )
        Order.objects.filter(id=paid_order.id).update(created_at=timezone.now() - timedelta(minutes=40))
        Payment.objects.create(
            order=paid_order, amount=Decimal("50.00"), status='success', is_processed=True
        )
        
        cancel_unpaid_orders()
        
        abandoned_order.refresh_from_db()
        fresh_order.refresh_from_db()
        paid_order.refresh_from_db()
        
        self.assertEqual(abandoned_order.status, OrderStatus.CANCELLED)
        self.assertEqual(fresh_order.status, OrderStatus.PENDING)
        self.assertEqual(paid_order.status, OrderStatus.PAID)
