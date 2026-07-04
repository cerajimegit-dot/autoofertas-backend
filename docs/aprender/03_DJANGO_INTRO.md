# 🎯 Django — qué es y cómo lo usamos

> Django es el **framework de Python que hace de "backend"** de nuestro
> sistema. En este archivo aprendés qué hace Django y cómo está
> estructurado nuestro proyecto.

---

## 1. ¿Qué es un framework?

Un **framework** es un conjunto de código ya hecho que resuelve problemas
comunes. En lugar de armar todo desde cero, aprovechás lo que ya está.

Django te da:
- Conexión a la base de datos
- Sistema de rutas (URLs → funciones)
- Sistema de usuarios y permisos
- Panel de administración automático
- Formularios, seguridad, sesiones, etc.

Sin Django, cada una de esas cosas sería 3-4 semanas de trabajo.

---

## 2. Arquitectura MTV de Django

Django separa el código en 3 partes:

```
Model     -->  representa una tabla de la base de datos
                (Customer, Sale, Vehicle, ...)

Template  -->  HTML dinámico
                (poco usado en nuestro caso porque el frontend es React)

View      -->  la lógica que responde a una request HTTP
                (busca datos, los procesa, devuelve JSON)
```

Este proyecto usa Django como **API** (backend). El **frontend** (que
es React separado) le pide datos vía HTTP, Django los devuelve en JSON.

---

## 3. El flujo de una request

Cuando el frontend pide `/api/customers/`:

```
1. El browser envía GET https://backend.com/api/customers/
2. Django recibe la URL
3. Busca en playas_autos/urls.py qué view corresponde
4. Encuentra: /api/ → core/urls.py → customers → CustomerViewSet.list
5. Ejecuta CustomerViewSet.list
6. La view consulta la BD: Customer.objects.all()
7. Serializa a JSON
8. Devuelve HTTP 200 con el JSON
9. El frontend recibe y muestra
```

Cada archivo tiene su rol. Vamos a ver dónde está cada cosa.

---

## 4. Estructura del proyecto (backend)

```
playa/
├── manage.py                        <- entrada principal para todo
├── playas_autos/                    <- config del proyecto Django
│   ├── settings.py                    (config: BD, apps, seguridad)
│   ├── urls.py                        (mapa de URLs top-level)
│   ├── wsgi.py                        (para deploy)
│   └── asgi.py                        (para deploy async)
├── core/                            <- nuestra app principal
│   ├── models/                        <- las tablas de la BD
│   │   ├── base.py                    (Enterprise, Branch, User)
│   │   ├── inventory.py               (Brand, VehicleModel, Vehicle)
│   │   ├── sales.py                   (Customer, Sale, Quotum, PaymentForm)
│   │   └── cash.py                    (CashMovement)
│   ├── views/                         <- endpoints de la API
│   │   ├── base.py                    (login, users, health)
│   │   ├── inventory.py               (endpoints de vehículos)
│   │   ├── sales.py                   (endpoints de ventas y cuotas)
│   │   ├── cash.py                    (endpoints de caja)
│   │   └── dashboard.py               (KPIs y reportes)
│   ├── serializers/                   <- conversión Python <-> JSON
│   ├── migrations/                    <- historial de cambios en la BD
│   ├── urls.py                        (mapa de URLs del app)
│   └── admin.py                       (panel /admin)
├── scripts/                         <- utilidades (no parte de Django)
├── docs/                            <- documentación
├── requirements.txt                 <- lista de paquetes Python que usamos
├── .env                             <- config sensible (no commiteada)
├── db.sqlite3                       <- la BD local
└── venv/                            <- ambiente virtual de Python
```

---

## 5. ¿Qué es un modelo?

Un **modelo** es una clase de Python que representa una **tabla en la
base de datos**. Django lee esa clase y crea la tabla automáticamente.

Ejemplo simplificado (mirá `core/models/sales.py` para ver el completo):

```python
from django.db import models

class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    document_number = models.CharField(max_length=50, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cliente'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
```

Cada `models.XField()` es una columna. Cuando corrés `manage.py migrate`,
Django lee esto y crea la tabla `core_customer` con esas columnas.

Después podés usar la clase para crear, leer, actualizar y borrar:

```python
# Crear
c = Customer.objects.create(
    first_name="Juan",
    last_name="Pérez",
    document_number="12345678",
)

# Leer todos
todos = Customer.objects.all()

# Filtrar
juanes = Customer.objects.filter(first_name="Juan")

# Uno solo
c = Customer.objects.get(document_number="12345678")

# Actualizar
c.phone = "0981-123456"
c.save()

# Borrar
c.delete()
```

---

## 6. Django ORM — el amigo tuyo

**ORM = Object Relational Mapper**. Es lo que traduce entre Python y SQL.

En vez de escribir:
```sql
SELECT * FROM core_customer WHERE first_name = 'Juan';
```

Escribís:
```python
Customer.objects.filter(first_name='Juan')
```

Django genera el SQL automáticamente. Más productivo y menos errores.

### Métodos comunes del ORM

