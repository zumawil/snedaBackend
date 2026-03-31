from celery import shared_task
import logging
from datetime import timedelta
from django.utils import timezone
from orders.models import Order
from utils.paymentConstants import PaymentStatus
from payments.models import Payment
from django.db.models import Exists, OuterRef
from services.checkout_service import CheckoutService
from utils.paymentConstants import Status as OrderStatus

logger = logging.getLogger(__name__)

@shared_task
def cancel_unpaid_orders():
    timeout = timezone.now() - timedelta(minutes=30)
    
    # orders that have NO successful payment
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
        CheckoutService._cancel_order_and_restore_stock(order)
        count += 1
        
    if count > 0:
        logger.info(f"Cleanup Task: Cancelled and restored stock for {count} abandoned orders.")
    return f"Cleanup Task: Cancelled {count} orders."
