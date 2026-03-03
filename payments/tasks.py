# payments/tasks.py
import logging
from django.db import transaction
from django.db.models import F
from payments.models import Payment
from products.models import Product
from products.models import Reservation
import utils

logger = logging.getLogger(__name__)


def handle_payment_success(reference, order_id):
    from django_q.tasks import async_task
    try:
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(
                paystack_reference=reference,
                is_processed=False
            )

            payment.status   = utils.paymentConstants.PaymentStatus.SUCCESS
            payment.is_processed = True
            payment.save()

            order = payment.order

            # confirm reservations and deduct actual stock
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

            # clear cart
            order.user.cart.items.all().delete()

            # update order status
            order.status = 'confirmed'
            order.save()

            # send confirmation email
            async_task('payments.tasks._send_confirmation_email', order.id, payment.id)

            logger.info(f"Payment success handled for order {order.id}")

    except Payment.DoesNotExist:
        logger.info(f"Payment {reference} not found or already processed")


def handle_payment_failed(reference, order_id):
    try:
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(paystack_reference=reference)
            payment.status       = utils.paymentConstants.PaymentStatus.FAILED
            payment.is_processed = True
            payment.save()

            # cancel reservations — no stock to restore since we never touched it
            Reservation.objects.filter(
                order=payment.order,
                status=Reservation.Status.ACTIVE
            ).update(status=Reservation.Status.CANCELLED)

            logger.info(f"Payment failed handled for order {payment.order.id}")

    except Payment.DoesNotExist:
        logger.info(f"Failed payment {reference} not found")


def handle_payment_abandoned(reference, order_id):
    try:
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(paystack_reference=reference)
            payment.status       = utils.paymentConstants.PaymentStatus.ABANDONED
            payment.is_processed = True
            payment.save()

            # cancel reservations — no stock to restore since we never touched it
            Reservation.objects.filter(
                order=payment.order,
                status=Reservation.Status.ACTIVE
            ).update(status=Reservation.Status.CANCELLED)

            logger.info(f"Payment abandoned handled for order {payment.order.id}")

    except Payment.DoesNotExist:
        logger.info(f"Abandoned payment {reference} not found")


def _send_confirmation_email(order_id, payment_id):
    from utils.email_templates import get_order_confirmation_html
    from payments.tasks import send_order_confirmation_email
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