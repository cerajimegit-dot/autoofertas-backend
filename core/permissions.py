from rest_framework import permissions
from core.models import Enterprise, Branch


class IsAuthenticated(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario está autenticado.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsAdmin(permissions.BasePermission):
    """
    Permiso para permitir acceso solo a administradores.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsManagerOrAdmin(permissions.BasePermission):
    """
    Permiso para permitir acceso a encargados y administradores.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ('manager', 'admin')
        )


class IsEnterpriseOwnerOrAdmin(permissions.BasePermission):
    """
    Permiso para verificar que el usuario pertenece a la empresa.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        # Verificar que el objeto pertenece a la empresa del usuario
        if hasattr(obj, 'enterprise'):
            return obj.enterprise == request.user.enterprise
        return False


class IsEnterpriseUser(permissions.BasePermission):
    """
    Permiso para verificar que el usuario es de la misma empresa.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'enterprise_id'):
            return obj.enterprise_id == request.user.enterprise_id
        if isinstance(obj, Enterprise):
            return obj.id == request.user.enterprise_id
        return False


class CanViewOwnBranchData(permissions.BasePermission):
    """
    Permiso para que managers vean solo datos de su sucursal.
    Admins pueden ver todo.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            # Admins pueden ver todo
            return True
        
        if request.user.role == 'manager':
            # Managers ven solo datos de su sucursal
            if hasattr(obj, 'branch_id'):
                user_branch = request.user.branches_managed.first()
                return obj.branch_id == user_branch.id if user_branch else False
        
        # Vendedores ven solo datos de su sucursal
        if request.user.role == 'vendor':
            if hasattr(obj, 'branch_id'):
                # Se asume que el vendedor tiene una sucursal asignada
                # Esto se puede mejorar agregando un many-to-many de vendedores por sucursal
                return True
        
        return False


class CanDeleteSale(permissions.BasePermission):
    """
    Permiso especial para eliminar ventas (requiere aprobación de manager/admin).
    """
    def has_permission(self, request, view):
        if request.method == 'DELETE':
            return (
                request.user and
                request.user.is_authenticated and
                request.user.role in ('manager', 'admin')
            )
        return True
    
    def has_object_permission(self, request, view, obj):
        if request.method == 'DELETE':
            if request.user.role == 'admin':
                return True
            if request.user.role == 'manager':
                # Manager solo puede eliminar de su sucursal
                user_branch = request.user.branches_managed.first()
                return obj.branch_id == user_branch.id if user_branch else False
        return True
