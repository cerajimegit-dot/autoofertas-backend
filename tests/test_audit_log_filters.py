"""Tests del endpoint /api/audit-logs/ con filtros.

Verificamos:
  - Sólo admins acceden.
  - Filtros: action, model, user, date_from/date_to, q (substring).
  - Tenancy: un admin no ve los logs de otra empresa.
"""

from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import CustomUser, Enterprise, AuditLog


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    e1 = Enterprise.objects.create(name='E1', ruc='1', email='e@x.com',
                                    phone='1', address='x', city='x')
    e2 = Enterprise.objects.create(name='E2', ruc='2', email='e2@x.com',
                                    phone='2', address='y', city='y')
    admin = CustomUser.objects.create_user(
        username='admin', email='admin@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    vendor = CustomUser.objects.create_user(
        username='v', email='v@e1.com', password='x',
        enterprise=e1, role='vendor',
    )

    def mk_log(e, user, action, model, obj_id, obj_str, ts_offset_min=0):
        log = AuditLog.objects.create(
            user=user, enterprise=e, action=action,
            model_name=model, object_id=obj_id, object_str=obj_str,
            ip_address='127.0.0.1',
        )
        if ts_offset_min:
            new_ts = timezone.now() + timedelta(minutes=ts_offset_min)
            AuditLog.objects.filter(pk=log.pk).update(timestamp=new_ts)
        return log

    # Logs en E1
    mk_log(e1, admin, 'create', 'Sale',  1, 'CM-001/26')
    mk_log(e1, admin, 'update', 'Sale',  1, 'CM-001/26')
    mk_log(e1, admin, 'delete', 'Sale',  1, 'CM-001/26')
    mk_log(e1, vendor, 'create', 'Customer', 1, 'Carlos Pérez')
    mk_log(e1, vendor, 'login',  'CustomUser', 2, 'v')
    # Log antiguo (1 hora atrás) para testear date_from/date_to
    mk_log(e1, admin, 'create', 'Vehicle', 1, 'JTDBT123ABC', ts_offset_min=-60 * 24 * 30)  # 30 días
    # Log de otra empresa — no debe aparecer
    admin_e2 = CustomUser.objects.create_user(
        username='admin2', email='ae2@e2.com', password='x',
        enterprise=e2, role='admin',
    )
    mk_log(e2, admin_e2, 'create', 'Sale', 99, 'SECRETO-OTRA')

    client_admin = APIClient()
    client_admin.force_authenticate(user=admin)
    client_vendor = APIClient()
    client_vendor.force_authenticate(user=vendor)
    return {
        'admin_client': client_admin,
        'vendor_client': client_vendor,
        'admin_id': admin.id,
        'vendor_id': vendor.id,
    }


def test_vendor_no_accede(setup):
    """role=vendor recibe 403."""
    r = setup['vendor_client'].get('/api/audit-logs/')
    assert r.status_code == 403


def test_admin_ve_logs(setup):
    r = setup['admin_client'].get('/api/audit-logs/')
    assert r.status_code == 200


def test_filtro_action(setup):
    r = setup['admin_client'].get('/api/audit-logs/?action=delete')
    body = r.json()
    assert all(log['action'] == 'delete' for log in body.get('results', body))


def test_filtro_model(setup):
    r = setup['admin_client'].get('/api/audit-logs/?model=Sale')
    body = r.json()
    items = body.get('results', body)
    assert all(log['model_name'] == 'Sale' for log in items)


def test_filtro_user(setup):
    r = setup['admin_client'].get(f'/api/audit-logs/?user={setup["vendor_id"]}')
    body = r.json()
    items = body.get('results', body)
    # Sólo logs del vendor
    assert len(items) >= 1
    for log in items:
        # user field puede ser id o objeto, hay que chequear ambos
        u = log.get('user')
        u_id = u.get('id') if isinstance(u, dict) else u
        assert u_id == setup['vendor_id']


def test_filtro_q_substring(setup):
    r = setup['admin_client'].get('/api/audit-logs/?q=CM-001')
    body = r.json()
    items = body.get('results', body)
    assert len(items) == 3   # las 3 acciones sobre la venta CM-001/26


def test_tenancy(setup):
    """El admin de E1 NUNCA ve el SECRETO-OTRA."""
    r = setup['admin_client'].get('/api/audit-logs/?q=SECRETO')
    body = r.json()
    items = body.get('results', body)
    assert len(items) == 0


def test_filtro_date_from(setup):
    """date_from=hoy excluye el log de hace 30 días."""
    today = datetime.now().date().isoformat()
    r = setup['admin_client'].get(f'/api/audit-logs/?date_from={today}&model=Vehicle')
    body = r.json()
    items = body.get('results', body)
    assert len(items) == 0
