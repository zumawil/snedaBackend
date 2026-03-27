# Backend Hardening & Features Summary

**Branch**: `refactor`
**Focus**: Bulletproofing the Checkout, Payment, and Inventory Flows against concurrency issues, overselling, and data drift.

---

## 1. Unified Stock Management & Reservations
- **Removed `in_stock` column**: Replaced redundant boolean states with a strict integer-based tracking system using `Product.inventory_qty`.
- **Global `Reservation` System**: When checking out, items are placed into a temporary 15-minute `Reservation` hold. 
- **Dynamic API Visibility**: `ProductSerializer` now mathematically computes `available_stock` (Physical `inventory_qty` MINUS `Active Reservations`). The frontend will inherently never allow users to add mathematically unavailable items to their cart.

## 2. Atomic Transactions & Zero Overselling
- **`select_for_update` Locks**: Database rows for `Payment` and `Order` are physically locked during webhook execution to prevent parallel Paystack callbacks from deducting the same stock twice (Duplicate Webhook Protection).
- **Atomic Operations**: Employs `inventory_qty__gte` at the database level. Stock is guaranteed never to drop below zero, even if thousands of global requests hit the database simultaneously.

## 3. Webhook Grace Periods & Late Event Handling
- **2-Minute Buffer**: Gives Paystack callbacks an extra 120 seconds of grace time beyond the 15-minute reservation window to successfully capture the stock lock.
- **Graceful OOM / Failure Avoidance**: If a webhook is horribly delayed and somebody else already bought the physical item, the system does **not** roll back the payment (since you already have the money). Instead:
  - Payment marks as `SUCCESS`.
  - Fulfillment is aborted.
  - A `CRITICAL: STOCK OVERSELL` error is explicitly logged.

## 4. Admin "Manual Review" Intervention API
- When the late webhook oversell scenario (described above) occurs, the `Order` model auto-flags `marked_for_review = True`.
- Added to the `OrderAdmin` Django panel so internal teams can quickly filter "Orders that took money but failed stock allocation" and reach out to the customer.
- Safely exposed to the frontend via `OrderSerializer` if you build a custom Admin dashboard in React/Next.js.

## 5. Refunds & `restore_stock` Integrity
- **Restoration Rules**: Handled entirely inside `order.restore_stock()`. If you cancel a user's order, it intelligently knows how to void their reservations.
- **Shipping Safety Check**: If `restore_stock()` sees the item is already `shipped` or `delivered` via the `Shipping` model, it strictly blocks physical integer restoration (items are gone).
- **Paystack Refund Webhook**: Added `initiate_paystack_refund` to `payment_helpers.py`. If you cancel a `PAID` order, the system hits the Paystack Refund endpoint live. If successful, the Order's state natively transforms to the brand new `REFUNDED` status field.

## 6. Celery Auto-Cleanup
- Improved `orders/tasks.py` -> `cancel_unpaid_orders()`.
- Runs automatically in the background via Celery Beat, scrubbing your database for entirely abandoned `PENDING` orders older than 30 minutes, actively canceling their stale reservations so the physical items become buyable again for new users.

## 7. Extensive Automated Coverage
- Created `payments/tests_logic.py`, utilizing Python Mocking and factories.
- **8 Distinct Testing Assertions**: Verifies Atomic Deduction failures, Background Celery Tasks, Paystack refund triggers, Grace Periods, and proper Order flag tracking within microseconds, guaranteeing code safety for subsequent deployments.
