"""Tests del filtro ?seller= en /api/sales/.

- `?seller=me` filtra por el usuario autenticado.
- `?seller=<id>` filtra por ese vendedor.
- Sin filtro: trae todas.
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
    b1 = Branch.objects.create(enterprise=e1, name='A', code='A')
    pf = PaymentForm.objects.create(enterprise=e1, name='Contado')
    brand = Brand.objects.create(enterprise=e1, name='Toyota')
    model = VehicleModel.objects.create(enterprise=e1, brand=brand, name='Vitz')

    me = CustomUser.objects.create_user(
        username='me', email='me@e1.com', password='x',
        enterprise=e1, role='vendor', first_name='Yo',
    )
    other = CustomUser.objects.create_user(
        username='otro', email='o@e1.com', password='x',
        enterprise=e1, role='vendor', first_name='Otro',
    )

    c = Customer.objects.create(
        enterprise=e1, first_name='X', last_name='Y',
        document_type='ci', document_number='1', email='x@x.com',
        phone='0', city='X',
    )

    def mk_v(vin):
        return Vehicle.objects.create(
            enterprise=e1, branch=b1, brand=brand, model=model, year=2018,
            vin=vin, state='available',
            fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
            cam_vol=Decimal('0'), price=Decimal('1'),
        )

    Sale.objects.create(
        enterprise=e1, branch=b1, customer=c, vehicle=mk_v('V1'),
        sale_number='S1', sale_date=datetime(2026, 5, 5),
        unit_price=Decimal('1000000'), total_price=Decimal('1000000'),
        payment_form=pf, seller=me, status='completed',
    )
    Sale.objects.create(
        enterprise=e1, branch=b1, customer=c, vehicle=mk_v('V2'),
        sale_number='S2', sale_date=datetime(2026, 5, 6),
        unit_price=Decimal('1000000'), total_price=Decimal('1000000'),
        payment_form=pf, seller=me, status='completed',
    )
    Sale.objects.create(
        enterprise=e1, branch=b1, customer=c, vehicle=mk_v('V3'),
        sale_number='S3', sale_date=datetime(2026, 5, 7),
        unit_price=Decimal('1000000'), total_price=Decimal('1000000'),
        payment_form=pf, seller=other, status='completed',
    )
    # Una venta sin vendedor — no debe aparecer en "mis ventas".
    Sale.objects.create(
        enterprise=e1, branch=b1, customer=c, vehicle=mk_v('V4'),
        sale_number='S4', sale_date=datetime(2026, 5, 8),
        unit_price=Decimal('1000000'), total_price=Decimal('1000000'),
        payment_form=pf, status='completed',
    )

    client = APIClient()
    client.force_authenticate(user=me)
    return {'client': client, 'me': me, 'other': other}


def test_seller_me_trae_solo_mias(setup):
    r = setup['client'].get('/api/sales/?seller=me')
    nums = [s['sale_number'] for s in (r.data.get('results') or r.data)]
    assert sorted(nums) == ['S1', 'S2']


def test_seller_id_explicito(setup):
    r = setup['client'].get(f'/api/sales/?seller={setup["other"].id}')
    nums = [s['sale_number'] for s in (r.data.get('results') or r.data)]
    assert nums == ['S3']


def test_sin_filtro_trae_todas(setup):
    r = setup['client'].get('/api/sales/')
    nums = sorted(s['sale_number'] for s in (r.data.get('results') or r.data))
    assert nums == ['S1', 'S2', 'S3', 'S4']
