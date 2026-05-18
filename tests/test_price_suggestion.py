"""Tests del endpoint /api/vehicles/price_suggestion/.

Casos:
  - Sin brand/model: matches=0, reason='missing_brand_or_model'.
  - Sin ventas históricas: matches=0, scope='none'.
  - Con ventas del año exacto: scope='exact_year', min/max/median/mean
    coherentes.
  - Año inexacto pero modelo con ventas en ±2 años: scope='year_window_2'.
  - Año muy distinto: scope='any_year'.
  - Tenancy: no devuelve precios de otra empresa.
"""

from decimal import Decimal
from datetime import date

import pytest
from rest_framework.test import APIClient

from core.models import (
    CustomUser, Enterprise, Branch, Customer, Brand, VehicleModel,
    Vehicle, Sale, PaymentForm,
)


pytestmark = pytest.mark.django_db


def _vehicle(e, b, brand, model, year, vin):
    return Vehicle.objects.create(
        enterprise=e, branch=b, brand=brand, model=model, year=year,
        vin=vin, state='sold',
        fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
        cam_vol=Decimal('0'), price=Decimal('1'),
    )


def _sale(e, b, c, v, num, price, status='completed'):
    return Sale.objects.create(
        enterprise=e, branch=b, customer=c, vehicle=v,
        sale_number=num, sale_date=date(2026, 4, 15),
        unit_price=Decimal(str(price)), total_price=Decimal(str(price)),
        status=status, payment_form=PaymentForm.objects.filter(enterprise=e).first(),
    )


@pytest.fixture
def setup():
    e1 = Enterprise.objects.create(
        name='E1', ruc='11111111', email='e1@x.com',
        phone='1', address='x', city='Asunción',
    )
    e2 = Enterprise.objects.create(
        name='E2', ruc='22222222', email='e2@x.com',
        phone='2', address='y', city='Asunción',
    )
    b1 = Branch.objects.create(enterprise=e1, name='A', code='A')
    b2 = Branch.objects.create(enterprise=e2, name='B', code='A')

    brand = Brand.objects.create(enterprise=e1, name='Toyota')
    brand_e2 = Brand.objects.create(enterprise=e2, name='Toyota')
    model_vitz = VehicleModel.objects.create(enterprise=e1, brand=brand, name='Vitz')
    model_vitz_e2 = VehicleModel.objects.create(enterprise=e2, brand=brand_e2, name='Vitz')

    PaymentForm.objects.create(enterprise=e1, name='Contado')
    PaymentForm.objects.create(enterprise=e2, name='Contado')

    c = Customer.objects.create(
        enterprise=e1, first_name='X', last_name='Y',
        document_type='ci', document_number='111', email='x@x.com',
        phone='0981', city='Asunción',
    )
    c2 = Customer.objects.create(
        enterprise=e2, first_name='X', last_name='Y',
        document_type='ci', document_number='222', email='x2@x.com',
        phone='0981', city='Asunción',
    )

    # 3 ventas del año 2018, Vitz, en E1: 70M, 80M, 95M
    for i, price in enumerate([70_000_000, 80_000_000, 95_000_000]):
        v = _vehicle(e1, b1, brand, model_vitz, 2018, f'VIN2018-{i}')
        _sale(e1, b1, c, v, f'V18-{i}', price)

    # 1 venta del año 2020, Vitz, en E1: 110M
    v2020 = _vehicle(e1, b1, brand, model_vitz, 2020, 'VIN2020')
    _sale(e1, b1, c, v2020, 'V20', 110_000_000)

    # 1 venta de otra empresa con el mismo modelo+año — NO debe aparecer.
    v_otra = _vehicle(e2, b2, brand_e2, model_vitz_e2, 2018, 'OTRA2018')
    _sale(e2, b2, c2, v_otra, 'OE-1', 999_000_000)

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {
        'client': client, 'e1': e1, 'e2': e2,
        'brand': brand, 'model': model_vitz,
    }


def test_sin_brand_o_model(setup):
    r = setup['client'].get('/api/vehicles/price_suggestion/')
    assert r.status_code == 200
    assert r.json() == {'matches': 0, 'reason': 'missing_brand_or_model'}


def test_modelo_sin_ventas(setup):
    """Pasamos un model_id que no tiene ventas — devuelve matches=0."""
    nuevo_modelo = VehicleModel.objects.create(
        enterprise=setup['e1'], brand=setup['brand'], name='ModeloNuevo',
    )
    r = setup['client'].get(
        f'/api/vehicles/price_suggestion/?brand={setup["brand"].id}'
        f'&model={nuevo_modelo.id}&year=2024'
    )
    body = r.json()
    assert body['matches'] == 0
    assert body['scope'] == 'none'


def test_exact_year(setup):
    """3 ventas de 2018 → mediana 80M, min 70M, max 95M."""
    r = setup['client'].get(
        f'/api/vehicles/price_suggestion/?brand={setup["brand"].id}'
        f'&model={setup["model"].id}&year=2018'
    )
    body = r.json()
    assert body['matches'] == 3
    assert body['scope'] == 'exact_year'
    assert body['min'] == 70_000_000
    assert body['max'] == 95_000_000
    assert body['median'] == 80_000_000
    # Promedio: 245M / 3 ≈ 81.67M
    assert 81_000_000 < body['mean'] < 82_000_000
    assert len(body['recent_examples']) == 3


def test_window_de_2_años(setup):
    """Año 2019: no hay exacto, pero hay en 2018 y 2020 → ventana ±2."""
    r = setup['client'].get(
        f'/api/vehicles/price_suggestion/?brand={setup["brand"].id}'
        f'&model={setup["model"].id}&year=2019'
    )
    body = r.json()
    assert body['scope'] == 'year_window_2'
    assert body['matches'] == 4   # 3 de 2018 + 1 de 2020


def test_any_year_fallback(setup):
    """Año 2030: ningún match en ventana ±2 → 'any_year'."""
    r = setup['client'].get(
        f'/api/vehicles/price_suggestion/?brand={setup["brand"].id}'
        f'&model={setup["model"].id}&year=2030'
    )
    body = r.json()
    assert body['scope'] == 'any_year'
    assert body['matches'] == 4


def test_tenancy_no_filtra_otra_empresa(setup):
    """La venta de 999M de la otra empresa no debe aparecer."""
    r = setup['client'].get(
        f'/api/vehicles/price_suggestion/?brand={setup["brand"].id}'
        f'&model={setup["model"].id}&year=2018'
    )
    body = r.json()
    assert body['max'] < 999_000_000
