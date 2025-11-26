from django.db import models
from orders.models import Order

class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=[
        ('card', 'Card'),
        ('mobile_money', 'Mobile Money'),
        ('bank', 'Bank Account'),
        ('ussd', 'USSD'),
        ('qr', 'QR Payment'),
        ('bank_transfer', 'Bank Transfer'),
    ])
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),            # Before webhook confirms
        ('success', 'Success'),            # Paystack -> 'success'
        ('failed', 'Failed'),              # Paystack -> 'failed'
        ('abandoned', 'Abandoned'),        # Paystack -> 'abandoned'
    ], default='pending')
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment #{self.id} for Order #{self.order.id} ({self.status})"
