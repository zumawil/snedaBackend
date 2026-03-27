import logging
from django.db import transaction
from shipping.models import Shipping
from shipping.generate_shipping_number import generate_tracking_number
from orders.models import Order

logger = logging.getLogger(__name__)

class ShippingService:
    @staticmethod
    def create_shipping_from_order(order):
        """
        Create a shipping record for a paid order.
        Includes idempotency guard and standard status management.
        """
        # 1. Idempotency guard: check if shipping already exists
        # In Django, OneToOne reverse relation can be checked via hasattr or getattr
        existing_shipping = getattr(order, 'shipping', None)
        if existing_shipping:
            logger.info(f"Shipping already exists for Order {order.order_id}, skipping creation.")
            return existing_shipping

        # 2. Validate order state (Must be paid)
        # We use the text choices from Order.Status if possible, 
        # but the user's plan specifically mentioned "paid".
        if order.status != Order.Status.PAID:
            logger.error(f"Cannot create shipping for Order {order.order_id} with status {order.status}")
            raise ValueError(f"Cannot create shipping for unpaid order (Status: {order.status})")

        # 3. Handle Pickup vs Delivery
        # If it's a pickup, we might still want a record or handle it differently.
        # Following the user's plan: "Skip Shipping (or Pickup model)"
        if order.is_pickup:
            logger.info(f"Order {order.order_id} is a pickup. Skipping dynamic shipping record creation.")
            return None

        with transaction.atomic():
            tracking_number = generate_tracking_number()
            shipping = Shipping.objects.create(
                order=order,
                status="pending",
                tracking_number=tracking_number,
                address=order.shipping_address,
                pickup=order.is_pickup,
                pickup_location=order.pickup_location
            )
            
            # Update order status to fulfilled (or keep as paid until dispatched?)
            # Usually 'fulfilled' means the shipment is prepared.
            # The user's transition was pending -> paid -> fulfilled -> delivered.
            # So creating the shipping record is the 'fulfillment' step.
            order.status = Order.Status.FULFILLED
            order.save(update_fields=['status'])
            
            logger.info(f"Shipping created for Order {order.order_id} with tracking: {tracking_number}")
            return shipping
