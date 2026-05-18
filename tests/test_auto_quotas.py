"""Tests del endpoint /api/sales/{id}/auto-generate-quotas/."""

from decimal import Decimal
from datetime import date, datetime, timedelta

import pytest
from rest_framework.test import APIClient

from core.models import (
    CustomUser, Enterprise, Branch, Customer, Brand, VehicleModel,
    Vehicle, Sale, Quotum, PaymentForm,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
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

    def mk_v(vin):
        return Vehicle.objects.create(
            enterprise=e1, branch=b, brand=brand, model=model, year=2018,
            vin=vin, state='available',
            fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
            cam_vol=Decimal('0'), price=Decimal('1'),
        )

    # Venta sin seña: total 120M → 12 cuotas de 10M (cuadra exacto)
    s1 = Sale.objects.create(
        enterprise=e1, branch=b, customer=c, vehicle=mk_v('V1'),
        sale_number='S1', sale_date=datetime(2026, 5, 1),
        unit_price=Decimal('120000000'), total_price=Decimal('120000000'),
        payment_form=pf, status='completed',
    )
    # Venta con seña: total 100M − seña 10M = 90M financiados
    s2 = Sale.objects.create(
        enterprise=e1, branch=b, customer=c, vehicle=mk_v('V2'),
        sale_number='S2', sale_date=datetime(2026, 5, 1),
        unit_price=Decimal('100000000'), total_price=Decimal('100000000'),
        down_payment=Decimal('10000000'),
        payment_form=pf, status='completed',
    )
    # Venta a contado: total 50M, seña 50M → a financiar 0
    s3 = Sale.objects.create(
        enterprise=e1, branch=b, customer=c, vehicle=mk_v('V3'),
        sale_number='S3', sale_date=datetime(2026, 5, 1),
        unit_price=Decimal('50000000'), total_price=Decimal('50000000'),
        down_payment=Decimal('50000000'),
        payment_form=pf, status='completed',
    )

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client, 's1': s1, 's2': s2, 's3': s3}


def test_default_12_cuotas(setup):
    r = setup['client'].post(
        f'/api/sales/{setup["s1"].id}/auto-generate-quotas/',
        {}, format='json',
    )
    assert r.status_code == 201, r.content
    body = r.json()
    assert body['count'] == 12
    assert body['a_financiar'] == 120_000_000

    # Verificar BD: 12 cuotas de 10M cada una
    qs = list(Quotum.objects.filter(sale=setup['s1']).order_by('quota_number'))
    assert len(qs) == 12
    for q in qs:
        assert q.amount == 10_000_000
        assert q.total_plan == 12
    # La suma exacta cuadra
    total = sum(q.amount for q in qs)
    assert total == 120_000_000


def test_seña_se_descuenta(setup):
    """Total 100M − seña 10M = 90M a financiar en N cuotas."""
    r = setup['client'].post(
        f'/api/sales/{setup["s2"].id}/auto-generate-quotas/',
        {'n_quotas': 6}, format='json',
    )
    assert r.status_code == 201
    body = r.json()
    assert body['a_financiar'] == 90_000_000
    qs = list(Quotum.objects.filter(sale=setup['s2']).order_by('quota_number'))
    total = sum(q.amount for q in qs)
    assert total == 90_000_000   # cuadra exacto


def test_redondeo_ultima_cuota_absorbe_diferencia(setup):
    """100M / 3 = 33.333.333 (no entero). 2 cuotas de 33.333.333 + última
    para que cuadre. La diferencia va a la última."""
    r = setup['client'].post(
        f'/api/sales/{setup["s1"].id}/auto-generate-quotas/',
        {'n_quotas': 7}, format='json',  # 120M / 7 = 17.142.857.14
    )
    assert r.status_code == 201
    qs = list(Quotum.objects.filter(sale=setup['s1']).order_by('quota_number'))
    total = sum(q.amount for q in qs)
    assert total == 120_000_000   # cuadra
    # Las primeras 6 son iguales, la última diferente
    assert qs[0].amount == qs[5].amount
    # La diferencia no es enorme (centavos)
    assert abs(qs[6].amount - qs[0].amount) < 10


def test_venta_sin_a_financiar_rechaza(setup):
    """Si total - seña ≤ 0, no se puede generar plan."""
    r = setup['client'].post(
        f'/api/sales/{setup["s3"].id}/auto-generate-quotas/',
        {}, format='json',
    )
    assert r.status_code == 400


def test_venta_con_cuotas_existentes_rechaza(setup):
    """Si la venta ya tiene cuotas, no las pisamos."""
    setup['client'].post(
        f'/api/sales/{setup["s1"].id}/auto-generate-quotas/',
        {}, format='json',
    )
    r = setup['client'].post(
        f'/api/sales/{setup["s1"].id}/auto-generate-quotas/',
        {}, format='json',
    )
    assert r.status_code == 409


def test_first_due_date_explicito(setup):
    """Si paso first_due_date, las cuotas arrancan ahí."""
    r = setup['client'].post(
        f'/api/sales/{setup["s1"].id}/auto-generate-quotas/',
        {'n_quotas': 3, 'first_due_date': '2026-06-15'},
        format='json',
    )
    assert r.status_code == 201
    qs = list(Quotum.objects.filter(sale=setup['s1']).order_by('quota_number'))
    assert qs[0].due_date == date(2026, 6, 15)
    assert qs[1].due_date == date(2026, 7, 15)
    assert qs[2].due_date == date(2026, 8, 15)


def test_n_quotas_capeado(setup):
    """n_quotas máximo 60."""
    r = setup['client'].post(
        f'/api/sales/{setup["s1"].id}/auto-generate-quotas/',
        {'n_quotas': 9999}, format='json',
    )
    assert r.status_code == 201
    assert r.json()['count'] == 60


def test_plan_name_default(setup):
    r = setup['client'].post(
        f'/api/sales/{setup["s1"].id}/auto-generate-quotas/',
        {'n_quotas': 18}, format='json',
    )
    body = r.json()
    assert body['plan_name'] == 'Plan 18 cuotas'
