from django.db import models

# Create your models here.

class ProductGroup(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class HSCode(models.Model):
    code = models.CharField(max_length=100)

    def __str__(self):
        return self.code

class Brand(models.Model):
    name = models.CharField(max_length=300)

class Category(models.Model):
    name = models.CharField(max_length=300, null=False, blank=False)

    def __str__(self):
        return self.name
    
class Product(models.Model):
    item_no = models.CharField(max_length=50, unique=True, primary_key=True)
    product_group = models.ForeignKey(ProductGroup, related_name='products', on_delete=models.CASCADE)
    # description 
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)

    hs_code = models.ForeignKey(HSCode, related_name='products', on_delete=models.CASCADE)
    gtin = models.CharField(max_length=14, unique=True, null=True, blank=True)

    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    box_qty = models.IntegerField(null=True, blank=True)
    inventory_qty = models.IntegerField(default=0)

    #expected_arrival = models.DateField(null=True, blank=True)

    gross_price = models.DecimalField(max_digits=10, decimal_places=2)
    brand = models.ForeignKey(Brand, related_name='products', on_delete=models.CASCADE)

    in_stock = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item_no} - {self.category.name}"


    
class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    url = models.URLField(max_length=255, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Image for {self.product.item_no}"
    
