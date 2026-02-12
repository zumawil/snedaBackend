import requests
import os

class RefundService:
    @staticmethod
    def refund_payment(reference, amount, reason):
        url = f"https://api.paystack.co/refund"
        headers = {
            "Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}",
            "Content-Type": "application/json"
        }
        data = {
            "transaction": reference,
            "amount": amount,
            "reason": reason
        }
        response = requests.post(url, json=data, headers=headers)
        return response.json()
