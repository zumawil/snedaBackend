# In your shipping app models.py

from django.db import models
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from orders.models import Order, PickupLocation
from users.models import CustomUser as User
from django.utils import timezone

class Shipping(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="shipping"
    )
    status = models.CharField(
        max_length=50,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("picked", "Picked"),              # Admin picked/prepared
            ("shipped", "Shipped"),            # In transit
            ("delivered", "Delivered"),        # CLOSED state
            ('cancelled', 'Cancelled'),
        ],
        default="pending"
    )
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(null=True)  # Required for delivery
    
    # Tracking fields
    picked_at = models.DateTimeField(null=True, blank=True)
    picked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='picked_shipments'
    )
    
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivered_shipments'
    )
    
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Shipping for Order {self.order.order_id} - {self.status}"

    def clean(self):
        """Ensure order is NOT marked as pickup"""
        if self.order and self.order.is_pickup:
            raise ValidationError("Cannot create shipping for pickup orders (is_pickup=True)")
        
        # Ensure no pickup fulfillment exists for this order
        if self.order:
            try:
                _ = self.order.pickup_fulfillment
                raise ValidationError("Order already has pickup record. Cannot have both pickup and shipping.")
            except ObjectDoesNotExist:
                pass
        
        # Ensure address is provided
        if not self.address:
            raise ValidationError("Shipping address is required for delivery orders")

    def save(self, *args, **kwargs):
        # Only validate on create or if it's a full update
        if not self.pk or 'update_fields' not in kwargs:
            self.full_clean()
        super().save(*args, **kwargs)

    def mark_as_picked(self, admin_user):
        """Admin marks order as picked"""
        if self.status not in ['pending', 'approved']:
            raise ValidationError(f"Cannot mark as picked. Current status: {self.status}")
        
        self.status = 'picked'
        self.picked_at = timezone.now()
        self.picked_by = admin_user
        self.save(update_fields=['status', 'picked_at', 'picked_by', 'updated_at'])

    def mark_as_delivered(self, admin_user):
        """Admin marks order as delivered"""
        if self.status != 'shipped':
            raise ValidationError(f"Order must be shipped before delivery. Current status: {self.status}")
        
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.delivered_by = admin_user
        self.save(update_fields=['status', 'delivered_at', 'delivered_by', 'updated_at'])