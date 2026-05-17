#!/usr/bin/env python
"""
PLAYAS DE AUTOS - Status and Access Guide
==========================================

Sistema completo de gestión de inventario de playas de autos.
Todos los servicios operativos en: http://localhost:8001
"""

import requests
import json
from datetime import datetime

print("\n" + "="*80)
print("🚀 PLAYAS DE AUTOS - STATUS DE SERVIDORES")
print("="*80)
print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# ACCESO AL SISTEMA
# ============================================================================
print("🌐 ACCESO AL SISTEMA")
print("-" * 80)
print(f"""
┌─ FRONTEND (Django Templates)
│  URL: http://localhost:8001/
│  Login: http://localhost:8001/login/
│  Usuario: admin
│  Contraseña: admin123
│
├─ DASHBOARD: http://localhost:8001/dashboard/
├─ VEHÍCULOS: http://localhost:8001/vehicles/
├─ VENTAS: http://localhost:8001/sales/
├─ CUOTAS: http://localhost:8001/quotas/
├─ CLIENTES: http://localhost:8001/customers/
│
└─ API REST
   URL Base: http://localhost:8001/api/
   Docs: http://localhost:8001/api/docs/
   ReDoc: http://localhost:8001/api/redoc/
""")

# ============================================================================
# ESTADO DEL SERVIDOR
# ============================================================================
print("\n✅ ESTADO DE SERVICIOS")
print("-" * 80)

try:
    # Test Frontend
    response = requests.get('http://localhost:8001/', timeout=2)
    status = "✅ OPERATIVO" if response.status_code in [200, 302] else "⚠️ ERROR"
    print(f"{status} Frontend Django ............ {response.status_code}")
except:
    print("❌ Frontend Django ............ OFFLINE")

try:
    # Test API
    response = requests.get('http://localhost:8001/api/', timeout=2)
    status = "✅ OPERATIVO" if response.status_code in [200, 401] else "⚠️ ERROR"
    print(f"{status} API REST ..................... {response.status_code}")
except:
    print("❌ API REST ..................... OFFLINE")

try:
    # Test API Docs
    response = requests.get('http://localhost:8001/api/docs/', timeout=2)
    status = "✅ OPERATIVO" if response.status_code == 200 else "⚠️ ERROR"
    print(f"{status} Swagger Docs ................. {response.status_code}")
except:
    print("❌ Swagger Docs ................. OFFLINE")

# ============================================================================
# DATOS IMPORTADOS
# ============================================================================
print("\n\n📊 DATOS IMPORTADOS")
print("-" * 80)
print(f"""
├─ 111 Vehículos en stock
├─ 21 Ventas registradas
├─ 108 Cuotas pendientes (Gs. 2.18 mil millones)
├─ 56 Clientes
└─ 3 Empresas configuradas
""")

# ============================================================================
# ACCIONES RÁPIDAS
# ============================================================================
print("\n💡 ACCIONES RÁPIDAS")
print("-" * 80)
print(f"""
1. Iniciar Login:
   http://localhost:8001/login/

2. Ver Dashboard:
   http://localhost:8001/dashboard/

3. Explorar Vehículos:
   http://localhost:8001/vehicles/

4. Revisar Ventas:
   http://localhost:8001/sales/

5. Cuotas por Cobrar:
   http://localhost:8001/quotas/

6. Gestionar Clientes:
   http://localhost:8001/customers/

7. Documentación API:
   http://localhost:8001/api/docs/
""")

print("="*80 + "\n")
