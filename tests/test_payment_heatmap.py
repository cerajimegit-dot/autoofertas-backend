"""Tests del endpoint /api/dashboard/payment_heatmap/."""

from decimal import Decimal
from datetime import date, datetime, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    CustomUser, Enterprise, Branch, Customer, Brand, VehicleModel,
    Vehicle, Sale, Quotum, PaymentForm,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    today = date.today()
    e1 = Enterprise.objects.create(name='E1', ruc='1', email='e@x.com',
                                    phone='1', address='x', city='x')
    b = Branch.objects.create(enterprise=e1, name='A', code='A')
    pf = PaymentForm.objects.create(enterprise=e1, name='Cr')
    brand = Brand.objects.create(enterprise=e1, name='T')
    model = VehicleModel.objects.create(enterprise=e1, brand=brand, name='V')
    c = Customer.objects.create(
        enterprise=e1, first_name='X', last_name='Y',
        document_type='ci', document_number='1', email='x@x.com',
        phone='0', city='X',
    )
    v = Vehicle.objects.create(
        enterprise=e1, branch=b, brand=brand, model=model, year=2018,
        vin='V1', state='available',
        fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
        cam_vol=Decimal('0'), price=Decimal('1'),
    )
    s = Sale.objects.create(
        enterprise=e1, branch=b, customer=c, vehicle=v,
        sale_number='S1',
        sale_date=timezone.make_aware(datetime(2026, 1, 1)),
        unit_price=Decimal('1000000'), total_price=Decimal('1000000'),
        payment_form=pf, status='completed',
    )

    # Cuotas pagadas en distintos días del mes — usamos fechas en el
    # último mes (dentro de la ventana default de 6 meses).
    # Concentramos en día 5 y día 20 para validar el ranking.
    def add_payment(day, amount):
        # Usamos un mes pasado (today - 45 días) para garantizar que
        # cualquier `day` (1-28) cae en el pasado y entra al filtro
        # `payment_date <= today`. Si usáramos el mes actual y day > hoy,
        # quedaría fuera de la ventana.
        anchor = today - timedelta(days=45)
        pd = anchor.replace(day=min(day, 28))
        Quotum.objects.create(
            enterprise=e1, sale=s, customer=c, total_plan=10,
            quota_number=Quotum.objects.filter(sale=s).count() + 1,
            amount=Decimal(str(amount)),
            due_date=pd, payment_date=pd, status='paid',
        )

    add_payment(5,  100000)
    add_payment(5,  150000)
    add_payment(5,  200000)   # día 5 concentra 3 cuotas, 450K
    add_payment(20, 500000)
    add_payment(20, 500000)   # día 20 concentra 2 cuotas, 1M

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client}


def test_estructura(setup):
    r = setup['client'].get('/api/dashboard/payment_heatmap/')
    assert r.status_code == 200
    body = r.json()
    assert 'days' in body
    assert len(body['days']) == 31    # 1 a 31, incluso si vacíos
    for d in body['days']:
        assert 'day' in d
        assert 'count' in d
        assert 'amount' in d


def test_dia_pico_por_cantidad(setup):
    """Día 5: 3 cuotas. Día 20: 2 cuotas. Pico por count = 5."""
    r = setup['client'].get('/api/dashboard/payment_heatmap/')
    body = r.json()
    assert body['top_count_day']['day'] == 5
    assert body['top_count_day']['count'] == 3


def test_dia_pico_por_monto(setup):
    """Día 5: 450K. Día 20: 1M. Pico por monto = 20."""
    r = setup['client'].get('/api/dashboard/payment_heatmap/')
    body = r.json()
    assert body['top_amount_day']['day'] == 20
    assert body['top_amount_day']['amount'] == 1_000_000.0


def test_totales(setup):
    r = setup['client'].get('/api/dashboard/payment_heatmap/')
    body = r.json()
    assert body['total_count'] == 5
    assert body['total_amount'] == 1_450_000.0


def test_months_cap(setup):
    """months=9999 → cap en 24."""
    r = setup['client'].get('/api/dashboard/payment_heatmap/?months=9999')
    assert r.json()['months'] == 24


def test_dias_sin_actividad_count_cero(setup):
    """Días donde no hubo cobros tienen count=0 y amount=0."""
    r = setup['client'].get('/api/dashboard/payment_heatmap/')
    body = r.json()
    by_day = {d['day']: d for d in body['days']}
    assert by_day[1]['count'] == 0
    assert by_day[1]['amount'] == 0
