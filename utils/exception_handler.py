from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status as http_status
from .normalize_errors import normalize_errors


def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats all exceptions using the api_response format.
    Returns responses with: success, data, message, error
    """
    # Let DRF handle the exception first
    response = exception_handler(exc, context)

    if response is None:
        # Unexpected error (500, etc.) - not handled by DRF
        return Response(
            {
                "success": False,
                "data": None,
                "message": "An unexpected error occurred on the server",
                "error": str(exc),
            },
            status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Standard DRF errors (ValidationError, NotFound, PermissionDenied, etc.)
    # Extract error message from response data
    error_detail = response.data
    
    # Try to extract a meaningful message
    if isinstance(error_detail, dict):
        # For validation errors, get the first error message
        if 'detail' in error_detail:
            message = error_detail['detail']
            error = error_detail
        else:
            # For field validation errors - normalize them for better readability
            message = "Validation failed"
            # Use normalize_errors to flatten nested validation errors
            try:
                normalized_errors = normalize_errors(error_detail)
                if normalized_errors:
                    error = normalized_errors
                else:
                    error = error_detail
            except Exception:
                # If normalization fails, use original error
                error = error_detail
    elif isinstance(error_detail, list):
        message = error_detail[0] if error_detail else "Request failed"
        error = error_detail
    else:
        message = str(error_detail)
        error = error_detail

    return Response(
        {
            "success": False,
            "data": None,
            "message": message,
            "error": error,
        },
        status=response.status_code
    )
