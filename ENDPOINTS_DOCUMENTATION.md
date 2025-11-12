# Sneda Ecommerce API - Complete Endpoint Documentation

**Last Updated:** After latest changes  
**Base URL:** All endpoints are relative to your Django server (e.g., `http://localhost:8000/`)

---

## 🔐 Authentication & User Management (`/users/`)

| Method | Endpoint | Description | Auth Required | Status |
|--------|----------|-------------|---------------|--------|
| `POST` | `/users/signup/` | Register new user, sends OTP email | ❌ | ✅ Working |
| `POST` | `/users/login/` | Login with email/password, returns JWT in cookies | ❌ | ✅ Working |
| `POST` | `/users/refresh/` | Refresh access token using refresh cookie | ❌ | ✅ Working |
| `POST` | `/users/verify-otp/` | Verify OTP code sent during signup | ❌ | ✅ Working |
| `GET` | `/users/users/` | List all users | ✅ | ✅ Working |

**Note:** JWT tokens are stored in HTTP-only cookies for security.

**Missing:**
- ❌ `GET /users/profile/` - Get current user profile
- ❌ `PUT/PATCH /users/profile/` - Update user profile
- ❌ `POST /users/logout/` - Logout (clear cookies)
- ❌ `POST /users/change-password/` - Change password
- ❌ `POST /users/reset-password/` - Request password reset

---

## 📦 Products (`/`)

| Method | Endpoint | Description | Auth Required | Status |
|--------|----------|-------------|---------------|--------|
| `GET` | `/categories/` | List all categories | ❌ | ✅ Working |
| `GET` | `/products/` | List all products | ❌ | ✅ Working |
| `GET` | `/products/<pk>/` | Get product details | ❌ | ✅ Working |
| `PUT` | `/products/<pk>/` | Update product | ✅ | ✅ Working |
| `PATCH` | `/products/<pk>/` | Partially update product | ✅ | ✅ Working |
| `DELETE` | `/products/<pk>/` | Delete product | ✅ | ✅ Working |
| `GET` | `/product-images/` | List all product images | ❌ | ✅ Working |

**Missing Endpoints:**
- ❌ `POST /categories/` - Create category
- ❌ `POST /products/` - Create product
- ❌ `POST /product-images/` - Upload product image
- ❌ `GET /categories/<pk>/` - Get category details
- ❌ `PUT/PATCH/DELETE /categories/<pk>/` - Update/delete category
- ❌ `GET /product-images/<pk>/` - Get specific product image
- ❌ `DELETE /product-images/<pk>/` - Delete product image

---

## 🛒 Cart Management (`/`)

| Method | Endpoint | Description | Auth Required | Status |
|--------|----------|-------------|---------------|--------|
| `GET` | `/cart/` | Get or create user's cart | ✅ | ✅ Working |
| `GET` | `/cart-items/` | List all cart items for user | ✅ | ✅ Working |
| `POST` | `/cart-items/` | Create cart item | ✅ | ✅ Working |
| `GET` | `/cart-items/<pk>/` | Get specific cart item | ✅ | ✅ Working |
| `PUT` | `/cart-items/<pk>/` | Update cart item quantity | ✅ | ✅ Working |
| `DELETE` | `/cart-items/<pk>/` | Remove item from cart | ✅ | ✅ Working |
| `POST` | `/checkout/` | Convert cart to order, clear cart | ✅ | ✅ **FIXED** |
| `POST` | `/add-to-cart/<product_pk>/` | Add product to cart (increments if exists) | ✅ | ✅ Working |

**Fixed:**
1. ✅ **CheckoutView** - Now calculates `total_amount` correctly by summing all order items.

---

## 📋 Orders (`/orders/`)

