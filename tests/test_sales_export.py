"""Tests del endpoint /api/sales/export/."""

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
    b = Branch.objects.create(enterprise=e1, name='A', code='A')
    b_e2 = Branch.objects.create(enterprise=e2, name='X', code='A')
    pf = PaymentForm.objects.create(enterprise=e1, name='Contado')
    pf_e2 = PaymentForm.objects.create(enterprise=e2, name='Contado')
    brand = Brand.objects.create(enterprise=e1, name='T')
    brand_e2 = Brand.objects.create(enterprise=e2, name='T')
    model = VehicleModel.objects.create(enterprise=e1, brand=brand, name='V')
    model_e2 = VehicleModel.objects.create(enterprise=e2, brand=brand_e2, name='V')

    c = Customer.objects.create(
        enterprise=e1, first_name='Mati', last_name='P',
        document_type='ci', document_number='123', email='m@x.com',
        phone='0', city='X',
    )
    c_e2 = Customer.objects.create(
        enterprise=e2, first_name='Otro', last_name='X',
        document_type='ci', document_number='999', email='o@x.com',
        phone='0', city='X',
    )

    def mk_v(vin, e=e1, br_=b, brnd=brand, md=model):
        return Vehicle.objects.create(
            enterprise=e, branch=br_, brand=brnd, model=md, year=2020,
            vin=vin, state='available',
            fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
            cam_vol=Decimal('0'), price=Decimal('1'),
        )

    Sale.objects.create(
        enterprise=e1, branch=b, customer=c, vehicle=mk_v('V1'),
        sale_number='CM-01/26', sale_date=datetime(2026, 5, 5),
        unit_price=Decimal('1000000'), total_price=Decimal('1000000'),
        payment_form=pf, status='completed',
    )
    Sale.objects.create(
        enterprise=e1, branch=b, customer=c, vehicle=mk_v('V2'),
        sale_number='CM-02/26', sale_date=datetime(2026, 5, 10),
        unit_price=Decimal('500000'), total_price=Decimal('500000'),
        payment_form=pf, status='completed',
    )
    Sale.objects.create(
        enterprise=e1, branch=b, customer=c, vehicle=mk_v('V3'),
        sale_number='CM-03/26', sale_date=datetime(2026, 4, 10),
        unit_price=Decimal('300000'), total_price=Decimal('300000'),
        payment_form=pf, status='completed',
    )
    # Otra empresa
    Sale.objects.create(
        enterprise=e2, branch=b_e2, customer=c_e2, vehicle=mk_v('VE2', e=e2, br_=b_e2, brnd=brand_e2, md=model_e2),
        sale_number='OE-01', sale_date=datetime(2026, 5, 5),
        unit_price=Decimal('9000000'), total_price=Decimal('9000000'),
        payment_form=pf_e2, status='completed',
    )

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client}


def _rows(response):
    body = response.content.decode('utf-8').lstrip('﻿')
    return [line for line in body.splitlines() if line != '']


def test_export_bom_y_filename(setup):
    r = setup['client'].get('/api/sales/export/?period=2026-05')
    assert r.status_code == 200
    assert r.content.startswith('﻿'.encode('utf-8'))
    assert 'ventas_2026-05.csv' in r['Content-Disposition']


def test_period_filtra_mes(setup):
    """Mayo 2026 trae las 2 ventas de ese mes, no la de abril."""
    r = setup['client'].get('/api/sales/export/?period=2026-05')
    rows = _rows(r)
    # 1 header + 2 ventas + 1 fila en blanco filtrada + 1 TOTAL = 4
    assert len(rows) == 4
    body = '\n'.join(rows)
    assert 'CM-01/26' in body
    assert 'CM-02/26' in body
    assert 'CM-03/26' not in body
    assert 'TOTAL' in rows[-1]


def test_total_correcto(setup):
    """Mayo: 1.000.000 + 500.000 = 1.500.000."""
    r = setup['client'].get('/api/sales/export/?period=2026-05')
    rows = _rows(r)
    assert '1500000.00' in rows[-1]


def test_tenancy_no_filtra_otra_empresa(setup):
    r = setup['client'].get('/api/sales/export/?period=2026-05')
    body = r.content.decode('utf-8')
    assert 'OE-01' not in body
    assert '9000000' not in body


def test_delimitador_coma(setup):
    r = setup['client'].get('/api/sales/export/?period=2026-05&delimiter=comma')
    rows = _rows(r)
    assert rows[0].startswith('Número,Fecha,Cliente')
