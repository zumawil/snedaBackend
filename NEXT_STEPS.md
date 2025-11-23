# 🚀 Next Steps - Sneda Ecommerce API

**Last Updated:** 2025-11-17
**Status:** Core endpoints working ✅ | Checkout creates Orders atomically but payment integration is pending

---

## 📋 Quick Summary

- ✅ **51 endpoints** currently working
- ✅ **0 critical bugs** found
- 🎯 **3 feature areas** remaining (payments, shipping, notifications)

---

## ⏭️ What to do next (Immediate)

1) Order cancellation rules (consistency) ✅ Completed
- Restrict cancel to `pending` orders only ✅
- Optional: restore stock on cancel ✅
- Add tests and docs

---

2) Checkout / Order hardening (NEW - immediate)
- Add idempotency support for checkout requests (require `X-Idempotency-Key` header or accept a key in request body). Persist a CheckoutAttempt or tie the idempotency key to an Order to avoid duplicate orders on retries.
- Shipping is now the source of truth for order state; ensure a Shipping record is created at checkout and used to represent status.
- Create a draft Order or CheckoutAttempt before calling external payment APIs so webhooks can reconcile state.
- Return appropriate 4xx errors for expected conditions (e.g., 409 Conflict for stock races) and log failures.


## 🔥 High Priority

### 1. Order Cancellation Enhancements ✅ Completed
**Updated:** `POST /orders/order/cancel/<pk>/`

**Implemented:**
1. ✅ Allow cancel only if order is cancellable (evaluated from shipping/effective status, e.g., 'pending')
2. ✅ Added `cancelled` status and stock restoration
3. ✅ Tests and documentation updated

---

## 🟡 Medium Priority

### 2. Reviews System ✅ Completed
**Endpoints implemented:**
- `GET /reviews/`, `POST /reviews/`, `GET /reviews/<pk>/`, `DELETE /reviews/<pk>/`

**Features:**
- Users can only review purchased & delivered products
- One review per product per user
- Rating 1-5, text content
- Proper validation and permissions

---

### 3. Payments Integration
**Endpoints to create:**
- `POST /payments/`, `GET /payments/<pk>/`, `POST /payments/<pk>/verify/`

**Implementation steps:**
1. Choose gateway (Stripe/PayPal)
2. Payment model + status flow
3. Webhook verification; update order status
4. Error handling + docs

---

## 🟢 Low Priority

### 6. Shipping Management
- Addresses CRUD and tracking lookups

### 7. Notifications System
- List, mark read, mark all read, delete

---

## ✅ Completed (Summary)
- User Profile Management — `GET/PUT/PATCH/DELETE /users/profile/`
- Logout — `POST /users/logout/`
- Order Status Update (Admin-only) — `PATCH /orders/order/update-status/<pk>/`
- Order Cancellation — `POST /orders/order/cancel/<pk>/` (base flow + stock restore)
- Product Creation — `POST /products/`
- Category Management — `GET/POST /categories/`, `GET/PUT/PATCH/DELETE /categories/<pk>/`
- Password Management — `POST /users/change-password/`, `POST /users/reset-password/`, `POST /users/reset-password/confirm/`
- Product Image Management — `POST /product-images/`, `GET /product-images/<pk>/`, `DELETE /product-images/<pk>/`
- Reviews System — `GET/POST /reviews/`, `GET/DELETE /reviews/<pk>/` (with purchase validation)

---

## 🎯 Recommended Implementation Order
1) Reviews ✅ Completed
2) Payments (Medium)
3) Shipping (Low)
4) Notifications (Low)

---

## 📝 Notes
- Require auth for non-public endpoints; consider RBAC
- Add tests as you implement each feature
- Update Swagger/Redoc examples with real payloads
- Use consistent error response format

---

## 🛠️ Recommended Immediate Checklist (apply now)
- [ ] Add idempotency key handling for `/checkout/` and persist keys with a CheckoutAttempt or Order
- [ ] Ensure shipping record is created at checkout and treat Shipping as the source-of-truth for order state
- [ ] Create and run a migration to drop `Order.status` from the database once code is fully migrated; include a backfill RunPython migration if you need to preserve historical status values.
- [ ] Return 4xx errors for expected failures (e.g., 409 Conflict for stock races) and avoid 500 for expected conditions
- [ ] Add unit/integration tests for concurrent checkout and stock validation
- [ ] Add logging/metrics for checkout failures and stock update conflicts
- [ ] Create a short migration plan if you add a CheckoutAttempt/draft Order model


## ✅ Checklist Template
- [ ] Create/update view class
- [ ] Create/update serializer (if needed)
- [ ] Add URL route
- [ ] Add authentication/permissions
- [ ] Add input validation
- [ ] Add error handling
- [ ] Write tests
- [ ] Update documentation
- [ ] Test manually
- [ ] Deploy to staging

