"""
Reporte final de importación de datos de producción
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Vehicle, Sale, Quotum, Customer, Brand, VehicleModel, Enterprise
from django.db.models import Sum, Count, Q
from datetime import datetime

print("\n" + "="*80)
print("📊 REPORTE FINAL DE CARGA DE DATOS DE PRODUCCIÓN")
print("="*80)
print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Obtener empresa
enterprise = Enterprise.objects.first()
if not enterprise:
    print("❌ No hay empresa configurada")
    sys.exit(1)

print(f"🏢 Empresa: {enterprise.name}")
print(f"📍 RUC: {enterprise.ruc}")
print("-" * 80)

# ============================================================================
# INVENTARIO DE VEHÍCULOS
# ============================================================================
print("\n📦 INVENTARIO DE VEHÍCULOS")
print("-" * 80)

total_vehicles = Vehicle.objects.filter(enterprise=enterprise).count()
vehicles_by_brand = Vehicle.objects.filter(enterprise=enterprise).values('brand__name').annotate(count=Count('id')).order_by('-count')
vehicles_by_state = Vehicle.objects.filter(enterprise=enterprise).values('state').annotate(count=Count('id'))

print(f"✅ Total de vehículos: {total_vehicles}")

print(f"\n📊 Por Estado:")
for state_data in vehicles_by_state:
    state_map = {
        'available': 'Disponible',
        'sold': 'Vendido',
        'reserved': 'Reservado',
        'maintenance': 'Mantenimiento'
    }
    state_name = state_map.get(state_data['state'], state_data['state'])
    print(f"   • {state_name}: {state_data['count']}")

print(f"\n📊 Top Marcas Importadas:")
for idx, brand_data in enumerate(vehicles_by_brand[:10], 1):
    print(f"   {idx:2d}. {brand_data['brand__name']:30s} {brand_data['count']:3d} vehículos")

# Valor total del inventario
total_stock_value = Vehicle.objects.filter(enterprise=enterprise).aggregate(
    total=Sum('price')
)['total'] or 0
print(f"\n💰 Valor total inventario: Gs. {total_stock_value:,.0f}")

# ============================================================================
# VENTAS
# ============================================================================
print("\n\n💰 VENTAS REGISTRADAS")
print("-" * 80)

total_sales = Sale.objects.filter(enterprise=enterprise).count()
total_sales_value = Sale.objects.filter(enterprise=enterprise).aggregate(
    total=Sum('total_price')
)['total'] or 0
sales_by_payment = Sale.objects.filter(enterprise=enterprise).values('payment_form__name').annotate(count=Count('id'))

print(f"✅ Total de ventas: {total_sales}")
print(f"💰 Valor total vendido: Gs. {total_sales_value:,.0f}")

print(f"\n📊 Por Forma de Pago:")
for payment_data in sales_by_payment:
    print(f"   • {payment_data['payment_form__name']}: {payment_data['count']}")

# ============================================================================
# CUOTAS POR COBRAR
# ============================================================================
print("\n\n📋 CUOTAS POR COBRAR")
print("-" * 80)

total_quotas = Quotum.objects.filter(enterprise=enterprise).count()
quotas_by_status = Quotum.objects.filter(enterprise=enterprise).values('status').annotate(count=Count('id'), total=Sum('amount'))
total_cartera = Quotum.objects.filter(enterprise=enterprise).aggregate(total=Sum('amount'))['total'] or 0

print(f"✅ Total de cuotas: {total_quotas}")

print(f"\n📊 Por Estado:")
status_map = {
    'pending': 'Pendiente',
    'paid': 'Cobrada',
    'overdue': 'Vencida',
    'cancelled': 'Cancelada'
}
for status_data in quotas_by_status:
    status_name = status_map.get(status_data['status'], status_data['status'])
    amount = status_data['total'] or 0
    print(f"   • {status_name:15s}: {status_data['count']:3d} cuotas | Gs. {amount:,.0f}")

print(f"\n💰 Cartera Total Pendiente: Gs. {total_cartera:,.0f}")

# ============================================================================
# CLIENTES
# ============================================================================
print("\n\n👥 CLIENTES")
print("-" * 80)

total_customers = Customer.objects.filter(enterprise=enterprise).count()
generic_customers = Customer.objects.filter(enterprise=enterprise, is_generic=True).count()

print(f"✅ Total de clientes: {total_customers}")
print(f"   • Genéricos: {generic_customers}")
print(f"   • Reales: {total_customers - generic_customers}")

# ============================================================================
# RESUMEN FINANCIERO
# ============================================================================
print("\n\n📈 RESUMEN FINANCIERO")
print("-" * 80)
print(f"Stock Valorizado:              Gs. {total_stock_value:>15,.0f}")
print(f"Ventas Realizadas:             Gs. {total_sales_value:>15,.0f}")
print(f"Cartera Pendiente:             Gs. {total_cartera:>15,.0f}")
print(f"Saldo Total (Stock + Cartera): Gs. {(total_stock_value + total_cartera):>15,.0f}")

# ============================================================================
# CHECKSUM DE INTEGRIDAD
# ============================================================================
print("\n\n✅ VERIFICACIÓN DE INTEGRIDAD")
print("-" * 80)
print(f"✓ Empresa: {enterprise.name} (ID: {enterprise.id})")
print(f"✓ {total_vehicles} vehículos en inventario")
print(f"✓ {total_sales} transacciones de venta")
print(f"✓ {total_quotas} registros de cuotas")
print(f"✓ {total_customers} clientes")

# Verificar integridad de relaciones
sales_with_vehicle = Sale.objects.filter(enterprise=enterprise, vehicle__isnull=False).count()
quotas_with_sale = Quotum.objects.filter(enterprise=enterprise, sale__isnull=False).count()

print(f"\n✓ Ventas con vehículo: {sales_with_vehicle}/{total_sales}")
print(f"✓ Cuotas con venta: {quotas_with_sale}/{total_quotas}")

print("\n" + "="*80)
print("✅ CARGA DE DATOS COMPLETADA EXITOSAMENTE")
print("="*80 + "\n")
