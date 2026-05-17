#!/usr/bin/env python
"""
Diagnóstico completo de BD, usuarios y APIs
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from core.models import Enterprise, Vehicle, Customer, Sale, Quotum
from rest_framework_simplejwt.tokens import RefreshToken
import json

User = get_user_model()

print("\n" + "="*80)
print("DIAGNÓSTICO COMPLETO: DATABASE, USUARIOS Y APIS")
print("="*80)

# ============================================================================
# 1. VERIFICAR BASE DE DATOS
# ============================================================================
print("\n1️⃣  BASE DE DATOS")
print("-" * 80)

try:
    enterprises = Enterprise.objects.all()
    print(f"Total empresas: {enterprises.count()}")
    
    for ent in enterprises:
        vehicles = Vehicle.objects.filter(enterprise=ent).count()
        customers = Customer.objects.filter(enterprise=ent).count()
        sales = Sale.objects.filter(enterprise=ent).count()
        quotas = Quotum.objects.filter(enterprise=ent).count()
        
        print(f"\n  Empresa: {ent.name} (RUC: {ent.ruc})")
        print(f"    ├─ Vehículos: {vehicles}")
        print(f"    ├─ Clientes: {customers}")
        print(f"    ├─ Ventas: {sales}")
        print(f"    └─ Cuotas: {quotas}")
        
except Exception as e:
    print(f"✗ Error conectando a BD: {e}")
    sys.exit(1)

# ============================================================================
# 2. VERIFICAR USUARIOS
# ============================================================================
print("\n2️⃣  USUARIOS Y SUS RELACIONES CON EMPRESAS")
print("-" * 80)

try:
    users = User.objects.all()
    print(f"Total usuarios: {users.count()}\n")
    
    for user in users:
        print(f"  Usuario: {user.username}")
        print(f"    ├─ Email: {user.email}")
        print(f"    ├─ Role: {user.role}")
        print(f"    ├─ Is Staff: {user.is_staff}")
        print(f"    ├─ Is Superuser: {user.is_superuser}")
        print(f"    └─ Empresa (ForeignKey): {user.enterprise}")
        
        if not user.enterprise:
            print(f"    ⚠️  ADVERTENCIA: Usuario sin empresa asignada!")
        print()
        
except Exception as e:
    print(f"✗ Error consultando usuarios: {e}")

# ============================================================================
# 3. TEST DE APIS
# ============================================================================
print("\n3️⃣  TEST DE ENDPOINTS API")
print("-" * 80)

admin_user = User.objects.filter(username='admin').first()
if not admin_user:
    print("✗ No hay usuario 'admin'")
    sys.exit(1)

# Generar token
try:
    refresh = RefreshToken.for_user(admin_user)
    access_token = str(refresh.access_token)
    print(f"✓ Token JWT generado para usuario 'admin'")
except Exception as e:
    print(f"✗ Error generando token: {e}")
    sys.exit(1)

# Test de APIs
client = Client()
headers = {
    'HTTP_AUTHORIZATION': f'Bearer {access_token}',
    'CONTENT_TYPE': 'application/json',
}

endpoints = [
    ('/api/vehicles/', 'GET'),
    ('/api/customers/', 'GET'),
    ('/api/sales/', 'GET'),
    ('/api/quotas/', 'GET'),
    ('/api/dashboard/summary/', 'GET'),
]

print("\nProbando endpoints (con autenticación):\n")

for endpoint, method in endpoints:
    try:
        response = client.get(endpoint, **headers)
        status_code = response.status_code
        
        if status_code == 200:
            try:
                data = response.json()
                
                # Contar items
                count = 0
                if isinstance(data, dict):
                    if 'results' in data:
                        count = len(data['results'])
                    elif 'data' in data:
                        count = len(data['data'])
                    elif isinstance(data, list):
                        count = len(data)
                elif isinstance(data, list):
                    count = len(data)
                
                print(f"  ✓ GET {endpoint:<30} → {status_code} (items: {count})")
                
            except json.JSONDecodeError:
                print(f"  ⚠️  GET {endpoint:<30} → {status_code} (respuesta no-JSON)")
        else:
            print(f"  ✗ GET {endpoint:<30} → {status_code}")
            
    except Exception as e:
        print(f"  ✗ GET {endpoint:<30} → ERROR: {str(e)[:50]}")

# ============================================================================
# 4. VERIFICAR FILTROS EN VISTA
# ============================================================================
print("\n4️⃣  ANÁLISIS DE FILTROS EN VISTAS")
print("-" * 80)

print(f"\nUsuario 'admin':")
print(f"  ├─ empresa asignada: {admin_user.enterprise}")

if admin_user.enterprise:
    # Contar datos que debería ver el usuario
    vehicles = Vehicle.objects.filter(enterprise=admin_user.enterprise).count()
    customers = Customer.objects.filter(enterprise=admin_user.enterprise).count()
    sales = Sale.objects.filter(enterprise=admin_user.enterprise).count()
    quotas = Quotum.objects.filter(enterprise=admin_user.enterprise).count()
    
    print(f"  └─ Datos visibles según filtro enterprise:")
    print(f"      ├─ Vehículos: {vehicles}")
    print(f"      ├─ Clientes: {customers}")
    print(f"      ├─ Ventas: {sales}")
    print(f"      └─ Cuotas: {quotas}")
else:
    print(f"  ⚠️  Sin empresa = sin datos (filtro retorna QuerySet vacío)")

# ============================================================================
# 5. RESUMEN Y RECOMENDACIONES
# ============================================================================
print("\n5️⃣  RESUMEN Y RECOMENDACIONES")
print("-" * 80)

issues = []

if not admin_user.enterprise:
    issues.append("❌ Usuario 'admin' no tiene empresa asignada")

if enterprises.count() == 0:
    issues.append("❌ No hay empresas en la BD")
else:
    ent = enterprises.first()
    if Vehicle.objects.filter(enterprise=ent).count() == 0:
        issues.append("❌ La empresa no tiene vehículos")
    if Customer.objects.filter(enterprise=ent).count() == 0:
        issues.append("❌ La empresa no tiene clientes")
    if Sale.objects.filter(enterprise=ent).count() == 0:
        issues.append("❌ La empresa no tiene ventas")

if issues:
    print("\n🔴 PROBLEMAS ENCONTRADOS:")
    for issue in issues:
        print(f"  {issue}")
else:
    print("\n✅ TODO PARECE ESTAR CORRECTO")

print("\n" + "="*80)
