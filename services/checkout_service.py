import logging
from django.db import transaction
from django.utils import timezone
from requests import Response
from carts.models import Cart, CheckoutAttempt
from orders.models import Order, OrderItem
from products.models import Product
from payments.models import Payment
from payments.serializers import PaymentSerializer
from orders.serializers import OrderSerializer
from shipping.models import Shipping
from shipping.generate_shipping_number import generate_tracking_number
from utils.payment_helpers import bill_user, verify_transaction_status
from utils.apiResponse import api_response
from rest_framework import status
import utils.paymentConstants

logger = logging.getLogger(__name__)

class CheckoutService:
    @staticmethod
    def create_shipping(order, address, pickup=False):
        """
        Create a shipping record for an order.
        """
        tracking_number = generate_tracking_number()
        Shipping.objects.create(
            order=order,
            status="pending",
            tracking_number=tracking_number,
            address=address,
            pickup=pickup
        )
        return tracking_number

    @staticmethod
    def handle_payment_retry(order_id, user, max_retries=3):
        try:
            order = Order.objects.get(id=order_id, user=user)
        except Order.DoesNotExist:
            return {
                'success': False,
                'error': 'Order not found',
                'message': 'Order not found or does not belong to you'
            }

        # Get the latest payment for this order
        latest_payment = Payment.objects.filter(
            order=order
        ).order_by('-date_created').first()

        if not latest_payment:
            return {
                'success': False,
                'error': 'No payment found',
                'message': 'No payment record found for this order. Please initiate checkout first.'
            }

        # If payment already succeeded and processed, no retry needed
        if latest_payment.status == utils.paymentConstants.PaymentStatus.SUCCESS and latest_payment.is_processed:
            return {
                'success': True,
                'data': {
                    'order': OrderSerializer(order).data,
                    'payment': PaymentSerializer(latest_payment).data,
                    'status': utils.paymentConstants.PaymentStatus.SUCCESS
                },
                'message': "Order is already paid"
            }

        # Check if already at max retries
        current_retry_count = getattr(latest_payment, 'retry_count', 0)
        # We need to check max retries from the payment object itself if it has the field, or use default
        max_retries_val = getattr(latest_payment, 'max_retries', max_retries)
        
        if current_retry_count >= max_retries_val:
            return {
                'success': False,
                'error': f'Maximum retry attempts ({max_retries_val}) reached',
                'data': {
                    'order': OrderSerializer(order).data,
                    'retry_count': current_retry_count,
                    'status': latest_payment.status
                },
                'message': f'Maximum retry attempts ({max_retries_val}) reached'
            }
        
        # Verify current payment status first
        current_status = verify_transaction_status(latest_payment.paystack_reference)
        
        if current_status == utils.paymentConstants.PaymentStatus.SUCCESS:
            # Payment already succeeded, update local record
            latest_payment.is_processed = True
            latest_payment.status = utils.paymentConstants.PaymentStatus.SUCCESS
            latest_payment.save()
            
            return {
                'success': True,
                'data': {
                    'order': OrderSerializer(order).data,
                    'payment': PaymentSerializer(latest_payment).data,
                    'status': utils.paymentConstants.PaymentStatus.SUCCESS
                },
                'message': 'Payment already completed'
            }
        
        # if the payment is pending return the existing URL
        if current_status == utils.paymentConstants.PaymentStatus.PENDING:
            authorization_url = getattr(latest_payment, 'authorization_url', None)
            return {
                'success': True,
                'data': {
                    'order': OrderSerializer(order).data,
                    'payment_url': authorization_url,
                    'reference': latest_payment.paystack_reference,
                    'retry_count': current_retry_count,
                    'status': utils.paymentConstants.PaymentStatus.PENDING
                },
                'message': 'Payment still pending. Please complete the existing payment.'
            }
        
        # Payment failed or abandoned - create new attempt
        new_retry_count = current_retry_count + 1
        logger.info(f"payment status retrying because it failed: {current_status}")

        # reserve stock for the order
        try:
            with transaction.atomic():
                for item in order.items.all():
                    product = Product.objects.select_for_update().get(pk=item.product.pk)
                    if product.inventory_qty < item.quantity:
                        return {
                            'success': False,
                            'error': 'Out of stock',
                            'message': f'Sorry, {product.item_no} is now out of stock and cannot be retried.'
                        }
                    product.inventory_qty -= item.quantity
                    product.save()

        except Exception as e:
            logger.error(f"Error retrying payment for order #{order_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Error reserving stock for retry'
            }

        # Initialize new payment with Paystack
        paystack_response = bill_user(
            amount=latest_payment.amount,
            email=order.user.email,
            order_id=order.id,
            retry_count=new_retry_count
        )
        
        if paystack_response.get('status'):
            # create new payment 
            new_payment = Payment.objects.create(
                        order=order,
                        amount=latest_payment.amount,
                        status=utils.paymentConstants.PaymentStatus.PENDING,
                        paystack_reference=paystack_response['data']['reference'],
                        authorization_url=paystack_response['data']['authorization_url'],
                        retry_count=new_retry_count,
                        last_retry_at = timezone.now()
                    )
            latest_payment.status = utils.paymentConstants.PaymentStatus.FAILED
            latest_payment.save()
            
            logger.info(f"New Payment issued for order #{order_id}")
            
            return {
                'success': True,
                'data': {
                    'order': OrderSerializer(order).data,
                    'payment_url': paystack_response['data']['authorization_url'],
                    'reference': paystack_response['data']['reference'],
                    'retry_count': new_retry_count,
                    'status': utils.paymentConstants.PaymentStatus.PENDING
                },
                'message': f'New Payment issued for order #{order_id}'
            }
        else:
            # Paystack initialization failed
            error_message = paystack_response.get('message', 'Failed to initialize payment')
            logger.error(f"Payment retry failed for order {order_id}: {error_message}")
            
            return {
                'success': False,
                'error': error_message,
                'data': {
                    'order': OrderSerializer(order).data,
                    'retry_count': current_retry_count,
                    'status': 'failed'
                },
                'message': error_message
            }

    @staticmethod
    def process_checkout(user, idempotency_key, address, pickup):
        """
        Coordinates the entire checkout process:
        1. Idempotency check & stock reservation (atomic)
        2. External Payment & Shipping calls
        """
        try:
            # Phase 1: Check idempotency and reserve stock (in transaction)
            result = CheckoutService._create_order_and_reserve_stock(user, idempotency_key)
            
            # If it's a dict, it's a response (likely duplicate order)
            if isinstance(result, dict):
                return result
            
            order, amount = result
            
            # Phase 2: External calls (outside transaction)
            return CheckoutService._process_payment_and_shipping(user, order, amount, address, pickup)
            
        except Cart.DoesNotExist:
             return {
                'success': False,
                'error': "Cart not found",
                'message': "Cart not found for user",
                'status_code': status.HTTP_404_NOT_FOUND
            }
        except Exception as e:
            logger.error(f"Error during checkout: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': "Error during checkout",
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
            }

    @staticmethod
    def _create_order_and_reserve_stock(user, idempotency_key):
        """
        Phase 1: Atomically check idempotency, create order, and reserve stock.
        Returns: (order, amount) tuple or response dict if order already exists
        """
        with transaction.atomic():
            # lock rows to prevent race conditions
            attempt, created = CheckoutAttempt.objects.select_for_update().get_or_create(key=idempotency_key)

            # If this is a duplicate request, return the existing order
            if not created and attempt.order:
                return CheckoutService._handle_existing_order(attempt)

            # Lock and fetch cart with items
            cart = Cart.objects.select_for_update().select_related('user').prefetch_related(
                'items__product'
            ).get(user=user)
            
            # Lock cart items to prevent modifications during checkout
            items = list(cart.items.select_for_update().all())
            
            if not items:
                raise Exception("Cart is empty. Please add items before checkout.")

            # Create order
            order = Order.objects.create(user=user)
            
            # Link order to checkout attempt for idempotency
            attempt.order = order
            attempt.save()

            # Reserve stock atomically for each item
            for item in items:
                # Lock the product row to prevent concurrent modifications
                product = Product.objects.select_for_update().get(pk=item.product.pk)
                
                # Check stock availability
                if product.inventory_qty < item.quantity:
                    current_stock = product.inventory_qty
                    raise Exception(
                        f'Insufficient stock for product {product.item_no}. '
                        f'Available: {current_stock}, Requested: {item.quantity}'
                    )
                
                # Decrement stock
                product.inventory_qty -= item.quantity
                product.save()
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=product.gross_price
                )

            # Calculate and save total amount
            amount = sum([item.get_total_price() for item in order.items.all()])
            order.total_amount = amount
            order.save()

            logger.info(f"Order {order.id} created during checkout for user {user.email}")
            
            return order, amount

    @staticmethod
    def _handle_existing_order(attempt):
        """
        Handle case where order already exists (duplicate idempotency key).
        Returns a response dict.
        """
        order_serializer = OrderSerializer(attempt.order)
        response_data = {
            "order": order_serializer.data,
            "detail": "Payment order already created"
        }
        
        # Check if payment exists and is processed
        payment = Payment.objects.filter(order=attempt.order).first()
        
        if payment and payment.is_processed:
            response_data['payment'] = PaymentSerializer(payment).data
            return {
                'success': True,
                'data': response_data,
                'message': "Payment order already created and processed",
                'status_code': status.HTTP_200_OK
            }
        else:
            # Payment exists but not processed - attempt retry
            # Use the user from the order since this is an internal call
            retry_result = CheckoutService.handle_payment_retry(attempt.order.id, attempt.order.user)
            
            if payment:
                response_data['payment'] = PaymentSerializer(payment).data
            
            if retry_result.get('success'):
                 # Merge retry data
                 if 'data' in retry_result:
                     response_data.update(retry_result['data'])
            
            message = retry_result.get('message', 'Payment order already created')
            
            return {
                'success': True,
                'data': response_data,
                'message': message,
                'status_code': status.HTTP_200_OK
            }

    @staticmethod
    def _process_payment_and_shipping(user, order, amount, address, pickup):
        """
        Phase 2: Process external payment and shipping (outside transaction).
        This prevents holding database locks during slow external API calls.
        """
        try:
            # Create shipping record and get tracking number
            tracking_number = CheckoutService.create_shipping(order, address, pickup)
            logger.info(f"Shipping created with tracking number: {tracking_number}")

            # Initiate payment with external provider
            data = bill_user(amount, user.email, order_id=order.id, retry_count=0)

            payment = None
            if data.get('status') == True:
                # Create payment record
                payment = Payment.objects.create(
                    order=order,
                    amount=amount,
                    status=utils.paymentConstants.PaymentStatus.PENDING,
                    paystack_reference=data['data']['reference'],
                    authorization_url=data['data']['authorization_url']
                )
                logger.info(f"Payment created for order {order.id} with reference {data['data']['reference']}")

            # Prepare response
            response_data = {
                'order': OrderSerializer(order).data,
            }

            if payment:
                response_data['payment'] = PaymentSerializer(payment).data
                response_data['payment_url'] = data['data']['authorization_url']

            return {
                'success': True,
                'data': response_data,
                'message': "Checkout completed successfully",
                'status_code': status.HTTP_201_CREATED
            }
            
        except Exception as e:
            # Payment/shipping failed but order exists with reserved stock
            CheckoutService._cancel_order_and_restore_stock(order)
            logger.error(f"Payment/shipping failed for order {order.id}: {str(e)}")
            
            return {
                'success': False,
                'data': {'order_id': order.id},
                'error': str(e),
                'message': "Order created but payment failed. Please contact support.",
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
            }
            
    @staticmethod
    def _cancel_order_and_restore_stock(order):
        """
            Cancel order and restore stock if payment fails.
        """
        with transaction.atomic():
            # Restore stock for each order item
            for order_item in order.items.select_for_update().all():
                product = Product.objects.select_for_update().get(pk=order_item.product.pk)
                product.inventory_qty += order_item.quantity
                product.save()
            
            # Mark order as cancelled
            order.status = 'cancelled'
            order.save()
            
            logger.info(f"Order {order.id} cancelled and stock restored")
