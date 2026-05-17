#!/usr/bin/env python
"""
Verificar que la migración se completó correctamente
"""
import os
import sys
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Customer, Vehicle, Sale, Quotum, Enterprise

def verify_migration():
    """Verificar datos migrados"""
    ent = Enterprise.objects.first()
    
    if not ent:
        print("ERROR: No enterprise found")
        return False
    
    print("\n" + "=" * 70)
    print("VERIFICACION DE MIGRACION")
    print("=" * 70)
    
    print(f"\nEmpresa: {ent.name}")
    
    # Clientes
    customers = Customer.objects.filter(enterprise=ent).count()
    print(f"\nClientes: {customers}")
    
    # Vehículos
    vehicles = Vehicle.objects.filter(enterprise=ent).count()
    print(f"Vehiculos: {vehicles}")
    
    # Ventas
    sales = Sale.objects.filter(enterprise=ent).count()
    print(f"Ventas: {sales}")
    
    # Cuotas
    quotas = Quotum.objects.filter(enterprise=ent).count()
    print(f"Cuotas: {quotas}")
    
    # Cuotas por estado
    quotas_pending = Quotum.objects.filter(enterprise=ent, status='pending').count()
    quotas_paid = Quotum.objects.filter(enterprise=ent, status='paid').count()
    
    print(f"\nCuotas Pendientes: {quotas_pending}")
    print(f"Cuotas Pagadas: {quotas_paid}")
    
    # Monto total en ventas
    from django.db.models import Sum
    from decimal import Decimal
    
    total_sales = Sale.objects.filter(enterprise=ent).aggregate(Sum('total_price'))['total_price__sum'] or Decimal('0')
    total_quotas = Quotum.objects.filter(enterprise=ent).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    print(f"\nMonto Total Ventas: {total_sales:,.2f}")
    print(f"Monto Total Cuotas: {total_quotas:,.2f}")
    
    # Estadísticas de pagos
    total_paid = Quotum.objects.filter(enterprise=ent, status='paid').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    pending_amount = Quotum.objects.filter(enterprise=ent, status='pending').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    print(f"\nMonto Cobrado: {total_paid:,.2f}")
    print(f"Monto Por Cobrar: {pending_amount:,.2f}")
    
    # Muestra de datos
    print(f"\n" + "-" * 70)
    print("MUESTRA DE DATOS")
    print("-" * 70)
    
    # Últimos clientes
    print("\nUltimos 5 Clientes:")
    for cust in Customer.objects.filter(enterprise=ent).order_by('-created_at')[:5]:
        print(f"  - {cust.full_name} ({cust.document_number})")
    
    # Últimas ventas
    print("\nUltimas 5 Ventas:")
    for sale in Sale.objects.filter(enterprise=ent).order_by('-sale_date')[:5]:
        print(f"  - {sale.sale_number}: {sale.total_price:,.2f} ({sale.status})")
    
    # Vehículos en stock
    print("\nVehiculos en Stock (disponibles):")
    available = Vehicle.objects.filter(enterprise=ent, state='available').count()
    sold = Vehicle.objects.filter(enterprise=ent, state='sold').count()
    print(f"  - Disponibles: {available}")
    print(f"  - Vendidos: {sold}")
    
    print("\n" + "=" * 70)
    print("VERIFICACION COMPLETADA")
    print("=" * 70)
    
    return True

if __name__ == '__main__':
    try:
        verify_migration()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
