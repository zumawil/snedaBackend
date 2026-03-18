# payments/tasks.py
"""
Celery background tasks for the payments app.
Webhook event logic lives in payments/webhook_handlers.py.
"""

import logging
import traceback
from celery import shared_task
from background_tasks.models import BackgroundJob
from utils.email_templates import get_order_confirmation_html
from utils.sendEmail import send_order_confirmation_email
from orders.models import Order
from payments.models import Payment

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_confirmation_email_task(self, job_id, order_id, payment_id):
    """
    Background Celery task: build and send the order confirmation email.
    Retries up to 3 times (60-second delay) on any failure.
    """
    job = None
    logger.info(f"[TASK] send_confirmation_email_task started | job_id={job_id} order_id={order_id} payment_id={payment_id}")

    # Fetch job
    try:
        job = BackgroundJob.objects.get(id=job_id)
    except BackgroundJob.DoesNotExist:
        logger.error(f"Job with id {job_id} not found for confirmation email task")
        return

    # Mark job as processing
    job.mark_processing()

    try:
        order = Order.objects.get(id=order_id)
        payment = Payment.objects.get(id=payment_id)
    except Order.DoesNotExist:
        logger.error(f"Order with id {order_id} not found for confirmation email task")
        job.mark_failed(f"Order {order_id} not found")
        return
    except Payment.DoesNotExist:
        logger.error(f"Payment with id {payment_id} not found for confirmation email task")
        job.mark_failed(f"Payment {payment_id} not found")
        return

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

    # 1. Send email (retryable block)
    try:
        send_order_confirmation_email(
            order.user.email,
            f"Order Confirmation - #{order.id} - Sneda Ecommerce",
            email_html
        )
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        
        # If retries exhausted → mark failed
        if job:
            job.mark_failed(f"Error sending confirmation email: {str(exc)}")
        return f"Failed to send confirmation email for order {order.id}"
        
    # 2. Mark job completed (non-retryable for email)
    try:
        if job:
            job.mark_completed()
            logger.info(f"Order confirmation email sent for order {order.id}")
    except Exception as e:
        logger.error(f"Failed to mark job {job_id} as completed: {str(e)}")

    return f"Confirmation email sent for order {order.id}"