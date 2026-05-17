"""Throttles con scope fijo, listos para usar desde @action.

`ScopedRateThrottle` no sirve acá porque su `allow_request` sobreescribe
`self.scope` con `view.throttle_scope`, y `@action` no acepta ese atributo
como kwarg. Heredamos directo de `SimpleRateThrottle` y fijamos el scope
de clase, leyendo el rate desde `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`.

Identificador: la IP del cliente (anon throttle), sin importar si está
autenticado o no — es lo que querés en login/register.
"""
from rest_framework.throttling import SimpleRateThrottle


class IPScopedThrottle(SimpleRateThrottle):
    """Base: clave de cache por (scope, IP)."""
    scope = ''  # override en subclase

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class LoginRateThrottle(IPScopedThrottle):
    scope = 'login'


class RegisterRateThrottle(IPScopedThrottle):
    scope = 'register'


class WhatsAppRateThrottle(IPScopedThrottle):
    scope = 'whatsapp'
