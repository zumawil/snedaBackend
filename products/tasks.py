from celery import shared_task
from orders.models import Reservation
from django.utils import timezone

@shared_task
def expire_reservations():
    """Expire reservations that are older than 15 minutes"""
    reservations = Reservation.objects.filter(
        status=Reservation.Status.ACTIVE,
        expires_at__lt=timezone.now()
    )
    count = reservations.count()  # capture before the loop mutates state
    for reservation in reservations:
        reservation.status = Reservation.Status.EXPIRED
        reservation.save()
    print(f"Expired {count} reservations")
    return f"Expired {count} reservations"