from django.db import models
from orders.models import Order
from payments.models import Payment

class Shipping(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
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
        ],
        default="pending"
    )
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Shipping for Order #{self.order.id} - {self.status}"

from django.db import models
from orders.models import Order
from payments.models import Payment

# once payment is successful shipping is created
class Shipping(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
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
        ],
        default="pending"
    )
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    pickup = models.BooleanField(default=False)


    def __str__(self):
        return f"Shipping for Order #{self.order.id if self.order else 'N/A'} - {self.status}"


