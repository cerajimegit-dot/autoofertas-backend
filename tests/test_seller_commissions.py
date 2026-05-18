"""Tests del endpoint /api/dashboard/seller_commissions/.

Casos:
  - Suma por vendedor.
  - Comisión = monto × rate / 100.
  - Filtro por período.
  - Filtro por branch.
  - Tenancy.
  - Rate clampeado a [0, 100].
"""

from decimal import Decimal
from datetime import datetime

import pytest
from rest_framework.test import APIClient

from core.models import (
    CustomUser, Enterprise, Branch, Customer, Brand, VehicleModel,
    Vehicle, Sale, PaymentForm,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    e1 = Enterprise.objects.create(name='E1', ruc='1', email='e@x.com',
                                    phone='1', address='x', city='x')
    e2 = Enterprise.objects.create(name='E2', ruc='2', email='e2@x.com',
                                    phone='2', address='y', city='y')
    b1 = Branch.objects.create(enterprise=e1, name='A', code='A')
    b2 = Branch.objects.create(enterprise=e1, name='B', code='B')
    b_e2 = Branch.objects.create(enterprise=e2, name='X', code='A')

    pf = PaymentForm.objects.create(enterprise=e1, name='Contado')
    brand = Brand.objects.create(enterprise=e1, name='Toyota')
    model = VehicleModel.objects.create(enterprise=e1, brand=brand, name='Vitz')

    s1 = CustomUser.objects.create_user(
        username='v1', email='v1@e1.com', password='x',
        enterprise=e1, role='vendor', first_name='Mati',
    )
    s2 = CustomUser.objects.create_user(
        username='v2', email='v2@e1.com', password='x',
        enterprise=e1, role='vendor', first_name='Marce',
    )

    c = Customer.objects.create(
        enterprise=e1, first_name='X', last_name='Y',
        document_type='ci', document_number='1', email='x@x.com',
        phone='0', city='X',
    )
    c_e2 = Customer.objects.create(
        enterprise=e2, first_name='X', last_name='Y',
        document_type='ci', document_number='2', email='y@x.com',
        phone='0', city='X',
    )

    def mk_v(branch, vin, e=e1, br=brand, md=model):
        return Vehicle.objects.create(
            enterprise=e, branch=branch, brand=br, model=md, year=2018,
            vin=vin, state='available',
            fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
            cam_vol=Decimal('0'), price=Decimal('1'),
        )

    v1 = mk_v(b1, 'V1')
    v2 = mk_v(b1, 'V2')
    v3 = mk_v(b2, 'V3')

    # Mayo: s1 vende 100M, s2 vende 50M + 30M (b2). Total: 180M.
    Sale.objects.create(
        enterprise=e1, branch=b1, customer=c, vehicle=v1,
        sale_number='M1', sale_date=datetime(2026, 5, 5),
        unit_price=Decimal('100000000'), total_price=Decimal('100000000'),
        payment_form=pf, seller=s1, status='completed',
    )
    Sale.objects.create(
        enterprise=e1, branch=b1, customer=c, vehicle=v2,
        sale_number='M2', sale_date=datetime(2026, 5, 6),
        unit_price=Decimal('50000000'), total_price=Decimal('50000000'),
        payment_form=pf, seller=s2, status='completed',
    )
    Sale.objects.create(
        enterprise=e1, branch=b2, customer=c, vehicle=v3,
        sale_number='M3', sale_date=datetime(2026, 5, 7),
        unit_price=Decimal('30000000'), total_price=Decimal('30000000'),
        payment_form=pf, seller=s2, status='completed',
    )
    # Abril: s1 vende 999M (no entra en el mes de mayo)
    v_abr = mk_v(b1, 'V_ABR')
    Sale.objects.create(
        enterprise=e1, branch=b1, customer=c, vehicle=v_abr,
        sale_number='A1', sale_date=datetime(2026, 4, 1),
        unit_price=Decimal('999000000'), total_price=Decimal('999000000'),
        payment_form=pf, seller=s1, status='completed',
    )
    # E2 — no debe aparecer
    pf_e2 = PaymentForm.objects.create(enterprise=e2, name='Contado')
    brand_e2 = Brand.objects.create(enterprise=e2, name='Toyota')
    model_e2 = VehicleModel.objects.create(enterprise=e2, brand=brand_e2, name='Vitz')
    v_e2 = mk_v(b_e2, 'V_E2', e=e2, br=brand_e2, md=model_e2)
    Sale.objects.create(
        enterprise=e2, branch=b_e2, customer=c_e2, vehicle=v_e2,
        sale_number='OE-1', sale_date=datetime(2026, 5, 10),
        unit_price=Decimal('5000000000'), total_price=Decimal('5000000000'),
        payment_form=pf_e2, status='completed',
    )

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client, 's1_id': s1.id, 's2_id': s2.id, 'b1': b1, 'b2': b2}


def test_default_rate_1pct(setup):
    """Mayo: total 180M → comisión 1.8M."""
    r = setup['client'].get(
        '/api/dashboard/seller_commissions/?date_from=2026-05-01&date_to=2026-05-31'
    )
    body = r.json()
    assert body['total_monto'] == 180_000_000
    assert body['total_comision'] == 1_800_000


def test_rate_custom(setup):
    """Rate 2.5% → 180M * 2.5% = 4.5M."""
    r = setup['client'].get(
        '/api/dashboard/seller_commissions/?date_from=2026-05-01&date_to=2026-05-31&rate=2.5'
    )
    body = r.json()
    assert body['rate_pct'] == 2.5
    assert body['total_comision'] == 4_500_000


def test_por_vendedor(setup):
    r = setup['client'].get(
        '/api/dashboard/seller_commissions/?date_from=2026-05-01&date_to=2026-05-31'
    )
    body = r.json()
    by_seller = {row['seller_id']: row for row in body['by_seller']}
    assert by_seller[setup['s1_id']]['monto_total'] == 100_000_000
    assert by_seller[setup['s1_id']]['comision'] == 1_000_000
    assert by_seller[setup['s2_id']]['monto_total'] == 80_000_000
    assert by_seller[setup['s2_id']]['comision'] == 800_000


def test_filtro_por_branch(setup):
    r = setup['client'].get(
        f'/api/dashboard/seller_commissions/'
        f'?date_from=2026-05-01&date_to=2026-05-31&branch={setup["b2"].id}'
    )
    body = r.json()
    assert body['total_monto'] == 30_000_000


def test_tenancy(setup):
    """La venta de 5B de E2 no debe aparecer."""
    r = setup['client'].get(
        '/api/dashboard/seller_commissions/?date_from=2026-05-01&date_to=2026-05-31'
    )
    body = r.json()
    assert body['total_monto'] < 1_000_000_000


def test_rate_clampeado_a_100(setup):
    r = setup['client'].get(
        '/api/dashboard/seller_commissions/?date_from=2026-05-01&date_to=2026-05-31&rate=99999'
    )
    assert r.json()['rate_pct'] == 100
