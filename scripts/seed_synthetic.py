"""Genera una BD sintetica para el Jr con datos 100% inventados (Faker).

Cero datos reales de la empresa. Todo es generado: nombres, vehiculos,
montos, fechas. Las relaciones son consistentes (ventas con vehiculos
disponibles, cuotas vinculadas a ventas, etc.).

ESTRUCTURA GENERADA:
  - 1 Enterprise "AUTO OFERTAS DEMO"
  - 2 Branches: "CASA CENTRAL", "SUCURSAL 1"
  - 5 Brands con sus modelos
  - 3 Users: admin/admin123, jr/demo1234, vendor/vendor123
  - 40 Customers (Faker nombres latinoamericanos)
  - 40 Vehicles (mix de available/sold)
  - 25 Sales (mix completed/pending/cancelled, contado/credito)
  - ~150 Quotums (para las ventas a credito)
  - ~80 CashMovements (cobros, ventas contado, gastos manuales)

USO (en BD vacia o sobre db_synthetic.sqlite3):
    set DB_ENGINE=sqlite
    venv\Scripts\python.exe scripts\seed_synthetic.py
    # esto MODIFICA tu db.sqlite3 actual — backupea antes

PARA EMPEZAR DE CERO:
    python manage.py migrate --run-syncdb
    venv\Scripts\python.exe scripts\seed_synthetic.py
"""

import argparse
import os
import random
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from django.db import transaction
from faker import Faker

from core.models import (
    Enterprise, Branch, Brand, VehicleModel, Vehicle,
    Customer, PaymentForm, Sale, Quotum, CashMovement, CustomUser,
)

fake = Faker('es_AR')  # nombres en español rioplatense (similar a Paraguay)
random.seed(42)        # determinista para que el Jr pueda discutir casos especificos
Faker.seed(42)


