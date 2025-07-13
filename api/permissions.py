from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj == request.user


class IsSalonOwner(permissions.BasePermission):
    """
    Custom permission to only allow salon owners to access their data.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # For salon objects
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For objects that have a salon relationship
        if hasattr(obj, 'salon'):
            return obj.salon.user == request.user
        
        # For documents that have salon relationship
        if hasattr(obj, 'document') and hasattr(obj.document, 'salon'):
            return obj.document.salon.user == request.user
        
        return False 