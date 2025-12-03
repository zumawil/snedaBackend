# API Response and Exception Handling Guide

This document explains how to use the standardized API response utilities in the e-commerce project.

## Overview

The project uses a standardized response format across all API endpoints to ensure consistency:

```json
{
    "success": true|false,
    "data": any|null,
    "message": "string",
    "error": any|null
}
```

## Utilities

### 1. `normalize_errors` Function

Located in `utils/normalize_errors.py`, this utility flattens deep nested validation error structures into a readable, flat format.

**Example:**
```python
# Nested error structure (hard to read)
{
    "name": {"0": {"message": "This field is required"}},
    "email": {"1": ["Invalid email format"]}
}

# Flattened structure (easy to read)
[
    {'field': 'name.0.message', 'message': 'This field is required'},
    {'field': 'email.1', 'message': 'Invalid email format'}
]
```

### 2. `api_response` Function

Located in `utils/apiResponse.py`, this function provides a standardized way to return API responses and automatically normalizes validation errors.

**Usage:**
```python
from utils.apiResponse import api_response
from rest_framework import status

# Success response
return api_response(
    success=True,
    data=serializer.data,
    message="Operation completed successfully",
    status_code=status.HTTP_200_OK
)

# Error response (validation errors are automatically normalized)
return api_response(
    success=False,
    data=None,
    error=serializer.errors,  # Will be flattened if it's a nested dict
    message="Validation failed",
    status_code=status.HTTP_400_BAD_REQUEST
)
```

**Automatic Error Normalization:**
The `api_response` function automatically detects and flattens nested validation error structures, making them much more readable for frontend developers.

**Before normalization:**
```json
{
    "success": false,
    "error": {
        "billing_address": {
            "street": {"0": "This field is required"},
            "city": {"0": ["City is too short"]}
        },
        "shipping": {"different_address": ["This field must be true"]}
    }
}
```

**After normalization:**
```json
{
    "success": false,
    "error": [
        {"field": "billing_address.street.0", "message": "This field is required"},
        {"field": "billing_address.city.0", "message": "City is too short"},
        {"field": "shipping.different_address", "message": "This field must be true"}
    ]
}
```

### 3. Custom Exception Handler

Located in `utils/exception_handler.py`, automatically handles all DRF exceptions and formats them using the standardized response structure. It also applies error normalization for validation errors.

**Configuration:** Already configured in `snedaEcommerceAPI/settings.py`:
```python
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "utils.exception_handler.custom_exception_handler",
}
```

### 4. Base Generic Views

Located in `utils/generic_views.py`, these base classes ensure all generic views automatically use the `api_response` utility.

**Available Base Classes:**
- `GenericListCreateAPIView` - Combines list and create operations
- `GenericRetrieveUpdateDestroyAPIView` - Combines retrieve, update, and delete operations
- `GenericListAPIView` - List operation only
- `GenericRetrieveAPIView` - Retrieve operation only
- `GenericCreateAPIView` - Create operation only
- `GenericUpdateAPIView` - Update operation only
- `GenericDestroyAPIView` - Delete operation only

## Implementation Examples

### APIView Classes

For APIView-based views, manually use the `api_response` function:

```python
from rest_framework.views import APIView
from utils.apiResponse import api_response

class MyAPIView(APIView):
    def get(self, request):
        data = {"key": "value"}
        return api_response(
            success=True,
            data=data,
            message="Data retrieved successfully",
            status_code=status.HTTP_200_OK
        )
```

### Generic Views

#### Option 1: Use Base Generic Views (Recommended)

```python
from utils.generic_views import GenericListCreateAPIView, GenericRetrieveUpdateDestroyAPIView
from .models import MyModel
from .serializers import MyModelSerializer

class MyModelListCreateView(GenericListCreateAPIView):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer

class MyModelDetailView(GenericRetrieveUpdateDestroyAPIView):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
```

#### Option 2: Override Methods in Existing Generic Views

If you can't use the base classes, override the methods in existing generic views:

```python
from rest_framework import generics
from utils.apiResponse import api_response

class MyModelListCreateView(generics.ListCreateAPIView):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            success=True,
            data=serializer.data,
            message="Models retrieved successfully",
            status_code=status.HTTP_200_OK
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data=serializer.data,
                message="Model created successfully",
                status_code=status.HTTP_201_CREATED
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
```

## Updated Views

The following views have been updated to use the `api_response` utility:

### Products App (`products/views.py`)
- `CategoryListCreateView`
- `CategoryDetailView`
- `ProductImageListView`
- `ProductImageDetailView`
- `ProductListCreateView`
- `ProductDetailView`

