from rest_framework.permissions import BasePermission

# check if the user is verified
class IsVerifiedUser(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.verified

class IsAdminUser(BasePermission):
    """
    Permission class to check if user is admin (staff or superuser).
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_staff or request.user.is_superuser)
        )
    
