"""Tests del endpoint /api/vehicles/stuck/?days=N.

Verificamos:
  - Devuelve vehículos available con created_at > N días.
  - Excluye los reservados/vendidos/mantenimiento.
  - Respeta el filtro de sucursal.
  - days clampado a [7, 720].
  - Tenancy.
  - Cada item lleva days_in_stock.
"""

from decimal import Decimal
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    CustomUser, Enterprise, Branch, Brand, VehicleModel, Vehicle,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    e1 = Enterprise.objects.create(
        name='E1', ruc='1', email='e1@x.com',
        phone='1', address='x', city='Asunción',
    )
    e2 = Enterprise.objects.create(
        name='E2', ruc='2', email='e2@x.com',
        phone='2', address='y', city='Asunción',
    )
    b1 = Branch.objects.create(enterprise=e1, name='A', code='A')
    b1b = Branch.objects.create(enterprise=e1, name='B', code='B')
    b_e2 = Branch.objects.create(enterprise=e2, name='X', code='A')

    brand = Brand.objects.create(enterprise=e1, name='Toyota')
    model = VehicleModel.objects.create(enterprise=e1, brand=brand, name='Vitz')
    brand_e2 = Brand.objects.create(enterprise=e2, name='Toyota')
    model_e2 = VehicleModel.objects.create(enterprise=e2, brand=brand_e2, name='Vitz')

    def mk(branch, vin, days_old, state='available', e=e1, br=brand, md=model):
        v = Vehicle.objects.create(
            enterprise=e, branch=branch, brand=br, model=md, year=2018,
            vin=vin, state=state,
            fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
            cam_vol=Decimal('0'), price=Decimal('1'),
        )
        if days_old:
            past = timezone.now() - timedelta(days=days_old)
            Vehicle.objects.filter(pk=v.pk).update(created_at=past)
        return v

    # Vehículos de e1
    mk(b1,  'V120D-A', 120)   # estancado
    mk(b1,  'V200D-A', 200)   # estancado más viejo
    mk(b1b, 'V120D-B', 120)   # estancado pero otra branch
    mk(b1,  'V10D',     10)   # nuevo — no estancado
    mk(b1,  'VSOLD',   200, state='sold')  # vendido — no cuenta
    mk(b1,  'VRES',    200, state='reserved')  # reservado — no cuenta
    # Otra empresa con el mismo VIN-prefijo no cuenta
    mk(b_e2, 'V200D-OTRA', 200, e=e2, br=brand_e2, md=model_e2)

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client, 'b1': b1, 'b1b': b1b}


def test_default_days_90(setup):
    """Sin params: trae los 3 vehículos available de e1 con >=90 días."""
    r = setup['client'].get('/api/vehicles/stuck/')
    body = r.json()
    assert body['days_threshold'] == 90
    vins = sorted(v['vin'] for v in body['results'])
    assert vins == ['V120D-A', 'V120D-B', 'V200D-A']


def test_orden_mas_viejo_primero(setup):
    r = setup['client'].get('/api/vehicles/stuck/?days=90')
    body = r.json()
    # El de 200d aparece primero
    assert body['results'][0]['vin'] == 'V200D-A'


def test_filtro_por_branch(setup):
    r = setup['client'].get(f'/api/vehicles/stuck/?days=90&branch={setup["b1"].id}')
    body = r.json()
    vins = [v['vin'] for v in body['results']]
    assert 'V120D-B' not in vins


def test_excluye_vendidos_y_reservados(setup):
    r = setup['client'].get('/api/vehicles/stuck/?days=180')
    body = r.json()
    vins = [v['vin'] for v in body['results']]
    assert 'VSOLD' not in vins
    assert 'VRES' not in vins


def test_days_in_stock_se_incluye(setup):
    r = setup['client'].get('/api/vehicles/stuck/?days=90')
    body = r.json()
    for v in body['results']:
        assert v['days_in_stock'] is not None
        assert v['days_in_stock'] >= 90


def test_days_clampado(setup):
    r = setup['client'].get('/api/vehicles/stuck/?days=1')
    assert r.json()['days_threshold'] == 7   # mínimo


def test_tenancy(setup):
    """V200D-OTRA es de la otra empresa, no debe aparecer."""
    r = setup['client'].get('/api/vehicles/stuck/?days=90')
    body = r.json()
    vins = [v['vin'] for v in body['results']]
    assert 'V200D-OTRA' not in vins
