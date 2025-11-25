# Sneda Ecommerce API - Complete Endpoint Documentation

**Last Updated:** 2025-11-25
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
| `POST` | `/product-reviews/` | Get all reviews for a specific product | ❌ | ✅ Working |

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

**Implementation note (current):** The `/checkout/` endpoint now performs server-side validation and creates an Order inside a database transaction. It validates product availability and stock, atomically decrements stock using an F() update, creates OrderItems, computes `total_amount`, and clears the user's cart. Payment integration is not yet implemented — the view creates an order but does not validate external payment provider status. See "Missing" and "Recommended Additions" below for production hardening items.

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
| `PATCH` | `/orders/order/update-status/<pk>/` | Update shipping status for an order (admin-only) | ✅ | ✅ Working |
| `POST` | `/orders/order/cancel/<pk>/` | Cancel own order (user) | ✅ | ✅ Working |

## 🚚 Shipping (`/shipping/`)

| Method | Endpoint | Description | Auth Required | Status |
|--------|----------|-------------|---------------|--------|
| `GET` | `/shipping/status/<order_id>/` | Get shipping status and details for an order | ✅ | ✅ Working |

**Admin-only:** `PATCH /orders/order/update-status/<pk>/`

**Notes:** Cancellation restricted to `pending` status only. Stock is restored upon cancellation.

**Status source of truth:** Shipping is now the authoritative source of truth for order state. The `Order.status` DB field has been removed from the model; APIs expose a computed `status` derived from the linked `Shipping` record when present. Admin status updates now update the shipping record.

---

## 💳 Payments (`/payments/`)

| Method | Endpoint | Description | Auth Required | Status |
|--------|----------|-------------|---------------|--------|
| `GET` | `/payments/` | List all payments for user | ✅ | ✅ Working |
| `GET` | `/payments/<pk>/` | Get specific payment details | ✅ | ✅ Working |
| `POST` | `/payments/` | Initiate a new payment for an order | ✅ | ✅ Working |
| `GET` | `/payments/callback/` | Handle Paystack payment callback/webhook | ❌ | ✅ Working |

**Notes:**
- Payment initiation uses Paystack API with callback URL set to API backend
- Callback endpoint verifies payment status and updates payment record
- Checkout now includes payment initialization with idempotency support

---

## ⭐ Reviews (`/`)

