# Sistema de Gestión de Playas de Autos - Guía de Prueba

## Estado del Sistema
✅ **Base de datos**: SQLite inicializada
✅ **Migraciones**: Aplicadas correctamente
✅ **Usuarios de prueba**: Creados
✅ **Servidor Django**: Corriendo en http://localhost:8001

---

## 🚀 URLs de Acceso

### Swagger UI (Documentación Interactiva)
- [Swagger UI](http://localhost:8001/api/docs/) - Interfaz interactiva para probar endpoints
- [ReDoc](http://localhost:8001/api/redoc/) - Documentación alternativa
- [OpenAPI Schema](http://localhost:8001/api/schema/) - Schema en JSON

### Admin Django
- [Admin Panel](http://localhost:8001/admin/) - Panel administrativo

---

## 👤 Credenciales de Prueba

### Superuser (Administrador)
```
Email: admin@playas.py
Password: admin123
Role: Administrador
Enterprise: Admin Enterprise
```

### Manager
```
Email: manager@playas.py
Password: manager123
Role: Encargado de Sucursal
Enterprise: Admin Enterprise
```

### Test Enterprise
```
Name: Playas Test S.A.
RUC: 1234567-8
```

---

## 📋 Endpoints Principales

### Autenticación

#### Login (Obtener Token JWT)
```
POST /api/users/login/
Content-Type: application/json

{
  "email": "admin@playas.py",
  "password": "admin123"
}

Response:
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Registrar Nuevo Usuario
```
POST /api/users/register/
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "secure_password",
  "username": "newuser",
  "first_name": "John",
  "last_name": "Doe",
  "role": "vendor"
}
```

#### Verificar Usuario Actual
```
GET /api/users/me/
Authorization: Bearer {access_token}
```

#### Logout
```
POST /api/users/logout/
Authorization: Bearer {access_token}
```

---

### Inventario

#### Listar Marcas de Vehículos
```
GET /api/brands/
GET /api/brands/?is_active=true
Authorization: Bearer {access_token}
```

#### Crear Nueva Marca
```
POST /api/brands/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Toyota",
  "is_active": true
}
```

#### Listar Modelos de Vehículos
```
GET /api/models/
GET /api/models/?brand=1
Authorization: Bearer {access_token}
```

#### Cotización USD/PYG
```
GET /api/exchange-rates/
GET /api/exchange-rates/current/
Authorization: Bearer {access_token}
```

#### Crear/Actualizar Cotización
```
POST /api/exchange-rates/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "date": "2026-04-03",
  "usd_to_pyg": 7250.00,
  "is_active": true
}
```

#### Listar Vehículos
```
GET /api/vehicles/
GET /api/vehicles/?state=available
GET /api/vehicles/?state=sold
GET /api/vehicles/?brand=1
Authorization: Bearer {access_token}
```

#### Crear Vehículo
```
POST /api/vehicles/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "brand": 1,
  "model": 1,
  "year": 2024,
  "vin": "JTDZX3EU7M3043762",
  "license_plate": "ABC-123",
  "color": "Blanco",
  "fob": 15000.00,
  "container": 200.00,
  "dispatch": 150.00,
  "cam_vol": 50.00,
  "price_currency": "USD",
  "price": 20000.00,
  "branch": 1
}
```

#### Stock Disponible
```
GET /api/vehicles/available/
Authorization: Bearer {access_token}
```

#### Stock Valorizado (por sucursal)
```
GET /api/vehicles/valorized_stock/
Authorization: Bearer {access_token}

Response:
[
  {
    "branch": 1,
    "branch_name": "Sucursal Centro",
    "total_by_state": {
      "available": 50000.00,
      "reserved": 10000.00,
      "sold": 0,
      "maintenance": 5000.00
    },
    "total_value": 65000.00
  }
]
```

---

### Ventas

#### Listar Clientes
```
GET /api/customers/
GET /api/customers/?is_generic=false
Authorization: Bearer {access_token}
```

#### Crear Cliente
```
POST /api/customers/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Juan Pérez",
  "document_type": "CI",
  "document_number": "3844123",
  "email": "juan@example.com",
  "phone": "0973123456",
  "address": "Av. Mariscal López 123",
  "city": "Asunción",
  "country": "Paraguay"
}
```

#### Formas de Pago
```
GET /api/payment-forms/
POST /api/payment-forms/
Authorization: Bearer {access_token}
```

#### Registrar Venta
```
POST /api/sales/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "customer": 1,
  "vehicle": 1,
  "unit_price": 20000.00,
  "discount": 500.00,
  "payment_form": 1,
  "notes": "Venta al contado"
}
```

#### Ventas del Mes
```
GET /api/sales/monthly_sales/
Authorization: Bearer {access_token}
```

#### Reporte de Ventas (por rango de fechas)
```
GET /api/sales/sales_report/?start_date=2026-01-01&end_date=2026-04-30
Authorization: Bearer {access_token}
```

---

### Cuotas

#### Listar Cuotas
```
GET /api/quotas/
GET /api/quotas/?status=pending
Authorization: Bearer {access_token}
```

#### Cuotas Vencidas
```
GET /api/quotas/overdue/
Authorization: Bearer {access_token}
```

#### Cuotas Próximos 30 Días
```
GET /api/quotas/next_30_days/
Authorization: Bearer {access_token}
```

#### Marcar Cuota Como Pagada
```
POST /api/quotas/{id}/mark_as_paid/
Authorization: Bearer {access_token}
```

#### Generar Link de WhatsApp
```
GET /api/quotas/{id}/contact_whatsapp/
Authorization: Bearer {access_token}