def fmt_money(n):
    return f'Gs.{int(n):,}'.replace(',', '.')


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--wipe', action='store_true',
                    help='Borrar datos previos antes de seedear (peligroso si hay datos reales)')
    args = p.parse_args()

    with transaction.atomic():
        if args.wipe:
            print('  Wipe previo de datos...')
            CashMovement.objects.all().delete()
            Quotum.objects.all().delete()
            Sale.objects.all().delete()
            Vehicle.objects.all().delete()
            Customer.objects.all().delete()
            VehicleModel.objects.all().delete()
            Brand.objects.all().delete()
            PaymentForm.objects.all().delete()

        # 1. Enterprise
        ent, _ = Enterprise.objects.get_or_create(
            name='AUTO OFERTAS DEMO',
            defaults={
                'ruc': '80000000-0',
                'email': 'demo@autoofertas.local',
                'phone': '021-000-000',
                'address': 'Calle Demo 123',
                'city': 'Asuncion',
                'subscription_status': 'active',
            },
        )
        print(f'  Enterprise: {ent.name}')

        # 2. Branches (Branch tiene name + code)
        cc, _ = Branch.objects.get_or_create(
            enterprise=ent, code='CC',
            defaults={'name': 'CASA CENTRAL', 'address': 'Demo CC',
                      'city': 'Asuncion', 'phone': '021-000-001'},
        )
        suc, _ = Branch.objects.get_or_create(
            enterprise=ent, code='SUC1',
            defaults={'name': 'SUCURSAL 1', 'address': 'Demo Sucursal',
                      'city': 'Asuncion', 'phone': '021-000-002'},
        )
        print(f'  Branches: {cc.name}, {suc.name}')

        # 3. Users
        users_data = [
            ('admin',  'admin123',   True,  True,  'admin'),
            ('jr',     'demo1234',   False, False, 'vendor'),
            ('vendor', 'vendor123',  False, False, 'vendor'),
        ]
        users = {}
        for username, password, is_staff, is_super, role in users_data:
            u, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@demo.local',
                    'enterprise': ent,
                    'is_staff': is_staff,
                    'is_superuser': is_super,
                    'role': role,
                    'password': make_password(password),
                },
            )
            if not created:
                u.password = make_password(password)
                u.save()
            users[username] = u
        print(f'  Users: admin/admin123, jr/demo1234, vendor/vendor123')

        # 4. Brands + Models
        brands_models = {
            'TOYOTA': ['VITZ 1.0', 'VITZ 1.3', 'VITZ 1.3 RS', 'RACTIS 1.3', 'RACTIS 1.5',
                       'SIENTA 1.5', 'IST 1.5', 'AURIS 1.5', 'ALLION 1.5', 'BELTA 1.0'],
            'KIA':    ['SPORTAGE', 'PICANTO', 'RIO', 'CERATO'],
            'HYUNDAI':['TUCSON', 'I10', 'ACCENT', 'SANTA FE'],
            'HONDA':  ['FIT', 'CIVIC', 'CRV'],
            'NISSAN': ['MARCH', 'NOTE', 'X-TRAIL'],
        }
        all_models = []
        for bname, mnames in brands_models.items():
            b, _ = Brand.objects.get_or_create(
                enterprise=ent, name=bname,
                defaults={'is_active': True},
            )
            for mname in mnames:
                m, _ = VehicleModel.objects.get_or_create(
                    enterprise=ent, brand=b, name=mname,
                    defaults={'is_active': True},
                )
                all_models.append(m)
        print(f'  Brands: {len(brands_models)}, Models: {len(all_models)}')

        # 5. Payment forms
        pf_contado, _ = PaymentForm.objects.get_or_create(
            enterprise=ent, name='CONTADO',
            defaults={'is_active': True},
        )
        pf_credito, _ = PaymentForm.objects.get_or_create(
            enterprise=ent, name='CREDITO',
            defaults={'is_active': True},
        )

        # 6. Customers (Faker)
        customers = []
        for i in range(40):
            c, _ = Customer.objects.get_or_create(
                enterprise=ent,
                document_number=f'{random.randint(1_000_000, 9_999_999)}',
                defaults={
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'document_type': 'ci',
                    'email': fake.email() if random.random() < 0.5 else '',
                    'phone': f'098{random.randint(1_000_000, 9_999_999)}',
                    'address': fake.address()[:100],
                    'city': random.choice(['Asuncion', 'San Lorenzo', 'Lambare', 'Capiata']),
                },
            )
            customers.append(c)
        print(f'  Customers: {len(customers)}')

        # 7. Vehicles
        vehicles = []
        for i in range(40):
            brand = random.choice(list(Brand.objects.filter(enterprise=ent)))
            model = random.choice(list(VehicleModel.objects.filter(brand=brand)))
            year = random.choice(range(2005, 2024))
            # FOB en USD (1500-5000), cost_total en PYG con exchange ~7800
            fob_usd = Decimal(random.randint(1500, 5000))
            cost_total = fob_usd * Decimal('7800') + Decimal(random.randint(2_000_000, 8_000_000))
            price = cost_total + Decimal(random.randint(8_000_000, 20_000_000))
            # Vehicle.fob es Decimal(12,2) - alcanza para PYG hasta 9.999.999.999,99
            fob = fob_usd * Decimal('7800')  # FOB en PYG
            vin = f'VIN{i:03d}{fake.bothify("???-#######").upper()}'

            v = Vehicle.objects.create(
                enterprise=ent,
                branch=random.choice([cc, suc]),
                brand=brand,
                model=model,
                year=year,
                vin=vin,
                color=random.choice(['BLANCO', 'NEGRO', 'PLATA', 'AZUL', 'ROJO', 'GRIS']),
                mileage=random.randint(30_000, 200_000),
                fob=fob,
                container=Decimal('0'),
                dispatch=Decimal(random.randint(5_000_000, 12_000_000)),
                cam_vol=Decimal('2000000'),
                price=price,
                currency='PYG',
                state='available',  # se ajusta segun Sales
            )
            vehicles.append(v)
        print(f'  Vehicles: {len(vehicles)} (todos available por ahora)')

        # 8. Sales (mix de tipos)
        sales = []
        sn_counter = 1
        for i in range(25):
            customer = random.choice(customers)
            vehicle = random.choice([v for v in vehicles if v.state == 'available'])
            year = random.choice([2025, 2026])
            sale_date_obj = fake.date_between(
                start_date=date(year, 1, 1),
                end_date=date(year, 12, 31) if year == 2025 else date.today(),
            )
            status = random.choices(
                ['completed', 'pending', 'cancelled'],
                weights=[15, 7, 3],
            )[0]
            pf = random.choices([pf_contado, pf_credito], weights=[8, 17])[0]

            total = vehicle.price
            down = Decimal('0') if pf == pf_contado else total * Decimal(random.choice([0.20, 0.30, 0.40]))

            s = Sale.objects.create(
                enterprise=ent,
                branch=vehicle.branch,
                sale_number=f'DEMO{sn_counter:02d}/{str(year)[-2:]}',
                sale_date=datetime.combine(sale_date_obj, datetime.min.time()),
                customer=customer,
                vehicle=vehicle,
                unit_price=total,
                discount=Decimal('0'),
                total_price=total,
                down_payment=down,
                payment_form=pf,
                seller=users['vendor'],
                status=status,
            )
            sales.append(s)
            sn_counter += 1
        print(f'  Sales: {len(sales)}')

        # 9. Quotums (solo para sales completed a credito)
        total_q = 0
        for s in sales:
            if s.status != 'completed' or s.payment_form == pf_contado:
                continue
            credit_amount = s.total_price - s.down_payment
            n_cuotas = random.choice([6, 12, 18, 24])
            cuota_amount = (credit_amount / n_cuotas).quantize(Decimal('1'))
            first_due = s.sale_date.date() + timedelta(days=30)

            today = date.today()
            for n in range(1, n_cuotas + 1):
                due = first_due + timedelta(days=30 * (n - 1))
                # status: paid si due_date pasado en mas de 60 dias (cobrada),
                #         pending si pasado pero <60d (vencida),
                #         pending si futura (a vencer)
                if due < today - timedelta(days=60):
                    status = 'paid'
                    pay_date = due + timedelta(days=random.randint(-3, 5))
                else:
                    status = 'pending'
                    pay_date = None

                Quotum.objects.create(
                    enterprise=ent,
                    sale=s,
                    customer=s.customer,
                    quota_number=n,
                    plan_name=f'{n_cuotas} cuotas',
                    total_plan=n_cuotas,
                    amount=cuota_amount,
                    interest=Decimal('0'),
                    due_date=due,
                    payment_date=pay_date,
                    status=status,
                    payment_method='EF' if status == 'paid' else None,
                )
                total_q += 1
        print(f'  Quotums: {total_q}')

        # 10. CashMovements adicionales (gastos manuales)
        # Los cobro_cuota / venta_contado / seña_credito ya se crearon
        # automaticamente via Sale.save() y Quotum.save() hooks.
        gastos_kinds = [
            ('alquiler', 'in', 'out', 'Alquiler oficina'),
            ('sueldo', 'out', 'out', 'Sueldo personal'),
            ('gasto_playa', 'out', 'out', 'Gastos generales playa'),
            ('comision', 'out', 'out', 'Comision vendedor'),
            ('transporte', 'out', 'out', 'Flete vehiculo'),
        ]
        cm_count = 0
        for _ in range(20):
            kind, _, direction, desc = random.choice(gastos_kinds)
            amount = Decimal(random.randint(500_000, 8_000_000))
            d = fake.date_between(start_date=date(2025, 1, 1), end_date=date.today())
            CashMovement.objects.create(
                enterprise=ent,
                branch=random.choice([cc, suc]),
                date=d,
                kind=kind,
                direction=direction,
                description=desc,
                amount=amount,
                currency='PYG',
                created_by=random.choice(list(users.values())),
                is_auto=False,
            )
            cm_count += 1
        print(f'  CashMovements manuales: {cm_count}')

    # Resumen
    print('\n  === Datos sinteticos creados ===')
    print(f'    Customers:      {Customer.objects.count()}')
    print(f'    Vehicles:       {Vehicle.objects.count()} ({Vehicle.objects.filter(state="available").count()} available)')
    print(f'    Sales:          {Sale.objects.count()}')
    print(f'    Quotums:        {Quotum.objects.count()}')
    print(f'    CashMovements:  {CashMovement.objects.count()}')
    print(f'\n  Credenciales:')
    print(f'    admin / admin123 (superuser)')
    print(f'    jr    / demo1234 (vendedor)')
    print(f'    vendor / vendor123 (vendedor)')


if __name__ == '__main__':
    main()
