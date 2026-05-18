"""Tests del endpoint /api/quotas/upcoming/?days=N.

Casos:
  - Default days=7: incluye sólo cuotas con due_date entre hoy y +7d.
  - Custom days=14: ventana mayor.
  - Cap en 90 días.
  - ?branch= filtra por sucursal.
  - ?include_overdue=true: agrega cuotas ya vencidas no pagadas.
  - Cada item trae `whatsapp_link` y `days_until_due`.
  - Cuotas paid/cancelled NO aparecen.
  - Cuotas sin teléfono del cliente: whatsapp_link es null pero el
    item sigue apareciendo.
"""

from decimal import Decimal
from datetime import date, timedelta, datetime

import pytest
from rest_framework.test import APIClient

from core.models import (
    CustomUser, Enterprise, Branch, Customer, Brand, VehicleModel,
    Vehicle, Sale, Quotum, PaymentForm,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    today = date.today()

    e1 = Enterprise.objects.create(
        name='E1', ruc='1', email='e1@x.com',
        phone='1', address='x', city='Asunción',
    )
    b1 = Branch.objects.create(enterprise=e1, name='A', code='A')
    b2 = Branch.objects.create(enterprise=e1, name='B', code='B')

    brand = Brand.objects.create(enterprise=e1, name='Toyota')
    model = VehicleModel.objects.create(enterprise=e1, brand=brand, name='Vitz')
    pf = PaymentForm.objects.create(enterprise=e1, name='Crédito')

    c_con_tel = Customer.objects.create(
        enterprise=e1, first_name='Mati', last_name='Pérez',
        document_type='ci', document_number='1', email='m@x.com',
        phone='0981111111', city='X',
    )
    c_sin_tel = Customer.objects.create(
        enterprise=e1, first_name='Sin', last_name='Tel',
        document_type='ci', document_number='2', email='s@x.com',
        phone='', city='X',
    )

    def make_vehicle(vin, branch=b1):
        return Vehicle.objects.create(
            enterprise=e1, branch=branch, brand=brand, model=model, year=2020,
            vin=vin, state='available',
            fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
            cam_vol=Decimal('0'), price=Decimal('1'),
        )

    v1 = make_vehicle('VIN1', b1)
    v2 = make_vehicle('VIN2', b2)
    v3 = make_vehicle('VIN3', b1)

    s1 = Sale.objects.create(
        enterprise=e1, branch=b1, customer=c_con_tel, vehicle=v1,
        sale_number='S1', sale_date=datetime.now(),
        unit_price=Decimal('1000000'), total_price=Decimal('1000000'),
        payment_form=pf, status='completed',
    )
    s2 = Sale.objects.create(
        enterprise=e1, branch=b2, customer=c_sin_tel, vehicle=v2,
        sale_number='S2', sale_date=datetime.now(),
        unit_price=Decimal('1000000'), total_price=Decimal('1000000'),
        payment_form=pf, status='completed',
    )
    s3 = Sale.objects.create(
        enterprise=e1, branch=b1, customer=c_con_tel, vehicle=v3,
        sale_number='S3', sale_date=datetime.now(),
        unit_price=Decimal('1000000'), total_price=Decimal('1000000'),
        payment_form=pf, status='completed',
    )

    # Cuotas:
    # - Q_HOY: vence hoy, pending. Aparece con days=1+
    # - Q_3D:  vence en 3 días, pending. Aparece con days=3+
    # - Q_14D: vence en 14 días, pending. Aparece con days=14+
    # - Q_60D: vence en 60 días — fuera de la ventana por default.
    # - Q_VENCIDA: vencida hace 5 días, pending. Sólo si include_overdue=true.
    # - Q_PAID: vence en 5 días pero ya pagada → NUNCA aparece.
    # - Q_CANCEL: cancelada → NUNCA aparece.
    # - Q_OTRA_BRANCH: vence en 3 días pero en branch b2.
    # - Q_SIN_TEL: vence en 5 días, customer sin teléfono.
    def mk(sale, cust, n, days_offset, status='pending'):
        return Quotum.objects.create(
            enterprise=e1, sale=sale, customer=cust, total_plan=10,
            quota_number=n, amount=Decimal('100000'),
            due_date=today + timedelta(days=days_offset),
            status=status,
            payment_date=(today if status == 'paid' else None),
        )

    mk(s1, c_con_tel, 1, 0)
    mk(s1, c_con_tel, 2, 3)
    mk(s1, c_con_tel, 3, 14)
    mk(s1, c_con_tel, 4, 60)
    mk(s1, c_con_tel, 5, -5)  # vencida
    mk(s1, c_con_tel, 6, 5, status='paid')
    mk(s1, c_con_tel, 7, 5, status='cancelled')
    mk(s3, c_con_tel, 8, 3)   # otra venta misma branch
    mk(s2, c_sin_tel, 9, 3)   # otra branch
    mk(s1, c_sin_tel, 10, 5)  # sin tel pero misma branch — debe aparecer

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client, 'b1': b1, 'b2': b2}


def test_default_days_7(setup):
    """days por default = 7. Capta hoy, 3d, 5d (sin tel). NO 14d, 60d, -5d, paid, cancelled."""
    r = setup['client'].get('/api/quotas/upcoming/')
    body = r.json()
    assert body['days'] == 7
    # Quotas con due en [hoy, +7d] de cualquier branch + status pending:
    # nums: 1 (hoy), 2 (3d), 8 (3d), 9 (3d otra branch), 10 (5d sin tel) = 5
    nums = sorted(q['quota_number'] for q in body['results'])
    assert nums == [1, 2, 8, 9, 10]


def test_days_14_incluye_mas(setup):
    r = setup['client'].get('/api/quotas/upcoming/?days=14')
    body = r.json()
    nums = sorted(q['quota_number'] for q in body['results'])
    assert 3 in nums  # 14 días
    assert 4 not in nums  # 60 días — fuera


def test_filtro_por_branch(setup):
    r = setup['client'].get(f'/api/quotas/upcoming/?branch={setup["b1"].id}')
    body = r.json()
    # No debe aparecer la quota 9 (branch b2)
    nums = [q['quota_number'] for q in body['results']]
    assert 9 not in nums


def test_include_overdue(setup):
    r = setup['client'].get('/api/quotas/upcoming/?include_overdue=true')
    body = r.json()
    nums = [q['quota_number'] for q in body['results']]
    assert 5 in nums  # vencida hace 5 días


def test_paid_y_cancelled_excluidas(setup):
    r = setup['client'].get('/api/quotas/upcoming/?days=30&include_overdue=true')
    body = r.json()
    nums = [q['quota_number'] for q in body['results']]
    assert 6 not in nums   # paid
    assert 7 not in nums   # cancelled


def test_whatsapp_link_y_days_until_due(setup):
    r = setup['client'].get('/api/quotas/upcoming/?days=7')
    body = r.json()
    # Para una con teléfono → link con wa.me/595...
    q_con = next(q for q in body['results'] if q['quota_number'] == 1)
    assert q_con['whatsapp_link'].startswith('https://wa.me/595')
    assert q_con['days_until_due'] == 0
    q_futuro = next(q for q in body['results'] if q['quota_number'] == 2)
    assert q_futuro['days_until_due'] == 3
    # Cliente sin teléfono → whatsapp_link null
    q_sin = next(q for q in body['results'] if q['quota_number'] == 10)
    assert q_sin['whatsapp_link'] is None


def test_cap_en_90_dias(setup):
    """days=9999 queda capeado en 90."""
    r = setup['client'].get('/api/quotas/upcoming/?days=9999')
    body = r.json()
    assert body['days'] == 90
