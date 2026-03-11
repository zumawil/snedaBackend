from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from django.db.models import F
from django.db import transaction

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


# ============================================================================
# DASHBOARD
# ============================================================================

class DashboardStatsView(APIView):
    permission_classes = [IsVerifiedUser, IsAdminUser]

    def get(self, request):
        try:
            today = timezone.now().date()
            total_revenue = Payment.objects.filter(status='success', date_created=today).aggregate(Sum('amount'))['amount__sum'] or 0
            total_orders = Order.objects.filter(created_at=today).count()
            total_pending_orders = Order.objects.filter(shipping__status='pending').count()
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

            data = {
                "stats": {
                    "total_revenue_for_today": float(total_revenue),
                    "total_orders": total_orders,
                    "total_products": total_products,
                    'total_pending_orders': total_pending_orders,
                    "total_users": total_users,
                    "revenue_growth": round(revenue_growth, 2),
                    "this_month_revenue": float(this_month_revenue)
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


# ============================================================================
# ORDER MANAGEMENT
# ============================================================================

class AdminOrderListView(APIView):
    permission_classes = [IsVerifiedUser,IsAdminUser]
    pagination_class = PageNumberPagination

    def get(self, request):
        try:
            # Support filtering by status
            order_status = request.query_params.get('status', None)
            orders = Order.objects.all().order_by('-created_at')
            
            if order_status:
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
    """Update order status (Admin only) - Processing → Shipped → Delivered"""
    permission_classes = [IsVerifiedUser, IsAdminUser]
    
    @transaction.atomic
    def patch(self, request, pk):
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
            
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_status = serializer.validated_data['status']
            
        if hasattr(order, 'shipping') and order.shipping:
            order.shipping.status = new_status
            order.shipping.save()
                
                # Get tracking number if provided
            tracking_number = request.data.get('tracking_number')
                
            # Send email notification asynchronously
            from admin_panel.tasks import send_shipping_status_email_task
            transaction.on_commit(
                lambda: send_shipping_status_email_task.delay(order.id, new_status, tracking_number)
            )
        else:
            return api_response(
                success=False,
                data=None,
                error="No shipping record",
                message="No shipping related to this order was found",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = OrderSerializer(order)
            return api_response(
                success=True,
                data=serializer.data,
                message=f"Order status updated to {new_status}",
                status_code=status.HTTP_200_OK
            )
        


class AdminOrderApproveView(APIView):
    """Approve an order for further processing"""
    permission_classes = [IsVerifiedUser, IsAdminUser]
    
    def post(self, request, pk):
        try:
            order = get_object_or_404(Order, pk=pk)
            
            # Check if already approved
            if order.approved is True:
                return api_response(
                    success=False,
                    data=None,
                    error="Already approved",
                    message="Order is already approved",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            order.approved = True
            order.save()
            
            # Send email notification asynchronously
            from admin_panel.tasks import send_order_approved_email_task
            send_order_approved_email_task.delay(order.id)
            
            return api_response(
                success=True,
                data=None,
                message="Order approved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error approving order",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class AdminOrderRejectView(APIView):
    """Reject an order"""
    permission_classes = [IsVerifiedUser, IsAdminUser]
    
    def post(self, request, pk):
        try:
            order = get_object_or_404(Order, pk=pk)
            
            # Check if already rejected (approved=False means explicitly rejected)
            if order.approved is False:
                return api_response(
                    success=False,
                    data=None,
                    error="Already rejected",
                    message="Order is already rejected",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get rejection reason from request if provided
            reason = request.data.get('reason')
            
            order.approved = False
            order.save()
            
            # Send email notification asynchronously
            from admin_panel.tasks import send_order_disapproved_email_task
            send_order_disapproved_email_task.delay(order.id, reason)
            
            return api_response(
                success=True,
                data=None,
                message="Order rejected successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error rejecting order",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class AdminOrderCancelView(APIView):
    """Cancel an order with stock restoration (Admin only)"""
    permission_classes = [IsVerifiedUser, IsAdminUser]
    
    @transaction.atomic
    def post(self, request, pk):
        try:
            # Use select_for_update to prevent race conditions
            order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
            current_status = order.effective_status if hasattr(order, 'effective_status') else order.shipping.status
            
            if current_status == "cancelled":
                return api_response(
                    success=False,
                    data=None,
                    error="Already cancelled",
                    message="Order already cancelled",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Restore stock for each order item
            for item in order.items.all():
                Product.objects.filter(id=item.product.id).update(inventory_qty=F('inventory_qty') + item.quantity)
            
            # Cancel shipping if present
            if hasattr(order, 'shipping') and order.shipping:
                order.shipping.status = 'cancelled'
                order.shipping.save()
            
            # Mark order as not approved and save
            order.approved = False
            order.save()
            
            return api_response(
                success=True,
                data=None,
                message="Order cancelled successfully and stock restored",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error cancelling order",
                status_code=status.HTTP_400_BAD_REQUEST
            )


# ============================================================================
# PRODUCT MANAGEMENT
# ============================================================================

class AdminProductListView(APIView):
    permission_classes = [IsVerifiedUser, IsAdminUser]
    pagination_class = PageNumberPagination

    def get(self, request):
        try:
            products = Product.objects.all().order_by('-item_no')
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