```python
# Contar
Customer.objects.count()

# Existe alguno?
Customer.objects.filter(email__endswith='@gmail.com').exists()

# El primero / último
Customer.objects.first()
Customer.objects.last()

# Ordenar
Customer.objects.order_by('-created_at')    # descendente

# Limitar
Customer.objects.all()[:10]                  # primeros 10

# Filtros avanzados
Customer.objects.filter(created_at__year=2026)
Customer.objects.filter(email__icontains='gmail')    # contiene (case-insensitive)
Customer.objects.filter(document_number__startswith='12')

# Excluir
Customer.objects.exclude(email='')
```

### Joins (relaciones)

Si `Sale` tiene un FK a `Customer`, podés navegar:
```python
sale = Sale.objects.get(id=1)
print(sale.customer.first_name)   # navega al Customer

# Todas las ventas de un cliente
juan = Customer.objects.get(first_name='Juan')
sus_ventas = juan.sales.all()      # inversa (definida por related_name)
```

---

## 7. Views — el endpoint

Una **view** responde a una URL. En este proyecto usamos **DRF (Django
REST Framework)**, que estructura las views como **ViewSets**.

Ejemplo simplificado:

```python
from rest_framework import viewsets
from core.models import Customer
from core.serializers import CustomerSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
```

Con esas 3 líneas, Django REST Framework te crea automáticamente
todos los endpoints CRUD:
- `GET /api/customers/` — listar
- `GET /api/customers/42/` — uno solo
- `POST /api/customers/` — crear
- `PUT /api/customers/42/` — actualizar
- `DELETE /api/customers/42/` — borrar

### Actions custom

Para endpoints custom (no CRUD), agregás un `@action`:

```python
class SaleViewSet(viewsets.ModelViewSet):
    ...

    @action(detail=False, methods=['get'])
    def del_mes(self, request):
        """Devuelve solo las ventas del mes actual."""
        from datetime import date
        hoy = date.today()
        ventas = Sale.objects.filter(
            sale_date__year=hoy.year,
            sale_date__month=hoy.month,
        )
        serializer = self.get_serializer(ventas, many=True)
        return Response(serializer.data)
```

Eso crea el endpoint `GET /api/sales/del_mes/`.

---

## 8. URLs

En `playas_autos/urls.py`:

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
]
```

En `core/urls.py`:

```python
from rest_framework.routers import DefaultRouter
from core.views import CustomerViewSet, SaleViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'sales', SaleViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
```

Eso genera automáticamente las URLs de cada ViewSet.

---

## 9. El Django shell — tu mejor amigo

El **shell** es un REPL de Python donde ya está cargado el proyecto.
Súper útil para probar cosas.

Abrir:
```cmd
set DB_ENGINE=sqlite
set PYTHONUTF8=1
venv\Scripts\python.exe manage.py shell
```

Ejemplos de cosas que podés hacer ahí:

```python
from core.models import Customer, Sale

# Ver los primeros 5 clientes
for c in Customer.objects.all()[:5]:
    print(c.id, c.first_name, c.last_name)

# Contar ventas del último mes
from datetime import date, timedelta
hace_30 = date.today() - timedelta(days=30)
Sale.objects.filter(sale_date__gte=hace_30).count()

# Ver todos los ventas con monto > 50M
from django.db.models import Q
Sale.objects.filter(total_price__gt=50_000_000).count()
```

Cerrás con `exit()`.

---

## 10. Migrations — cambios en la BD

Cada vez que cambiás un modelo (agregás campo, cambiás tipo, etc.),
tenés que crear una **migration**:

```cmd
venv\Scripts\python.exe manage.py makemigrations
venv\Scripts\python.exe manage.py migrate
```

`makemigrations` genera un archivo Python que describe el cambio.
`migrate` lo aplica a la BD.

Las migrations están en `core/migrations/`. **Nunca las edites a
mano** — siempre generarlas con `makemigrations`.

---

## 11. El panel de admin

Django trae un panel de admin en `/admin`. Podés loguearte y ver /
modificar las tablas directamente.

Abrí http://localhost:8001/admin en el browser (con backend corriendo).
Login: usuario admin de tu seed sintético.

Es útil para inspeccionar datos rápido pero **no lo uses para modificar
datos importantes** — hay lógica de negocio que solo pasa por las views.

---

## Ejercicios (hacelos en el Django shell)

Abrí el shell y probá:

### Ejercicio 1
```python
# Cuántos clientes hay
from core.models import Customer
print(Customer.objects.count())
```

### Ejercicio 2
```python
# Los 3 clientes más recientes
recientes = Customer.objects.order_by('-created_at')[:3]
for c in recientes:
    print(c.first_name, c.last_name)
```

### Ejercicio 3
```python
# Crear un cliente nuevo (con datos ficticios)
from core.models import Customer, Enterprise
ent = Enterprise.objects.first()
c = Customer.objects.create(
    enterprise=ent,
    first_name="Pedro",
    last_name="Rojas",
    document_number="99999999",
    phone="0981-000-111",
)
print(f"Creado con id={c.id}")

# Después borralo
c.delete()
print("Borrado")
```

Si te salen los 3: entendiste lo básico.

---

## Recursos para profundizar

- **Django Girls Tutorial (español)**: https://tutorial.djangogirls.org/es/ (curso gratuito, 4-6 horas)
- **Django docs (inglés)**: https://docs.djangoproject.com/
- **DRF docs (inglés)**: https://www.django-rest-framework.org/

---

## Próximo paso

Abrí `04_REACT_INTRO.md` para aprender el frontend.
