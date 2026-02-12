import os
import time
import requests
import logging
from decimal import Decimal, ROUND_HALF_UP
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# convert cedis to pesewas for paystack
def to_pesewas(amount):
    """Convert amount to pesewas (smallest currency unit for GHS)."""
    return int((Decimal(amount) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def bill_user(amount, email, order_id=None, retry_count=0):
    amount = to_pesewas(amount)
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    url = "https://api.paystack.co/transaction/initialize"
    
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    # Generate reference
    timestamp = int(time.time())
    if order_id:
        if retry_count > 0:
            reference = f"ORD-{order_id}-R{retry_count}-{timestamp}"
        else:
            reference = f"ORD-{order_id}-{timestamp}"
    else:
        reference = None
    
    data = {
        "email": email,
        "amount": amount,
        "currency": "GHS",
        "callback_url": f"{os.getenv('APP_URL')}payments/callback/"
    }
    
    if reference:
        data["reference"] = reference
        data["metadata"] = {
            "order_id": order_id,
            "retry_count": retry_count
        }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Paystack API error: {str(e)}")
        return {
            'status': False,
            'message': f'Network error: {str(e)}'
        }

def verify_transaction_status(reference):
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('status'):
            return data['data']['status']
        
        return 'unknown'
    except requests.exceptions.RequestException as e:
        logger.error(f"Error verifying transaction {reference}: {str(e)}")
        return 'unknown'
