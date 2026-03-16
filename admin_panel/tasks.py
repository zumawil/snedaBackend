# admin_panel/tasks.py
"""
Celery background tasks for admin panel email notifications.
Sends emails to users when:
- Order is approved
- Order is rejected/disapproved
- Shipping status is updated
"""

import logging
import traceback
from celery import shared_task

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_approved_email_task(self, order_id):
    """
    Background Celery task: send email when admin approves an order.
    Retries up to 3 times (60-second delay) only on transient failures
    (SMTP, network, connection errors). Non-retriable errors (Order.DoesNotExist,
    template errors, validation errors) are logged but not retried.
    """
    import socket
    import smtplib
    
    logger.info(f"[TASK] send_order_approved_email_task started | order_id={order_id}")
    
    # Step 1: DB lookup and template rendering (no retry on failure)
    try:
        from utils.email_templates import get_order_approved_html
        from orders.models import Order
        
        order = Order.objects.get(id=order_id)
        
        # Build order items summary
        items_summary = "\n".join([
            f"- {item.product.item_no} x {item.quantity}: GHS {item.get_total_price()}"
            for item in order.items.all()
        ])
        
        # Generate email HTML
        email_html = get_order_approved_html(
            order_id=order.id,
            user_first_name=order.user.first_name,
            items_summary=items_summary,
            total_amount=order.total_amount
        )
        
    except Order.DoesNotExist:
        logger.error(
            f"Order {order_id} not found - cannot send approval email",
            exc_info=True
        )
        # Do not retry - order doesn't exist, retrying won't help
        return
    
    except Exception as exc:
        # Template errors, validation errors, or other DB issues
        logger.error(
            f"Failed to prepare order approval email data for order {order_id}: {exc}",
            exc_info=True
        )
        # Do not retry - these are permanent failures
        return
    
    # Step 2: Send email (retry only on transient errors)
    try:
        from utils.sendEmail import send_admin_notification_email
        
        send_admin_notification_email(
            order.user.email,
            f"Order Approved - #{order.id} - Sneda Ecommerce",
            email_html
        )
        
        logger.info(f"Order approval email sent for order {order.id}")
        
    except (smtplib.SMTPException, socket.error, ConnectionError, TimeoutError) as exc:
        # Transient errors - retry
        logger.error(
            f"Transient error sending order approval email for order {order_id}: {exc}",
            exc_info=True
        )
        raise self.retry(exc=exc)
    
    except Exception as exc:
        # Permanent failures (invalid email, etc.) - do not retry
        logger.error(
            f"Permanent error sending order approval email for order {order_id}: {exc}",
            exc_info=True
        )
        # Do not retry - these are permanent failures
        return

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_disapproved_email_task(self, order_id, reason=None):
    """
    Background Celery task: send email when admin rejects an order.
    Retries up to 3 times (60-second delay) on any failure.
    """
    logger.info(f"[TASK] send_order_disapproved_email_task started | order_id={order_id}")

    try:
        from utils.email_templates import get_order_disapproved_html
        from utils.sendEmail import send_admin_notification_email
        from orders.models import Order

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} does not exist. Email not sent.")
            return  # stop task, no retry

        # Generate email HTML
        email_html = get_order_disapproved_html(
            order_id=order.id,
            user_first_name=order.user.first_name,
            reason=reason
        )

        # Send email
        send_admin_notification_email(
            order.user.email,
            f"Order Update - #{order.id} - Sneda Ecommerce",
            email_html
        )

        logger.info(f"Order rejection email sent for order {order.id}")

    except Exception as exc:
        logger.error(
            f"Failed to send order rejection email for order {order_id}: {exc}",
            exc_info=True
        )
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_shipping_status_email_task(self, order_id, new_status, tracking_number=None):
    """
    Background Celery task: send email when shipping status is updated.
    Retries up to 3 times (60-second delay) on any failure.
    """
    logger.info(f"[TASK] send_shipping_status_email_task started | order_id={order_id} status={new_status}")

    try:
        from utils.email_templates import get_shipping_status_update_html
        from utils.sendEmail import send_admin_notification_email
        from orders.models import Order

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} does not exist. Email not sent.")
            return  # stop task, no retry

        # Generate email HTML
        email_html = get_shipping_status_update_html(
            order_id=order.id,
            user_first_name=order.user.first_name,
            new_status=new_status,
            tracking_number=tracking_number
        )

        # Send email
        send_admin_notification_email(
            order.user.email,
            f"Shipping Update - Order #{order.id} - Sneda Ecommerce",
            email_html
        )

        logger.info(f"Shipping status email sent for order {order.id}")

    except Exception as exc:
        logger.error(
            f"Failed to send shipping status email for order {order_id}: {exc}",
            exc_info=True
        )
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_cancelled_email_task(self, order_id):
    """
    Background Celery task: send email when admin cancels an order.
    Retries up to 3 times (60-second delay) on any failure.
    """
    logger.info(f"[TASK] send_order_cancelled_email_task started | order_id={order_id}")

    try:
        from utils.email_templates import get_order_cancelled_html
        from utils.sendEmail import send_admin_notification_email
        from orders.models import Order

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} does not exist. Email not sent.")
            return  # stop task, no retry

        # Generate email HTML
        email_html = get_order_cancelled_html(
            order_id=order.id,
            user_first_name=order.user.first_name
        )

        # Send email
        send_admin_notification_email(
            order.user.email,
            f"Order Cancelled - #{order.id} - Sneda Ecommerce",
            email_html
        )

        logger.info(f"Order cancellation email sent for order {order.id}")

    except Exception as exc:
        logger.error(
            f"Failed to send order cancellation email for order {order_id}: {exc}",
            exc_info=True
        )
        raise self.retry(exc=exc)