### Carts App (`carts/views.py`)
- `CartItemListCreateView`
- `CartItemDetailView`

### Reviews App (`reviews/views.py`)
- `ReviewListCreateView`
- `ReviewDetailView`

## Error Normalization Feature

The project now includes automatic error normalization that makes validation errors much more readable:

### What It Does
- **Flattens nested error structures**: Converts complex nested validation errors into a simple, flat array
- **Improves readability**: Makes it easy for frontend developers to display errors clearly
- **Automatic integration**: Works automatically with `api_response` and the exception handler
- **Backward compatible**: If normalization fails, it falls back to the original error format

### How It Works

The system detects when errors are passed as nested dictionaries and automatically converts them:

```python
# Nested Django validation error structure
{
    'billing_address': {
        'street': ['This field is required'],
        'city': ['City name too short', 'Invalid characters']
    },
    'shipping': ['Different address field must be true']
}

# Gets converted to
[
    {'field': 'billing_address.street', 'message': 'This field is required'},
    {'field': 'billing_address.city', 'message': 'City name too short'},
    {'field': 'billing_address.city', 'message': 'Invalid characters'},
    {'field': 'shipping', 'message': 'Different address field must be true'}
]
```

### Benefits
1. **Frontend Developer Friendly**: Easy to iterate through errors and display them
2. **Consistent Error Format**: All validation errors follow the same structure
3. **Field Mapping**: Errors include field names for better UX
4. **Error Handling**: Graceful fallback if normalization fails

### Usage
The normalization happens automatically when you use:
- `api_response()` function
- Custom exception handler
- Base generic views

No additional code required - just use your existing error handling!

## Best Practices

### 1. Always Use api_response
For all new views, always use the `api_response` function or the base generic views to ensure consistent response formatting.

### 2. Meaningful Messages
Provide clear, user-friendly messages that describe what happened:

```python
# Good
message="Product created successfully"

# Bad
message="Success"
```

### 3. Appropriate Status Codes
Use appropriate HTTP status codes:

- `HTTP_200_OK` - Successful GET, PUT, PATCH
- `HTTP_201_CREATED` - Successful POST
- `HTTP_204_NO_CONTENT` - Successful DELETE
- `HTTP_400_BAD_REQUEST` - Validation errors, bad requests
- `HTTP_401_UNAUTHORIZED` - Authentication required
- `HTTP_403_FORBIDDEN` - Permission denied
- `HTTP_404_NOT_FOUND` - Resource not found
- `HTTP_500_INTERNAL_SERVER_ERROR` - Server errors

### 4. Error Details
Include relevant error information in the `error` field:

```python
return api_response(
    success=False,
    data=None,
    error="Stock unavailable",
    message="Not enough stock for the requested quantity",
    status_code=status.HTTP_400_BAD_REQUEST
)
```

### 5. Data Structure
Be consistent with data structure in the `data` field:

```python
# For single objects
return api_response(
    success=True,
    data=serializer.data,
    message="Product retrieved successfully"
)

# For lists
return api_response(
    success=True,
    data={"products": serializer.data},
    message="Products retrieved successfully"
)

# For custom data
return api_response(
    success=True,
    data={
        "order": order_serializer.data,
        "payment": payment_serializer.data,
        "total": total_amount
    },
    message="Checkout completed successfully"
)
```

## Migration Guide

To migrate existing generic views to use the `api_response` utility:

1. **Identify generic views** that don't use `api_response`
2. **Choose approach:**
   - Use base generic views (cleaner)
   - Override methods in existing views
3. **Test thoroughly** to ensure responses work as expected
4. **Update API documentation** if needed

## Troubleshooting

### Common Issues

1. **Views still returning default DRF responses**
   - Ensure you're using the base generic views or have overridden the methods
   - Check that `api_response` is imported correctly

2. **Exception handler not working**
   - Verify the exception handler is configured in `settings.py`
   - Check that the import path is correct

3. **Validation errors not being caught**
   - The exception handler should automatically catch DRF validation errors
   - For custom validation, manually handle and return `api_response`

### Testing Responses

You can test that your views are using the standardized response format by making API calls and checking the response structure:

```python
# Example response structure
{
    "success": true,
    "data": {...},
    "message": "Operation completed successfully",
    "error": null
}
```

## Future Development

When creating new views:

1. **Start with the base generic views** when possible
2. **Use `api_response` for APIView classes**
3. **Follow the established patterns** for consistency
4. **Test the response format** to ensure it matches the standard

This ensures all endpoints in your API return consistent, well-formatted responses that are easy for frontend developers to work with.