"""Tests del management command send_daily_digest."""

from decimal import Decimal
from datetime import date, datetime, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from core.models import (
    CustomUser, Enterprise, Branch, Customer, Brand, VehicleModel,
    Vehicle, Sale, Quotum, PaymentForm, CashMovement,
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
        enterprise=e1, first_name='Mati', last_name='Pérez',
        document_type='ci', document_number='1', email='m@x.com',
        phone='0', city='X',
    )
    v = Vehicle.objects.create(
        enterprise=e1, branch=b, brand=brand, model=model, year=2018,
        vin='V1', state='available',
        fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
        cam_vol=Decimal('0'), price=Decimal('1'),
    )

    # Venta del día con sale_date=today
    s = Sale.objects.create(
        enterprise=e1, branch=b, customer=c, vehicle=v,
        sale_number='HOY-1',
        sale_date=timezone.make_aware(datetime.combine(today, datetime.min.time())),
        unit_price=Decimal('10000000'), total_price=Decimal('10000000'),
        payment_form=pf, status='completed',
    )

    # Cuotas: vence hoy, vence ayer (vencida), pagada hoy
    Quotum.objects.create(
        enterprise=e1, sale=s, customer=c, total_plan=3,
        quota_number=1, amount=Decimal('1000000'),
        due_date=today, status='pending',
    )
    Quotum.objects.create(
        enterprise=e1, sale=s, customer=c, total_plan=3,
        quota_number=2, amount=Decimal('1500000'),
        due_date=today - timedelta(days=5), status='pending',  # vencida
    )
    Quotum.objects.create(
        enterprise=e1, sale=s, customer=c, total_plan=3,
        quota_number=3, amount=Decimal('800000'),
        due_date=today, status='paid', payment_date=today,
    )

    # Cash del día
    CashMovement.objects.create(
        enterprise=e1, branch=b, date=today,
        kind='cobro_cuota', direction='in', amount=Decimal('800000'),
        description='Cobro cuota 3',
    )
    CashMovement.objects.create(
        enterprise=e1, branch=b, date=today,
        kind='gasto_playa', direction='out', amount=Decimal('200000'),
        description='Limpieza',
    )

    return {'enterprise': e1}


def test_dry_run_imprime(setup):
    """--dry-run no envía email pero imprime el digest a stdout."""
    out = StringIO()
    call_command('send_daily_digest', '--dry-run', stdout=out)
    text = out.getvalue()
    assert 'DIGEST DIARIO' in text
    assert 'E1' in text


def test_digest_incluye_ventas(setup):
    out = StringIO()
    call_command('send_daily_digest', '--dry-run', stdout=out)
    text = out.getvalue()
    assert 'VENTAS DEL DÍA' in text
    assert '1 venta(s)' in text
    # 10M en formato es-PY
    assert '10.000.000' in text


def test_digest_incluye_cuotas_que_vencen_hoy(setup):
    out = StringIO()
    call_command('send_daily_digest', '--dry-run', stdout=out)
    text = out.getvalue()
    assert 'VENCEN HOY' in text
    assert 'Mati' in text  # nombre del cliente en la lista


def test_digest_marca_vencidas(setup):
    out = StringIO()
    call_command('send_daily_digest', '--dry-run', stdout=out)
    text = out.getvalue()
    assert 'CARTERA VENCIDA' in text
    assert '1 cuota(s) vencidas' in text


def test_digest_incluye_cobranzas(setup):
    out = StringIO()
    call_command('send_daily_digest', '--dry-run', stdout=out)
    text = out.getvalue()
    assert 'COBRANZAS' in text
    assert 'cobraron 1' in text


def test_digest_incluye_caja(setup):
    out = StringIO()
    call_command('send_daily_digest', '--dry-run', stdout=out)
    text = out.getvalue()
    assert 'FLUJO DE CAJA' in text
    assert '800.000' in text  # ingresos
    assert '200.000' in text  # egresos
    assert '600.000' in text  # neto


def test_filtro_por_enterprise(setup):
    """--enterprise N sólo procesa esa empresa."""
    Enterprise.objects.create(name='Otra', ruc='99', email='o@x.com',
                              phone='9', address='z', city='z')
    out = StringIO()
    call_command('send_daily_digest', '--dry-run',
                 f'--enterprise={setup["enterprise"].id}', stdout=out)
    text = out.getvalue()
    assert 'E1' in text
    assert 'Otra' not in text
