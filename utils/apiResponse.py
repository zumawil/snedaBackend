
from rest_framework.response import Response
from rest_framework import status
from .normalize_errors import normalize_errors

def api_response(success, data=None, message=None, error=None, status_code=status.HTTP_200_OK):
    """
    Generalized API response helper function
    
    Args:
        success (bool): Whether the operation was successful
        data: The data to return (can be any type)
        message (str): A human-readable message about the response
        error: Error information (will be normalized if it's a validation error dict)
        status_code: HTTP status code
    
    Returns:
        Response: DRF Response object with standardized format
    """
    
    # Normalize validation errors if they come as nested dicts
    if error and isinstance(error, dict):
        try:
            normalized_errors = normalize_errors(error)
            if normalized_errors:  # Only use normalized errors if we got results
                error = normalized_errors
        except Exception:
            # If normalization fails, use original error
            pass
    
    return Response(
        {
            "success": success,
            "data": data,
            "message": message,
            "error": error,
        },
        status=status_code
    )
