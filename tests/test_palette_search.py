"""Tests de los endpoints search/ usados por el palette global (Ctrl+K).

Tres endpoints:
  - /api/customers/search/  (cubierto en test_customer_search.py)
  - /api/sales/search/
  - /api/vehicles/search/

Verificamos que:
  - q corto (<2) devuelve lista vacía sin tocar la BD.
  - El filtro multi-empresa funciona.
  - Cada uno matchea sus campos principales.
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

    b1 = Branch.objects.create(enterprise=e1, name='Suc A', code='A')
    b2 = Branch.objects.create(enterprise=e2, name='Otra', code='A')

    brand_toyota = Brand.objects.create(enterprise=e1, name='Toyota')
    brand_honda = Brand.objects.create(enterprise=e1, name='Honda')
    brand_e2 = Brand.objects.create(enterprise=e2, name='Toyota')
    model_vitz = VehicleModel.objects.create(enterprise=e1, brand=brand_toyota, name='Vitz')
    model_civic = VehicleModel.objects.create(enterprise=e1, brand=brand_honda, name='Civic')
    model_e2 = VehicleModel.objects.create(enterprise=e2, brand=brand_e2, name='Yaris')

    # Vehículos con todos los campos requeridos por el modelo.
    v1 = Vehicle.objects.create(
        enterprise=e1, branch=b1, brand=brand_toyota, model=model_vitz,
        year=2018, vin='JTDBT123ABC', state='available',
        fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
        cam_vol=Decimal('0'), price=Decimal('1'),
    )
    Vehicle.objects.create(
        enterprise=e1, branch=b1, brand=brand_honda, model=model_civic,
        year=2020, vin='JHMFB789XYZ', state='available',
        fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
        cam_vol=Decimal('0'), price=Decimal('1'),
    )
    # Veh. de la otra empresa — no debe aparecer.
    Vehicle.objects.create(
        enterprise=e2, branch=b2, brand=brand_e2, model=model_e2,
        year=2018, vin='SECRETOOTRA1', state='available',
        fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
        cam_vol=Decimal('0'), price=Decimal('1'),
    )

    # Cliente y venta
    c1 = Customer.objects.create(
        enterprise=e1, first_name='Juan', last_name='Pérez',
        document_type='ci', document_number='5555555',
        email='juan@x.com', phone='0981', city='Asunción',
    )
    pf = PaymentForm.objects.create(enterprise=e1, name='Contado')
    Sale.objects.create(
        enterprise=e1, branch=b1, customer=c1, vehicle=v1,
        sale_number='CM-001/26', sale_date=date(2026, 5, 5),
        unit_price=Decimal('100000000'),
        total_price=Decimal('100000000'), payment_form=pf, status='completed',
    )

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client, 'e1': e1, 'e2': e2}


# ---------- /vehicles/search/ ----------

def test_vehicles_search_q_corto(setup):
    r = setup['client'].get('/api/vehicles/search/?q=a')
    assert r.status_code == 200
    assert r.json()['results'] == []


def test_vehicles_search_por_vin(setup):
    r = setup['client'].get('/api/vehicles/search/?q=JTDBT')
    body = r.json()['results']
    assert len(body) == 1
    assert body[0]['vin'].startswith('JTDBT')


def test_vehicles_search_por_marca(setup):
    r = setup['client'].get('/api/vehicles/search/?q=Toyota')
    body = r.json()['results']
    assert len(body) == 1
    assert body[0]['brand_name'] == 'Toyota'


def test_vehicles_search_por_año_numerico(setup):
    r = setup['client'].get('/api/vehicles/search/?q=2020')
    body = r.json()['results']
    assert any(v['year'] == 2020 for v in body)


def test_vehicles_search_tenancy(setup):
    r = setup['client'].get('/api/vehicles/search/?q=SECRETO')
    body = r.json()['results']
    assert body == []   # no debe traer el de la otra empresa


# ---------- /sales/search/ ----------

def test_sales_search_q_corto(setup):
    r = setup['client'].get('/api/sales/search/?q=x')
    assert r.status_code == 200
    assert r.json()['results'] == []


def test_sales_search_por_numero(setup):
    r = setup['client'].get('/api/sales/search/?q=CM-001')
    body = r.json()['results']
    assert len(body) == 1
    assert body[0]['sale_number'] == 'CM-001/26'


def test_sales_search_por_cliente(setup):
    r = setup['client'].get('/api/sales/search/?q=Juan')
    body = r.json()['results']
    assert len(body) == 1
    assert 'Juan' in body[0]['customer_name']


def test_sales_search_por_vin_del_vehiculo(setup):
    r = setup['client'].get('/api/sales/search/?q=JTDBT')
    body = r.json()['results']
    assert len(body) == 1
    assert body[0]['sale_number'] == 'CM-001/26'
