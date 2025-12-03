from rest_framework.views import exception_handler
from .response import error_response
# from apiResponse import apiResponse

def custom_exception_handler(exc, context):
    # Let DRF handle the exception first
    response = exception_handler(exc, context)

    if response is None:
        # Unexpected error (500, etc.)
        return error_response(
            message="Something went wrong on the server",
            errors=str(exc),
            status=500
        )

    # Standard DRF errors (ValidationError, NotFound, PermissionDenied, etc.)
    return error_response(
        message="Request failed",
        errors=response.data,
        status=response.status_code
    )
