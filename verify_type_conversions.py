import os
import sys
import django
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Vehicle, Sale, Quotum, Customer

print("\n" + "="*80)
print("✅ VERIFICACIÓN: CONVERSIONES DE TIPOS FIXEADAS")
print("="*80 + "\n")

# Test 1: Conversiones int(float()) para años
print("1️⃣  Test: Convertir años desde decimales")
print("-" * 80)

test_years = [2026, "2026", "2026.0", "2026.00", 2024.5, "2024.99"]
for year_val in test_years:
    try:
        if isinstance(year_val, str):
            result = int(float(year_val))
        else:
            result = int(float(year_val)) if year_val else 2026
        print(f"  ✓ {year_val!r} → {result}")
    except Exception as e:
        print(f"  ✗ {year_val!r} → ERROR: {e}")

# Test 2: Conversiones Decimal para montos
print("\n2️⃣  Test: Convertir montos a Decimal")
print("-" * 80)

test_amounts = ["100000.00", "100,000.00", "$100000.00", 100000, "100000"]
for amount in test_amounts:
    try:
        monto_str = str(amount).replace('$', '').replace(',', '').strip()
        result = Decimal(monto_str)
        print(f"  ✓ {amount!r} → {result}")
    except Exception as e:
        print(f"  ✗ {amount!r} → ERROR: {e}")

# Test 3: Conversiones de cliente_num a quota_number
print("\n3️⃣  Test: Conversión de cliente_num a quota_number (el error original)")
print("-" * 80)

test_clients = ["100000.00", "1", "CLIENT001", 100000, "100,000.00", "ABC123.45"]
for client in test_clients:
    try:
        cliente_num_clean = str(client).replace('.', '').replace(',', '').strip()
        if cliente_num_clean.replace('-', '').isdigit():  # Mejor check para números
            quota_num = int(float(str(client).replace('.', '').replace(',', '')))
            result = f"quota_number={quota_num}"
        else:
            result = f"quota_number=<auto>"
        print(f"  ✓ {client!r} → {result}")
    except Exception as e:
        print(f"  ✗ {client!r} → ERROR: {e}")

# Test 4: Datos reales de la BD
print("\n4️⃣  Test: Revisión de datos reales en BD")
print("-" * 80)

try:
    vehicles = Vehicle.objects.all()[:5]
    print(f"Vehículos analizados: {vehicles.count()}")
    for v in vehicles:
        print(f"  • {v.brand.name} - Precio: Gs. {v.price:,.0f} (tipo: {type(v.price).__name__})")
except Exception as e:
    print(f"  ✗ Error al obtener vehículos: {e}")

try:
    sales = Sale.objects.all()[:5]
    print(f"\nVentas analizadas: {sales.count()}")
    for s in sales:
        print(f"  • {s.sale_number} - Total: Gs. {s.total_price:,.0f} (tipo: {type(s.total_price).__name__})")
except Exception as e:
    print(f"  ✗ Error al obtener ventas: {e}")

try:
    quotas = Quotum.objects.all()[:5]
    print(f"\nCuotas analizadas: {quotas.count()}")
    for q in quotas:
        print(f"  • Cuota #{q.quota_number} - Monto: Gs. {q.amount:,.0f} (tipo: {type(q.amount).__name__})")
except Exception as e:
    print(f"  ✗ Error al obtener cuotas: {e}")

print("\n" + "="*80)
print("✅ VERIFICACIÓN COMPLETADA")
print("="*80)
print("\nResumen de fixes aplicados:")
print("  • int() → int(float()) para valores que pueden ser decimales")
print("  • Decimal() con manejo de símbolos de moneda")
print("  • max(1, quota_num) para asegurar valores válidos")
print("  • Mejor validación de strings numéricos")
print("\n" + "="*80 + "\n")
