# Sneda Ecommerce API - Complete Endpoint Documentation

**Last Updated:** 2025-11-14
**Base URL:** All endpoints are relative to your Django server (e.g., `http://localhost:8000/`)

---

## 🔐 Authentication & User Management (`/users/`)

| Method | Endpoint | Description | Auth Required | Status |
|--------|----------|-------------|---------------|--------|
| `POST` | `/users/signup/` | Register new user, sends OTP email | ❌ | ✅ Working |
| `POST` | `/users/login/` | Login with email/password, returns JWT and role in cookies | ❌ | ✅ Working |
| `POST` | `/users/refresh/` | Refresh access token using refresh cookie | ❌ | ✅ Working |
| `POST` | `/users/verify-otp/` | Verify OTP code sent during signup | ❌ | ✅ Working |
| `GET` | `/users/users/` | List all users | ✅ | ✅ Working |
| `GET` | `/users/profile/` | Get current authenticated user profile | ✅ | ✅ Working |
| `PUT` | `/users/profile/` | Replace user profile data | ✅ | ✅ Working |
| `PATCH` | `/users/profile/` | Partially update user profile | ✅ | ✅ Working |
| `DELETE` | `/users/profile/` | Delete own account | ✅ | ✅ Working |
| `POST` | `/users/logout/` | Logout and clear auth cookies | ✅ | ✅ Working |
| `POST` | `/users/change-password/` | Change user password | ✅ | ✅ Working |
| `POST` | `/users/reset-password/` | Request password reset | ❌ | ✅ Working |
| `POST` | `/users/reset-password/confirm/` | Confirm password reset | ❌ | ✅ Working |

**Note:** JWT tokens are stored in HTTP-only cookies for security. The login endpoint also sets a 'role' cookie (non-HTTP-only) containing the user's group name.

**Missing:**

---

## 📦 Products (`/`)

| Method | Endpoint | Description | Auth Required | Status |
|--------|----------|-------------|---------------|--------|
| `GET` | `/categories/` | List all categories (returns `products_count` per category) | ✅ (verified) | ✅ Working |
| `POST` | `/categories/` | Create category | ✅ (verified) | ✅ Working |
| `GET` | `/categories/<pk>/` | Retrieve category details | ✅ (verified) | ✅ Working |
| `PUT` | `/categories/<pk>/` | Replace category | ✅ (verified) | ✅ Working |
| `PATCH` | `/categories/<pk>/` | Partially update category | ✅ (verified) | ✅ Working |
| `DELETE` | `/categories/<pk>/` | Delete category | ✅ (verified) | ✅ Working |
| `GET` | `/products/` | List all products | ✅ (verified) | ✅ Working |
| `POST` | `/products/` | Create new product | ✅ (verified) | ✅ Working |
| `GET` | `/products/<pk>/` | Get product details | ✅ (verified) | ✅ Working |
| `PUT` | `/products/<pk>/` | Replace product | ✅ (verified) | ✅ Working |
| `PATCH` | `/products/<pk>/` | Partially update product | ✅ (verified) | ✅ Working |
| `DELETE` | `/products/<pk>/` | Delete product | ✅ (verified) | ✅ Working |
| `GET` | `/product-images/` | List all product images | ✅ (verified) | ✅ Working |
| `POST` | `/product-images/` | Upload product image | ✅ (verified) | ✅ Working |
| `GET` | `/product-images/<pk>/` | Get specific product image | ✅ (verified) | ✅ Working |
| `DELETE` | `/product-images/<pk>/` | Delete product image | ✅ (verified) | ✅ Working |

**Notes:**
- Category list endpoint annotates `products_count` for each category.
- Product and product image endpoints require verified permissions.

**Remaining Gaps:**

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
| `POST` | `/checkout/` | Convert cart to order, clear cart | ✅ | ✅ Working |
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
| `PATCH` | `/orders/order/update-status/<pk>/` | Update order status (admin-only) | ✅ | ✅ Working |
| `POST` | `/orders/order/cancel/<pk>/` | Cancel own order (user) | ✅ | ✅ Working |

**Admin-only:** `PATCH /orders/order/update-status/<pk>/`

**Notes:** Consider restricting cancellation to `pending` status only.

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
1. No reviews endpoints (reviews app exists but no URLs)
2. No payments endpoints (payments app exists but no URLs)
3. No shipping endpoints (shipping app exists but no URLs)
4. No notifications endpoints (notifications app exists but no URLs)

---

## ✅ Recommended Additions

### Medium Priority:
1. **Reviews**: CRUD endpoints for product reviews (`/reviews/`)

### Low Priority (if needed):
6. **Payments**: Payment processing endpoints (`/payments/`)
7. **Shipping**: Shipping address and tracking endpoints (`/shipping/`)
8. **Notifications**: User notification endpoints (`/notifications/`)

---

## 📊 Endpoint Summary

| Category | Total Endpoints | Working | Issues | Missing |
|----------|----------------|---------|--------|---------|
| Authentication | 13 | 13 | 0 | 0 |
| Products | 15 | 15 | 0 | 0 |
| Cart | 8 | 8 | 0 | 0 |
| Orders | 9 | 9 | 0 | 0 |
| Documentation | 2 | 2 | 0 | 0 |
| **TOTAL** | **47** | **47** | **0** | **0** |

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

**Added:** Admin-only order status update endpoint:
- `PATCH /orders/order/update-status/<pk>/` (requires admin)

**Added:** Order cancellation endpoint:
- `POST /orders/order/cancel/<pk>/` (user cancels own order)

**Added:** User profile management endpoints:
- `GET/PUT/PATCH/DELETE /users/profile/`

**Added:** Logout endpoint:
- `POST /users/logout/`

**Added:** Category management endpoints:
- `GET/POST /categories/`
- `GET/PUT/PATCH/DELETE /categories/<pk>/`

**Added:** Product creation endpoint:
- `POST /products/`

**Added:** Password management endpoints:
- `POST /users/change-password/`
- `POST /users/reset-password/`
- `POST /users/reset-password/confirm/`

**Added:** Product image management endpoints:
- `POST /product-images/`
- `GET /product-images/<pk>/`
- `DELETE /product-images/<pk>/`

**Modified:** Login endpoint now sets 'role' cookie with user's group name.

**Modified:** Product, category, and product image endpoints now require only verified user permissions instead of admin + verified.
