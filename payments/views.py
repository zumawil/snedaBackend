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
import hmac
import hashlib
import json
from carts.views import to_pesewas, bill_user
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

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

   
class GetPaymentByOrder(APIView):
    permission_classes = [IsVerifiedUser]
    """
    Get payment by order.
    """
    def get(self, request, order_id):
        try:
            payment = Payment.objects.get(order_id=order_id, order__user=request.user)
            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    """
        initialize payment for failed payment t checkout
    """
    def post(self, request, order_id):
        try:
            order = get_object_or_404(Order, pk=order_id, 
            user=request.user, shipping__status='pending')

            data = bill_user(order.total_amount, request.user.email)
            print(data)

            if data.get('status') == True:
                # create payment for order
                payment = Payment.objects.create(
                    order=order,
                    amount=order.total_amount,
                    status='pending',
                    paystack_reference=data['data']['reference']
                )
                data = {
                    'order': OrderSerializer(order).data,
                    'payment_url':data.get('data').get('authorization_url'),
                }
           
                return Response(data, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Payment failed try again'}, status=status.HTTP_400_BAD_REQUEST)
           
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
            return Response(
                {'error': 'Reference parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = verify_payment(reference)
        
        if success:
            return Response({'detail': message}, status=status.HTTP_200_OK)
        else:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(APIView):
    """
    webhook for paystack payment gateway
    """

    def post(self, request):

        # 1. Verify signature
        signature = request.headers.get('x-paystack-signature', None)
        if not signature:
            return Response({"error": "Missing signature"}, status=status.HTTP_400_BAD_REQUEST)

        secret = os.getenv('PAYSTACK_SECRET_KEY').encode('utf-8')
        payload = request.body

        computed_hash = hmac.new(secret, payload, hashlib.sha512).hexdigest()
        verified = hmac.compare_digest(computed_hash, signature)

        if not verified:
            return Response({"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

        # 2. Handle events
        event = request.data.get('event')
        data = request.data.get('data', {})
        
        if event == 'charge.success':
            payment_id = data.get('id')
            reference = data.get('reference')
            payment_status = data.get('status')
            method = data.get('channel')
            amount = data.get('amount') / 100
            
            # 3. Get payment object by reference
            try:
                payment = Payment.objects.get(paystack_reference=reference, is_processed=False)
                payment.transaction_id = str(payment_id)  
                
                if payment_status == 'success':
                    payment.status = 'success'
                    # Update product stock
                    self.update_product_stock(payment.order)
                    
                elif payment_status == 'abandoned':
                    payment.status = 'abandoned'
                else:
                    payment.status = 'failed'
                
                payment.method = method
                payment.is_processed = True
                # Add explicit save with force_update
                payment.save()
            
                # Verify the save worked
                payment.refresh_from_db()
        
                if payment.status != 'success':
                    print(f"ERROR: Status not updated! Expected 'success', got '{payment.status}'")
                
            except Payment.DoesNotExist:
                # log for debugging
                print(f"DEBUG: Payment with reference {reference} not found in database or is already processed")
                
           
        elif event == 'charge.failed':
            # Handle failed payments
            reference = data.get('reference')
            try:
                payment = Payment.objects.get(paystack_reference=reference)
                payment.status = 'failed'
                payment.is_processed = True
                payment.save()
            except Payment.DoesNotExist:
                print(f"Failed payment with reference {reference} not found")
        elif event == 'charge.abandoned':
            # Handle abandoned payments
            reference = data.get('reference')
            try:
                payment = Payment.objects.get(paystack_reference=reference)
                payment.status = 'abandoned'
                payment.is_processed = True
                payment.save()
            except Payment.DoesNotExist:
                print(f"Abandoned payment with reference {reference} not found")
        # respond 200 to Paystack
        return Response(status=status.HTTP_200_OK)
    

    def update_product_stock(self, order):
        """
        Update product stock when payment succeeds.
        """
        from django.db.models import F
        from products.models import Product
        
        for order_item in order.items.all():
            # Update stock atomically
            updated = Product.objects.filter(
                id=order_item.product.id, # get the product id of the order item
                stock__gte=order_item.quantity # check if the stock of the product is greate than the item requested
            ).update(stock=F('stock') - order_item.quantity) # update it directly in DB to prevent race conditions
            
            if updated == 0:
                print(f"Warning: Insufficient stock for product {order_item.product.name}")

    