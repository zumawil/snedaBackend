# payments/tasks.py
"""
Celery background tasks for the payments app.
Webhook event logic lives in payments/webhook_handlers.py.
"""

import logging
import traceback
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_confirmation_email_task(self, order_id, payment_id):
    """
    Background Celery task: build and send the order confirmation email.
    Retries up to 3 times (60-second delay) on any failure.
    """
    logger.info(f"[TASK] send_confirmation_email_task started | order_id={order_id} payment_id={payment_id}")

    try:
        from utils.email_templates import get_order_confirmation_html
        from utils.sendEmail import send_order_confirmation_email
        from orders.models import Order
        from payments.models import Payment

        order = Order.objects.get(id=order_id)
        payment = Payment.objects.get(id=payment_id)

        order_items_summary = "\n".join([
            f"- {item.product.item_no} x {item.quantity}: GHS {item.get_total_price()}"
            for item in order.items.all()
        ])

        email_html = get_order_confirmation_html(
            order_id=order.id,
            user_first_name=order.user.first_name,
            amount=payment.amount,
            order_items_summary=order_items_summary,
            total_amount=order.total_amount
        )

        send_order_confirmation_email(
            order.user.email,
            f"Order Confirmation - #{order.id} - Sneda Ecommerce",
            email_html
        )
        logger.info(f"Order confirmation email sent for order {order.id}")

    except Exception as exc:
        # Log the FULL traceback so you can see exactly which line failed
        logger.error(
            f"Failed to send confirmation email for order {order_id}: {exc}",
            exc_info=True   # <-- this includes the full stack trace in the log
        )
        raise self.retry(exc=exc)