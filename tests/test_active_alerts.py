"""Tests del endpoint /api/dashboard/active_alerts/."""

from decimal import Decimal
from datetime import date, datetime, timedelta

import pytest
from django.test import override_settings
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
    pf = PaymentForm.objects.create(enterprise=e1, name='Crédito')
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
        unit_price=Decimal('100000000'), total_price=Decimal('100000000'),
        payment_form=pf, status='completed',
    )

    # 4 cuotas: 2 vencidas no pagadas, 2 al día.
    Quotum.objects.create(
        enterprise=e1, sale=s, customer=c, total_plan=4,
        quota_number=1, amount=Decimal('25000000'),
        due_date=today - timedelta(days=10), status='pending',
    )
    Quotum.objects.create(
        enterprise=e1, sale=s, customer=c, total_plan=4,
        quota_number=2, amount=Decimal('25000000'),
        due_date=today - timedelta(days=5), status='pending',
    )
    Quotum.objects.create(
        enterprise=e1, sale=s, customer=c, total_plan=4,
        quota_number=3, amount=Decimal('25000000'),
        due_date=today + timedelta(days=10), status='pending',
    )
    Quotum.objects.create(
        enterprise=e1, sale=s, customer=c, total_plan=4,
        quota_number=4, amount=Decimal('25000000'),
        due_date=today + timedelta(days=30), status='pending',
    )

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client, 'e1': e1, 'b': b, 'brand': brand, 'model': model}


def test_mora_50_pct_dispara_critico(setup):
    """2 vencidas / 4 activas = 50% morosidad → crit (umbral 25)."""
    r = setup['client'].get('/api/dashboard/active_alerts/')
    alerts = r.json()['alerts']
    crit_mora = [a for a in alerts if a['id'] == 'mora_pct_crit']
    assert len(crit_mora) == 1
    assert crit_mora[0]['value'] == 50.0


@override_settings(ALERT_THRESHOLDS={
    'mora_pct_warn': 90,   # alto para no dispararse
    'mora_pct_crit': 99,
    'estancados_warn': 1, 'estancados_crit': 5,
    'vencidas_count_warn': 99, 'vencidas_count_crit': 999,
    'dias_pago_warn': 99, 'dias_pago_crit': 999,
})
def test_estancados_dispara_warn(setup):
    """Creamos 2 vehículos viejos available → alerta warn (umbral 1)."""
    for i in range(2):
        v = Vehicle.objects.create(
            enterprise=setup['e1'], branch=setup['b'],
            brand=setup['brand'], model=setup['model'], year=2017,
            vin=f'OLD{i}', state='available',
            fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
            cam_vol=Decimal('0'), price=Decimal('1'),
        )
        past = timezone.now() - timedelta(days=100)
        Vehicle.objects.filter(pk=v.pk).update(created_at=past)

    r = setup['client'].get('/api/dashboard/active_alerts/')
    alerts = r.json()['alerts']
    est = [a for a in alerts if a['id'].startswith('estancados')]
    assert len(est) == 1
    # 2 estancados >= warn (1) pero < crit (5)
    assert est[0]['severity'] == 'warn'
    assert est[0]['value'] == 2


def test_thresholds_en_response(setup):
    r = setup['client'].get('/api/dashboard/active_alerts/')
    body = r.json()
    assert 'thresholds' in body
    assert 'mora_pct_warn' in body['thresholds']


def test_estructura_alerta(setup):
    r = setup['client'].get('/api/dashboard/active_alerts/')
    alerts = r.json()['alerts']
    if alerts:
        a = alerts[0]
        for field in ['id', 'severity', 'title', 'detail', 'value',
                      'threshold', 'action']:
            assert field in a, f'falta {field}'
        assert a['severity'] in ('warn', 'crit')
