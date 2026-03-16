# Database Schema Documentation

This document provides an overview of the database tables and their fields in the Sneda Ecommerce project, based on the Django models.

## Users App

### `CustomUser`
Extends `AbstractUser`. Uses `email` as the `USERNAME_FIELD`.

| Field | Type | Description |
| :--- | :--- | :--- |
| `email` | EmailField | Primary identifier, unique. |
| `verified` | BooleanField | Whether the user is verified (OTP). |
| `otp_secret` | CharField | Secret key for TOTP generation. |
| `first_name` | CharField | User's first name. |
| `last_name` | CharField | User's last name. |
| `phone_number` | CharField | User's contact number. |
| `address` | TextField | User's primary address. |
| `city` | CharField | User's city. |
| `profile_picture` | ImageField | Path to user's profile picture. |

---

## Products App

### `Product`
The core product model.

| Field | Type | Description |
| :--- | :--- | :--- |
| `item_no` | CharField | Primary Key, unique. |
| `product_group` | ForeignKey | Relation to `ProductGroup`. |
| `category` | ForeignKey | Relation to `Category`. |
| `hs_code` | ForeignKey | Relation to `HSCode`. |
| `gtin` | CharField | Global Trade Item Number. |
| `height`, `width`, `length` | DecimalField | Product dimensions. |
| `weight` | DecimalField | Product weight. |
| `box_qty` | IntegerField | Quantity per box. |
| `inventory_qty` | IntegerField | Total stock quantity. |
| `gross_price` | DecimalField | Price. |
| `brand` | ForeignKey | Relation to `Brand`. |
| `in_stock` | IntegerField | Current available stock. |
| `created_at` | DateTimeField | Timestamp of creation. |
| `updated_at` | DateTimeField | Timestamp of last update. |

### `ProductGroup`, `HSCode`, `Brand`, `Category`
Lookup tables for products.

### `ProductImage`
Images associated with products. Foreign Key to `Product`.

---

## Carts App

### `Cart`
Shopping cart associated with a user. One-to-one with `CustomUser`.

### `CartItem`
Individual items within a cart. Foreign Key to `Cart` and `Product`.

### `CheckoutAttempt`
Idempotency table for checkouts.

| Field | Type | Description |
| :--- | :--- | :--- |
| `key` | CharField | Unique key for the attempt. |
| `order` | ForeignKey | Related `Order`. |
| `created_at` | DateTimeField | Creation timestamp. |

---

## Orders App

### `Order`
Customer orders.

| Field | Type | Description |
| :--- | :--- | :--- |
| `user` | ForeignKey | The user who placed the order. |
| `total_amount` | DecimalField | Total order value. |
| `approved` | BooleanField | Admin approval status. |
| `created_at` | DateTimeField | Creation timestamp. |

### `OrderItem`
Items included in an order. Foreign Key to `Order` and `Product`.

### `Reservation`
Temporary stock reservation for products in an order.

| Field | Type | Description |
| :--- | :--- | :--- |
| `order` | ForeignKey | Related `Order`. |
| `product` | ForeignKey | Related `Product`. |
| `quantity` | PositiveIntegerField| Reserved quantity. |
| `status` | CharField | Choice: `active`, `expired`, `confirmed`, `cancelled`. |
| `expires_at` | DateTimeField | Expiration timestamp. |

---

## Payments App

### `Payment`
Payment transactions for orders.

| Field | Type | Description |
| :--- | :--- | :--- |
| `order` | ForeignKey | Related `Order`. |
| `amount` | DecimalField | Transaction amount. |
| `method` | CharField | CARD, MOBILE_MONEY, BANK, etc. |
| `status` | CharField | PENDING, SUCCESS, FAILED, ABANDONED. |
| `paystack_reference` | CharField | External payment reference. |
| `authorization_url` | URLField | Payment redirection URL. |
| `is_processed` | BooleanField | To prevent duplicate processing. |

---

## Shipping App

### `Shipping`
Shipping details for orders. One-to-one with `Order`.

| Field | Type | Description |
| :--- | :--- | :--- |
| `status` | CharField | PENDING, SHIPPED, DELIVERED, CANCELLED, APPROVED. |
| `tracking_number` | CharField | Tracking identifier. |
| `address` | TextField | Shipping destination. |
| `pickup` | BooleanField | Whether it's a pickup order. |

---

## Notifications App

### `Notification`
User notifications. Foreign Key to `CustomUser`.

---

## Reviews App

### `Reviews`
Product reviews. Foreign Key to `CustomUser` and `Product`. Includes `rating` (1-5).

---

## Background Tasks App

### `BackgroundJob`
Centralized tracking for background Celery tasks.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUIDField | Primary Key, UUID. |
| `task_id` | CharField | Celery task unique ID. |
| `task_type` | CharField | Name of the task being executed. |
| `status` | CharField | `pending`, `processing`, `completed`, `failed`. |
| `related_object_type` | CharField | Model name of related object (e.g., 'order'). |
| `related_object_id` | IntegerField | PK of the related object. |
| `created_at` | DateTimeField | Job creation timestamp. |
| `started_at` | DateTimeField | Execution start timestamp. |
| `finished_at` | DateTimeField | Execution finish timestamp. |
| `error` | TextField | Error details if the job failed. |
