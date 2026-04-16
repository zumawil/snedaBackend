from django.db import models, transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from products.models import Product
from users.models import CustomUser as User
from django.utils import timezone
from datetime import timedelta
import uuid
import random
import string
import logging

logger = logging.getLogger(__name__)
from utils.paymentConstants import OrderStatus

class PickupLocation(models.TextChoices):
    NIA = 'NIA', 'National Information Agency'
    SPINTEX = 'SPINTEX', 'Spintex'
    OSU = 'OSU', 'Osu'

    @classmethod
    def get_address(cls, key):
        mapping = {
            cls.NIA: 'National Information Agency Area, Accra',
            cls.SPINTEX: 'Spintex Road, Behind Coca-Cola, Accra',
            cls.OSU: 'Oxford Street, Osu, Accra'
        }
        return mapping.get(key, 'Unknown Branch')

class Order(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_id = models.CharField(max_length=30, unique=True, editable=False, null=True, blank=True)
    total_amount = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # System-controlled status (payment/business state only)
    status = models.CharField(
        max_length=20, 
        choices=OrderStatus.choices, 
        default=OrderStatus.PENDING
    )
    
    # Fulfillment type indicator ONLY
    is_pickup = models.BooleanField(default=False)
    
    # Alert admins to review the order
    marked_for_review = models.BooleanField(default=False)
    approved = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return f"order {self.order_id} for {self.user.email}"

    def clean(self):
        """Enforce: order must have EITHER pickup OR shipping, not both, not neither"""
        has_pickup = hasattr(self, 'pickup_fulfillment')
        has_shipping = hasattr(self, 'shipping')
        
        if self.pk:  # Only validate for existing orders
            if self.is_pickup and has_shipping:
                raise ValidationError("Pickup orders cannot have shipping records")
            
            if not self.is_pickup and has_pickup:
                raise ValidationError("Delivery orders cannot have pickup records")

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = self.generate_unique_order_id()
        self.full_clean()
        super().save(*args, **kwargs)

    def get_payment(self):
        return self.payments.first()

    @property
    def effective_status(self):
        """
        User-facing status that shows current fulfillment state.
        """
        # Delivery orders - Shipping.status is the source of truth
        if hasattr(self, 'shipping') and self.shipping:
            return self.shipping.status
        
        # Pickup orders - PickupFulfillment.status is the source of truth
        if hasattr(self, 'pickup_fulfillment') and self.pickup_fulfillment:
            return self.pickup_fulfillment.status
        
        # Fallback to system status
        return self.status

    @property
    def is_closed(self):
        """Check if order is in a closed/completed state"""
        if hasattr(self, 'pickup_fulfillment') and self.pickup_fulfillment:
            return self.pickup_fulfillment.status == 'completed'
        elif hasattr(self, 'shipping') and self.shipping:
            return self.shipping.status == 'delivered'
        return False

    @property
    def fulfillment_type(self):
        return 'pickup' if self.is_pickup else 'delivery'

    @property
    def fulfillment_display_address(self):
        """Get the display address for this order"""
        if hasattr(self, 'pickup_fulfillment') and self.pickup_fulfillment:
            return self.pickup_fulfillment.get_display_address()
        elif hasattr(self, 'shipping') and self.shipping:
            return self.shipping.address
        return 'No address provided'

    @property
    def fulfillment(self):
        """Get fulfillment details"""
        if hasattr(self, 'pickup_fulfillment') and self.pickup_fulfillment:
            return {
                "type": "pickup",
                "status": self.pickup_fulfillment.status,
                "location": self.pickup_fulfillment.location,
                "display_address": self.pickup_fulfillment.get_display_address(),
                "is_closed": self.is_closed
            }
        elif hasattr(self, 'shipping') and self.shipping:
            return {
                "type": "delivery",
                "status": self.shipping.status,
                "address": self.shipping.address,
                "tracking_number": self.shipping.tracking_number,
                "is_closed": self.is_closed
            }
        return {"type": "unknown", "status": self.status}

    def prepare_stock_restore(self):
        """
        DB-side stock restoration and state changes.
        Should be called inside a transaction with select_for_update.
        Returns: (needs_refund, payment)
        """
        # 1. Determine if a refund is needed
        needs_refund = self.status == OrderStatus.PAID
        payment = None

        if needs_refund:
            payment = self.payments.filter(status='success', is_processed=True).first()
            if not payment or not payment.paystack_reference:
                logger.warning(f"Refund needed for order {self.order_id} but no valid payment found.")
                self.marked_for_review = True
                self.status = OrderStatus.CANCELLATION_PENDING
                self.save(update_fields=['marked_for_review', 'status'])
                return False, None

        # 2. Cancel active/confirmed reservations
        active_reservations = self.reservations.filter(status=Reservation.Status.ACTIVE)
        active_reservations.update(status=Reservation.Status.CANCELLED)

        can_restore_physical = True
        
        # Preserve audit trail for handoff-complete states
        if hasattr(self, 'shipping') and self.shipping:
            if self.shipping.status in ['shipped', 'delivered']:
                can_restore_physical = False
                logger.warning(f"Order {self.id}: Stock NOT restored - already shipped/delivered")
            else:
                self.shipping.status = 'cancelled'
                self.shipping.save(update_fields=['status'])
        
        if hasattr(self, 'pickup_fulfillment') and self.pickup_fulfillment:
            if self.pickup_fulfillment.status == 'completed':
                can_restore_physical = False
                logger.warning(f"Order {self.id}: Stock NOT restored - pickup already completed")
            else:
                self.pickup_fulfillment.status = 'cancelled'
                self.pickup_fulfillment.save(update_fields=['status'])

        if can_restore_physical:
            confirmed_res = self.reservations.filter(status=Reservation.Status.CONFIRMED)
            for res in confirmed_res:
                Product.objects.filter(pk=res.product.pk).update(
                    inventory_qty=models.F('inventory_qty') + res.quantity
                )
                res.status = Reservation.Status.CANCELLED
                res.save()
        
        # Initially set status to CANCELLED if no refund needed
        # if user never made payment
        if not needs_refund:
            self.status = OrderStatus.CANCELLED
            self.save(update_fields=['status'])
            
        return needs_refund, payment

    def perform_refund(self, payment):
        """
        Handles the external Paystack refund call.
        """
        if not payment:
            return False, "No payment provided"

        from utils.payment_helpers import initiate_paystack_refund
        success, message = initiate_paystack_refund(payment.paystack_reference, payment.amount)
        
        # Update status based on refund result
        with transaction.atomic():
            # Lock again for final update
            order = Order.objects.select_for_update().get(pk=self.pk)
            if success:
                order.status = OrderStatus.REFUNDED
                logger.info(f"Refund issued for order {order.order_id}")
            else:
                logger.error(f"Refund failed for order {order.order_id}: {message}")
                order.marked_for_review = True
                order.status = OrderStatus.CANCELLATION_PENDING
            order.save(update_fields=['status', 'marked_for_review'])
            
        return success, message

    def restore_stock(self, trigger_refund=True):
        """Backward compatible wrapper for automated restoration."""
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            needs_refund, payment = order.prepare_stock_restore()
        
        if trigger_refund and needs_refund and payment:
            self.perform_refund(payment)
        elif not needs_refund:
            logger.info(f"Order {self.order_id} restored and cancelled (no refund needed)")


    def is_cancellable(self):
        """Return True if order can be cancelled"""
        if self.is_closed:
            return False
        return self.status in [OrderStatus.PENDING, OrderStatus.PAID]

    
    def generate_unique_order_id(self):
        date_str = timezone.now().strftime("%Y%m%d")
        while True:
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            new_id = f"GH-{date_str}-{random_str}"
            if not Order.objects.filter(order_id=new_id).exists():
                return new_id

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_total_price(self):
        return self.quantity * self.price
    
    def __str__(self):
        return f"order item for {self.order}"

def get_default_expiry():
    return timezone.now() + timedelta(minutes=15)

class Reservation(models.Model):
    
    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        EXPIRED   = 'expired',   'Expired'
        CONFIRMED = 'confirmed', 'Confirmed' # reservation is made available to user
        CANCELLED = 'cancelled', 'Cancelled'
    
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='reservations')
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reservations')
    quantity   = models.PositiveIntegerField()
    status     = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    expires_at = models.DateTimeField(default=get_default_expiry)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('order', 'product')
        
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Reservation {self.id} - {self.product} x{self.quantity} [{self.status}]"

