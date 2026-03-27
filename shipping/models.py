from django.db import models
from orders.models import Order, PickupLocation
# from payments.models import Payment

# once payment is successful shipping is created
class Shipping(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shipping"
    )
    status = models.CharField(
        max_length=50,
        choices=[
            ("pending", "Pending"),
            ("shipped", "Shipped"),
            ("delivered", "Delivered"),
            ('cancelled', 'Cancelled'),
            ('approved', 'Approved'),
            ('fulfilled', 'Fulfilled')
        ],
        default="pending"
    )
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    # address the product is shipping to
    address = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    # pickup option 
    pickup = models.BooleanField(default=False)
    pickup_location = models.CharField(max_length=255, choices=PickupLocation.choices, null=True, blank=True)


    def __str__(self):
        return f"Shipping for Order #{self.order.id if self.order else 'N/A'} - {self.status}"


