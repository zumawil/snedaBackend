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
