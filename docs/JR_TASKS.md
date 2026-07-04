# Tareas Jr — onboarding progresivo

> Plan de 2-3 semanas para que el Jr aprenda el sistema con tareas
> chicas, **sin acceso a datos reales de la empresa**.
>
> Trabaja sobre una BD 100% sintética generada con Faker. Cuando
> termina una tarea, hace PR y el senior revisa.

---

## Filosofía

- **Tareas chicas** (1-4 horas cada una)
- **Aisladas**: cada una toca un solo lugar del código
- **Sin datos reales**: BD sintética con nombres inventados
- **Visibles**: el Jr puede ver el resultado en la UI
- **Acumulativas**: cada sprint construye sobre el anterior

Si el Jr ve más de 4 horas en una tarea, **escalá** — algo está mal
(falta contexto, hay un bug, la tarea es más grande de lo que pensábamos).

---

## Setup inicial (día 1, no es tarea)

1. Clonar repos `playa` y `playa-frontend`
2. Setup venv + dependencias (ver `ONBOARDING.md` parte 1)
3. **Generar BD sintética** (en vez de pedir la BD real):
   ```cmd
   set DB_ENGINE=sqlite
   set PYTHONUTF8=1
   venv\Scripts\python.exe manage.py migrate
   venv\Scripts\python.exe scripts\seed_synthetic.py
   ```
   Eso genera ~40 customers, 40 vehicles, 25 sales, 150 cuotas, 80 CMs
   **todos inventados con Faker**.
4. Login: `admin / admin123` (o `jr / demo1234`)
5. Leer `docs/DB_SCHEMA.md` (modelo de datos)

---

## SPRINT 1 — UI cosméticas (~1 semana)

Objetivo: aprender el código del frontend sin tocar lógica de negocio.

### T1.1 — Agregar tooltip al chip de estado en /vehicles
**Donde**: `src/pages/Vehicles.jsx` o componente Badge
**Qué**: cuando pasa el mouse sobre el chip "Disponible/Vendido/Reservado",
mostrar tooltip explicativo del estado
**Tiempo**: 2h
**Aprende**: estructura del frontend, componentes, eventos UI

### T1.2 — Skeleton loader en página vacía
**Donde**: alguna página donde al cargar muestra "Cargando..."
**Qué**: reemplazar el texto por skeleton boxes animados usando
el componente `Skeleton.jsx` existente
**Tiempo**: 2h
**Aprende**: estados de carga, reutilización de componentes

### T1.3 — Botón "↑ Volver arriba" cuando se hace scroll
**Donde**: agregar a Layout principal o al final de listados largos
**Qué**: botón flotante que aparece cuando se hace scroll > 500px,
click suaviza el scroll al top
**Tiempo**: 1h
**Aprende**: eventos scroll, posicionamiento fixed

### T1.4 — Empty state mejorado en /customers
**Donde**: `src/pages/Customers.jsx`
**Qué**: cuando no hay clientes (búsqueda sin resultados), mostrar
un ilustración + texto + botón "Crear cliente" en vez de tabla vacía
**Tiempo**: 2h
**Aprende**: componente EmptyState.jsx, condiciones de render

### T1.5 — Validación visual mejorada en formularios
**Donde**: cualquier formulario (Sales, Customers, Vehicles)
**Qué**: cuando un campo tiene error, agregar:
  - Borde rojo
  - Ícono de exclamación
  - Mensaje de error debajo del campo
**Tiempo**: 2h
**Aprende**: validación de formularios, estados de error

---

## SPRINT 2 — Pequeñas mejoras de UX (~1 semana)

Objetivo: agregar mini-features que mejoran la experiencia diaria.

### T2.1 — Botón "Copiar al portapapeles" en sale_number
**Donde**: lista de ventas (`/sales`) y detalle
**Qué**: al lado del sale_number, ícono 📋 que copia al portapapeles + toast "Copiado"
**Tiempo**: 2h
**Aprende**: clipboard API, componente Toast existente

### T2.2 — Atajo de teclado para crear nuevo
**Donde**: /vehicles, /sales, /customers
**Qué**: la tecla `N` abre el modal/página de "nuevo"
(respetando que no esté en un input)
**Tiempo**: 3h
**Aprende**: KeyboardShortcuts.jsx existente, event listeners globales

### T2.3 — Confirmación antes de cancelar venta
**Donde**: cambio de status de Sale a "cancelled"
**Qué**: modal "¿Seguro que querés cancelar esta venta? El vehículo
volverá a disponible y las cuotas quedarán inactivas"
**Tiempo**: 2h
**Aprende**: modal patterns, confirmaciones

### T2.4 — Formato de número en inputs de monto
**Donde**: todos los inputs de `Decimal` (precios, montos)
**Qué**: mostrar el monto con separador de miles mientras se escribe
("1.500.000" en lugar de "1500000")
**Tiempo**: 3h
**Aprende**: input controlado, transformación display vs valor

### T2.5 — Highlight de fila al hacer hover
**Donde**: tablas grandes (vehicles, sales, customers, cuotas)
**Qué**: cuando se hace hover en una fila, fondo gris claro + cursor pointer
**Tiempo**: 1h
**Aprende**: CSS hover states, accesibilidad

---

## SPRINT 3 — Backend chico (~1 semana)

Objetivo: tocar API y modelos en pequeñas iteraciones.

### T3.1 — Endpoint /api/health/ext (mejora del existente)
**Donde**: `core/views/base.py`
**Qué**: el `/health/` actual devuelve `{"status": "ok"}`. Ampliarlo
para devolver:
```json
{
  "status": "ok",
  "version": "1.0",
  "timestamp": "2026-06-08T...",
  "db_ok": true,
  "cache_ok": true
}
```
**Tiempo**: 2h
**Aprende**: views, DRF Response, datetime

