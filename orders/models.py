from django.db import models
from products.models import Product
from users.models import CustomUser as User
# Create your models here.
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=50,
                              choices=[('pending', 'Pending'),
                                        ('shipped', 'Shipped'),
                                        ('delivered', 'Delivered'),
                                        ('cancelled', 'Cancelled')], default='pending')
    total_amount = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)                

    def __str__(self):
        return f"order for {self.user.email}"

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