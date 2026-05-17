# Quick Start - Sistema de Gestión de Playas de Autos

## 1. Instalación Rápida

### Windows:
```bash
# Ejecutar script de configuración
setup.bat
```

### Mac/Linux:
```bash
# Ejecutar script de configuración
bash setup.sh
```

## 2. Configuración Manual

### Paso 1: Crear entorno virtual
```bash
python -m venv venv

# Activar
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### Paso 2: Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 3: Configurar .env
```bash
cp .env.example .env

# Editar .env con tus datos de PostgreSQL
# Ejemplo:
# DB_NAME=playas_autos
# DB_USER=postgres
# DB_PASSWORD=tu_contraseña
# DB_HOST=localhost
# DB_PORT=5432
```

### Paso 4: Base de datos (con Docker)
```bash
# Iniciar PostgreSQL y Redis
docker-compose up -d

# Verificar que está corriendo
docker-compose ps
```

### Paso 5: Crear migraciones y tablas
```bash
python manage.py makemigrations
python manage.py migrate
```

### Paso 6: Crear datos de prueba
```bash
python scripts/create_test_data.py
python scripts/generate_sample_excel.py
```

### Paso 7: Ejecutar servidor
```bash
python manage.py runserver
```

## 3. Acceso a la Aplicación

### Admin Django
- **URL**: http://localhost:8000/admin/
- **Usuario**: admin
- **Contraseña**: admin123456

### API REST
- **URL**: http://localhost:8000/api/
- **Documentación**: (Swagger será agregado)

### Otros usuarios de prueba
- **manager1** / manager123456 (Encargado de sucursal)
- **vendor1** / vendor123456 (Vendedor)

## 4. Endpoints principales

### Autenticación
```bash
# Registrar
POST /api/users/register/
{
  "username": "nuevo_usuario",
  "email": "usuario@email.com",
  "password": "segura123456",
  "password_confirm": "segura123456",
  "enterprise_name": "Mi Empresa",
  "ruc": "80000000",
  "phone": "+595971234567"
}

# Login
POST /api/users/login/
{
  "username": "admin",
  "password": "admin123456"
}

# Obtener datos del usuario actual
GET /api/users/me/
Authorization: Bearer <access_token>
```

### Vehículos
```bash
# Listar vehículos disponibles
GET /api/vehicles/available/

# Listar vehículos por estado
GET /api/vehicles/by_state/?state=available

# Stock valorizado
GET /api/vehicles/valorized_stock/

# Detalle de vehículo
GET /api/vehicles/{id}/
```

### Ventas
```bash
# Crear venta
POST /api/sales/
{
  "customer": 1,
  "vehicle": 1,
  "unit_price": 20000,
  "discount": 0,
  "total_price": 20000,
  "payment_form": 1
}

# Ventas del mes
GET /api/sales/monthly_sales/

# Reporte de ventas
GET /api/sales/sales_report/?date_from=2024-01-01&date_to=2024-04-03
```

### Cuotas
```bash
# Cuotas pendientes
GET /api/quotas/pending/

# Cuotas vencidas
GET /api/quotas/overdue/

# Cuotas próximos 30 días
GET /api/quotas/next_30_days/

# Marcar como cobrada
POST /api/quotas/{id}/mark_as_paid/

# Contacto WhatsApp
GET /api/quotas/{id}/contact_whatsapp/
```

## 5. Estructura del Proyecto

```
playa/
├── playas_autos/        # Configuración de Django
├── core/               # Aplicación principal
│   ├── models/        # Modelos de BD
│   ├── views/         # ViewSets
│   ├── serializers/   # Serializadores DRF
│   ├── permissions.py # Permisos personalizados
│   └── admin.py       # Admin de Django
├── scripts/           # Scripts de utilidad
├── tests/             # Tests automáticos
└── manage.py          # CLI Django
```

## 6. Desarrollo

### Ejecutar tests
```bash
pytest
```

### Hacer migraciones después de cambiar modelos
```bash
python manage.py makemigrations
python manage.py migrate
```

### Crear superusuario nuevo
```bash
python manage.py createsuperuser
```

### Shell de Django
```bash
python manage.py shell
```

## 7. Variables de Entorno

Ver `.env.example` para todas las variables disponibles.

Variables más importantes:
- `DEBUG`: True/False para modo debug
- `SECRET_KEY`: Clave secreta (CAMBIAR EN PRODUCCIÓN)
- `DATABASE_URL` o `DB_*`: Configuración de PostgreSQL
- `JWT_SECRET`: Clave secreta para JWT

## 8. docker-compose

### Iniciar servicios
```bash
docker-compose up -d
```

### Ver logs
```bash
docker-compose logs -f db
docker-compose logs -f redis
```

### Detener servicios
```bash
docker-compose down
```

### Limpiar datos (CUIDADO!)
```bash
docker-compose down -v
```

## 9. Troubleshooting

### "django.db.utils.OperationalError: could not connect to server"
- Verificar que PostgreSQL está corriendo
- Verificar variables de entorno en .env
- Ejecutar: `docker-compose up -d db`

### "ModuleNotFoundError"
- Verificar que el entorno virtual está activado
- Reinstalar dependencias: `pip install -r requirements.txt`

### "Table doesn't exist"
- Ran migraciones: `python manage.py migrate`

## 10. Documentación Completa

Ver `README.md` para documentación completa del proyecto.
Ver `progress.md` para el estado actual del desarrollo.
