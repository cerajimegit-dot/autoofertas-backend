"""Tests de validación TC obligatorio cuando moneda=USD.

Aplica a:
  - Vehicle.price en USD requiere FK exchange_rate.
  - VehicleCost.amount en USD requiere DecimalField exchange_rate.
  - CashMovement.amount en USD requiere exchange_rate + amount_usd.
"""

from decimal import Decimal
from datetime import date

import pytest
from rest_framework.test import APIClient

from core.models import (
    CustomUser, Enterprise, Branch, Brand, VehicleModel, Vehicle,
    CashMovement, ExchangeRate,
)
from core.models.inventory import VehicleCost


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    e1 = Enterprise.objects.create(
        name='E1', ruc='1', email='e@x.com',
        phone='1', address='x', city='x',
    )
    b = Branch.objects.create(enterprise=e1, name='A', code='A')
    brand = Brand.objects.create(enterprise=e1, name='T')
    model = VehicleModel.objects.create(enterprise=e1, brand=brand, name='V')
    tc = ExchangeRate.objects.create(
        enterprise=e1, rate=Decimal('7300'), date=date(2026, 5, 1),
        is_active=True,
    )
    v = Vehicle.objects.create(
        enterprise=e1, branch=b, brand=brand, model=model, year=2018,
        vin='V1', state='available',
        fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
        cam_vol=Decimal('0'), price=Decimal('1'),
    )
    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client, 'v': v, 'tc': tc, 'e1': e1, 'b': b}


# ---------- Vehicle ----------

def test_vehicle_usd_sin_tc_rechazado(setup):
    """POST a /vehicles/ con currency=USD pero sin exchange_rate → 400."""
    payload = {
        'brand': None, 'model': None, 'year': 2020, 'vin': 'NEW1',
        'fob': '0', 'container': '0', 'dispatch': '0', 'cam_vol': '0',
        'price': '5000', 'currency': 'USD', 'state': 'available',
    }
    r = setup['client'].post('/api/vehicles/', payload, format='json')
    assert r.status_code == 400
    assert 'exchange_rate' in r.json()


def test_vehicle_usd_con_tc_acepta(setup):
    payload = {
        'year': 2020, 'vin': 'NEW2',
        'fob': '0', 'container': '0', 'dispatch': '0', 'cam_vol': '0',
        'price': '5000', 'currency': 'USD', 'state': 'available',
        'exchange_rate': setup['tc'].id,
    }
    r = setup['client'].post('/api/vehicles/', payload, format='json')
    assert r.status_code in (200, 201), r.content


# ---------- VehicleCost ----------

def test_vehiclecost_usd_sin_tc_rechazado(setup):
    payload = {
        'vehicle': setup['v'].id,
        'concept': 'Flete USA',
        'amount': '500',
        'currency': 'USD',
        'order': 0,
    }
    r = setup['client'].post('/api/vehicle-costs/', payload, format='json')
    assert r.status_code == 400
    assert 'exchange_rate' in r.json()


def test_vehiclecost_usd_con_tc_acepta(setup):
    payload = {
        'vehicle': setup['v'].id,
        'concept': 'Flete USA',
        'amount': '500',
        'currency': 'USD',
        'exchange_rate': '7300',
        'order': 0,
    }
    r = setup['client'].post('/api/vehicle-costs/', payload, format='json')
    assert r.status_code in (200, 201), r.content


def test_vehiclecost_pyg_no_exige_tc(setup):
    payload = {
        'vehicle': setup['v'].id,
        'concept': 'Patente',
        'amount': '500000',
        'currency': 'PYG',
        'order': 0,
    }
    r = setup['client'].post('/api/vehicle-costs/', payload, format='json')
    assert r.status_code in (200, 201)


def test_vehiclecost_amount_pyg_property(setup):
    """El property `amount_pyg` convierte si USD+TC, devuelve amount si PYG,
    None si USD sin TC."""
    pyg = VehicleCost(vehicle=setup['v'], enterprise=setup['e1'],
                      concept='X', amount=Decimal('100'), currency='PYG')
    assert pyg.amount_pyg == Decimal('100')

    usd_con_tc = VehicleCost(vehicle=setup['v'], enterprise=setup['e1'],
                              concept='Y', amount=Decimal('100'),
                              currency='USD', exchange_rate=Decimal('7300'))
    assert usd_con_tc.amount_pyg == Decimal('730000')

    usd_sin_tc = VehicleCost(vehicle=setup['v'], enterprise=setup['e1'],
                              concept='Z', amount=Decimal('100'),
                              currency='USD')
    assert usd_sin_tc.amount_pyg is None


# ---------- CashMovement ----------

def test_cashmovement_usd_sin_tc_rechazado(setup):
    payload = {
        'date': '2026-05-15',
        'kind': 'gasto_playa',
        'direction': 'out',
        'amount': '5000000',
        'description': 'Compra USD',
        'currency': 'USD',
        # No mando amount_usd ni exchange_rate
    }
    r = setup['client'].post('/api/cash-movements/', payload, format='json')
    assert r.status_code == 400
    body = r.json()
    assert 'exchange_rate' in body or 'amount_usd' in body


def test_cashmovement_usd_completo_acepta(setup):
    payload = {
        'date': '2026-05-15',
        'kind': 'gasto_playa',
        'direction': 'out',
        'amount': '5000000',
        'description': 'Compra USD',
        'currency': 'USD',
        'amount_usd': '700',
        'exchange_rate': '7300',
    }
    r = setup['client'].post('/api/cash-movements/', payload, format='json')
    assert r.status_code in (200, 201), r.content


def test_cashmovement_pyg_sin_tc_acepta(setup):
    payload = {
        'date': '2026-05-15',
        'kind': 'gasto_playa',
        'direction': 'out',
        'amount': '5000000',
        'description': 'Compra Gs',
        'currency': 'PYG',
    }
    r = setup['client'].post('/api/cash-movements/', payload, format='json')
    assert r.status_code in (200, 201)
