from django.db import models
from users.models import CustomUser as User
from products.models import Product
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
class Reviews(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE, 
        related_name='reviews', 
        null=True, blank=True
    )
    content = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    rating = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    def __str__(self):
        return f"Review by {self.user.email} on {self.product}"


    class Meta:
        ordering = ['-date_created']