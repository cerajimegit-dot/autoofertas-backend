"""
Script para configurar empresa y sucursal si no existen
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Enterprise, Branch, CustomUser

# Crear o obtener empresa
enterprise, created = Enterprise.objects.get_or_create(
    name="AUTO OFERTAS",
    defaults={
        'ruc': '12345678',
        'address': 'Casa Central',
        'phone': '+555-123-4567',
        'email': 'info@autoofertas.com.py'
    }
)

if created:
    print(f"✅ Empresa creada: {enterprise.name}")
else:
    print(f"✅ Empresa existente: {enterprise.name}")

# Crear o obtener sucursal
branch, created = Branch.objects.get_or_create(
    enterprise=enterprise,
    name="CASA CENTRAL",
    defaults={
        'address': 'Casa Central',
        'phone': '+555-123-4567'
    }
)

if created:
    print(f"✅ Sucursal creada: {branch.name}")
else:
    print(f"✅ Sucursal existente: {branch.name}")

print(f"\n📋 Configuración lista:")
print(f"   Empresa ID: {enterprise.id}")
print(f"   Sucursal ID: {branch.id}")
