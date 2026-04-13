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


class IsVerifiedOrGuest(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.verified:
            return True
        return getattr(request.user, 'is_guest', False)
    
