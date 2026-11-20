from rest_framework.permissions import BasePermission, SAFE_METHODS
from profiles.access import has_complete_profile

class IsSuperOrAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return (
            request.method in ("PUT", "PATCH")
            and has_complete_profile(request.user)
        )

