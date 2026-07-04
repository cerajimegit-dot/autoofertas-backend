# 🗂 Estructura del proyecto — recorrido guiado

> Ahora que sabés Python, Django, React y Git básico, es hora de
> explorar el proyecto real. Este archivo es un **tour por las
> carpetas y archivos** que vas a tocar.

---

## 1. Los 2 repos

Hay 2 carpetas separadas, cada una es un repo de Git independiente:

```
playa/            <- backend Django (Python)
playa-frontend/   <- frontend React (JavaScript/JSX)
```

Los levantás por separado (backend en :8001, frontend en :3000) y
se comunican por HTTP.

---

## 2. Backend — `playa/`

```
playa/
│
├── manage.py                <- ⭐ punto de entrada de Django
├── requirements.txt         <- paquetes Python del proyecto
├── .env.example             <- config de ejemplo (copiar como .env)
├── db.sqlite3               <- BD local (generada, no en Git)
├── venv/                    <- ambiente Python (generado, no en Git)
│
├── playas_autos/            <- config del proyecto
│   ├── settings.py            (config general: BD, apps, seguridad)
│   ├── urls.py                (rutas top-level: /admin, /api, /docs)
│   ├── wsgi.py                (para deploy en Render)
│   └── asgi.py                (para deploy async)
│
├── core/                    <- ⭐⭐⭐ el corazón del sistema
│   ├── models/                <- las tablas de la BD
│   │   ├── base.py            (Enterprise, Branch, CustomUser, AuditLog)
│   │   ├── inventory.py       (Brand, VehicleModel, Vehicle, ExchangeRate)
│   │   ├── sales.py           (Customer, PaymentForm, Sale, Quotum)
│   │   └── cash.py            (CashMovement)
│   │
│   ├── views/                 <- endpoints de la API
│   │   ├── base.py            (login, users, health)
│   │   ├── inventory.py       (vehicles, brands, models)
│   │   ├── sales.py           (sales, customers, quotas)
│   │   ├── cash.py            (movimientos de caja)
│   │   └── dashboard.py       (KPIs y reportes)
│   │
│   ├── serializers/           <- conversión Python ↔ JSON
│   │   ├── base.py
│   │   ├── inventory.py
│   │   ├── sales.py
│   │   └── cash.py
│   │
│   ├── migrations/            <- historial de cambios en la BD
│   │   ├── 0001_initial.py    (migración inicial)
│   │   ├── 0002_...py         (cada cambio subsecuente)
│   │   └── ...
│   │
│   ├── urls.py                <- rutas del app: /api/customers, /api/sales, ...
│   ├── admin.py               <- config del panel /admin
│   ├── permissions.py         <- políticas de acceso
│   ├── pagination.py          <- paginación de listados
│   └── middleware.py          <- middlewares custom
│
├── scripts/                 <- utilidades (no parte de Django runtime)
│   ├── seed_synthetic.py      (genera datos ficticios — ⭐ el que vos usás)
│   ├── health_check.py        (27 chequeos de integridad)
│   ├── apply_flujo_caja.py    (procesa archivos .ods)
│   ├── run_local.bat          (levanta backend con SQLite)
│   └── ... (~40 scripts más para casos específicos)
│
├── docs/                    <- documentación
│   ├── aprender/              (⭐ acá estás vos)
│   ├── ONBOARDING_JR.md
│   ├── DB_SCHEMA.md
│   ├── JR_TASKS.md
│   └── ...
│
└── ui/                      <- app secundaria para el /admin custom
```

### Archivos que vas a abrir MUCHO

| Archivo | Cuándo |
|---|---|
| `core/models/sales.py` | Para entender clientes/ventas/cuotas |
| `core/views/dashboard.py` | Para ver cómo se calculan los KPIs |
| `core/urls.py` | Para saber qué endpoints existen |
| `playas_autos/settings.py` | Para config global (raro tocarlo) |

---

## 3. Frontend — `playa-frontend/`

```
playa-frontend/
│
├── index.html               <- ⭐ HTML principal — carga TODO
├── config.js                <- URL del backend
├── server.py                <- servidor HTTP local (puerto 3000)
├── run-frontend.bat         <- levanta el frontend
│
└── src/
    ├── App.jsx              <- ⭐ router principal
    │
    ├── pages/               <- las 12+ páginas de la app
    │   ├── Login.jsx
    │   ├── Dashboard.jsx      (KPIs y paneles)
    │   ├── Sales.jsx          (listado y crear venta)
    │   ├── Vehicles.jsx       (inventario)
    │   ├── Customers.jsx      (clientes)
    │   ├── CustomerDetail.jsx (ficha de cliente)
    │   ├── Quotas.jsx         (cuotas)
    │   ├── Cash.jsx           (flujo de caja)
    │   ├── Users.jsx          (usuarios del sistema)
    │   └── AuditLogs.jsx      (visor de auditoría)
    │
    ├── components/          <- reutilizables
    │   ├── Card.jsx
    │   ├── Button.jsx
    │   ├── Badge.jsx
    │   ├── FormField.jsx
    │   ├── Skeleton.jsx
    │   ├── EmptyState.jsx
    │   ├── Toast.jsx
    │   ├── ResponsiveTable.jsx
    │   ├── Navbar.jsx
    │   ├── Sidebar.jsx
    │   └── KeyboardShortcuts.jsx (palette global Ctrl+K)
    │
    ├── context/             <- estado global
    │   ├── AuthContext.jsx    (usuario logueado, tokens)
    │   └── BranchContext.jsx  (sucursal seleccionada)
    │
    └── utils/               <- helpers
        ├── api.js             (⭐ cliente axios con auth)
        ├── auth.js            (helpers de login/logout)
        ├── storage.js         (localStorage helpers)
        ├── format.js          (formatear números, fechas)
        └── printSchedule.js   (PDF de cronograma)
```

