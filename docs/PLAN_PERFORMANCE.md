# Plan de optimización de performance APIs

## Diagnóstico

**Causa raíz de la lentitud:**
- Latencia Paraguay ↔ Supabase São Paulo: ~50-100ms por roundtrip
- Cada listado de Django hace 1 query principal + N queries por relación (N+1)
- Dashboard ejecuta 8-10 endpoints en paralelo al cargar, cada uno con su propio set de queries
- Sin índices: full table scans en filtros por fecha, status, branch

**Meta:** llevar el tiempo p50 del Dashboard de >10s a <2s, sin pagar por mejor hosting ni mover Supabase.

---

## Fase 1 — Wins inmediatos (≤2 horas, ~80% del impacto)

### 1.1. Índices de base de datos

Las queries más frecuentes filtran/ordenan por estas columnas. PostgreSQL los crea online (sin downtime):

| Tabla | Columna(s) | Por qué |
|---|---|---|
| core_sale | `sale_date` | Dashboard agrupa ventas por mes / filtra por rango |
| core_sale | `branch_id, status` | Listado de ventas filtrado por sucursal |
| core_sale | `enterprise_id` | Multi-tenant: cada query lo usa |
| core_quotum | `due_date` | "Próximas a vencer" / aging |
| core_quotum | `payment_date` | "Cobradas este mes" |
| core_quotum | `status, sale_id` | "Pendientes por venta" |
| core_quotum | `enterprise_id` | Multi-tenant |
| core_vehicle | `branch_id, state` | Stock por sucursal disponible |
| core_vehicle | `vin` | Búsqueda exacta por chasis |
| core_customer | `(first_name, last_name)` GIN | Búsqueda fuzzy de clientes |

**Implementación:** ver `scripts/migracion/create_indexes.py` más abajo.

### 1.2. `select_related` en todos los listados (ya parcialmente hecho)

Falta agregar en:
- `CustomerViewSet` (si lista con datos de ventas/cuotas relacionadas)
- Cualquier action custom que itere y use FKs

### 1.3. Limitar campos en listados

Los listados de Vehicles/Sales/Quotas no necesitan traer `notes`, `description`, `image` (campos largos). Usar `.only()` o un serializer "list" que excluya esos campos:

```python
# Antes
vehicles = Vehicle.objects.all()
# Después
vehicles = Vehicle.objects.only(
    'id', 'vin', 'year', 'color', 'price', 'state',
    'brand_id', 'model_id', 'branch_id'
).select_related('brand', 'model', 'branch')
```

Ahorro: típicamente 30-50% del payload de cada response.

---

## Fase 2 — Endpoints sin paginar (≤2 horas)

Identificá los que devuelven listas completas sin `?page=`:

- `GET /vehicles/available/` — devuelve TODOS los disponibles (~400 filas)
- `GET /quotas/pending/` — TODAS las pendientes
- `GET /quotas/overdue/` — TODAS las vencidas
- `GET /brands/`, `/vehicle-models/`, `/payment-forms/` (esos son chicos, está OK)

**Acciones:**
1. Para listados largos (`available`, `pending`, `overdue`): forzar paginación o aceptar `?limit=` con default razonable (50).
2. Permitir traer solo el `count` cuando el frontend solo necesita el badge:
   ```python
   if request.query_params.get('count_only') == '1':
       return Response({'count': queryset.count()})
   ```
3. Frontend: cuando solo se necesita el count para mostrar un número, pedir con `count_only=1`.

---

## Fase 3 — Cache de dashboard (≤2 horas)

Los endpoints del dashboard son **agregaciones que cambian lento** (sales_by_month, top_morosos, etc). Cache de 60-120s reduce 95% del tráfico repetido.

Django ya tiene `LocMemCache` configurada por default. Solo agregar el decorador a cada action:

```python
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

@method_decorator(vary_on_headers('Authorization'), name='dispatch')
class DashboardViewSet(viewsets.ViewSet):
    ...

    @method_decorator(cache_page(60))  # 60s
    @action(detail=False, methods=['get'])
    def summary(self, request):
        ...
```

**Importante:** `vary_on_headers('Authorization')` hace que el cache sea por-usuario, no global. Sin eso, un admin vería datos cacheados de otro tenant.

**TTL sugeridos:**
- `summary`, `inventory_stats`, `quotas_status`: 60s
- `sales_by_month`, `sales_by_branch`, `vehicle_models_ranking`: 300s (5 min)
- `aging_cuotas`, `top_morosos`: 300s
- `alertas`: 120s

---

## Fase 4 — Medición y ajuste fino (continuo)

### 4.1. Activar logging de queries lentas

En `settings.py` para entorno dev:

```python
if DEBUG:
    LOGGING['loggers'] = {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['file'],
        },
    }
```

Hace que cada query SQL aparezca en `logs/django.log` con su tiempo. Buscar las que pasen 200ms y ver cuántas se ejecutan por request.

### 4.2. Middleware de timing por request

Agregar un middleware simple que loguee qué endpoint tardó cuánto, así sabés cuáles atacar:

```python
class TimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        import time, logging
        t0 = time.perf_counter()
        response = self.get_response(request)
        dt = (time.perf_counter() - t0) * 1000
        if dt > 500:  # log solo lo que tarde >500ms
            logging.getLogger('perf').warning(
                f"SLOW {request.method} {request.path} {dt:.0f}ms"
            )
        return response
```

### 4.3. `EXPLAIN ANALYZE` en queries problemáticas

Cuando identifiquemos una query lenta puntual, podemos correrla con `EXPLAIN ANALYZE` para ver si está usando los índices.

---

## Fase 5 — Frontend (≤1 hora)

El frontend también ayuda:

1. **No pedir todo al cargar el dashboard** — algunos endpoints (top_morosos, aging) pueden cargarse después en lazy load cuando el usuario scrollea hasta esa sección.
2. **Debounce en filtros** — si hay búsquedas que disparan request por cada tecla, agregar `setTimeout` de 300ms.
3. **Cancelar requests en flight** cuando el usuario cambia de página — `AbortController` en axios.

---

## Roadmap de implementación (sugerido)

| Fase | Tiempo | Impacto esperado |
|---|---|---|
| 1.1 Índices | 30 min | Cada query filtrada baja de 200ms a 20ms |
| 1.2 select_related (en curso) | 30 min | -70% queries por listado |
| 1.3 `.only()` en listados | 30 min | -30% bytes por response |
| 2. Paginación faltante | 1h | -80% en `available`, `pending`, `overdue` |
| 3. Cache dashboard | 1h | Dashboard pasa de 10 queries a 1-2 |
| 4. Logging | 30 min | Visibilidad para iterar |
| 5. Frontend lazy | 1h | Carga inicial -50% |

**Total estimado:** ~5 horas de trabajo concentrado.

---

## Después de todo esto, si todavía es lento

- **Mover el backend a una región cercana a São Paulo** (Render → São Paulo si lo soportan, o AWS sa-east-1). Esto solo paga 50-100ms de RTT por request.
- **Plan pago de Supabase** ($25/mes) — connection pooler con más capacidad, mejor I/O.
- **Migrar a una BD local o más cercana** — opciones: PostgreSQL en Render (mismo data center que el backend), Neon en sa-east-1, Railway en Sao Paulo.

Pero antes de pagar, agotamos lo gratis.
