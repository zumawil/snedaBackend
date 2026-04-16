from celery import shared_task
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction, models
from orders.models import Order
from utils.paymentConstants import PaymentStatus
from payments.models import Payment
from django.db.models import Exists, OuterRef
from services.checkout_service import CheckoutService
from utils.paymentConstants import OrderStatus

logger = logging.getLogger(__name__)

@shared_task
def cancel_unpaid_orders():
    timeout = timezone.now() - timedelta(minutes=30)
    
    # Initial query for potentially abandoned orders
    has_successful_payment = Payment.objects.filter(
        order=OuterRef('pk'),
        status=PaymentStatus.SUCCESS
    )
    
    unpaid_orders = Order.objects.filter(
        created_at__lt=timeout,
        status=OrderStatus.PENDING
    ).exclude(
        Exists(has_successful_payment)
    )
    
    count = 0
    for order in unpaid_orders:
        try:
            with transaction.atomic():
                # 1. Lock the order row to prevent concurrent updates (e.g. from webhooks)
                locked_order = Order.objects.select_for_update().get(pk=order.pk)
                
                # 2. Re-verify abandonment criteria under lock
                # We check BOTH the order status AND the existence of a success payment
                has_paid_now = Payment.objects.filter(
                    order=locked_order,
                    status=PaymentStatus.SUCCESS
                ).exists()

                if locked_order.status == OrderStatus.PENDING and not has_paid_now:
                    CheckoutService._cancel_order_and_restore_stock(locked_order)
                    count += 1
                else:
                    logger.info(
                        f"Cleanup Task: Skipping order {locked_order.id}. "
                        f"Status: {locked_order.status}, Has Success Payment: {has_paid_now}"
                    )
        except Exception as e:
            logger.error(f"Cleanup Task: Failed to process order {order.id}: {str(e)}")
        
    if count > 0:
        logger.info(f"Cleanup Task: Cancelled and restored stock for {count} abandoned orders.")
    return f"Cleanup Task: Cancelled {count} orders."
