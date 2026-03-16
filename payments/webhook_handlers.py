# payments/webhook_handlers.py
"""
Webhook event handlers for Paystack payment events.

Each function is called directly from WebhookView after the
Paystack signature has been verified. Heavy work (email) is
offloaded to a Celery background task.
"""

import logging
from django.db import transaction
from django.db.models import F
from payments.models import Payment
from products.models import Product
from orders.models import Reservation
from background_tasks.models import BackgroundJob
import utils

logger = logging.getLogger(__name__)


def handle_payment_success(reference, order_id):
    """
    charge.success handler.

    - Marks the payment as SUCCESS
    - Deducts stock and confirms reservations
    - Clears the user's cart
    - Updates the order status to 'confirmed'
    - Fires a Celery task to send an order confirmation email
    """
    # Import here to avoid circular imports (tasks -> webhook_handlers -> tasks)
    from payments.tasks import send_confirmation_email_task

    try:
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(
                paystack_reference=reference,
                is_processed=False
            )

            payment.status = utils.paymentConstants.PaymentStatus.SUCCESS
            payment.is_processed = True
            payment.save()

            order = payment.order

            # Confirm reservations and deduct actual stock
            reservations = Reservation.objects.select_for_update().filter(
                order=order,
                status=Reservation.Status.ACTIVE
            )
            for reservation in reservations:
                Product.objects.filter(pk=reservation.product.pk).update(
                    inventory_qty=F('inventory_qty') - reservation.quantity
                )
                reservation.status = Reservation.Status.CONFIRMED
                reservation.save()

            # Clear cart
            order.user.cart.items.all().delete()

            # Update order status
            order.status = 'confirmed'
            order.save()

            # 1. Create the tracking record in 'pending' state
            job = BackgroundJob.objects.create(
                task_type="send_confirmation_email",
                related_object_type="order",
                related_object_id=order.id
            )

            # 2. Queue the Celery task safely
            def dispatch_task():
                result = send_confirmation_email_task.delay(job.id, order.id, payment.id)
                # Capture the Celery task_id immediately
                job.task_id = result.id
                job.save(update_fields=['task_id'])

            transaction.on_commit(dispatch_task)

            logger.info(f"Payment success handled for order {order.id}")

    except Payment.DoesNotExist:
        logger.info(f"Payment {reference} not found or already processed")


def handle_payment_failed(reference, order_id):
    """
    charge.failed handler.

    Marks the payment as FAILED and cancels all active reservations.
    No stock restoration is needed because stock is only deducted on success.
    """
    try:
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(paystack_reference=reference)
            payment.status = utils.paymentConstants.PaymentStatus.FAILED
            payment.is_processed = True
            payment.save()

            Reservation.objects.filter(
                order=payment.order,
                status=Reservation.Status.ACTIVE
            ).update(status=Reservation.Status.CANCELLED)

            logger.info(f"Payment failed handled for order {payment.order.id}")

    except Payment.DoesNotExist:
        logger.info(f"Failed payment {reference} not found")


def handle_payment_abandoned(reference, order_id):
    """
    charge.abandoned handler.

    Marks the payment as ABANDONED and cancels all active reservations.
    No stock restoration is needed because stock is only deducted on success.
    """
    try:
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(paystack_reference=reference)
            payment.status = utils.paymentConstants.PaymentStatus.ABANDONED
            payment.is_processed = True
            payment.save()

            Reservation.objects.filter(
                order=payment.order,
                status=Reservation.Status.ACTIVE
            ).update(status=Reservation.Status.CANCELLED)

            logger.info(f"Payment abandoned handled for order {payment.order.id}")

    except Payment.DoesNotExist:
        logger.info(f"Abandoned payment {reference} not found")
