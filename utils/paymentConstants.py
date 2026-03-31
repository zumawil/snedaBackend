from django.db import models

class PaymentStatus:
    
    ABANDONED = "abandoned"
    FAILED = "failed"
    SUCCESS = "success"
    PENDING = "pending"


class PaymentMethod:
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    BANK = "bank"
    USSD = "ussd"
    QR = "qr"
    BANK_TRANSFER = "bank_transfer"

class Status(models.TextChoices):
    PENDING = 'pending', 'Pending'         # System: cart created
    PAID = 'paid', 'Paid'                  # System: payment confirmed
    CANCELLED = 'cancelled', 'Cancelled'   # System/Business logic
    REFUNDED = 'refunded', 'Refunded'      # System: refund processed
