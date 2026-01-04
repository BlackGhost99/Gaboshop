"""
Finance permissions
"""
from rest_framework import permissions


class IsStoreManager(permissions.BasePermission):
    """Seul le gérant du store peut accéder"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.managed_stores.exists()
    
    def has_object_permission(self, request, view, obj):
        # Pour Expense ou autre objet avec FK store
        return obj.store.manager == request.user
