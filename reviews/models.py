from django.db import models
from products.models import Product
from django.core.validators import MinValueValidator, MaxLengthValidator

# Create your models here.
class Reviews(models.Model):
    product = models.ForeignKey(Product, models.CASCADE, related_name='reviews', null=True, blank=True)
    content = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    rating = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxLengthValidator(5)]
    )

    def __str__(self):
        return f"Review by {self.user.username} on {self.product.name}"