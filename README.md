# Sistema de Gestión de Playas de Autos - Playa Autos

Sistema web multiempresa para la gestión integral de playas de autos, construido con Django REST Framework y PostgreSQL.

## Características Principales

### 1. Autenticación y Roles
- Registro y login de usuarios
- Roles: Administrador, Encargado de sucursal, Vendedor
- Multiempresa: cada cliente puede crear su propia empresa y gestionar sucursales

### 2. Módulos Principales
- **Empresas**: CRUD de empresas y sucursales
- **Marcas y Modelos**: gestión de marcas de vehículos con imágenes
- **Vehículos**: stock con atributos completos, costos (FOB, CONTEN, DESPACHO, CAM/VOL), precios en guaraní/dólar
- **Ventas**: registro de ventas con crear clientes automáticamente si es necesario
- **Cuotas**: planes de financiación, fechas de vencimiento, integración con WhatsApp
- **Clientes**: datos personales e historial de compras
- **Reportes**: ventas mensuales, cuotas por cobrar, stock valorizado, ranking de modelos

### 3. Dashboard
- KPIs: ventas, cuotas, stock por sucursal
- Gráficos de tendencias
- Filtros por empresa, sucursal y período

### 4. Migración de Datos
- Scripts para carga masiva desde Excel
- Validación automática
- Archivos de prueba de ejemplo
- Módulo especial para archivos con formato no estándar

### 5. Seguridad
- Auditoría de acciones
- Aprobaciones para operaciones críticas
- Respaldos semanales

## Requerimientos Técnicos

- Python 3.11+
- Django 4.2+
- PostgreSQL 14+
- Django REST Framework
- Docker (opcional)

## Instalación

### 1. Clonar repositorio
```bash
git clone <repo-url>
cd playa
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con las credenciales de PostgreSQL
```

### 5. Ejecutar migraciones
```bash
python manage.py migrate
```

### 6. Crear superusuario
```bash
python manage.py createsuperuser
```

### 7. Ejecutar servidor de desarrollo
```bash
python manage.py runserver
```

## Estructura del Proyecto

```
playa/
├── playas_autos/           # Proyecto Django principal
│   ├── settings.py         # Configuración
│   ├── urls.py            # Rutas principales
│   └── wsgi.py            # WSGI para producción
├── core/                   # App principal
│   ├── models/            # Modelos de base de datos
│   ├── views/             # Vistas y viewsets
│   ├── serializers/       # Serializadores DRF
│   ├── permissions.py     # Permisos personalizados
│   ├── admin.py           # Admin de Django
│   └── migrations/        # Migraciones de BD
├── scripts/               # Scripts de importación y utilidades
│   ├── import_vehicles.py
│   ├── import_sales.py
│   ├── import_customers.py
│   └── import_quotas.py
├── tests/                 # Tests automáticos
├── static/               # Archivos estáticos
├── media/               # Archivos de usuario (imágenes)
├── manage.py            # Herramienta de línea de comandos
└── requirements.txt     # Dependencias Python
```

## Desarrollo

### Ejecutar tests
```bash
pytest
```

### Criar archivo de progreso
Ver `progress.md` para tracking de avances

## API Endpoints

### Autenticación
- `POST /api/auth/register/` - Registro de usuario
- `POST /api/auth/login/` - Login
- `POST /api/auth/logout/` - Logout

### Empresas
- `GET/POST /api/enterprises/` - Listar/crear empresas
- `GET/PUT/DELETE /api/enterprises/{id}/` - Detalle/editar/eliminar

### Vehículos
- `GET/POST /api/vehicles/` - Listar/crear vehículos
- `GET/PUT/DELETE /api/vehicles/{id}/` - Detalle/editar/eliminar

### Ventas
- `GET/POST /api/sales/` - Listar/crear ventas
- `GET/PUT/DELETE /api/sales/{id}/` - Detalle/editar/eliminar

### Cuotas
- `GET/POST /api/quotas/` - Listar/crear cuotas
- `GET/PUT /api/quotas/{id}/` - Detalle/marcar como cobrada

### Clientes
- `GET/POST /api/customers/` - Listar/crear clientes
- `GET/PUT/DELETE /api/customers/{id}/` - Detalle/editar/eliminar

## Documentación API

Una vez en desarrollo, acceder a:
- Swagger UI: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`

## Licencia

Privado - Sistema propietario

## Contacto

Para consultas sobre desarrollo y mantenimiento, contactar al equipo de desarrollo.
