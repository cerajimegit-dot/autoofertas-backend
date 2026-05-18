"""Tests del endpoint /api/dashboard/margin_analysis/."""

from decimal import Decimal
from datetime import datetime

import pytest
from rest_framework.test import APIClient

from core.models import (
    CustomUser, Enterprise, Branch, Customer, Brand, VehicleModel,
    Vehicle, Sale, PaymentForm,
)
from core.models.inventory import VehicleCost


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    e1 = Enterprise.objects.create(name='E1', ruc='1', email='e@x.com',
                                    phone='1', address='x', city='x')
    b = Branch.objects.create(enterprise=e1, name='A', code='A')
    pf = PaymentForm.objects.create(enterprise=e1, name='Contado')
    brand = Brand.objects.create(enterprise=e1, name='T')
    model = VehicleModel.objects.create(enterprise=e1, brand=brand, name='V')

    c = Customer.objects.create(
        enterprise=e1, first_name='X', last_name='Y',
        document_type='ci', document_number='1', email='x@x.com',
        phone='0', city='X',
    )

    # Vehículo 1: costo base 50M, precio 100M → margen 50M (50%)
    v1 = Vehicle.objects.create(
        enterprise=e1, branch=b, brand=brand, model=model, year=2018,
        vin='V1', state='available',
        fob=Decimal('30000000'), container=Decimal('10000000'),
        dispatch=Decimal('5000000'), cam_vol=Decimal('5000000'),
        price=Decimal('100000000'),
    )
    # Vehículo 2: costo base 80M, precio 90M → margen 10M (~11%)
    v2 = Vehicle.objects.create(
        enterprise=e1, branch=b, brand=brand, model=model, year=2019,
        vin='V2', state='available',
        fob=Decimal('80000000'), container=Decimal('0'),
        dispatch=Decimal('0'), cam_vol=Decimal('0'),
        price=Decimal('90000000'),
    )
    # Vehículo 3: costo base 30M + extra 5M, precio 50M → margen 15M (30%)
    v3 = Vehicle.objects.create(
        enterprise=e1, branch=b, brand=brand, model=model, year=2020,
        vin='V3', state='available',
        fob=Decimal('30000000'), container=Decimal('0'),
        dispatch=Decimal('0'), cam_vol=Decimal('0'),
        price=Decimal('50000000'),
    )
    VehicleCost.objects.create(
        enterprise=e1, vehicle=v3, concept='Patente', amount=Decimal('5000000'),
        currency='PYG', order=0,
    )

    Sale.objects.create(
        enterprise=e1, branch=b, customer=c, vehicle=v1,
        sale_number='V1S', sale_date=datetime(2026, 5, 5),
        unit_price=Decimal('100000000'), total_price=Decimal('100000000'),
        payment_form=pf, status='completed',
    )
    Sale.objects.create(
        enterprise=e1, branch=b, customer=c, vehicle=v2,
        sale_number='V2S', sale_date=datetime(2026, 5, 6),
        unit_price=Decimal('90000000'), total_price=Decimal('90000000'),
        payment_form=pf, status='completed',
    )
    Sale.objects.create(
        enterprise=e1, branch=b, customer=c, vehicle=v3,
        sale_number='V3S', sale_date=datetime(2026, 5, 7),
        unit_price=Decimal('50000000'), total_price=Decimal('50000000'),
        payment_form=pf, status='completed',
    )

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client}


def test_margins_calculados(setup):
    r = setup['client'].get('/api/dashboard/margin_analysis/?date_from=2026-05-01&date_to=2026-05-31')
    body = r.json()
    assert body['n_ventas'] == 3
    by_num = {row['sale_number']: row for row in body['results']}
    # V1: 100M - 50M = 50M (50%)
    assert by_num['V1S']['cost']   == 50_000_000
    assert by_num['V1S']['margin'] == 50_000_000
    assert by_num['V1S']['margin_pct'] == 50.0
    # V2: 90M - 80M = 10M (~11.1%)
    assert by_num['V2S']['margin'] == 10_000_000
    assert 10.0 < by_num['V2S']['margin_pct'] < 12.0
    # V3: 50M - 35M = 15M (30%)
    assert by_num['V3S']['cost']   == 35_000_000
    assert by_num['V3S']['margin_pct'] == 30.0


def test_orden_peores_primero(setup):
    r = setup['client'].get('/api/dashboard/margin_analysis/?date_from=2026-05-01&date_to=2026-05-31')
    body = r.json()
    nums = [row['sale_number'] for row in body['results']]
    # V2 tiene el peor margen
    assert nums[0] == 'V2S'
    assert nums[-1] == 'V1S'


def test_totales_agregados(setup):
    r = setup['client'].get('/api/dashboard/margin_analysis/?date_from=2026-05-01&date_to=2026-05-31')
    body = r.json()
    # total_price = 100 + 90 + 50 = 240M
    assert body['total_price'] == 240_000_000
    # total_cost = 50 + 80 + 35 = 165M
    assert body['total_cost'] == 165_000_000
    # total_margin = 75M
    assert body['total_margin'] == 75_000_000
