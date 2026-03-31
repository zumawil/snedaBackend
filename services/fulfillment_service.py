import logging
from .shipping_service import ShippingService

logger = logging.getLogger(__name__)

class FulfillmentService:
    @staticmethod
    def handle_post_payment(order):
        """
        Main entry point for all post-payment activities.
        Calls ShippingService and any other future-proof actions.
        """
        logger.info(f"Fulfillment started for Order {order.order_id}")
        
        try:
            shipping = ShippingService.create_shipping_from_order(order)
            if shipping:
                logger.info(f"Fulfillment success for Order {order.order_id}")
            else:
                logger.info(f"Fulfillment handled for Pickup Order {order.order_id}")
        except Exception as e:
            logger.error(f"Fulfillment failed for Order {order.order_id}: {str(e)}")
            # Raise here or handle gracefully; webhook handler will log it.
            raise e
