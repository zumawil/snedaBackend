from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Payment
from .serializers import PaymentSerializer
from orders.models import Order
from users.permissions import IsVerifiedUser
from orders.serailizer import OrderSerializer
import requests
from dotenv import load_dotenv
import os

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
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # List all payments for user
                payments = Payment.objects.filter(order__user=request.user)
                serializer = PaymentSerializer(payments, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Initiate a payment for an order.
        Expects: order_id, amount, method
        """
        try:
            order_id = request.data.get('order_id')
            amount = request.data.get('amount')
            method = request.data.get('method')

            if not all([order_id, amount, method]):
                return Response({'error': 'order_id, amount, and method are required'}, status=status.HTTP_400_BAD_REQUEST)

            order = get_object_or_404(Order, pk=order_id, user=request.user)

            # Check if payment already exists for this order
            if Payment.objects.filter(order=order).exists():
                return Response({'error': 'Payment already initiated for this order'}, status=status.HTTP_400_BAD_REQUEST)

            payment = Payment.objects.create(
                order=order,
                amount=amount,
                method=method
            )

            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
        try:
            payment = Payment.objects.get(paystack_reference=reference)
        except Payment.DoesNotExist:
            return False, "Payment record not found"
        
        if response_data.get('status') and response_data.get('data', {}).get('status') == 'success':
            payment.transaction_id = response_data.get("data", {}).get('id')
            payment.status = "completed"
            payment.save()
            return True, "Payment verified successfully"
        
        # Payment failed or has other status
        paystack_status = response_data.get('data', {}).get('status', 'failed')
        if paystack_status == 'abandoned':
            payment.status = 'abandoned'
        else:
            payment.status = 'failed'
        payment.save()
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
            return Response(
                {'error': 'Reference parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = verify_payment(reference)
        
        if success:
            return Response({'detail': message}, status=status.HTTP_200_OK)
        else:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

        # updated = Product.objects.filter(
                #     id=item.product.id,
                #     stock__gte=item.quantity # select product who have enough stock for quantity requested
                # ).update(stock=F('stock') - item.quantity)

                # if updated == 0:
                #     raise Exception(f"Stock changed for {item.product.name}")
    
        # Add error handling
        # if not reference:
        #     return Response(
        #         {'error': 'reference is required'},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        
        # try:
        #     payment = Payment.objects.get(transaction_id=reference)
        #     order = OrderSerializer(payment.order)
            
        #     return Response(
        #         {
        #             'detail': 'payment callback called',
        #             'reference': reference,  
        #             'data': order.data
        #         },
        #         status=status.HTTP_200_OK
        #     )
        # except Payment.DoesNotExist:
        #     return Response(
        #         {'error': 'Payment not found'},
        #         status=status.HTTP_404_NOT_FOUND
        #     )