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
        logger.info("Fulfillment started for Order %s", order.order_id)
        
        try:
            shipping = ShippingService.create_shipping_from_order(order)
            if shipping:
                logger.info("Fulfillment success for Order %s", order.order_id)
            else:
                logger.info("Fulfillment handled for Pickup Order %s", order.order_id)
        except Exception:
            logger.exception("Fulfillment failed for Order %s", order.order_id)
            raise
