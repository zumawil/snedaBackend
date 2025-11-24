import uuid
from django.utils import timezone

def generate_tracking_number():
    date_str = timezone.now().strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:8].upper()
    return f"GH-{date_str}-{random_part}"