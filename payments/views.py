from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Payment
from .serializers import PaymentSerializer, PaymentRetrySerializer
from orders.models import Order
from users.permissions import IsVerifiedUser
from orders.serializers import OrderSerializer
import requests
from dotenv import load_dotenv
import os
import hmac
import hashlib
import json
from utils.payment_helpers import to_pesewas, bill_user
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from utils.apiResponse import api_response
from carts.models import Cart
from django.shortcuts import redirect
import utils.paymentConstants
from payments.webhook_handlers import handle_payment_success, handle_payment_failed, handle_payment_abandoned

load_dotenv()

# Create your views here.

class PaymentView(APIView):
    """
    Handle payments.

    GET /payments/: List all payments for the authenticated user.
    GET /payments/<pk>/: Retrieve details of a specific payment.
    POST /payments/: Initiate a new payment for an order.
    """

    permission_classes = [IsVerifiedUser]

    def get(self, request, pk=None):
        try:
            if pk:
                # Get specific payment
                payment = get_object_or_404(Payment, pk=pk, order__user=request.user)
                serializer = PaymentSerializer(payment)
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Payment retrieved successfully",
                    status_code=status.HTTP_200_OK
                )
            else:
                # List all payments for user
                payments = Payment.objects.filter(order__user=request.user)
                serializer = PaymentSerializer(payments, many=True)
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Payments retrieved successfully",
                    status_code=status.HTTP_200_OK
                )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error retrieving payments",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GetPaymentByOrder(APIView):
    permission_classes = [IsVerifiedUser]
    """
    Get payment by order.
    """
    def get(self, request, order_id):
        try:
            payment = Payment.objects.filter(order_id=order_id, order__user=request.user)
            serializer = PaymentSerializer(payment, many=True)
            return api_response(
                success=True,
                data=serializer.data,
                message="Payment for order retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Payment.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="Payment not found",
                message="Payment not found for this order",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error retrieving payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
      
def verify_payment(reference):
    """
    Verify a Paystack payment transaction.
    
    Args:
        reference: The Paystack transaction reference
        
    Returns:
        tuple: (success: bool, message: str)
    """
    if not reference:
        return False, "Reference is required"
    
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    
    if not PAYSTACK_SECRET_KEY:
        return False, "Paystack secret key not configured"

    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(verify_url, headers=headers)
        response_data = response.json()
        
        # Get payment record
        # try:
        #     payment = Payment.objects.get(paystack_reference=reference)
        # except Payment.DoesNotExist:
        #     return False, "Payment record not found"
        
        if response_data.get('status') and response_data.get('data', {}).get('status') == 'success':
            return True, "Payment verified successfully"
        
        # Payment failed or has other status
        paystack_status = response_data.get('data', {}).get('status', 'failed')
        return False, f"Payment verification failed: {paystack_status}"
        
    except requests.RequestException as e:
        return False, f"Network error while verifying payment: {str(e)}"
    except Exception as e:
        return False, f"Error verifying payment: {str(e)}"

class PaymentCallback(APIView):
    """
    Handle Paystack payment callback.
    This endpoint is called by Paystack after payment completion.
    """

    def get(self, request):
        reference = request.query_params.get('reference')

        if not reference:
            return api_response(
                success=False,
                data=None,
                error="Missing reference",
                message="Reference parameter is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = verify_payment(reference)
        
        if success:
            # payment = Payment.objects.get(paystack_reference=reference)

            frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
            return redirect(f'{frontend_url}/payment/success')
        else:
            frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
            return redirect(f'{frontend_url}/payment/failure')

@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(APIView):
    """
    webhook for paystack payment gateway
    """
    def post(self, request):
        print('DEGUB webhook called')
        # 1. Verify signature from paystack
        signature = request.headers.get('x-paystack-signature', None)
        if not signature:
            return api_response(
                success=False,
                data=None,
                error="Missing signature",
                message="Webhook signature is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        secret = os.getenv('PAYSTACK_SECRET_KEY').encode('utf-8')
        payload = request.body

        computed_hash = hmac.new(secret, payload, hashlib.sha512).hexdigest()
        verified = hmac.compare_digest(computed_hash, signature)

        if not verified:
            return api_response(
                success=False,
                data=None,
                error="Invalid signature",
                message="Webhook signature verification failed",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        event = request.data.get('event')
        data  = request.data.get('data', {})

        # grab order_id from metadata
        order_id  = data.get('metadata', {}).get('order_id')
        reference = data.get('reference')

        # 2. Call handler functions directly (email is offloaded to Celery inside each handler)
        if event == 'charge.success':
            handle_payment_success(reference, order_id)

        elif event == 'charge.failed':
            handle_payment_failed(reference, order_id)

        elif event == 'charge.abandoned':
            handle_payment_abandoned(reference, order_id)

        # 3. Return 200 immediately to Paystack
        return api_response(
            success=True,
            data=None,
            message="Webhook received",
            status_code=status.HTTP_200_OK
        )