| Method | Endpoint | Description | Auth Required | Status |
|--------|----------|-------------|---------------|--------|
| `GET` | `/orders/orders/` | List all orders for user | ✅ | ✅ Working |
| `GET` | `/orders/orders/<pk>/` | Get specific order (user's own) | ✅ | ✅ Working |
| `GET` | `/orders/order-items/` | List all order items for user | ✅ | ✅ Working |
| `POST` | `/orders/order-items/` | Create order item | ✅ | ✅ Working |
| `GET` | `/orders/order-items/<pk>/` | Get specific order item | ✅ | ✅ Working |
| `PUT` | `/orders/order-items/<pk>/` | Update order item | ✅ | ✅ Working |
| `DELETE` | `/orders/order-items/<pk>/` | Delete order item | ✅ | ✅ Working |

**Missing Endpoints:**
- ❌ `PUT/PATCH /orders/orders/<pk>/` - Update order status
- ❌ `DELETE /orders/orders/<pk>/` - Cancel order

---

## 📚 Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/swagger/` | Swagger UI documentation |
| `GET` | `/redoc/` | ReDoc documentation |

---

## 🔍 Issues Summary

### Critical Issues:
- ✅ **All fixed!** No critical issues found.

### Code Quality Issues:
- None found! ✅

### Missing Functionality:
1. No endpoint to update order status
2. No endpoint to cancel orders
3. No endpoint to get user profile
4. No endpoint to update user profile
5. No logout endpoint (should clear cookies)
6. No password reset/change endpoints
7. No reviews endpoints (reviews app exists but no URLs)
8. No payments endpoints (payments app exists but no URLs)
9. No shipping endpoints (shipping app exists but no URLs)
10. No notifications endpoints (notifications app exists but no URLs)
11. No product/category creation endpoints (admin only?)

---

## ✅ Recommended Additions

### High Priority (New Features):
1. **Update order status**: `PATCH /orders/orders/<pk>/status/` - Update order status
2. **User profile**: `GET /users/profile/` - Get current user profile
3. **Update profile**: `PUT/PATCH /users/profile/` - Update user profile
4. **Logout**: `POST /users/logout/` - Clear authentication cookies

### Medium Priority:
5. **Order cancellation**: `POST /orders/orders/<pk>/cancel/` - Cancel pending order
6. **Password change**: `POST /users/change-password/` - Change user password
7. **Password reset**: `POST /users/reset-password/` - Request password reset
8. **Product creation** (if admin): `POST /products/` - Create new product
9. **Category management**: Full CRUD for categories

### Low Priority (if needed):
10. **Reviews**: CRUD endpoints for product reviews (`/reviews/`)
11. **Payments**: Payment processing endpoints (`/payments/`)
12. **Shipping**: Shipping address and tracking endpoints (`/shipping/`)
13. **Notifications**: User notification endpoints (`/notifications/`)

---

## 📊 Endpoint Summary

| Category | Total Endpoints | Working | Issues | Missing |
|----------|----------------|---------|--------|---------|
| Authentication | 5 | 5 | 0 | 4 |
| Products | 7 | 7 | 0 | 7 |
| Cart | 8 | 8 | 0 | 0 |
| Orders | 7 | 7 | 0 | 2 |
| Documentation | 2 | 2 | 0 | 0 |
| **TOTAL** | **29** | **29** | **0** | **13** |

---

## 📝 Notes

- All endpoints that require authentication use JWT tokens stored in HTTP-only cookies
- The API uses Django REST Framework
- Swagger documentation is available at `/swagger/`
- ReDoc documentation is available at `/redoc/`
- Media files are served at `/media/` in DEBUG mode
- Apps installed but not exposed: `reviews`, `payments`, `shipping`, `notifications`

---

## ✅ Recent Fixes

**Fixed:** `carts/views.py` - `CheckoutView.post()`

The `total_amount` is now correctly calculated when creating an order:
```python
# Calculate total amount
total_amount = sum(item.get_total_price() for item in order.items.all())
order.total_amount = total_amount
order.save()
```
