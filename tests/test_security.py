"""Tests de las defensas pre-producción: throttling, blacklist, settings."""

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Cada test arranca con throttle cache limpia.

    DRF throttle vive en el cache; sin limpiar entre tests cada uno arrastra
    los hits del anterior y los rate limits estallan después del primero.
    """
    cache.clear()
    yield
    cache.clear()


class TestLoginThrottle:
    """El endpoint /api/users/login/ se throttlea a 5/min por IP."""

    def test_login_throttle_kicks_in_after_limit(self, settings, test_admin_user):
        # Forzamos una rate baja para que el test sea rápido y determinístico.
        settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'] = '3/min'
        client = APIClient()

        # 3 intentos pasan (devuelven 401 por contraseña mala, no 429)
        for i in range(3):
            r = client.post('/api/users/login/', {
                'username': 'admintest', 'password': 'wrong',
            }, format='json')
            assert r.status_code == 401, f'iter {i}: {r.status_code} {r.data}'

        # El 4° está throttled
        r = client.post('/api/users/login/', {
            'username': 'admintest', 'password': 'wrong',
        }, format='json')
        assert r.status_code == 429, r.data
        assert 'detail' in r.data

    def test_successful_login_also_counts(self, settings, test_admin_user):
        settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'] = '2/min'
        client = APIClient()
        r = client.post('/api/users/login/', {
            'username': 'admintest', 'password': 'testpass123',
        }, format='json')
        assert r.status_code == 200
        r = client.post('/api/users/login/', {
            'username': 'admintest', 'password': 'testpass123',
        }, format='json')
        assert r.status_code == 200
        # Tercer intento — throttled
        r = client.post('/api/users/login/', {
            'username': 'admintest', 'password': 'testpass123',
        }, format='json')
        assert r.status_code == 429


class TestJWTBlacklist:
    """Logout invalida el refresh; rotación lo blacklistea después de usarlo."""

    def test_logout_blacklists_refresh(self, test_admin_user):
        client = APIClient()
        # Login → obtener tokens
        r = client.post('/api/users/login/', {
            'username': 'admintest', 'password': 'testpass123',
        }, format='json')
        assert r.status_code == 200
        access = r.data['access']
        refresh = r.data['refresh']

        # Logout pasando refresh
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        r = client.post('/api/users/logout/', {'refresh': refresh}, format='json')
        assert r.status_code == 200

        # El refresh ya no debe servir para obtener un nuevo access
        client.credentials()
        r = client.post('/api/token/refresh/', {'refresh': refresh}, format='json')
        assert r.status_code == 401, f'refresh blacklistedo debería fallar: {r.data}'

    def test_refresh_token_rotates_and_old_is_blacklisted(self, test_admin_user):
        client = APIClient()
        r = client.post('/api/users/login/', {
            'username': 'admintest', 'password': 'testpass123',
        }, format='json')
        old_refresh = r.data['refresh']

        # Renovar — debería emitir un nuevo refresh distinto al viejo y
        # blacklistear el viejo (ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION).
        r = client.post('/api/token/refresh/', {'refresh': old_refresh}, format='json')
        assert r.status_code == 200
        new_refresh = r.data.get('refresh')
        assert new_refresh and new_refresh != old_refresh, 'refresh debería rotar'

        # El refresh viejo NO debería volver a servir.
        r = client.post('/api/token/refresh/', {'refresh': old_refresh}, format='json')
        assert r.status_code == 401

    def test_logout_without_refresh_returns_400(self, test_admin_user):
        client = APIClient()
        r = client.post('/api/users/login/', {
            'username': 'admintest', 'password': 'testpass123',
        }, format='json')
        access = r.data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        r = client.post('/api/users/logout/', {}, format='json')
        assert r.status_code == 400


class TestSecuritySettings:
    """Verificamos que los settings sensibles tengan valores seguros."""

    def test_secret_key_not_default_in_production_mode(self):
        from django.conf import settings
        # En tests/local, SECRET_KEY tiene el default insecure. Eso es OK
        # porque DEBUG=True. El guard productivo se activa cuando DEBUG=False
        # y SECRET_KEY sigue empezando con 'django-insecure-' — ese caso lo
        # cubre `playas_autos/settings.py` con `raise RuntimeError(...)`.
        if not settings.DEBUG:
            assert not settings.SECRET_KEY.startswith('django-insecure-'), (
                'SECRET_KEY default no permitida en producción'
            )

    def test_jwt_rotation_is_on(self):
        from django.conf import settings
        assert settings.SIMPLE_JWT['ROTATE_REFRESH_TOKENS'] is True
        assert settings.SIMPLE_JWT['BLACKLIST_AFTER_ROTATION'] is True

    def test_throttle_rates_defined(self):
        from django.conf import settings
        rates = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {})
        assert 'anon' in rates and 'user' in rates
        assert 'login' in rates
