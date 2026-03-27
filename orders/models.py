from django.db import models, transaction
from products.models import Product
from users.models import CustomUser as User
from django.utils import timezone
from datetime import timedelta
import uuid
import random
import string
import logging

logger = logging.getLogger(__name__)

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
   

# Create your models here.
class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FULFILLED = 'fulfilled', 'Fulfilled'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_id = models.CharField(max_length=30, unique=True, editable=False, null=True, blank=True)
    total_amount = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True) 

    approved = models.BooleanField(null=True)
    
    # New fields for post-payment shipping
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    shipping_address = models.TextField(null=True, blank=True)
    is_pickup = models.BooleanField(default=False)
    pickup_location = models.CharField(max_length=255, choices=PickupLocation.choices, null=True, blank=True)
    # to alert admins to review the order   
    marked_for_review = models.BooleanField(default=False)

    def __str__(self):
        return f"order {self.order_id} for {self.user.email}"

    def get_payment(self):
        return self.payments.first()

    @property
    def effective_status(self):
        """
        Derive an effective order status.
        Priority:
        1. If Shipping exists, its status determines the order's progress in fulfillment.
        2. Otherwise, use the Order.status field.
        """
        shipping = getattr(self, 'shipping', None)
        if shipping:
            if shipping.status == 'cancelled':
                return self.Status.CANCELLED
            if shipping.status == 'delivered':
                return self.Status.DELIVERED
            if shipping.status == 'shipped':
                return self.Status.FULFILLED # Or a custom 'SHIPPED' status if added
            return self.Status.PAID # If shipping is pending, the order is at least PAID
        
        return self.status

    def restore_stock(self, trigger_refund=True):
        """
        Restores stock for a cancelled order and optionally triggers a refund.
        1. Cancels all active reservations.
        2. If order was already PAID/FULFILLED, we might need to increment inventory_qty
           (assuming inventory_qty was deducted during payment confirmation).
        """
        with transaction.atomic():
            # 1. Cancel active reservations
            active_reservations = self.reservations.filter(status=Reservation.Status.ACTIVE)
            active_reservations.update(status=Reservation.Status.CANCELLED)

            # 2. If stock was already deducted (Order was PAID or FULFILLED)
            # We ONLY restore if the items haven't been physically shipped or delivered.
            shipping = getattr(self, 'shipping', None)
            can_restore_physical = True
            if shipping and shipping.status in ['shipped', 'delivered']:
                can_restore_physical = False
                logger.warning(
                    f"Order {self.order_id} cancellation: Stock NOT restored because "
                    f"shipping status is '{shipping.status}'."
                )

            if can_restore_physical and self.status in [self.Status.PAID, self.Status.FULFILLED]:
                confirmed_reservations = self.reservations.filter(status=Reservation.Status.CONFIRMED)
                for res in confirmed_reservations:
                    Product.objects.filter(pk=res.product.pk).update(
                        inventory_qty=models.F('inventory_qty') + res.quantity
                    )
                    res.status = Reservation.Status.CANCELLED
                    res.save()
            
            new_status = self.Status.CANCELLED
            if trigger_refund and self.status in [self.Status.PAID, self.Status.FULFILLED]:
                from utils.payment_helpers import initiate_paystack_refund
                payment = self.payments.filter(status='success', is_processed=True).first()
                if payment and payment.paystack_reference:
                    success, message = initiate_paystack_refund(payment.paystack_reference, payment.amount)
                    if success:
                        new_status = self.Status.REFUNDED
                        logger.info(f"Refund successfully issued for order {self.order_id}")
                    else:
                        logger.error(f"Refund failed for order {self.order_id}: {message}")
            
            # 3. Cancel shipping if it exists
            if shipping:
                shipping.status = 'cancelled'
                shipping.save(update_fields=['status'])
            
            self.status = new_status
            self.save()
            
            logger.info(f"Stock restored and order {self.order_id} set to {new_status}.")

    def get_fulfillment_status(self):
        return 'pickup' if self.is_pickup else 'delivery'

    @property
    def fulfillment_display_address(self):
        if self.is_pickup and self.pickup_location:
            return PickupLocation.get_address(self.pickup_location)
        return self.shipping_address or 'No address provided'

    @property
    def fulfillment_type(self):
        return 'pickup' if self.is_pickup else 'delivery'

    def is_cancellable(self):
        """Return True if the order is in a state that allows cancellation."""
        return self.status == self.Status.PENDING

    def generate_unique_order_id(self):
        date_str = timezone.now().strftime("%Y%m%d")
        while True:
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            new_id = f"GH-{date_str}-{random_str}"
            if not Order.objects.filter(order_id=new_id).exists():
                return new_id

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = self.generate_unique_order_id()
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.IntegerField()
    # unit price
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
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='reservations')
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reservations')
    quantity   = models.PositiveIntegerField()
    status     = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    expires_at = models.DateTimeField(default=get_default_expiry)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('order', 'product')  # one reservation per product per orderd   
        
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Reservation {self.id} - {self.product} x{self.quantity} [{self.status}]"