# In orders/models.py (add this)

class PickupFulfillment(models.Model):
    """Separate model for pickup order fulfillment data"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        READY = 'ready', 'Ready for Pickup'       # Admin marked as picked
        COMPLETED = 'completed', 'Completed'      # Customer collected (CLOSED)
        CANCELLED = 'cancelled', 'Cancelled'
    
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='pickup_fulfillment'
    )
    location = models.CharField(
        max_length=255,
        choices=PickupLocation.choices
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Tracking fields
    picked_at = models.DateTimeField(null=True, blank=True)
    picked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='picked_orders'
    )
    
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_pickup_orders'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pickup for Order {self.order.order_id} at {self.location} - {self.status}"

    def clean(self):
        """Ensure order is marked as pickup"""
        if not self.order_id:
            return
            
        if self.order and not self.order.is_pickup:
            raise ValidationError("Can only create PickupFulfillment for pickup orders (is_pickup=True)")
        
        # Ensure no shipping exists for this order
        if self.order:
            try:
                _ = self.order.shipping
                raise ValidationError("Order already has shipping record. Cannot have both pickup and shipping.")
            except ObjectDoesNotExist:
                pass

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_display_address(self):
        """Get human-readable address for this pickup location"""
        return PickupLocation.get_address(self.location)

    def mark_as_ready(self, admin_user):
        """Admin marks order as picked and ready for customer pickup"""
        if self.status != self.Status.PENDING:
            raise ValidationError(f"Cannot mark as ready. Current status: {self.status}")
        
        self.status = self.Status.READY
        self.picked_at = timezone.now()
        self.picked_by = admin_user
        self.save(update_fields=['status', 'picked_at', 'picked_by', 'updated_at'])
        logger.info(f"Pickup order {self.order.order_id} marked as ready by {admin_user.email}")

    def mark_as_completed(self, admin_user):
        """Admin marks order as completed (customer collected)"""
        if self.status != self.Status.READY:
            raise ValidationError(f"Order must be ready before completing. Current status: {self.status}")
        
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.completed_by = admin_user
        self.save(update_fields=['status', 'completed_at', 'completed_by', 'updated_at'])
        logger.info(f"Pickup order {self.order.order_id} completed by {admin_user.email}")