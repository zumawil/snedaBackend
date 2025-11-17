# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from shipping.models import Shipping

# from .models import Order

# @receiver(post_save, sender=Order)
# def create_shipping_for_order(sender, instance, created, **kwargs):
#     order = instance
#     if created: # only true when order is created
#         Shipping.objects.create(order=order,
#                                 status=order.status,
#                                 )

