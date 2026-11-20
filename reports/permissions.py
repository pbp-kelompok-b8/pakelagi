from rest_framework.permissions import BasePermission

from profiles.access import has_complete_profile


class HasCompleteProfile(BasePermission):
    def has_permission(self, request, view):
        return has_complete_profile(request.user)
