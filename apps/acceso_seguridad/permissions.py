from rest_framework import permissions

class IsAdminRole(permissions.BasePermission):

    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.is_staff or request.user.rol == 'ADMIN'