| Method | Endpoint | Description | Auth Required | Status |
|--------|----------|-------------|---------------|--------|
| `GET` | `/reviews/` | List all reviews for authenticated user | ✅ | ✅ Working |
| `POST` | `/reviews/` | Create new review | ✅ | ✅ Working |
| `GET` | `/reviews/<pk>/` | Get specific review (user's own) | ✅ | ✅ Working |
| `DELETE` | `/reviews/<pk>/` | Delete review (owner only) | ✅ | ✅ Working |

**Notes:**
- Users can only review products they've purchased and received (order status: `delivered`)
- One review per product per user
- Rating scale: 1-5 stars
- Product specified by name in POST request

---

## 📚 Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/swagger/` | Swagger UI documentation |
| `GET` | `/redoc/` | ReDoc documentation |

---

## 🔍 Issues Summary

### Critical Issues:
1. Payments: Partial payment provider integration implemented with Paystack. Payment initiation and callback handling are working, but full webhook reconciliation and error handling may need refinement for production.
2. Database migration: `Order.status` was removed from the model. Before deploying to production, run migrations and (optionally) run a backfill migration to copy existing `Order.status` values into `Shipping` or an audit table if you need to preserve history.

### Code Quality Issues:
- None found! ✅

### Missing Functionality:
1. Payments: Full webhook reconciliation and advanced error handling for production
2. Idempotency: CheckoutAttempt tracking is implemented, but may need refinement
3. Shipping endpoints (shipping app exists but no URLs) — shipping model exists; add CRUD and tracking endpoints
4. Notifications endpoints (notifications app exists but no URLs)

---

## ✅ Recommended Additions

### Medium Priority:
1. **Payments**: Payment processing endpoints (`/payments/`) and PaymentIntent/webhook reconciliation
2. **Idempotency & Draft Orders**: Add a `CheckoutAttempt` or draft `Order` model that stores idempotency keys, payment provider IDs, and cart snapshots to support retries and webhook reconciliation.
3. **Shipping endpoints & migration**: Add shipping endpoints and implement a migration/backfill plan to preserve any required historical `Order.status` values before dropping the column in the database.

### Low Priority (if needed):
2. **Shipping**: Shipping address and tracking endpoints (`/shipping/`)
3. **Notifications**: User notification endpoints (`/notifications/`)

---

## 📊 Endpoint Summary

| Category | Total Endpoints | Working | Issues | Missing |
|----------|----------------|---------|--------|---------|
| Authentication | 13 | 13 | 0 | 0 |
| Products | 16 | 16 | 0 | 0 |
| Cart | 8 | 8 | 0 | 0 |
| Orders | 9 | 9 | 0 | 0 |
| Shipping | 1 | 1 | 0 | 0 |
| Payments | 4 | 4 | 0 | 0 |
| Reviews | 4 | 4 | 0 | 0 |
| Documentation | 2 | 2 | 0 | 0 |
| **TOTAL** | **57** | **57** | **0** | **0** |

---

## 📝 Notes

- All endpoints that require authentication use JWT tokens stored in HTTP-only cookies
- The API uses Django REST Framework
- Swagger documentation is available at `/swagger/`
- ReDoc documentation is available at `/redoc/`
- Media files are served at `/media/` in DEBUG mode
- Apps installed but not exposed: `payments`, `shipping`, `notifications`

---

## ✅ Recent Fixes

**Fixed:** `shipping/serializers.py` - `ShippingSerializer`

Changed from `serializers.Serializer` to `serializers.ModelSerializer` to properly serialize model fields. Added `order_id` as a `SerializerMethodField` to include the order's ID in the response.

**Fixed:** `shipping/generate_shipping_number.py` - `generate_tracking_number()`

Added database uniqueness check to prevent duplicate tracking numbers, ensuring reliable shipment tracking.

**Fixed:** `carts/views.py` - `CheckoutView.post()`

The `total_amount` is now correctly calculated when creating an order:
```python
# Calculate total amount
total_amount = sum(item.get_total_price() for item in order.items.all())
order.total_amount = total_amount
order.save()
```

**Added:** Shipping status endpoint:
- `GET /shipping/status/<order_id>/` (get shipping details for an order)

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

**Added:** Reviews system endpoints:
- `GET /reviews/` (list user's reviews)
- `POST /reviews/` (create review with validation)
- `GET /reviews/<pk>/` (get specific review)
- `DELETE /reviews/<pk>/` (delete own review)

**Added:** Product reviews retrieval endpoint:
- `POST /product-reviews/` (get all reviews for a specific product)

**Notes on Reviews:**
- Users can only review products they've purchased and received (order status: `delivered`)
- One review per product per user enforced
- Rating: 1-5 stars, content: text review
- Product identified by name in POST request

**Recent changes:**
- `Order.status` removed from the `Order` model; shipping is now authoritative for order state. API responses still expose a `status` field computed from the linked `Shipping` record for compatibility.
- Added Paystack payment integration with callback handling for payment verification.
- Fixed checkout flow to properly calculate order amount before payment initialization.
- Implemented idempotency in checkout using CheckoutAttempt model.

---

## 🔧 Bug Fixes (2025-11-25)

**Fixed:** `payments/views.py` - `verify_payment()` function

- **Bug**: `response_data(response_data.get('status'))` was calling a dict as a function
- **Fix**: Changed to proper status assignment with `payment.status = 'failed'`
- **Added**: Comprehensive error handling with try/except blocks
- **Added**: Validation for missing reference and Paystack secret key
- **Added**: Network error handling with `requests.RequestException`
- **Added**: Return tuple `(success, message)` for better error communication

**Fixed:** `payments/views.py` - `PaymentCallback` class

- **Added**: Reference parameter validation before calling `verify_payment()`
- **Improved**: Response messages now include detailed error information

**Fixed:** `payments/urls.py` - URL name typo

- **Changed**: `name='paymenet-callback'` → `name='payment-callback'`

**Fixed:** `carts/views.py` - `bill_user()` function

- **Changed**: Now accepts `email` parameter instead of hardcoded `"customer@example.com"`
- **Updated**: Checkout view passes `request.user.email` to the function

**Fixed:** `carts/views.py` - `create_shipping()` function

- **Added**: Now returns the generated `tracking_number`
- **Added**: Logging statement in checkout view for tracking number
