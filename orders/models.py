from django.db import models
from products.models import Product
from users.models import CustomUser as User
# Create your models here.
class Order(models.Model):
    order = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=50, 
                              choices=[('pending', 'Pending'),
                                        ('shipped', 'Shipped'), 
                                        ('delivered', 'Delivered')], default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)                

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)    