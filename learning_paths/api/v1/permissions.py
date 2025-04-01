"""
Django REST framework permissions.
"""

from rest_framework.permissions import BasePermission


class IsAdminOrSelf(BasePermission):
    """
    Permission to allow only admins or the user themselves to access the API.

    Non-staff users cannot pass "username" that is not their own.
    """

    def has_permission(self, request, view):
        if request.user.is_staff:
            return True

        if request.method == "GET":
            username = request.query_params.get("username")
        else:
            username = request.data.get("username")

        # For learners, the username passed should match the logged in user
        if username:
            return request.user.username == username
        return True
