# Undefined Serializers Report

This document lists all serializers that are **used in views but NOT defined** in their respective serializers files.

## Summary
- **Total Undefined Serializers**: 2
- **Affected Views**: 2 (products, products)

---

## Undefined Serializers

### 1. `ProductImageCreateSerializer`
**Status**: ❌ **UNDEFINED**

- **Used in**: `products/views.py`
- **Location**: `ProductImageDetailView.get_serializer_class()` (Line 80)
- **Usage**: Used for PUT/PATCH requests on product images
- **Current Import**: ❌ NOT imported (import statement at line 13 does not include it)

**Code Reference**:
```python
class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductImageCreateSerializer  # ❌ UNDEFINED
        return ProductImageSerializer
```

**Defined In**: Should be in `products/serializers.py` - **MISSING**

**Imported From**: `products/views.py` line 13
```python
from .serializers import ProductImageSerializer, ProductSerializer, CategorySerializer
# ProductImageCreateSerializer NOT included
```

---

### 2. `ProductCreateUpdateSerializer`
**Status**: ❌ **UNDEFINED**

- **Used in**: `products/views.py`
- **Locations**:
  - `ProductListCreateView.get_serializer_class()` (Line 105) - for POST requests
  - `ProductDetailView.get_serializer_class()` (Line 237) - for PUT/PATCH requests
- **Usage**: Used for creating and updating products
- **Current Import**: ❌ NOT imported (import statement at line 13 does not include it)

**Code References**:
```python
class ProductListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer  # ❌ UNDEFINED
        return ProductSerializer

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer  # ❌ UNDEFINED
        return ProductSerializer
```

**Defined In**: Should be in `products/serializers.py` - **MISSING**

**Imported From**: `products/views.py` line 13
```python
from .serializers import ProductImageSerializer, ProductSerializer, CategorySerializer
# ProductCreateUpdateSerializer NOT included
```

---

## Summary Table

| Serializer Name | File | Defined? | Used In | Issue |
|---|---|---|---|---|
| `ProductImageCreateSerializer` | products/serializers.py | ❌ No | ProductImageDetailView | Missing definition & import |
| `ProductCreateUpdateSerializer` | products/serializers.py | ❌ No | ProductListCreateView, ProductDetailView | Missing definition & import |

---

## Action Items

- [ ] Define `ProductImageCreateSerializer` in `products/serializers.py`
- [ ] Define `ProductCreateUpdateSerializer` in `products/serializers.py`
- [ ] Update imports in `products/views.py` to include both serializers

## All Other Serializers (✅ DEFINED)

These serializers are properly defined and imported:

- ✅ `CartItemSerializer` - carts/serializer.py
- ✅ `CartItemCreateSerializer` - carts/serializer.py
- ✅ `CartSerializer` - carts/serializer.py
- ✅ `CheckoutSerializer` - carts/serializer.py
- ✅ `CheckoutResponseSerializer` - carts/serializer.py
- ✅ `OrderSerializer` - orders/serailizer.py
- ✅ `OrderItemSerializer` - orders/serailizer.py
- ✅ `OrderItemCreateSerializer` - orders/serailizer.py
- ✅ `OrderItemUpdateSerializer` - orders/serailizer.py
- ✅ `OrderStatusUpdateSerializer` - orders/serailizer.py
- ✅ `PaymentSerializer` - payments/serializers.py
- ✅ `PaymentRetrySerializer` - payments/serializers.py
- ✅ `UserSerializer` - users/serializers.py
- ✅ `UserCreateSerializer` - users/serializers.py
- ✅ `UserProfileUpdateSerializer` - users/serializers.py
- ✅ `ReviewsSerializer` - reviews/serializers.py
- ✅ `ShippingSerializer` - shipping/serializers.py
- ✅ `NotificationSerializer` - notifications/serializers.py
- ✅ `ProductSerializer` - products/serializers.py
- ✅ `ProductImageSerializer` - products/serializers.py
- ✅ `CategorySerializer` - products/serializers.py
