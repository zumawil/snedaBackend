from django.db import models
from orders.models import Order
# from payments.models import Payment

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
            ('cancelled', 'Cancelled'),
            ('approved', 'Approved')
        ],
        default="pending"
    )
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    # address the product is sipping to
    address = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    # pickup option 
    pickup = models.BooleanField(default=False)


    def __str__(self):
        return f"Shipping for Order #{self.order.id if self.order else 'N/A'} - {self.status}"