### T3.2 — Filtro `?color=` en /api/vehicles/
**Donde**: `core/views/inventory.py` (VehicleViewSet)
**Qué**: agregar `?color=ROJO` que filtra por color exacto, case-insensitive
**Tiempo**: 2h
**Aprende**: filtering en DRF, query params

### T3.3 — Property `Customer.full_name` (si no existe ya)
**Donde**: `core/models/sales.py` (Customer)
**Qué**: agregar property que devuelve `"first_name last_name"` strippeado
+ tests unitarios para 3 casos (con apellido, sin apellido, con espacios)
**Tiempo**: 2h
**Aprende**: model properties, tests pytest/unittest

### T3.4 — Endpoint que devuelve cuotas por vencer próximos 7 días
**Donde**: `core/views/dashboard.py`
**Qué**: nuevo action `@action(detail=False, methods=['get'])` que
devuelve cuotas con `due_date` en los próximos 7 días, con cliente +
sale + monto
**Tiempo**: 4h
**Aprende**: DRF action, query optimización con `select_related`

### T3.5 — Tests para `Sale._sync_vehicle_state` hook
**Donde**: nuevo archivo `core/tests/test_sale_hooks.py`
**Qué**: 4 tests:
1. Cuando se crea Sale completed → vehicle.state = sold
2. Cuando se cambia Sale a cancelled → vehicle.state = available
3. Cuando hay 2 sales pending al mismo vehicle, cancelar 1 NO cambia state
4. Cuando se elimina Sale completada, vehicle vuelve a available si no hay otra
**Tiempo**: 4h
**Aprende**: Django test framework, fixtures, side effects de save()

---

## SPRINT 4 — Calidad y observabilidad (~1 semana)

Objetivo: bug fixing y mejoras de visibilidad.

### T4.1 — Documentar 1 endpoint del backend
**Qué**: elegí un endpoint complejo (ej. `/dashboard/summary/`) y agregale:
- Docstring detallado en la view
- Comentarios en la lógica no obvia
- Sección en `docs/API.md` (crear el archivo) con: params, response, ejemplos
**Tiempo**: 3h
**Aprende**: documentación técnica

### T4.2 — Agregar logging a operaciones críticas
**Qué**: en `Sale.delete()` y `Quotum._sync_cash_movement()`, agregar
logs con `logging.info(...)` que dejen rastro de qué pasó.
**Tiempo**: 2h
**Aprende**: módulo logging de Python, niveles

### T4.3 — Test de regresión para health_check.py
**Qué**: el script `health_check.py` tiene 27 chequeos. Escribir 1
test que asegura que, dado un fixture mínimo, `health_check` no tira
errores y devuelve la cantidad esperada de warnings.
**Tiempo**: 3h
**Aprende**: testing scripts, fixtures sintéticos

### T4.4 — Investigar bug reportado (sintético)
**Bug**: "Cuando creo una venta cancelled directamente (sin pasar por
completed primero), el vehículo queda en `state=reserved` en vez de
`available`"
**Qué**: reproducir, identificar la línea, proponer fix con test.
**Tiempo**: 3h
**Aprende**: debugging, lectura de stack trace, propuesta de PR

---

## SPRINT 5 — Frontend feature mediana (~1 semana, al final del onboarding)

### T5.1 — Página "Mis cuotas a cobrar hoy"
**Donde**: nueva página `/cobrar-hoy` en frontend
**Qué**:
- Lista las cuotas que vencen HOY o están vencidas hace ≤ 7 días
- Por cada una: cliente (anónimo en BD sintética), sale_number, monto, botón "Marcar pagada"
- Filtro por sucursal arriba
- Bonus: chips de estado (vencida hoy / vencida 1-7 días / por vencer)
**Tiempo**: 6-8h
**Aprende**: full feature E2E (página + ruta + endpoint si hace falta + componentes)

---

## Cómo trabajar cada tarea

1. **Crear branch**: `git checkout -b jr/T1.1-tooltip-vehicles` (usar el código de la tarea)
2. **Hacer el cambio en chiquito**: empezar simple, después agregar polish
3. **Probar local**: navegá la UI y validá el comportamiento
4. **Commit**: `git commit -m "T1.1: tooltip en chip de estado de vehiculos"`
5. **Push + PR a `staging`**:
   ```
   git push origin jr/T1.1-tooltip-vehicles
   ```
6. **Anotá en una planilla**: tiempo real vs estimado, dudas, decisiones
7. **Senior review**: comentarios en el PR, iterar hasta merge

---

## Métricas que vamos a llevar

| Sprint | # Tareas | % completadas | Tiempo promedio | Reviews por PR |
|---|---|---|---|---|
| 1 | 5 | | | |
| 2 | 5 | | | |
| 3 | 5 | | | |
| 4 | 4 | | | |
| 5 | 1 | | | |

---

## Si te quedás trabado en una tarea

1. Re-leer el enunciado completo
2. Buscar componentes/utils existentes (`grep` en el código)
3. Mirar `docs/DB_SCHEMA.md` si la duda es de modelo
4. Anotar la duda concreta en `docs/decisiones_pendientes.md`
5. Avisar al senior

Regla: si llevás 30 minutos sin avanzar, escalá.

---

## Qué NO se hace en estas tareas (alcance)

❌ Tocar datos reales de la empresa
❌ Modificar lógica de pricing o impuestos
❌ Cambiar el schema de la BD sin discusión
❌ Hacer pushes a `main` (siempre a `staging` + PR)
❌ Borrar datos sin entender qué relación tienen

---

*Versión 1.0 — actualizar cuando aparezcan tareas nuevas.*