Response:
{
  "whatsapp_url": "https://wa.me/595973123456?text=Cuota+pendiente+de+pago+..."
}
```

#### Reporte de Cuotas (por estado)
```
GET /api/quotas/quota_report/
Authorization: Bearer {access_token}

Response:
{
  "total": 150000.00,
  "by_status": {
    "pending": 80000.00,
    "paid": 50000.00,
    "overdue": 20000.00
  }
}
```

---

### Dashboard / KPIs

```
GET /api/dashboard/summary/
GET /api/dashboard/sales_by_month/
GET /api/dashboard/sales_by_branch/
GET /api/dashboard/vehicle_models_ranking/
GET /api/dashboard/quotas_status/
GET /api/dashboard/inventory_stats/
GET /api/dashboard/top_customers/

Authorization: Bearer {access_token}
```

---

## 📁 Archivos de Prueba Generados

Los siguientes archivos Excel se generaron para pruebas de importación:

```
/scripts/
├── sample_vehicles.xlsx       - Template de importación de vehículos
├── sample_customers.xlsx      - Template de importación de clientes
├── sample_sales.xlsx          - Template de importación de ventas
└── sample_quotas.xlsx         - Template de importación de cuotas
```

Estos archivos contienen datos de ejemplo y pueden ser modificados para probar los scripts de importación.

---

## 🧪 Pruebas Recomendadas

1. **Autenticación**
   - [ ] Login exitoso
   - [ ] Obtener token JWT
   - [ ] Acceso con token en Authorization header
   - [ ] Logout

2. **Inventario**
   - [ ] Crear marca
   - [ ] Crear modelo
   - [ ] Crear exchange rate
   - [ ] Crear vehículo en USD
   - [ ] Listar vehículos disponibles
   - [ ] Calcular stock valorizado

3. **Ventas**
   - [ ] Crear cliente
   - [ ] Registrar venta
   - [ ] Verificar stock updated (vehicle → sold)

4. **Cuotas**
   - [ ] Crear cuota
   - [ ] Listar cuotas pendientes
   - [ ] Marcar como pagada
   - [ ] Generar link WhatsApp

5. **Dashboard**
   - [ ] Resumen ejecutivo
   - [ ] Ventas por mes
   - [ ] Ventas por sucursal
   - [ ] Ranking de modelos
   - [ ] Estado de cuotas
   - [ ] Estadísticas de inventario
   - [ ] Top clientes

6. **Filtros y Búsqueda**
   - [ ] Filtrar por estado del vehículo
   - [ ] Filtrar por rama/sucursal
   - [ ] Filtrar por rango de fechas
   - [ ] Buscar por documento de cliente

---

## 🐞 Bugs Conocidos / Limitaciones

- La base de datos usa SQLite (para desarrollo). Para producción, cambiar a PostgreSQL en settings.py
- Los campos de imagen (logo, brand image) están habilitados pero requieren storage configurado
- Auditoría registra cambios automáticamente en todos los modelos

---

## 🔧 Troubleshooting

### Servidor no responde
```bash
# Reiniciar servidor
python manage.py runserver 0.0.0.0:8000
```

### Base de datos corrupta
```bash
# Restaurar migraciones
python manage.py migrate --fake core zero
python manage.py migrate core
python manage.py migrate
```

### Limpiar datos de prueba
```bash
# Borrar y recrear base de datos
rm db.sqlite3
python manage.py migrate
python scripts/create_superuser.py
python scripts/create_test_data.py
```

---

## 📝 Próximos Pasos

1. ✅ Base de datos inicializada
2. ✅ Usuarios de prueba creados
3. ✅ Servidor corriendo
4. 📋 Ejecutar pruebas manuales en Swagger UI
5. 📋 Ejecutar scripts de importación con archivos sample
6. 📋 Validar calculaciones de KPIs
7. 📋 Testing automático (pytest)
8. 📋 Deploy a producción (PostgreSQL)

---

**Generado**: 2026-04-03 08:00:00 UTC
