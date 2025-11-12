from django.db import models
from orders.models import Order

# class Payment(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     method = models.CharField(max_length=20, choices=[
#         ('momo', 'Mobile Money'),
#         ('card', 'Credit Card'),
#         ('cash', 'Cash'),
#     ])
#     status = models.CharField(max_length=20, choices=[
#         ('pending', 'Pending'),
#         ('completed', 'Completed'),
#         ('failed', 'Failed'),
#     ], default='pending')
#     transaction_id = models.CharField(max_length=100, blank=True, null=True)
#     date_created = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Payment #{self.id} for Order #{self.order.id} ({self.status})"