### Archivos que vas a abrir MUCHO

| Archivo | Cuándo |
|---|---|
| `src/utils/api.js` | Para saber cómo llamar al backend |
| `src/pages/Dashboard.jsx` | Ejemplo grande de página |
| `src/components/Button.jsx` | Ejemplo de componente reutilizable |
| `index.html` | Para agregar nuevos JSX a la carga |

---

## 4. Ejercicio guiado — recorrer un flujo

Vamos a rastrear qué pasa cuando **listás clientes en la UI**.

### Paso 1 — Frontend hace la request
Abrí `playa-frontend/src/pages/Customers.jsx`.
Buscá dónde llama a `api.get('/customers/')`.

Es algo así:
```jsx
useEffect(() => {
    api.get('/customers/').then(res => setCustomers(res.data.results));
}, []);
```

### Paso 2 — El cliente axios
Abrí `playa-frontend/src/utils/api.js`.
Vas a ver que `api` es un axios configurado con:
- Base URL de `window.API_BASE_URL` (definido en `config.js`)
- Header `Authorization: Bearer <token>`

Entonces la request final es:
```
GET http://localhost:8001/api/customers/
Authorization: Bearer eyJ0eXA...
```

### Paso 3 — Django recibe
Abrí `playa/playas_autos/urls.py`. Vas a ver:
```python
path('api/', include('core.urls')),
```

Así que `/api/customers/` se resuelve mirando `core/urls.py`.

### Paso 4 — El router
Abrí `playa/core/urls.py`. Vas a ver:
```python
router.register(r'customers', CustomerViewSet, basename='customer')
```

Eso mapea `/customers/` al `CustomerViewSet`.

### Paso 5 — El ViewSet
Abrí `playa/core/views/sales.py`. Buscá `class CustomerViewSet`. Vas
a ver algo como:
```python
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    ...
```

Cuando llega `GET /customers/`, DRF llama al método `list()` que:
1. Ejecuta `Customer.objects.all()`
2. Serializa cada Customer a JSON usando `CustomerSerializer`
3. Devuelve la respuesta

### Paso 6 — El serializer
Abrí `playa/core/serializers/sales.py`. Buscá `class CustomerSerializer`.
Define qué campos incluir en el JSON.

### Paso 7 — La BD
`Customer.objects.all()` genera un SQL:
```sql
SELECT id, first_name, last_name, ... FROM core_customer;
```

Django lo ejecuta contra SQLite (local) o Postgres (prod), lee las
filas, y crea instancias de `Customer` en memoria.

### Paso 8 — Vuelve al frontend
El JSON llega al frontend. `setCustomers(res.data.results)` actualiza
el estado. React re-renderiza la página con los clientes.

---

## 5. Herramientas útiles

### Ver todos los endpoints disponibles
Con el backend corriendo, abrí:
```
http://localhost:8001/api/docs/
```

Ves la documentación auto-generada (Swagger).

### Django Debug Toolbar
Si `DEBUG=True` en `.env`, aparece una barra en el browser con info
de queries SQL, tiempos, etc.

### Panel de admin
```
http://localhost:8001/admin/
```

Login con `admin` / la password de tu seed. Podés inspeccionar tablas
directamente.

---

## 6. Ejercicio final — mapeás qué archivo tocarías para...

Sin abrir los archivos aún, respondé:

**a)** Agregar un campo `favorite_color` a Customer.
- Model: `___________________________`
- Serializer: `_______________________`
- Migration: `_______________________`

**b)** Crear un endpoint `/api/vehicles/populares/` que devuelva los 5
vehículos más vendidos.
- View: `___________________________`
- URL: `_____________________________`

**c)** Cambiar el color del botón "Guardar" en el formulario de venta.
- Componente: `_______________________`
- Archivo del form: `_________________`

### Respuestas
- a) `core/models/sales.py`, `core/serializers/sales.py`, `core/migrations/00XX_add_favorite_color.py` (generado con `makemigrations`)
- b) `core/views/inventory.py` (nuevo `@action`), no hace falta editar URL (viene automático del ViewSet)
- c) `src/components/Button.jsx` para el estilo global; `src/pages/Sales.jsx` para el form específico

Si acertaste 2/3, entendiste la estructura. Si acertaste 1/3, releé
las secciones 2 y 3.

---

## 7. Convenciones de código

### Python (backend)
- **4 espacios** (no tabs) para indentación
- Nombres de clases: `PascalCase` (`Customer`, `SaleViewSet`)
- Nombres de funciones/variables: `snake_case` (`get_current_month`)
- Constantes: `SCREAMING_SNAKE_CASE` (`MAX_ATTEMPTS`)
- Imports al inicio del archivo, agrupados

### JavaScript / JSX (frontend)
- **4 espacios**
- Nombres de componentes: `PascalCase` (`Card`, `CustomerDetail`)
- Nombres de funciones/variables: `camelCase` (`handleClick`, `userName`)
- Usar `const` por default, `let` si va a cambiar, **nunca `var`**
- Prefer arrow functions: `() => { ... }`

---

## Próximo paso

Abrí `07_RECURSOS_EXTERNOS.md`.
