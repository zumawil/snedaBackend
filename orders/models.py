from django.db import models
from products.models import Product
from users.models import CustomUser as User
from django.utils import timezone
from datetime import timedelta
import uuid
from products.models import Product
# Create your models here.
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    # Order.status removed — Shipping model is the source of truth for shipment state.
    total_amount = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True) 

    approved = models.BooleanField(null=True)
    def __str__(self):
        return f"order for {self.user.email}"

    def get_payment(self):
        return self.payments.first()

    def compute_status_from_shipping(self):
        """
        Derive an effective order status from the related Shipping record when present.
        If no Shipping exists, treat the order as 'pending'. Shipping holds the authoritative
        state once it is created.
        """
        try:
            shipping = getattr(self, 'shipping', None)
        except Exception:
            shipping = None

        if shipping:
            # use shipping.status as authoritative when available
            return shipping.status

        return 'pending'

    @property
    def effective_status(self):
        return self.compute_status_from_shipping()


    def get_fulfillment_status(self):
        return 'pickup' if self.shipping.pickup else 'delivery'

    def is_cancellable(self):
        """Return True if the order is in a state that allows cancellation."""
        return self.effective_status == 'pending'

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

# set default expiry to 15 minutes from now
#
default_expiry = timezone.now() + timedelta(minutes=15)    
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
    expires_at = models.DateTimeField(default=default_expiry)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('order', 'product')  # one reservation per product per order

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Reservation {self.id} - {self.product} x{self.quantity} [{self.status}]"