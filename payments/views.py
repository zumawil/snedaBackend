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
from utils.sendEmail import send_order_confirmation_email

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

    # """
    #     initialize payment for failed payment t checkout
    # """
    # def post(self, request, order_id):
    #     try:
    #         order = get_object_or_404(Order, pk=order_id, 
    #         user=request.user, shipping__status='pending')

    #         data = bill_user(order.total_amount, request.user.email, order_id=order.id)

    #         if data.get('status') == True:
    #             # create payment for order
    #             payment = Payment.objects.create(
    #                 order=order,
    #                 amount=order.total_amount,
    #                 status='pending',
    #                 paystack_reference=data['data']['reference']
    #             )
    #             response_data = {
    #                 'order': OrderSerializer(order).data,
    #                 'payment_url':data.get('data').get('authorization_url'),
    #             }
           
    #             return api_response(
    #                 success=True,
    #                 data=response_data,
    #                 message="Payment initialized successfully",
    #                 status_code=status.HTTP_200_OK
    #             )
    #         else:
    #             return api_response(
    #             success=False,
    #             data=None,
    #             error="Payment failed",
    #             message="Payment failed, please try again",
    #             status_code=status.HTTP_400_BAD_REQUEST
    #         )
           
    #     except Exception as e:
    #         return api_response(
    #             success=False,
    #             data=None,
    #             error=str(e),
    #             message="Error initializing payment",
    #             status_code=status.HTTP_400_BAD_REQUEST
    #         )

            
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
            # can clear cart now
            payment = Payment.objects.get(paystack_reference=reference)
            
            # cart = Cart.objects.filter(user=payment.order.user).first()
            # if cart:
            #     cart.items.all().delete()

            # return api_response(
            #     success=True,
            #     data=None,
            #     message=message,
            #     status_code=status.HTTP_200_OK
            # )

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
        #1. Verify signature from paystack
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
        data = request.data.get('data', {})
        
        if event == 'charge.success':
            payment_id = data.get('id')
            reference = data.get('reference')
            payment_status = data.get('status')
            method = data.get('channel')
            amount = data.get('amount') / 100 # convert to ghs
            
            try:
                payment = Payment.objects.get(paystack_reference=reference, is_processed=False)
                payment.transaction_id = str(payment_id)
                
                if payment_status == utils.paymentConstants.PaymentStatus.SUCCESS:
                    payment.status = utils.paymentConstants.PaymentStatus.SUCCESS
                    # clear cart here
                    cart = Cart.objects.filter(user=payment.order.user).first()
                    if cart:
                        cart.items.all().delete()

                elif payment_status == utils.paymentConstants.PaymentStatus.ABANDONED:
                    payment.status = utils.paymentConstants.PaymentStatus.ABANDONED
                else:
                    payment.status = utils.paymentConstants.PaymentStatus.FAILED
                
                payment.method = method
                payment.is_processed = True  # Mark as processed to prevent reprocessing
                
                # Add explicit save with update_fields for efficiency
                payment.save()
            
                # Send order confirmation email
                order = payment.order
                order_items_summary = "\n".join([f"- {item.product.item_no} x {item.quantity}: GHS {item.get_total_price()}" for item in order.items.all()])
                
                email_html = f"""
                <!DOCTYPE html>
                <html>
                <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f9; margin: 0; padding: 0;">
                    <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border: 1px solid #e1e4e8;">
                        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 40px 20px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">Order Confirmed!</h1>
                            <p style="color: #d1fae5; margin-top: 8px; font-size: 16px;">Order #{order.id}</p>
                        </div>
                        <div style="padding: 40px;">
                            <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">Hello {order.user.first_name or 'Valued Customer'},</p>
                            <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">Your payment of <b>GHS {payment.amount}</b> has been successfully processed. We're now preparing your order for shipment.</p>
                            
                            <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; border: 1px solid #e5e7eb; margin-bottom: 24px;">
                                <h2 style="font-size: 18px; color: #1f2937; margin-top: 0; margin-bottom: 16px;">Order Summary</h2>
                                <pre style="white-space: pre-wrap; font-family: inherit; color: #4b5563; margin: 0; font-size: 14px;">{order_items_summary}</pre>
                                <div style="margin-top: 16px; border-top: 1px solid #e5e7eb; padding-top: 12px; font-weight: 700; color: #1f2937;">
                                    Total: GHS {order.total_amount}
                                </div>
                            </div>
                            
                            <p style="color: #6b7280; font-size: 14px; line-height: 1.5;">You can track your order status in your profile. Thank you for shopping with Sneda Ecommerce!</p>
                        </div>
                        <div style="background-color: #f9fafb; padding: 24px; text-align: center; border-top: 1px solid #f1f5f9;">
                            <p style="font-size: 12px; color: #9ca3af; margin: 0;">&copy; 2026 Sneda Ecommerce. All rights reserved.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                send_order_confirmation_email(
                    order.user.email,
                    f"Order Confirmation - #{order.id} - Sneda Ecommerce",
                    email_html
                )

                logger.info(f"Order confirmation email sent for order {order.id}")
                
            except Payment.DoesNotExist:
                # log for debugging
                logger.info(f"DEBUG: Payment with reference {reference} not found in database or is already processed")    
        elif event == 'charge.failed':
            # Handle failed payments
            reference = data.get('reference')
            try:
                payment = Payment.objects.get(paystack_reference=reference)
                payment.status = utils.paymentConstants.PaymentStatus.FAILED
                payment.is_processed = True  # Mark as processed since it failed and we restored stock
                payment.save()

                # restore product stock
                self.restore_product_stock(payment.order)
                
            except Payment.DoesNotExist:
                logger.info(f"Failed payment with reference {reference} not found")
        elif event == 'charge.abandoned':
            # Handle abandoned payments
            reference = data.get('reference')
            try:
                payment = Payment.objects.get(paystack_reference=reference)
                payment.status = utils.paymentConstants.PaymentStatus.ABANDONED
                payment.is_processed = True
                payment.save()
                #  restore payment stcok 
                self.restore_product_stock(payment.order)

            except Payment.DoesNotExist:
                logger.info(f"Abandoned payment with reference {reference} not found")
        # respond 200 to Paystack
        return api_response(
            success=True,
            data=None,
            message="Webhook processed successfully",
            status_code=status.HTTP_200_OK
        )

    def restore_product_stock(self, order):
        """Restore product stock when payment fails."""
        from django.db.models import F
        from products.models import Product
        
        for order_item in order.items.all():
            Product.objects.filter(
                pk=order_item.product.item_no
            ).update(inventory_qty=F('inventory_qty') + order_item.quantity)