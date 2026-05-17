#!/usr/bin/env python
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')

import django
django.setup()

from core.models import Enterprise, Brand, Vehicle

output = []

try:
    output.append("=" * 80 + "\n")
    output.append("RELACIONANDO DATOS CON EMPRESA DE PRUEBAS\n")
    output.append("=" * 80 + "\n")
    
    # Obtener empresa
    enterprise = Enterprise.objects.first()
    if not enterprise:
        output.append("ERROR: No hay empresas\n")
        sys.exit(1)
    
    output.append(f"\nEmpresa: {enterprise.name} (ID: {enterprise.id})\n")
    
    # Actualizar marcas
    output.append("\n1. MARCAS\n")
    output.append("-" * 80 + "\n")
    
    orphan_brands = Brand.objects.filter(enterprise__isnull=True).count()
    if orphan_brands > 0:
        Brand.objects.filter(enterprise__isnull=True).update(enterprise=enterprise)
        output.append(f"✓ {orphan_brands} marcas asignadas\n")
    
    total_brands = Brand.objects.filter(enterprise=enterprise).count()
    output.append(f"✓ Total: {total_brands} marcas\n")
    
    # Actualizar vehículos
    output.append("\n2. VEHÍCULOS\n")
    output.append("-" * 80 + "\n")
    
    orphan_vehicles = Vehicle.objects.filter(enterprise__isnull=True).count()
    if orphan_vehicles > 0:
        Vehicle.objects.filter(enterprise__isnull=True).update(enterprise=enterprise)
        output.append(f"✓ {orphan_vehicles} vehículos asignados\n")
    
    total_vehicles = Vehicle.objects.filter(enterprise=enterprise).count()
    output.append(f"✓ Total: {total_vehicles} vehículos\n")
    
    # Resumen
    output.append("\n3. RESUMEN\n")
    output.append("-" * 80 + "\n")
    output.append(f"Empresa: {enterprise.name}\n")
    output.append(f"Marcas: {total_brands}\n")
    output.append(f"Vehículos: {total_vehicles}\n")
    output.append(f"\n✓ COMPLETADO\n")
    output.append("=" * 80 + "\n")

except Exception as e:
    output.append(f"ERROR: {e}\n")
    import traceback
    output.append(traceback.format_exc())

# Guardar a archivo
with open('link_output.txt', 'w') as f:
    f.writelines(output)

# Imprimir
for line in output:
    print(line, end='')
