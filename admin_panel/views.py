from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from django.db.models import F
from django.db import transaction
from admin_panel.tasks import (
    send_shipping_status_email_task,
    send_order_approved_email_task,
    send_order_disapproved_email_task
)

from users.models import CustomUser
from products.models import Product, ProductImage, Category, Brand, HSCode, ProductGroup
from orders.models import Order, OrderItem
from payments.models import Payment
from shipping.models import Shipping
from notifications.models import Notification
from users.permissions import IsAdminUser, IsVerifiedUser
from utils.apiResponse import api_response

from orders.serializers import OrderDetailSerializer, OrderSerializer, OrderStatusUpdateSerializer
from products.serializers import ProductSerializer, ProductCreateUpdateSerializer, ProductImageSerializer
from users.serializers import UserSerializer
from shipping.serializers import ShippingSerializer
from notifications.serializers import NotificationSerializer
from django.shortcuts import get_object_or_404

from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi    

# ============================================================================
# DASHBOARD
# ============================================================================

class DashboardStatsView(APIView):
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Get dashboard statistics",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Dashboard statistics retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "stats": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "total_revenue_for_today": openapi.Schema(type=openapi.TYPE_NUMBER, description="Total revenue for today"),
                                        "total_orders": openapi.Schema(type=openapi.TYPE_INTEGER, description="Total orders today"),
                                        "total_products": openapi.Schema(type=openapi.TYPE_INTEGER, description="Total products in system"),
                                        "total_pending_orders": openapi.Schema(type=openapi.TYPE_INTEGER, description="Total pending orders"),
                                        "total_users": openapi.Schema(type=openapi.TYPE_INTEGER, description="Total registered users"),
                                        "revenue_growth": openapi.Schema(type=openapi.TYPE_NUMBER, description="Revenue growth percentage compared to last month"),
                                        "this_month_revenue": openapi.Schema(type=openapi.TYPE_NUMBER, description="Total revenue this month"),
                                    }
                                ),
                                "recent_orders": openapi.Schema(
                                    type=openapi.TYPE_ARRAY, 
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                                    description="List of 5 most recent orders"
                                )
                            }
                        ),
                        "error": openapi.Schema(type=openapi.TYPE_STRING, description="Error message if any")
                    }
                )
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing authentication",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            403: openapi.Response(
                description="Forbidden - User is not an admin",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )

    def get(self, request):
        try:
            today = timezone.now().date()
            total_revenue = Payment.objects.filter(status='success', date_created__date=today).aggregate(Sum('amount'))['amount__sum'] or 0
            total_orders = Order.objects.filter(created_at__date=today).count()
            total_pending_orders = Order.objects.filter(Q(shipping__status='pending') | Q(shipping__isnull=True)).count()
            total_products = Product.objects.count()
            total_users = CustomUser.objects.count()

            now = timezone.now()
            this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_end = this_month_start - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            this_month_revenue = Payment.objects.filter(
                status='success', 
                date_created__gte=this_month_start
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            last_month_revenue = Payment.objects.filter(
                status='success', 
                date_created__gte=last_month_start,
                date_created__lt=this_month_start
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            revenue_growth = 0
            if last_month_revenue > 0:
                revenue_growth = ((this_month_revenue - last_month_revenue) / last_month_revenue) * 100

            recent_orders = Order.objects.order_by('-created_at')[:5]
            recent_orders_serializer = OrderDetailSerializer(recent_orders, many=True)

            # Alerts/Warnings data
            total_low_stock = Product.objects.filter(inventory_qty__lt=10).count()
            
            last_24h = timezone.now() - timedelta(days=1)
            total_failed_payments = Payment.objects.filter(
                status='failed',
                date_created__gte=last_24h
            ).count()

            data = {
                "stats": {
                    "total_revenue_for_today": float(total_revenue),
                    "total_orders": total_orders,
                    "total_products": total_products,
                    'total_pending_orders': total_pending_orders,
                    "total_users": total_users,
                    "revenue_growth": round(revenue_growth, 2),
                    "this_month_revenue": float(this_month_revenue),
                    "total_low_stock": total_low_stock,
                    "total_failed_payments": total_failed_payments
                },
                "recent_orders": recent_orders_serializer.data
            }

            return api_response(
                success=True,
                data=data,
                message="Dashboard statistics retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error retrieving dashboard statistics",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SalesChartDataView(APIView):
    """Return daily revenue and order count for the last 30 days."""
    permission_classes = [IsVerifiedUser, IsAdminUser]

    def get(self, request):
        try:
            from django.db.models.functions import TruncDate

            today = timezone.now().date()
            start_date = today - timedelta(days=29)  # 30 days including today

            # Daily revenue from successful payments
            #Gets all successful payments since start_date, groups them by day,
            # sums the payment amounts for each day, and returns the daily revenue 
            # ordered by date
            revenue_qs = (
                Payment.objects
                .filter(status='success', date_created__date__gte=start_date)
                .annotate(day=TruncDate('date_created'))
                .values('day')
                .annotate(revenue=Sum('amount'))
                .order_by('day')
            )
            # returns a dictionary of days and their corresponding revenue
            revenue_map = {entry['day']: float(entry['revenue']) for entry in revenue_qs}

            # Daily order count
            orders_qs = (
                Order.objects
                .filter(created_at__date__gte=start_date)
                .annotate(day=TruncDate('created_at'))
                .values('day')
                .annotate(count=Count('id'))
                .order_by('day')
            )
            # returns a dictionary of days and their corresponding order count
            orders_map = {entry['day']: entry['count'] for entry in orders_qs}

            # Build a continuous 30-day array (fill gaps with zeros)
            # chat data stores he revenue and order count for each day
            # eg
            # {
            # "date": "2026-03-03",
            # "revenue": 180.0,
            # "orders": 8
            # }
            chart_data = []
            for i in range(30):
                day = start_date + timedelta(days=i)
                chart_data.append({
                    'date': day.strftime('%Y-%m-%d'),
                    'revenue': revenue_map.get(day, 0),
                    'orders': orders_map.get(day, 0),
                })

            return api_response(
                success=True,
                data=chart_data,
                message="Sales chart data retrieved successfully",
                status_code=status.HTTP_200_OK,
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error retrieving sales chart data",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# ORDER MANAGEMENT
# ============================================================================

class AdminOrderListView(APIView):
    permission_classes = [IsVerifiedUser,IsAdminUser]
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        operation_description="Get a paginated list of all orders",
        security=['Bearer', 'Cookie'],
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by shipping status (pending, shipped, delivered, cancelled)", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Number of items per page", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Response(
                description="Orders retrieved successfully",
                schema=OrderDetailSerializer(many=True)
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only")
        }
    )
    def get(self, request):
        try:
            # Support filtering by status
            order_status = request.query_params.get('status', None)
            orders = Order.objects.all().order_by('-created_at')
            
            if order_status:
                if order_status == 'pending':
                    orders = orders.filter(Q(shipping__status='pending') | Q(shipping__isnull=True))
                else:
                    orders = orders.filter(shipping__status=order_status)
            
            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(orders, request)
            serializer = OrderDetailSerializer(result_page, many=True)
            data = paginator.get_paginated_response(serializer.data).data

            return api_response(
                success=True,
                data=data,
                message="All orders retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error retrieving orders",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminOrderDetailView(APIView):
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Get details of a specific order by ID",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Order retrieved successfully",
                schema=OrderSerializer()
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Order not found")
        }
    )
    def get(self, request, pk):
        try:
            order = get_object_or_404(Order, pk=pk)
            # Use OrderSerializer to include shipping and items fields
            serializer = OrderSerializer(order)
            return api_response(
                success=True,
                data=serializer.data,
                message="Order retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error retrieving order",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AdminUpdateOrderStatusView(APIView):
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Update the shipping status of an order",
        security=['Bearer', 'Cookie'],
        request_body=OrderStatusUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Order status updated successfully",
                schema=OrderSerializer()
            ),
            400: openapi.Response(description="Bad request - Invalid status or no shipping record"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Order not found")
        }
    )
    @transaction.atomic
    def patch(self, request, pk):
        # Lock row to avoid race conditions
        order = Order.objects.select_for_update().get(pk=pk)

        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True) # automatically checks and raises error
        new_status = serializer.validated_data["status"]

        if not hasattr(order, "shipping") or not order.shipping:
            return api_response(
                success=False,
                error="No shipping record",
                message="No shipping related to this order was found",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        shipping = order.shipping
        shipping.status = new_status

        tracking_number = request.data.get("tracking_number")
        if tracking_number:
            shipping.tracking_number = tracking_number

        shipping.save()

        # Safe closure to avoid late-binding issues
        transaction.on_commit(
            lambda oid=order.id, status=new_status, tn=tracking_number:
                send_shipping_status_email_task.delay(oid, status, tn)
        )

        serializer = OrderSerializer(order)

        return api_response(
            success=True,
            data=serializer.data,
            message=f"Order status updated to {new_status}",
            status_code=status.HTTP_200_OK
        )     

class AdminOrderApproveView(APIView):
    permission_classes = [IsVerifiedUser, IsAdminUser]
    
    @swagger_auto_schema(
        operation_description="Approve an order for further processing",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Order approved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_OBJECT, properties={}),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(description="Bad request - Order already approved"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Order not found")
        }
    )
    @transaction.atomic
    def post(self, request, pk):
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
        # Check if already approved
        if order.approved:
            return api_response(
                success=False,
                data=None,
                error="Already approved",
                message="Order is already approved",
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        order.approved = True
        # Save first, then schedule email task after transaction commits
        order.save()
        transaction.on_commit(
            lambda oid=order.id: send_order_approved_email_task.delay(oid)
        )
            
        return api_response(
            success=True,
            data=None,
            message="Order approved successfully",
            status_code=status.HTTP_200_OK
        )
       
class AdminOrderRejectView(APIView):
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Reject an order",
        security=['Bearer', 'Cookie'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'reason': openapi.Schema(type=openapi.TYPE_STRING, description="Reason for rejection (optional)")
            }
        ),
        responses={
            200: openapi.Response(
                description="Order rejected successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_OBJECT, properties={}),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(description="Bad request - Order already rejected"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Order not found")
        }
    )
    @transaction.atomic
    def post(self, request, pk):
        # Lock order row to prevent concurrent updates
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk)

        if order.approved is False:
            return api_response(
                success=False,
                error="Already rejected",
                message="Order is already rejected",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get("reason", "")  

        order.approved = False
        order.save()

        # Safe closure to avoid late-binding
        transaction.on_commit(
            lambda oid=order.id, r=reason:
                send_order_disapproved_email_task.delay(oid, r)
        )

        return api_response(
            success=True,
            message="Order rejected successfully",
            status_code=status.HTTP_200_OK
        )

class AdminOrderCancelView(APIView):
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Cancel an order and restore stock",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Order cancelled successfully and stock restored",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_OBJECT, properties={}),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(description="Bad request - Order already cancelled"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Order not found")
        }
    )
    @transaction.atomic
    def post(self, request, pk):
        # Lock order row to avoid race conditions
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk)

        if order.effective_status == "cancelled":
            return api_response(
                success=False,
                error="Already cancelled",
                message="Order already cancelled",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Restore stock for each order item
        for item in order.items.all():
            Product.objects.filter(id=item.product.id).update(
                inventory_qty=F('inventory_qty') + item.quantity
            )

        # Cancel shipping if present
        if hasattr(order, "shipping") and order.shipping:
            order.shipping.status = "cancelled"
            order.shipping.save()

        # Mark order as not approved
        order.approved = False
        order.save()
        
        from admin_panel.tasks import send_order_cancelled_email_task
        # Optionally: notify user after commit
        transaction.on_commit(
            lambda oid=order.id: send_order_cancelled_email_task.delay(oid)
        )

        return api_response(
            success=True,
            message="Order cancelled successfully and stock restored",
            status_code=status.HTTP_200_OK
        )

# ============================================================================
# PRODUCT MANAGEMENT
# ============================================================================

class AdminProductListView(APIView):
    permission_classes = [IsVerifiedUser, IsAdminUser]
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        operation_description="Get a paginated list of all products supports category filtering",
        security=['Bearer', 'Cookie'],
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Number of items per page", type=openapi.TYPE_INTEGER),
            openapi.Parameter('category', openapi.IN_QUERY, description="Category name", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="Products retrieved successfully",
                schema=ProductSerializer(many=True)
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only")
        }
    )
    def get(self, request):
        try:
            products = Product.objects.all().order_by('-item_no')
            
            # Support category filtering
            category_name = request.query_params.get('category', None)
            if category_name:
                products = products.filter(category__name__icontains=category_name)
                
            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(products, request)
            serializer = ProductSerializer(result_page, many=True)
            data = paginator.get_paginated_response(serializer.data).data

            return api_response(
                success=True,
                data=data,
                message="All products retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error retrieving products",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminProductCreateView(APIView):
    """Create a new product (Admin only)"""
    permission_classes = [IsVerifiedUser, IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_description="Create a new product",
        security=['Bearer', 'Cookie'],
        request_body=ProductCreateUpdateSerializer,
        responses={
            201: openapi.Response(
                description="Product created successfully",
                schema=ProductSerializer()
            ),
            400: openapi.Response(description="Bad request - Validation failed"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Product group not found")
        }
    )
    def post(self, request):
        try:
            data = request.data.copy()

            # Handle Product Group (Required, expects ID)
            product_group_id = data.get('product_group')
            if not product_group_id:
                return api_response(
                    success=False,
                    data=None,
                    error="Product group ID is required",
                    message="Product group ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            try:
                product_group = ProductGroup.objects.get(id=product_group_id)
                data['product_group'] = product_group.id
            except ProductGroup.DoesNotExist:
                return api_response(
                    success=False,
                    data=None,
                    error="Product group not found",
                    message="Product group not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Handle Category (expects name, creates if missing)
            category_name = data.get('category')
            if category_name:
                category, _ = Category.objects.get_or_create(name=category_name)
                data['category'] = category.id
            
            # Handle Brand (expects name, creates if missing)
            brand_name = data.get('brand')
            if brand_name:
                brand, _ = Brand.objects.get_or_create(name=brand_name)
                data['brand'] = brand.id

            # Handle HS Code (expects code, creates if missing)
            hs_code_value = data.get('hs_code')
            if hs_code_value:
                hs_code, _ = HSCode.objects.get_or_create(code=hs_code_value)
                data['hs_code'] = hs_code.id

            serializer = ProductCreateUpdateSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Product created successfully",
                    status_code=status.HTTP_201_CREATED
                )
            
            return api_response(
                success=False,
                data=None,
                error="Validation failed",
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Internal Server Error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminProductDetailView(APIView):
    """Get, Update, or Delete a product (Admin only)"""
    permission_classes = [IsVerifiedUser,IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_description="Get details of a specific product",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Product retrieved successfully",
                schema=ProductSerializer()
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Product not found")
        }
    )
    def get(self, request, pk):
        try:
            product = get_object_or_404(Product, pk=pk)
            serializer = ProductSerializer(product)
            return api_response(
                success=True,
                data=serializer.data,
                message="Product retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error retrieving product",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Update a product",
        security=['Bearer', 'Cookie'],
        request_body=ProductCreateUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Product updated successfully",
                schema=ProductSerializer()
            ),
            400: openapi.Response(description="Bad request - Validation failed"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Product or Product group not found")
        }
    )
    def put(self, request, pk):
        try:
            product = get_object_or_404(Product, pk=pk)
            data = request.data.copy()

            # Handle Product Group
            product_group_id = data.get('product_group')
            if product_group_id:
                try:
                    product_group = ProductGroup.objects.get(id=product_group_id)
                    data['product_group'] = product_group.id
                except ProductGroup.DoesNotExist:
                    return api_response(
                        success=False,
                        data=None,
                        error="Product group not found",
                        message="Product group not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )

            # Handle Category
            category_name = data.get('category')
            if category_name:
                category, _ = Category.objects.get_or_create(name=category_name)
                data['category'] = category.id
            
            # Handle Brand
            brand_name = data.get('brand')
            if brand_name:
                brand, _ = Brand.objects.get_or_create(name=brand_name)
                data['brand'] = brand.id

            serializer = ProductCreateUpdateSerializer(product, data=data)
            if serializer.is_valid():
                serializer.save()
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Product updated successfully",
                    status_code=status.HTTP_200_OK
                )
            
            return api_response(
                success=False,
                data=None,
                error="Validation failed",
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error updating product",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Delete a product",
        security=['Bearer', 'Cookie'],
        responses={
            204: openapi.Response(description="Product deleted successfully"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Product not found")
        }
    )
    def delete(self, request, pk):
        try:
            product = get_object_or_404(Product, pk=pk)
            product.delete()
            return api_response(
                success=True,
                data=None,
                message="Product deleted successfully",
                status_code=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error deleting product",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminToggleProductStatusView(APIView):
    """Toggle product active/inactive status"""
    # NOTE: Commented out - Product model doesn't have is_active field
    # TODO: Either add is_active field to Product model or remove this view
    # permission_classes = [IsVerifiedUser]
    pass
    
    # def post(self, request, pk):
    #     try:
    #         product = get_object_or_404(Product, pk=pk)
    #         
    #         # Check if product has is_active field, if not create it
    #         if not hasattr(product, 'is_active'):
    #             return api_response(
    #                 success=False,
    #                 data=None,
    #                 error="Field not found",
    #                 message="Product model does not have is_active field",
    #                 status_code=status.HTTP_400_BAD_REQUEST
    #             )
    #         
    #         product.is_active = not product.is_active
    #         product.save()
    #         
    #         return api_response(
    #             success=True,
    #             data={"is_active": product.is_active},
    #             message=f"Product status updated to {'active' if product.is_active else 'inactive'}",
    #             status_code=status.HTTP_200_OK
    #         )
    #     except Exception as e:
    #         return api_response(
    #             success=False,
    #             error=str(e),
    #             message="Error updating product status",
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    #         )


class AdminProductStockUpdateView(APIView):
    """Quick stock adjustment endpoint"""
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Adjust product stock quantity (positive to add, negative to subtract)",
        security=['Bearer', 'Cookie'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['stock'],
            properties={
                'stock': openapi.Schema(type=openapi.TYPE_INTEGER, description="Stock adjustment amount (e.g., +10 to add 10, -5 to reduce by 5)")
            }
        ),
        responses={
            200: openapi.Response(
                description="Stock updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "inventory_qty": openapi.Schema(type=openapi.TYPE_INTEGER)
                            }
                        ),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(description="Bad request - Missing field, invalid value, or insufficient stock"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Product not found")
        }
    )
    def patch(self, request, pk):
        try:
            product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
            stock_adjustment = request.data.get('stock')
            
            if stock_adjustment is None:
                return api_response(
                    success=False,
                    data=None,
                    error="Missing field",
                    message="stock field is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                stock_adjustment = int(stock_adjustment)
            except ValueError:
                return api_response(
                    success=False,
                    data=None,
                    error="Invalid value",
                    message="stock must be an integer",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate that stock adjustment won't result in negative inventory
            if product.inventory_qty + stock_adjustment < 0:
                return api_response(
                    success=False,
                    data=None,
                    error="Insufficient stock",
                    message=f"Cannot reduce stock by {stock_adjustment}. Current inventory: {product.inventory_qty}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            product.inventory_qty += stock_adjustment
            product.save(update_fields=['inventory_qty'])
            # Refresh to get actual value
            product.refresh_from_db()
            
            return api_response(
                success=True,
                data={"inventory_qty": product.inventory_qty},
                message=f"Stock adjusted by {stock_adjustment}",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error updating stock",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminProductImageView(APIView):
    """Manage product images (Admin only)"""
    permission_classes = [IsVerifiedUser, IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Upload a product image",
        security=['Bearer', 'Cookie'],
        request_body=ProductImageSerializer,
        responses={
            201: openapi.Response(
                description="Product image created successfully",
                schema=ProductImageSerializer()
            ),
            400: openapi.Response(description="Bad request - Validation failed"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only")
        }
    )
    def post(self, request):
        try:
            serializer = ProductImageSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Product image created successfully",
                    status_code=status.HTTP_201_CREATED
                )
            return api_response(
                success=False,
                data=None,
                error="Validation failed",
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error creating product image",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Delete a product image by ID",
        security=['Bearer', 'Cookie'],
        manual_parameters=[
            openapi.Parameter('id', openapi.IN_QUERY, description="Image ID to delete", type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={
            204: openapi.Response(description="Product image deleted successfully"),
            400: openapi.Response(description="Bad request - Missing or invalid image ID"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Image not found")
        }
    )
    def delete(self, request):
        try:
            image_id = request.query_params.get('id')
            if not image_id:
                return api_response(
                    success=False,
                    data=None,
                    error="Missing parameter",
                    message="Image ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate image_id is an integer
            try:
                image_id = int(image_id)
            except (TypeError, ValueError):
                return api_response(
                    success=False,
                    data=None,
                    error="Invalid parameter",
                    message="Image ID must be an integer",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            image = get_object_or_404(ProductImage, pk=image_id)
            image.delete()
            return api_response(
                success=True,
                data=None,
                message="Product image deleted successfully",
                status_code=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error deleting product image",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# SHIPPING MANAGEMENT
# ============================================================================

class AdminShippingListView(APIView):
    """List all shipping records (Admin only)"""
    permission_classes = [IsVerifiedUser, IsAdminUser]
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        operation_description="Get a paginated list of all shipping records",
        security=['Bearer', 'Cookie'],
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Number of items per page", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Response(
                description="Shipping records retrieved successfully",
                schema=ShippingSerializer(many=True)
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only")
        }
    )
    def get(self, request):
        try:
            shippings = Shipping.objects.all()
            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(shippings, request)
            serializer = ShippingSerializer(result_page, many=True)
            data = paginator.get_paginated_response(serializer.data).data

            return api_response(
                success=True,
                data=data,
                message="All shipping records retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error retrieving shipping records",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminShippingDetailView(APIView):
    """Get specific shipping record by ID (Admin only)"""
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Get details of a specific shipping record",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Shipping record retrieved successfully",
                schema=ShippingSerializer()
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Shipping record not found")
        }
    )
    def get(self, request, pk):
        try:
            shipping = get_object_or_404(Shipping, pk=pk)
            serializer = ShippingSerializer(shipping)
            return api_response(
                success=True,
                data=serializer.data,
                message="Shipping record retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error retrieving shipping record",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminUpdateShippingStatusView(APIView):
    """Update shipping status (Admin only)"""
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Update shipping status by order ID",
        security=['Bearer', 'Cookie'],
        request_body=ShippingSerializer,
        responses={
            200: openapi.Response(
                description="Shipping status updated successfully",
                schema=ShippingSerializer()
            ),
            400: openapi.Response(description="Bad request - Validation failed"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="Shipping record not found")
        }
    )
    def put(self, request, order_id):
        try:
            shipping = get_object_or_404(Shipping, order__id=order_id)
            serializer = ShippingSerializer(shipping, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Shipping status updated successfully",
                    status_code=status.HTTP_200_OK
                )
            return api_response(
                success=False,
                data=None,
                error="Validation failed",
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error updating shipping status",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# USER MANAGEMENT
# ============================================================================

class AdminUserListView(APIView):
    permission_classes = [IsVerifiedUser, IsAdminUser]
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        operation_description="Get a paginated list of all users",
        security=['Bearer', 'Cookie'],
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Number of items per page", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Response(
                description="Users retrieved successfully",
                schema=UserSerializer(many=True)
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only")
        }
    )
    def get(self, request):
        try:
            users = CustomUser.objects.all().order_by('-date_joined')
            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(users, request)
            serializer = UserSerializer(result_page, many=True)
            data = paginator.get_paginated_response(serializer.data).data
            return api_response(
                success=True,
                data=data,
                message="All users retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error retrieving users",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminUserDetailView(APIView):
    """Get user details with order history (Admin only)"""
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Get details of a specific user including their order history",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="User details retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "user": openapi.Schema(type=openapi.TYPE_OBJECT),
                                "orders": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                                "total_orders": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "total_spent": openapi.Schema(type=openapi.TYPE_NUMBER)
                            }
                        ),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="User not found")
        }
    )
    def get(self, request, pk):
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            user_serializer = UserSerializer(user)
            
            # Get user's order history with aggregation using DB
            orders_query = Order.objects.filter(user=user)
            order_stats = orders_query.aggregate(
                total_orders=Count('id'),
                total_spent=Sum('total_amount')
            )
            
            orders = orders_query.order_by('-created_at')[:10]
            order_serializer = OrderDetailSerializer(orders, many=True)
            
            data = {
                "user": user_serializer.data,
                "orders": order_serializer.data,
                "total_orders": order_stats['total_orders'],
                "total_spent": float(order_stats['total_spent'] or 0)
            }
            
            return api_response(
                success=True,
                data=data,
                message="User details retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error retrieving user details",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminSearchUsersView(APIView):
    """Search/filter users (Admin only)"""
    permission_classes = [IsVerifiedUser, IsAdminUser]
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        operation_description="Search users by name or email",
        security=['Bearer', 'Cookie'],
        manual_parameters=[
            openapi.Parameter('q', openapi.IN_QUERY, description="Search query (searches in first_name, last_name, email)", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Number of items per page", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Response(
                description="Users retrieved successfully",
                schema=UserSerializer(many=True)
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only")
        }
    )
    def get(self, request):
        try:
            search_query = request.query_params.get('q', '')
            users = CustomUser.objects.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
            
            paginator = self.pagination_class()
            paginated_users = paginator.paginate_queryset(users, request)
            
            serializer = UserSerializer(paginated_users, many=True)
            data = paginator.get_paginated_response(serializer.data).data

            return api_response(
                success=True,
                data=data,
                message="Users retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error searching users",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminAssignUserRoleView(APIView):
    """Assign roles/permissions to users (Admin only)"""
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Assign staff or superuser roles to a user",
        security=['Bearer', 'Cookie'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'is_staff': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Grant staff access"),
                'is_superuser': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Grant superuser access")
            }
        ),
        responses={
            200: openapi.Response(
                description="User role updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "is_staff": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                "is_superuser": openapi.Schema(type=openapi.TYPE_BOOLEAN)
                            }
                        ),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            403: openapi.Response(description="Forbidden - Only superusers can assign roles / Cannot remove superuser status from superuser"),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User not found")
        }
    )
    def post(self, request, pk):
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            
            # Explicitly convert to boolean to avoid type confusion
            is_staff = bool(request.data.get('is_staff', user.is_staff))
            is_superuser = bool(request.data.get('is_superuser', user.is_superuser))
            
            # Security: Only superusers can grant superuser or staff roles
            if not request.user.is_superuser:
                return api_response(
                    success=False,
                    data=None,
                    error="Permission denied",
                    message="Only superusers can assign staff or superuser roles",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Prevent removing superuser status from superusers
            if user.is_superuser and not is_superuser:
                return api_response(
                    success=False,
                    data=None,
                    error="Permission denied",
                    message="Cannot remove superuser status from a superuser",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save()
            
            return api_response(
                success=True,
                data={
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser
                },
                message="User role updated successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error updating user role",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ToggleUserStatusView(APIView):
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Toggle user active status (activate/deactivate)",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="User status updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN)
                            }
                        ),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            403: openapi.Response(description="Forbidden - Cannot toggle own account or superuser status"),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User not found")
        }
    )
    def post(self, request, pk):
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            
            # Prevent self-deactivation
            if user == request.user:
                return api_response(
                    success=False,
                    message="Cannot deactivate your own account",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            if user.is_superuser:
                return api_response(
                    success=False,
                    message="Cannot toggle status of a superuser",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            user.is_active = not user.is_active
            user.save()
            
            return api_response(
                success=True,
                data={"is_active": user.is_active},
                message=f"User status updated to {'active' if user.is_active else 'inactive'}",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error updating user status",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# NOTIFICATION MANAGEMENT
# ============================================================================

class AdminCreateNotificationView(APIView):
    """Create notification for a user (Admin only)"""
    permission_classes = [IsVerifiedUser, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Create a notification for a specific user",
        security=['Bearer', 'Cookie'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['user_id', 'message'],
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the user to send notification to"),
                'message': openapi.Schema(type=openapi.TYPE_STRING, description="Notification message")
            }
        ),
        responses={
            201: openapi.Response(
                description="Notification created successfully",
                schema=NotificationSerializer()
            ),
            400: openapi.Response(description="Bad request - Missing required fields"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden - Admin only"),
            404: openapi.Response(description="User not found")
        }
    )
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            message = request.data.get('message')
            
            if not user_id or not message:
                return api_response(
                    success=False,
                    data=None,
                    error="Missing required fields",
                    message="user_id and message are required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            user = get_object_or_404(CustomUser, id=user_id)
            notification = Notification.objects.create(
                user=user,
                message=message
            )
            serializer = NotificationSerializer(notification)
            
            return api_response(
                success=True,
                data=serializer.data,
                message="Notification created successfully",
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error creating notification",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
