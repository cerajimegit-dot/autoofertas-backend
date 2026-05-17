"""
Middleware para auditoria + medicion de performance
"""

import logging
import time
from core.models import AuditLog


perf_logger = logging.getLogger('perf')


class TimingMiddleware:
    """Loguea endpoints que tarden mas de 500ms."""

    SLOW_THRESHOLD_MS = 500

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        t0 = time.perf_counter()
        response = self.get_response(request)
        dt_ms = (time.perf_counter() - t0) * 1000

        if dt_ms > self.SLOW_THRESHOLD_MS:
            user = getattr(request, 'user', None)
            user_id = user.id if user and getattr(user, 'is_authenticated', False) else 'anon'
            perf_logger.warning(
                f"SLOW {request.method} {request.path} {int(dt_ms)}ms user={user_id} "
                f"status={response.status_code}"
            )
        # Header informativo (util en DevTools Network)
        response['X-Response-Time-ms'] = str(int(dt_ms))
        return response


class AuditLogMiddleware:
    """
    Middleware que registra todas las acciones (POST, PUT, DELETE) en AuditLog
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Registrar acciones POST, PUT, DELETE
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            self.log_action(request, response)
        
        return response
    
    def log_action(self, request, response):
        """Registrar la acción en AuditLog"""
        try:
            user = request.user if request.user.is_authenticated else None
            enterprise = user.enterprise if user else None
            
            if not enterprise:
                return
            
            # Mapear método HTTP a acción
            action_map = {
                'POST': 'create',
                'PUT': 'update',
                'PATCH': 'update',
                'DELETE': 'delete',
            }
            action = action_map.get(request.method, 'unknown')
            
            # Obtener información del endpoint
            path_parts = request.path.split('/')
            model_name = path_parts[-2] if len(path_parts) >= 2 else 'unknown'
            
            # No registrar ciertos endpoints
            if model_name in ['token', 'auth']:
                return
            
            object_id = 0
            object_str = f"{action} {model_name}"
            
            # Obtener IP
            ip_address = self.get_client_ip(request)
            
            # Crear log
            AuditLog.objects.create(
                user=user,
                enterprise=enterprise,
                action=action,
                model_name=model_name,
                object_id=object_id,
                object_str=object_str,
                ip_address=ip_address
            )
        
        except Exception as e:
            # No interrumpir la respuesta si hay error en auditoría
            pass
    
    @staticmethod
    def get_client_ip(request):
        """Obtener IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
