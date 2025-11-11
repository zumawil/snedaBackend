from django.db import models
from users.models import CustomUser as User
from products.models import Product
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
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} of {self.product.name} in cart of {self.cart.user.email}"
    
    # a user can buy more of one thing , this calculaes the sum of it
    def get_total_price(self):
        return self.quantity * self.product.price


