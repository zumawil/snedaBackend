from celery import shared_task
from orders.models import Reservation
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task
def expire_reservations():
    """Expire reservations that are older than 15 minutes"""
    reservations = Reservation.objects.filter(
        status=Reservation.Status.ACTIVE,
        expires_at__lt=timezone.now()
    )
    count = reservations.count()  
    for reservation in reservations:
        reservation.status = Reservation.Status.EXPIRED
        reservation.save()
    logger.info(f"Expired {count} reservations")
    return f"Expired {count} reservations"