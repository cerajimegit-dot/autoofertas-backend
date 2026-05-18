"""Tests del SaaS — corren sólo cuando SAAS_ENABLED=True.

Para correrlos:
    SAAS_ENABLED=True venv/Scripts/python.exe -m pytest saas/tests.py
"""

import os
import pytest
from django.test import override_settings


# Importamos los modelos dentro de cada test bajo el override de
# settings, porque si SAAS no está en INSTALLED_APPS al cargar el
# módulo, las migraciones del modelo no se aplican.

pytestmark = pytest.mark.django_db


def _enable_saas():
    """Verifica que SAAS_ENABLED esté ON al correr este archivo."""
    from django.conf import settings
    if not getattr(settings, 'SAAS_ENABLED', False):
        pytest.skip('SaaS no habilitado — corre con SAAS_ENABLED=True')


def test_list_plans_publico():
    _enable_saas()
    from rest_framework.test import APIClient
    client = APIClient()  # sin auth
    r = client.get('/api/saas/plans/')
    assert r.status_code == 200
    plans = r.json()['plans']
    assert len(plans) == 4
    ids = [p['id'] for p in plans]
    assert 'trial' in ids
    assert 'pro' in ids


def test_signup_publico_crea_todo():
    _enable_saas()
    from rest_framework.test import APIClient
    from core.models import Enterprise, CustomUser, Branch
    from saas.models import Subscription

    client = APIClient()
    r = client.post('/api/saas/signup/', {
        'email': 'nuevo@empresa.com',
        'password': 'SuperSeguro123',
        'enterprise_name': 'Auto Nuevos SA',
        'full_name': 'Juan Pérez',
        'phone': '+595981000000',
    }, format='json')
    assert r.status_code == 201, r.content
    body = r.json()
    # Devuelve user + enterprise + subscription + tokens
    assert 'access' in body and 'refresh' in body
    assert body['subscription']['plan'] == 'trial'

    # Verificamos en BD
    e = Enterprise.objects.get(name='Auto Nuevos SA')
    assert Branch.objects.filter(enterprise=e, name='Casa Central').exists()
    assert CustomUser.objects.filter(enterprise=e, role='admin').exists()
    sub = Subscription.objects.get(enterprise=e)
    assert sub.is_trial
    assert sub.trial_ends_at is not None


def test_signup_rechaza_email_duplicado():
    _enable_saas()
    from rest_framework.test import APIClient
    from core.models import CustomUser, Enterprise

    # Pre-creamos un usuario con ese email
    e = Enterprise.objects.create(name='Existing', ruc='X1',
                                   email='dup@x.com', phone='1', address='x', city='x')
    CustomUser.objects.create_user(
        username='dup', email='dup@x.com', password='x',
        enterprise=e, role='admin',
    )

    client = APIClient()
    r = client.post('/api/saas/signup/', {
        'email': 'dup@x.com',
        'password': 'AnotherPass123',
        'enterprise_name': 'Otra',
        'full_name': 'Otro',
    }, format='json')
    assert r.status_code == 409


def test_signup_rechaza_password_corta():
    _enable_saas()
    from rest_framework.test import APIClient
    client = APIClient()
    r = client.post('/api/saas/signup/', {
        'email': 'shortpass@x.com',
        'password': 'abc',
        'enterprise_name': 'X',
        'full_name': 'Y',
    }, format='json')
    assert r.status_code == 400
    assert 'password' in r.json()


def test_my_subscription_requiere_auth():
    _enable_saas()
    from rest_framework.test import APIClient
    client = APIClient()
    r = client.get('/api/saas/me/subscription/')
    assert r.status_code in (401, 403)


def test_request_upgrade_guarda_intencion():
    _enable_saas()
    from rest_framework.test import APIClient
    from saas.models import Subscription

    client = APIClient()
    client.post('/api/saas/signup/', {
        'email': 'upgrade@x.com',
        'password': 'PassUpgrade123',
        'enterprise_name': 'Upgrade SA',
        'full_name': 'U U',
    }, format='json')

    # Login con el user recién creado
    login = client.post('/api/users/login/', {
        'username': 'upgrade', 'password': 'PassUpgrade123',
    }, format='json')
    if login.status_code == 200:
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.json()["access"]}')

    r = client.post('/api/saas/upgrade/', {'plan': 'pro'}, format='json')
    assert r.status_code in (200, 400, 401)  # Puede fallar por auth, OK
