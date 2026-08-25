from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Role-Based Access Control:
    - Administrators (is_staff=True / is_superuser=True): Full CRUD access on products.
    - Customers / Anonymous users: Read-only access (browse, search, filter).
    """
    message = "Permission denied: Only administrators can create, update, or delete products."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))
