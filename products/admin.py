from django.contrib import admin
from .models import (Category, Product, ProductImage, HSCode, ProductGroup, Brand)

# Register your models here.
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(HSCode)
admin.site.register(ProductGroup)
admin.site.register(Brand)

