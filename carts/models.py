from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from users.models import CustomUser as User
from products.models import Product
from orders.models import Order
# Create your models here.

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.email}"
    
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    

class CartItem(models.Model):
    # how many is bought
    quantity = models.IntegerField(default=1)
    product = models.ForeignKey(Product,related_name="cart_items", on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.quantity} of {self.product.item_no} in cart of {self.cart.user.email}"
    
    # a user can buy more of one thing , this calculaes the sum of it
    def get_total_price(self):
        return self.quantity * self.product.gross_price

# Idempotency table  to prevent creating same order mutiple times times
class CheckoutAttempt(models.Model):
    key = models.CharField(max_length=255, unique=True)
    order = models.ForeignKey(
                        Order, 
                        on_delete=models.CASCADE, 
                        null=True, 
                        blank=True
                    )
    # Store fulfillment data for post-payment processing
    address = models.TextField(null=True, blank=True)  # Delivery address
    pickup_location = models.CharField(max_length=255, null=True, blank=True)  # Pickup location choice
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(address__isnull=False) & Q(pickup_location__isnull=True)) |
                    (Q(address__isnull=True) & Q(pickup_location__isnull=False))
                ),
                name='exactly_one_fulfillment_target'
            )
        ]

    def clean(self):
        """Ensure exactly one of address or pickup_location is set."""
        if not self.address and not self.pickup_location:
            raise ValidationError("Exactly one of address or pickup_location must be provided.")
        if self.address and self.pickup_location:
            raise ValidationError("Only one of address or pickup_location can be provided.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
