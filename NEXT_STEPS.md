# 🚀 Next Steps - Sneda Ecommerce API

**Last Updated:** After endpoint review  
**Status:** All current endpoints working ✅ | Focus shifting to remaining features

---

## 📋 Quick Summary

- ✅ **41 endpoints** currently working
- ✅ **0 critical bugs** found
- 🎯 **6 feature areas** remaining (passwords, product images, reviews, payments, shipping, notifications)

---

## ⏭️ What to do next (Immediate)

1) Password management (security)
- Add: `POST /users/change-password/`, `POST /users/reset-password/`, `POST /users/reset-password/confirm/`
- Validate current password on change; use token-based reset flow
- Update docs and add tests

2) Product image management (catalog completeness)
- Add: `POST /product-images/`, `GET /product-images/<pk>/`, `DELETE /product-images/<pk>/`
- Accept multipart/form-data; enforce size/type; link to product
- Prefetch images in product responses where needed

3) Order cancellation rules (consistency)
- Restrict cancel to `pending` orders only
- Optional: restore stock on cancel
- Add tests and docs

---

## 🔥 High Priority

### 1. Password Management (NEW)
**Endpoints to create:**
- `POST /users/change-password/` — Change password (requires current password)
- `POST /users/reset-password/` — Request password reset (email token)
- `POST /users/reset-password/confirm/` — Confirm reset with token

**Implementation steps:**
1. Serializers for change/reset/confirm
2. Views + URLs; use Django validators
3. Email template for reset
4. Tests and documentation

---

### 2. Product Image Management (NEW)
**Endpoints to create:**
- `POST /product-images/` — Upload product image
- `GET /product-images/<pk>/` — Retrieve image
- `DELETE /product-images/<pk>/` — Remove image

**Implementation steps:**
1. Serializer for image upload (validate type/size)
2. Views (Create/Retrieve/Destroy)
3. URLs and Swagger examples
4. Prefetch in product detail, optional thumbnail field

---

### 3. Order Cancellation Enhancements
**Update existing:** `POST /orders/order/cancel/<pk>/`

**Implementation steps:**
1. Allow cancel only if `status == 'pending'`
2. Add `cancelled` to status choices if not present
3. Restore stock optionally; audit log
4. Tests + docs

---

## 🟡 Medium Priority

### 4. Reviews System
**Endpoints to create:**
- `GET /reviews/`, `POST /reviews/`, `GET/PUT/PATCH/DELETE /reviews/<pk>/`

**Implementation steps:**
1. Serializer and views (ListCreate, RetrieveUpdateDestroy)
2. URL routes and permissions (owner can update/delete)
3. Filtering by product/user; pagination

---

### 5. Payments Integration
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
- Order Cancellation — `POST /orders/order/cancel/<pk>/` (base flow)
- Product Creation — `POST /products/create/`
- Category Management — `GET/POST /categories/`, `GET/PUT/PATCH/DELETE /categories/<pk>/`

---

## 🎯 Recommended Implementation Order
1) Password Management (High)
2) Product Image Management (High)
3) Order Cancellation Enhancements (High)
4) Reviews (Medium)
5) Payments (Medium)
6) Shipping (Low)
7) Notifications (Low)

---

## 📝 Notes
- Require auth for non-public endpoints; consider RBAC
- Add tests as you implement each feature
- Update Swagger/Redoc examples with real payloads
- Use consistent error response format

---

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

