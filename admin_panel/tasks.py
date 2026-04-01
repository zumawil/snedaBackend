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
import socket
import smtplib
from celery import shared_task
from background_tasks.models import BackgroundJob
from utils.email_templates import (
    get_order_approved_html,
    get_order_disapproved_html,
    get_shipping_status_update_html,
    get_order_cancelled_html
)
from utils.sendEmail import send_admin_notification_email
from orders.models import Order

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_approved_email_task(self, job_id, order_id, user_id=None):
    """
    Background Celery task: send email when admin approves an order.
    Retries up to 3 times (60-second delay) only on transient failures
    (SMTP, network, connection errors). Non-retriable errors (Order.DoesNotExist,
    template errors, validation errors) are logged but not retried.
    """
    import socket
    import smtplib
    
    job = None
    logger.info(f"[TASK] send_order_approved_email_task started | job_id={job_id} order_id={order_id}")
    
    try:
        # Fetch job
        try:
            job = BackgroundJob.objects.get(id=job_id)
        except BackgroundJob.DoesNotExist:
            logger.error(f"Job with id {job_id} not found for order approved email task")
            return

        # Mark job as processing
        job.mark_processing()
        if user_id:
            job.user_id = user_id
            job.save(update_fields=['user'])

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
        if job:
            job.mark_failed(f"Order {order_id} not found")
        return
    
    except Exception as exc:
        # Template errors, validation errors, or other DB issues
        logger.error(
            f"Failed to prepare order approval email data for order {order_id}: {exc}",
            exc_info=True
        )
        if job:
            job.mark_failed(f"Preparation error: {str(exc)}")
        return
    
    # Step 2: Send email (retry only on transient errors)
    try:
        send_admin_notification_email(
            order.user.email,
            f"Order Approved - #{order.id} - Sneda Ecommerce",
            email_html
        )
    except (smtplib.SMTPException, socket.error, ConnectionError, TimeoutError) as exc:
        # Transient errors - retry
        logger.error(f"Transient error sending order approval email for order {order_id}: {exc}", exc_info=True)
        if job and self.request.retries >= self.max_retries:
            job.mark_failed(f"Transient SMTP error after retries: {str(exc)}")
        raise self.retry(exc=exc)
    except Exception as exc:
        # Permanent failures (invalid email, etc.) - do not retry
        logger.error(f"Permanent error sending order approval email for order {order_id}: {exc}", exc_info=True)
        if job:
            job.mark_failed(f"Permanent sending error: {str(exc)}")
        return

    # Step 3: Mark job completed (non-retryable for email)
    try:
        if job:
            job.mark_completed()
            logger.info(f"Order approval email sent for order {order.id}")
    except Exception as e:
        logger.error(f"Failed to mark job {job_id} as completed: {str(e)}")

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_disapproved_email_task(self, job_id, order_id, user_id=None, reason=None):
    """
    Background Celery task: send email when admin rejects an order.
    Retries up to 3 times (60-second delay) on any failure.
    """
    job = None
    logger.info(f"[TASK] send_order_disapproved_email_task started | job_id={job_id} order_id={order_id}")

    # Fetch job
    try:
        job = BackgroundJob.objects.get(id=job_id)
    except BackgroundJob.DoesNotExist:
        logger.error(f"Job with id {job_id} not found for order disapproved email task")
        return

    # Mark job as processing
    job.mark_processing()
    if user_id:
        job.user_id = user_id
        job.save(update_fields=['user'])

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} does not exist. Email not sent.")
        job.mark_failed(f"Order {order_id} does not exist")
        return  # stop task, no retry

    # Generate email HTML
    email_html = get_order_disapproved_html(
        order_id=order.id,
        user_first_name=order.user.first_name,
        reason=reason
    )

    # Send email (retryable block)
    try:
        from utils.sendEmail import send_admin_notification_email
        send_admin_notification_email(
            order.user.email,
            f"Order Update - #{order.id} - Sneda Ecommerce",
            email_html
        )
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        
        # If retries exhausted → mark failed
        if job:
            job.mark_failed(f"Error sending disapproval email: {str(exc)}")
        return f"Failed to send disapproval email for order {order.id}"

    # Mark job completed (non-retryable for email)
    try:
        if job:
            job.mark_completed()
            logger.info(f"Order rejection email sent for order {order.id}")
    except Exception as e:
        logger.error(f"Failed to mark job {job_id} as completed: {str(e)}")

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_shipping_status_email_task(self, job_id, order_id, new_status, user_id=None, order_id_display=None, fulfillment=None, **kwargs):
    """
    Background Celery task: send email when shipping status is updated.
    Retries up to 3 times (60-second delay) on any failure.
    """
    # Handle legacy tracking_number
    _ = kwargs.pop('tracking_number', None)
    job = None
    logger.info(f"[TASK] send_shipping_status_email_task started | job_id={job_id} order_id={order_id} status={new_status}")

    # Fetch job
    try:
        job = BackgroundJob.objects.get(id=job_id)
    except BackgroundJob.DoesNotExist:
        logger.error(f"Job with id {job_id} not found for shipping status email task")
        return

    # Mark job as processing
    job.mark_processing()
    if user_id:
        job.user_id = user_id
        job.save(update_fields=['user'])

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} does not exist. Email not sent.")
        job.mark_failed(f"Order {order_id} does not exist")
        return  # stop task, no retry

    email_html = get_shipping_status_update_html(
        order_id=order_id_display or order.order_id or order.id,
        user_first_name=order.user.first_name,
        new_status=new_status,
        fulfillment=fulfillment
    )

    # Send email (retryable block)
    try:
        from utils.sendEmail import send_admin_notification_email
        send_admin_notification_email(
            order.user.email,
            f"Shipping Update - Order #{order.id} - Sneda Ecommerce",
            email_html
        )
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        
        # If retries exhausted → mark failed
        if job:
            job.mark_failed(f"Error sending shipping update email: {str(exc)}")
        return f"Failed to send shipping update for order {order.id}"

    # Mark job completed (non-retryable for email)
    try:
        if job:
            job.mark_completed()
            logger.info(f"Shipping status email sent for order {order.id}")
    except Exception as e:
        logger.error(f"Failed to mark job {job_id} as completed: {str(e)}")

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_cancelled_email_task(self, job_id, order_id, user_id=None):
    """
    Background Celery task: send email when admin cancels an order.
    Retries up to 3 times (60-second delay) on any failure.
    """
    job = None
    logger.info(f"[TASK] send_order_cancelled_email_task started | job_id={job_id} order_id={order_id}")

    # Fetch job
    try:
        job = BackgroundJob.objects.get(id=job_id)
    except BackgroundJob.DoesNotExist:
        logger.error(f"Job with id {job_id} not found for order cancelled email task")
        return

    # Mark job as processing
    job.mark_processing()
    if user_id:
        job.user_id = user_id
        job.save(update_fields=['user'])

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} does not exist. Email not sent.")
        if job:
            job.mark_failed(f"Order {order_id} does not exist")
        return  # stop task, no retry

    # Generate email HTML
    email_html = get_order_cancelled_html(
        order_id=order.id,
        user_first_name=order.user.first_name
    )

    # Send email (retryable block)
    try:
        from utils.sendEmail import send_admin_notification_email
        send_admin_notification_email(
            order.user.email,
            f"Order Cancelled - #{order.id} - Sneda Ecommerce",
            email_html
        )
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        
        # If retries exhausted → mark failed
        if job:
            job.mark_failed(f"Error sending cancellation email: {str(exc)}")
        return f"Failed to send cancellation email for order {order.id}"

    # Mark job completed (non-retryable for email)
    try:
        if job:
            job.mark_completed()
            logger.info(f"Order cancellation email sent for order {order.id}")
    except Exception as e:
        logger.error(f"Failed to mark job {job_id} as completed: {str(e)}")
