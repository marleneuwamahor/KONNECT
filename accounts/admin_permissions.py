
from rest_framework.permissions import BasePermission

from .models import User


class IsSuperAdmin(BasePermission):
    """
    Restrict access to authenticated, active Django superusers
    with the KONNECT admin role.
    """

    message = "Only an active superadmin can perform this action."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_superuser
            and user.role == User.Role.ADMIN
        )
