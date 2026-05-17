#!/usr/bin/env python
"""
Script para relacionar vehículos y marcas con la empresa de pruebas
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Enterprise, Brand, Vehicle, VehicleModel

print("=" * 80)
print("RELACIONANDO VEHÍCULOS Y MARCAS CON EMPRESA DE PRUEBAS")
print("=" * 80)

# Obtener o crear la empresa de pruebas
try:
    # Primera empresa (de pruebas)
    enterprise = Enterprise.objects.first()
    if not enterprise:
        print("ERROR: No hay empresas en el sistema")
        sys.exit(1)
    
    print(f"\nEmpresa destino: {enterprise.name} (ID: {enterprise.id})\n")
    
    # Actualizar marcas sin empresa o con empresa incorrecta
    print("1. ACTUALIZANDO MARCAS...")
    print("-" * 80)
    
    # Marcas sin enterprise
    brands_no_enterprise = Brand.objects.filter(enterprise__isnull=True)
    if brands_no_enterprise.exists():
        count = brands_no_enterprise.count()
        Brand.objects.filter(enterprise__isnull=True).update(enterprise=enterprise)
        print(f"✓ {count} marcas asignadas (antes sin empresa)")
    else:
        print("  No hay marcas sin empresa")
    
    # Total de marcas por empresa
    total_brands = Brand.objects.filter(enterprise=enterprise).count()
    print(f"✓ Total de marcas en {enterprise.name}: {total_brands}")
    
    # Listado de marcas
    brands = Brand.objects.filter(enterprise=enterprise)
    if brands.exists():
        print("\n  Marcas:")
        for brand in brands:
            print(f"    - {brand.name}")
    
    # Actualizar vehículos
    print("\n2. ACTUALIZANDO VEHÍCULOS...")
    print("-" * 80)
    
    # Vehículos sin enterprise
    vehicles_no_enterprise = Vehicle.objects.filter(enterprise__isnull=True)
    if vehicles_no_enterprise.exists():
        count = vehicles_no_enterprise.count()
        Vehicle.objects.filter(enterprise__isnull=True).update(enterprise=enterprise)
        print(f"✓ {count} vehículos asignados (antes sin empresa)")
    else:
        print("  No hay vehículos sin empresa")
    
    # Total de vehículos por empresa
    total_vehicles = Vehicle.objects.filter(enterprise=enterprise).count()
    print(f"✓ Total de vehículos en {enterprise.name}: {total_vehicles}")
    
    # Mostrar algunas marcas de vehículos para verificar
    print("\n3. VERIFICACIÓN DE DATOS...")
    print("-" * 80)
    
    vehicles = Vehicle.objects.filter(enterprise=enterprise)
    if vehicles.exists():
        print(f"  Primeros 5 vehículos:")
        for v in vehicles[:5]:
            brand = v.brand.name if v.brand else "SIN MARCA"
            model = v.model.name if v.model else "SIN MODELO"
            print(f"    {v.year} {brand} {model} - VIN: {v.vin}")
        
        if vehicles.count() > 5:
            print(f"  ... y {vehicles.count() - 5} vehículos más")
    
    # Resumen final
    print("\n4. RESUMEN FINAL...")
    print("-" * 80)
    print(f"✓ Empresa: {enterprise.name}")
    print(f"✓ Marcas: {total_brands}")
    print(f"✓ Vehículos: {total_vehicles}")
    print(f"\n✓ RELACIÓN COMPLETADA EXITOSAMENTE")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
