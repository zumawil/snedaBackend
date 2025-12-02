
from rest_framework.response import Response
from rest_framework import status
def api_response(success, data=None, message=None, error=None, status_code=status.HTTP_200_OK):
    """Generalized API response helper function"""
    return Response(
        {
            "success": success,
            "data": data,
            "message": message,
            "error": error,
        },
        status=status_code
    )
