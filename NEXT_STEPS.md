# 🚀 Next Steps - Sneda Ecommerce API

**Last Updated:** 2025-11-25
**Status:** Focusing on Checkout Hardening, Shipping, and Notifications

---

## 📋 Quick Summary

- 🎯 **2 feature areas** remaining (shipping (partially), notifications)
- 🛠️ **Checkout hardening** in progress

---

## ⏭️ Pending Tasks (Immediate Priority)

### 1. Checkout / Order Hardening (Immediate)
- Create a draft Order or CheckoutAttempt before calling external payment APIs so webhooks can reconcile state.
- Return appropriate 4xx errors for expected conditions (e.g., 409 Conflict for stock races) and log failures.

### 2. Shipping Management (Low Priority - Partially Implemented)
- Addresses CRUD and additional tracking features

### 3. Notifications System (Low Priority)
- List, mark read, mark all read, delete

---

## 🛠️ Recommended Immediate Checklist (Pending)
- [ ] Create and run a migration to drop `Order.status` from the database once code is fully migrated; include a backfill RunPython migration if you need to preserve historical status values.
- [ ] Return 4xx errors for expected failures (e.g., 409 Conflict for stock races) and avoid 500 for expected conditions
- [ ] Add unit/integration tests for concurrent checkout and stock validation
- [ ] Add logging/metrics for checkout failures and stock update conflicts
- [ ] Create a short migration plan if you add a CheckoutAttempt/draft Order model

---

## 📝 Notes
- Require auth for non-public endpoints; consider RBAC
- Add tests as you implement each feature
- Update Swagger/Redoc examples with real payloads
- Use consistent error response format

---

## 🎯 Recommended Implementation Order
1) Shipping (Low)
2) Notifications (Low)

---

## 📝 Checklist Template
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
