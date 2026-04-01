import logging
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist as RelatedObjectDoesNotExist
from shipping.models import Shipping
from shipping.generate_shipping_number import generate_tracking_number
from orders.models import Order, PickupFulfillment
from carts.models import CheckoutAttempt
from utils.paymentConstants import OrderStatus

logger = logging.getLogger(__name__)

class ShippingService:
    @staticmethod
    @transaction.atomic
    def create_shipping_from_order(order):
        """
        Create a fulfillment record (Shipping or PickupFulfillment) for a paid order.
        Retrieves address/location from CheckoutAttempt.
        Includes idempotency guard and standard status management.
        """
        # Lock the order row to prevent concurrent fulfillment creation
        order = Order.objects.select_for_update().get(pk=order.pk)

        # 1. Idempotency guard: check if fulfillment already exists
        existing_shipping = None
        existing_pickup = None
        
        try:
            existing_shipping = order.shipping
        except RelatedObjectDoesNotExist:
            pass
            
        try:
            existing_pickup = order.pickup_fulfillment
        except RelatedObjectDoesNotExist:
            pass
            
        if existing_shipping or existing_pickup:
            logger.info(f"Fulfillment already exists for Order {order.order_id}, skipping creation.")
            return existing_shipping or existing_pickup

        # 2. Validate order state (Must be paid)
        if order.status != OrderStatus.PAID:
            logger.error(f"Cannot create fulfillment for Order {order.order_id} with status {order.status}")
            raise ValueError(f"Cannot create fulfillment for unpaid order (Status: {order.status})")

        # Get fulfillment data from CheckoutAttempt
        checkout_attempt = CheckoutAttempt.objects.filter(order=order).first()
        if not checkout_attempt:
            raise ValueError(f"No checkout attempt found for Order {order.order_id}")
        
        address = checkout_attempt.address
        pickup_location = checkout_attempt.pickup_location

        # 3. Handle Pickup vs Delivery
        if order.is_pickup:
            # Create PickupFulfillment for pickup orders
            if not pickup_location:
                raise ValueError("Pickup location required for pickup orders")
            
            pickup_fulfillment = PickupFulfillment.objects.create(
                order=order,
                location=pickup_location,
                status=PickupFulfillment.Status.PENDING
            )
            logger.info(f"PickupFulfillment created for Order {order.order_id} at {pickup_location}")
            return pickup_fulfillment
        else:
            # Create Shipping for delivery orders
            if not address:
                raise ValueError("Delivery address required for delivery orders")
            
            tracking_number = generate_tracking_number()
            shipping = Shipping.objects.create(
                order=order,
                status="pending",
                tracking_number=tracking_number,
                address=address
            )
            logger.info(f"Shipping created for Order {order.order_id} with tracking: {tracking_number}")
            return shipping
