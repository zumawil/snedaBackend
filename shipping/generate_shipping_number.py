import uuid
from django.utils import timezone
from .models import Shipping

def generate_tracking_number():
    while True:
        # Generate a unique tracking number
        date_str = timezone.now().strftime("%Y%m%d")
        random_part = uuid.uuid4().hex[:8].upper()
        tracking_number = f"GH-{date_str}-{random_part}"
        if not Shipping.objects.filter(tracking_number=tracking_number).exists():
            return tracking_number