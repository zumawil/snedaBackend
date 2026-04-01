# payments/webhook_handlers.py
"""
Webhook event handlers for Paystack payment events.

Each function is called directly from WebhookView after the
Paystack signature has been verified. Heavy work (email) is
offloaded to a Celery background task.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from payments.models import Payment
from products.models import Product
from orders.models import Reservation, Order
from services.fulfillment_service import FulfillmentService
from background_tasks.models import BackgroundJob
import utils

logger = logging.getLogger(__name__)


def handle_payment_success(reference, order_id):
    """
    charge.success handler.

    - Marks the payment as SUCCESS
    - Deducts stock and confirms reservations
    - Clears the user's cart
    - Updates the order status to 'paid'
    - Triggers fulfillment (shipping, etc.)
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

            # Defense in Depth: Lock the order and check if already processed
            order = Order.objects.select_for_update().get(pk=payment.order.pk)
            if order.status == utils.paymentConstants.OrderStatus.PAID:
                logger.info(f"Order {order.id} already processed (PAID), skipping stock deduction")
                return

            # Confirm reservations and deduct actual stock
            reservations = Reservation.objects.select_for_update().filter(
                order=order,
                # get expired reservations to cater for late webhooks
                status__in=[Reservation.Status.ACTIVE, Reservation.Status.EXPIRED]
            )
            
            # Now handle stock deduction and order status
            try:
                # 1. First, check availability for ALL items in the order
                # This ensures we don't partially fulfill an order.
                items_to_deduct = []
                for reservation in reservations:
                    # Use a 2-minute grace period for late webhooks
                    grace_expiry = reservation.expires_at + timedelta(minutes=2)
                    is_actually_expired = timezone.now() > grace_expiry
                    
                    if is_actually_expired or reservation.status == Reservation.Status.EXPIRED:
                        available = reservation.product.available_stock()
                        if available < reservation.quantity:
                                logger.critical(
                                    f"STOCK OVERSELL: Order {order.id} paid for {reservation.product.item_no} "
                                    f"but stock is unavailable (Available: {available}, Requested: {reservation.quantity})."
                                )
                                raise ValueError(f"Insufficient stock for product {reservation.product.item_no}")

                    items_to_deduct.append(reservation)

                # 2. Now perform atomic deduction for all items
                # We wrap this in a nested transaction so that if one item fails,
                # ALL items for this order are rolled back, but the payment stays SUCCESS.
                with transaction.atomic():
                    for reservation in items_to_deduct:
                        updated = Product.objects.filter(
                            pk=reservation.product.pk,
                            inventory_qty__gte=reservation.quantity
                        ).update(
                            inventory_qty=F('inventory_qty') - reservation.quantity
                        )

                        if updated == 0:
                            raise ValueError(f"Concurrency error: Stock taken for {reservation.product.item_no}")

                        reservation.status = Reservation.Status.CONFIRMED
                        reservation.save()

                    # Clear cart
                    order.user.cart.items.all().delete()

                    # Update order status to PAID (fulfillment follows)
                    order.status = utils.paymentConstants.OrderStatus.PAID
                    order.save()

                    # 1. Create the tracking record for email
                    job = BackgroundJob.objects.create(
                        task_type="send_confirmation_email",
                        related_object_type="order",
                        related_object_id=order.id,
                        user=order.user
                    )

                    # 2. Queue the Celery task and Fulfillment safely
                    def dispatch_post_payment_actions():
                        try:
                            FulfillmentService.handle_post_payment(order)
                        except Exception:
                            logger.exception("Failed to trigger fulfillment for order %s", order.id)

                        try:
                            result = send_confirmation_email_task.delay(job.id, order.id, payment.id, order.user.id)
                            BackgroundJob.objects.filter(pk=job.pk).update(task_id=result.id)
                        except Exception as exc:
                            logger.exception("Failed to enqueue confirmation email for order %s", order.id)
                            job.mark_failed(f"Dispatch error: {exc!s}")

                    transaction.on_commit(dispatch_post_payment_actions)
                    logger.info(f"Payment success handled for order {order.id}")

            except ValueError as e:
                # We do NOT rollback the entire transaction because we want to keep
                # the payment marked as SUCCESS (since we have the money).
                # We only log the failure. The Order remains PENDING or PAID (without fulfillment).
                logger.error(f"Fulfillment blocked for PAID order {order.id}: {str(e)}")
                order.marked_for_review = True
                order.status = utils.paymentConstants.OrderStatus.PAID
                order.save(update_fields=['marked_for_review', 'status'])
                
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
