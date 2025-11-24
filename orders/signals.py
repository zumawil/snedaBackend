# import logging
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from shipping.models import Shipping
# from shipping.generate_shipping_number import generate_tracking_number

# from .models import Order

# logger = logging.getLogger(__name__)

# # only create shipping when order is created
# @receiver(post_save, sender=Order)
# def create_shipping_for_order(sender, instance, created, **kwargs):
#     order = instance
#     # if order is created, create shipping
#     if created:
#         logger.info(f"Creating shipping record for order {order.id}")
#         Shipping.objects.create(
#             order=order,
#             status='pending',
#             tracking_number=generate_tracking_number(),
#             address="accra",
#             pickup = False
#         )
#         logger.info(f"Shipping record created for order {order.id}")

