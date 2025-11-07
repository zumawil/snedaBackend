from django.contrib import admin
from django.contrib.auth.models import Permission, Group

# Register your models here.
from .models import CustomUser

admin.site.register([CustomUser])
admin.site.register(Permission)
admin.site.register(Group)