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
    ], default='card')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),            # Before webhook confirms
        ('success', 'Success'),            # Paystack -> 'success'
        ('failed', 'Failed'),              # Paystack -> 'failed'
        ('abandoned', 'Abandoned'),        # Paystack -> 'abandoned'
    ], default='pending')
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    authorization_url = models.URLField(max_length=500, blank=True, null=True)  # Paystack payment URL
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    retry_count = models.IntegerField(default=0)  # Track retry attempts
    last_retry_at = models.DateTimeField(null=True, blank=True)
    max_retries = models.IntegerField(default=3)  # Maximum number of retries
    
    date_created = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False) # to make payment processed to 
                                                      # prevent duplicate webhook effects on DB

    def __str__(self):
        return f"Payment #{self.id} for Order #{self.order.id} ({self.status})"
