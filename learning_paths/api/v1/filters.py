"""
Django REST framework filters.
"""

from rest_framework.filters import BaseFilterBackend


class AdminOrSelfFilterBackend(BaseFilterBackend):
    """
    A filter backend that limits the queryset to the current user for non-staff.
    """

    def filter_queryset(self, request, queryset, view):
        if request.user.is_staff:
            return queryset
        return queryset.filter(user=request.user)
