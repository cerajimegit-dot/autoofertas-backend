# Diagnóstico UX y adopción — Playas de Autos / AUTO OFERTAS

Fecha del diagnóstico: 2026-05-12
Base de análisis: código en `playa/` y `playa-frontend/` + snapshot de
`db.sqlite3` con 298 clientes, 427 ventas, 3044 cuotas, 624 vehículos.

---

## 1. Resumen ejecutivo

El sistema está **funcionalmente cerca**, pero **no listo para que `papa`
lo abra el lunes y reemplace el Excel**. Hay 4 cosas que van a romper la
confianza el primer día y que, juntas, justifican una semana más de
trabajo antes del lanzamiento:

1. **Datos sucios visibles**: 183/427 ventas (43%) aparecen con
   "⚠ Sin cliente", incluidas todas las MC de 2026 de SUCURSAL 1
   (MC02/26 a MC30/26). 142 ventas con código MIG aparecen mezcladas con
   las reales. 67 clientes tienen documento `DRV026-xxxx`/`SUC026-xxxx`
   y 68 emails sintéticos `@import.local`.
2. **Funcionalidades clave rotas**: el botón **💬 WhatsApp** falla
   con 405 (frontend hace GET, backend espera POST); el filtro
   **Cuotas → Vencidas** muestra 62 cuotas cuando hay 970 vencidas
   "de facto"; el **selector de sucursal del navbar no afecta el
   dashboard**.
3. **Trazabilidad inexistente**: las 427 ventas tienen `seller_id=NULL`,
   no hay forma de saber quién vendió qué. El `mark_as_paid` no pide
   forma de pago (EF/TB/CJ/AC) ni fecha real — siempre marca "pagada
   hoy". El audit log graba `object_id=0` siempre.
4. **Seguridad rota**: cualquier vendedor autenticado puede, vía API
   directa, editar/desactivar/listar usuarios (incluido `papa`),
   porque `CustomUserViewSet` sólo valida `IsAuthenticated`. El
   frontend oculta el menú pero el backend no protege.

Hay además ~30 fricciones menores (copys gringos, `alert()` nativos,
falta de "+ Nuevo cliente" en /customers, etc.) que se pueden arreglar
en quick wins de 10-30 min cada uno.

---

## 2. Top 10 problemas priorizados

| # | Problema | Dónde | Severidad | Esfuerzo | Quién lo nota |
|---|---|---|---|---|---|
| 1 | Selector de sucursal del Navbar no filtra el dashboard | [Dashboard.jsx:53-72](../../playa-frontend/src/pages/Dashboard.jsx) + [dashboard.py:77-84](../core/views/dashboard.py) | **Alta** | M | papa, marcelo, mati |
| 2 | Filtro "Vencidas" en Cuotas muestra 62 en vez de ~970 reales | [Quotas.jsx:22-24](../../playa-frontend/src/pages/Quotas.jsx) + estado `overdue` vs `pending` con `due_date<today` | **Alta** | S | rocio, papa |
| 3 | Cualquier usuario puede tocar el endpoint /users/ | [base.py:23](../core/views/base.py) `permission_classes = [IsAuthenticated]` | **Alta** | S | (mati podría borrar/desactivar a papa) |
| 4 | Botón WhatsApp tira 405 — frontend GET, backend POST | [api.js:133-134](../../playa-frontend/src/utils/api.js) + [sales.py:273](../core/views/sales.py) | **Alta** | S | rocio (todos los días) |
| 5 | `mark_as_paid` no pide forma de pago, fecha, monto ni comprobante | [sales.py:262-271](../core/views/sales.py) — pone `payment_date=today` siempre; modelo Quotum no tiene `payment_form` | **Alta** | L | rocio (cada cobranza), papa (auditoría) |
| 6 | 183 ventas (43%) sin cliente — incluye **todas las MC/26 de SUC1** | [DB] `core_sale.customer_id IS NULL` | **Alta** | M | papa al primer reporte de morosos |
| 7 | `perform_create` ignora la sucursal seleccionada y siempre cae en `branches_managed.first()` o la primera de la empresa | [sales.py:97-99](../core/views/sales.py), [inventory.py:153-156](../core/views/inventory.py) | **Alta** | S | marcelo cargando una venta de SUC1 y viéndola en CASA CENTRAL |
| 8 | 427/427 ventas con `seller_id=NULL` → "ventas de Marcelo este mes" no existe | DB + no hay UI de filtro | **Alta** | M (backfill por sucursal + agregar filtro en UI) | papa cuando pida ranking de vendedores |
| 9 | 142 ventas MIGxxx mezcladas con las reales en /sales, sin diferenciación visual ni filtro "ocultar MIGs" | [Sales.jsx:262-317](../../playa-frontend/src/pages/Sales.jsx) | Media | S | papa, rocio |
| 10 | 1372/3044 cuotas con `plan_name=""`; en `/quotas` se muestra `plan_name` como columna principal y no `sale_number` | [Quotas.jsx:111](../../playa-frontend/src/pages/Quotas.jsx) | Media | S | rocio buscando "cuota de Bogado" |

### Detalle y propuesta de fix

**#1 Sucursal no filtra dashboard.** El usuario asume que el selector global
filtra todo. El backend acepta `?branch=` en las vistas de ventas/cuotas/vehículos,
pero `DashboardViewSet` no lee `branch` en NINGUNO de sus 10 endpoints. Fix:
agregar `branch_id = self.request.query_params.get('branch')` a
`_parse_period` (o helper similar) y aplicarlo en cada queryset.
Mientras tanto, agregar texto visible en el header del dashboard:
"Mostrando todas las sucursales" (ya que el filtro no funciona).

**#2 Cuotas vencidas escondidas.** El estado `overdue` no se calcula en
runtime: hay 62 filas con `status='overdue'` pero 970 con
`status='pending' AND due_date < today`. El dashboard usa la fórmula
correcta; la página `/quotas` con filtro "Vencidas" envía `status=overdue`
literal → solo trae 62. Fix dirigido: en
[Quotas.jsx:23](../../playa-frontend/src/pages/Quotas.jsx), cuando
`filterStatus==='overdue'`, llamar al endpoint `/quotas/overdue/`
(ya existe en [sales.py:209-220](../core/views/sales.py)) en vez de
mandar `status=overdue` al list.

**#3 Permisos de usuarios.** `CustomUserViewSet.permission_classes = [IsAuthenticated]`
significa que `mati` (vendedor) puede hacer `PATCH /api/users/8/` con
`{"role":"admin"}` y promoverse, o `{"is_active":false}` y desactivar
a `papa`. Hay un `if request.user.role != 'admin': raise status.HTTP_403_FORBIDDEN(...)`
en `perform_create` pero **es un bug** (intenta llamar a un int como
función → TypeError → 500 en lugar de 403). Fix: cambiar a
`permission_classes = [IsAuthenticated, IsAdmin]` para `update/partial_update/destroy/list`
o usar `get_permissions` por action.

**#4 WhatsApp roto.** El frontend ([api.js:133](../../playa-frontend/src/utils/api.js))
hace `api.get('/quotas/{id}/contact_whatsapp/')` pero el decorador es
`@action(detail=True, methods=['post'])` ([sales.py:273](../core/views/sales.py)).
Tira 405. Fix: cambiar a `methods=['get', 'post']` (o sólo `get`) en
el backend — la operación es idempotente. Bonus: el método actual
devuelve `whatsapp_link` mientras el front lee `whatsapp_url`
([Quotas.jsx:47](../../playa-frontend/src/pages/Quotas.jsx)) — incluso
si arreglás el verbo, el link sigue sin abrir. **Doble bug, pasa
silencioso porque nadie lo probó.**

**#5 `mark_as_paid` sin contexto.** El usuario maneja EF/TB/CJ/AC.
El modelo `Quotum` no tiene campo `payment_form`. La acción setea
`payment_date=datetime.now().date()` y nada más
([sales.py:267-268](../core/views/sales.py)). Resultado: imposible
backdatar un cobro recibido ayer, imposible saber si la cuota se cobró
en efectivo o por TB, no se puede adjuntar un comprobante. Fix mínimo
viable: agregar `payment_form` (FK a PaymentForm) y `paid_amount` al
modelo + leer `payment_date` y `payment_form` del body en
`mark_as_paid`, con default a hoy/efectivo. En el frontend, abrir un
modalcito con esos 3 campos antes de POST.

**#6 Ventas sin cliente.** 183 de 427. **Críticamente**, las 24
ventas más recientes de SUCURSAL 1 (MC02/26 hasta MC30/26, **enero a
abril 2026**) están sin cliente, lo que las invisibiliza en cualquier
reporte por cliente. Fix combinado: (a) por script, intentar matchear
contra el ODS de cobranza por monto+fecha o por sale_number original;
(b) por UI, agregar un filtro en /sales tipo "Solo ventas sin cliente"
(o chip "⚠ Pendientes de completar"), para que rocio pueda atacarlas
en lote.

**#7 Branch ignorada al crear.** Si `marcelo` está mirando SUCURSAL 1
en el navbar y carga `MC42/26`, la venta cae en CASA CENTRAL porque
`marcelo` (rol vendor) no está en `branches_managed`. Fix: leer
`request.data.get('branch')` o `request.query_params.get('branch')`
y respetarlo, validando que está en `branches_visible` del usuario.

**#8 Sin seller_id.** Todas las 427 son `seller_id=NULL`. No hay forma
de filtrar por vendedor en /sales tampoco. Fix corto: backfill por
sucursal (CC → seller `marcelo` o `mati`; S1 → seller responsable
correspondiente — preguntar al usuario). Fix medio: agregar dropdown
"Vendedor" al modal de Nueva Venta (default = usuario actual si rol
'vendor'), y filtro `seller` en `/sales`. Dashboard: agregar bloque
"Ventas del período por vendedor".

**#9 MIGs mezclados.** 142 ventas con código `MIGNNNNNN` aparecen
intercaladas en /sales. Hay un export Excel ("📥 Exportar MIGs a Excel"
[Sales.jsx:230](../../playa-frontend/src/pages/Sales.jsx)) pero ningún
filtro UI. Fix: chip "Solo MIGs / Solo reales / Todas" en el header de
/sales y un badge `🟡 MIG` en la columna Número.

**#10 plan_name vacío.** El listado de /quotas tiene como primera
columna `plan_name`; el 45% está vacío. Para rocio "¿de qué venta es
esta cuota?" no hay respuesta. Fix: reemplazar columna por
`sale_number` (link a Sales modal). Bonus: agregar buscador por nombre
de cliente y filtro por sucursal en /quotas (hoy solo hay
Pendientes/Vencidas).

---

## 3. Fricción por persona

### papa (60+, viene de Excel + papel)

1. **No puede confiar en el dashboard mientras los datos estén sucios.**
   La cartera vencida sale exagerada (970 cuotas pendientes con
   `due_date<today`, incluye 6 cuotas con `due_date=2021` por typos de
   migración), las "Ventas del período" excluyen MIG pero no excluyen
   "MC??/25", y el ratio de morosidad va a leerse como
   "casi todo está vencido" durante días hasta que se limpie.
2. **No hay vista por cliente ni por vendedor.** Si papa quiere
   "ver todas las cuotas pagadas de Mario Bogado", la única forma es
   abrir /quotas (sin filtro por cliente), bajar 3000 filas y leer.
   En Excel lo hacía con Ctrl+F. Acá *retrocede*.
3. **El Login dice "API en: http://localhost:8001"** y "Credenciales
   de demostración: admin / admin123" cargado por defecto
   ([Login.jsx:101-103, 110](../../playa-frontend/src/pages/Login.jsx)).
   Para un dueño que va a ver la pantalla por primera vez, esto se lee
   como producto a medio terminar. Eliminar para producción.

### mati / marcelo (vendedores, día a día)

1. **Crear una venta a crédito con 24 cuotas + 2 refuerzos toma
   muchos clicks dentro de modales anidados.** Flujo: Sales → +Nueva
   venta (modal 1) → +Crear cliente (modal 2 dentro de 1) → cerrar
   modal 2 → +Crear vehículo (modal 2bis) → +Crear marca (modal 3) →
   ... → Guardar. Después se abre AUTOMÁTICAMENTE el modal de edición
   ([Sales.jsx:469-473](../../playa-frontend/src/pages/Sales.jsx)),
   y desde ahí hay que ir al modal de cuotas para generar el plan.
   Son ~30 clicks por venta a crédito. El generador de cuotas tampoco
   tiene "refuerzo cada 12 cuotas con monto X" — hay que editar fila
   por fila a mano. Refuerzos están solo como nota libre.
2. **El selector de sucursal no se respeta al crear.** marcelo en S1
   carga `MC42/26` y queda en CASA CENTRAL (ver #7). Cuando se dé cuenta
   va a desconfiar de TODO el sistema.
3. **No hay autosave.** Si marcelo está cargando una venta de
   60.000.000 Gs. con 24 cuotas, llena la mitad y se le cae el wifi
   en el showroom, pierde todo. Los modales no persisten estado en
   localStorage. Sumado a los `LocMemCache` que pueden bloquear, es
   territorio inseguro.

### rocio (admin/secretaria, registra ventas y cobranzas)

1. **Cobrar una cuota es destructivo y sin contexto.** Click en "✓ Pagar"
   en [Quotas.jsx:127](../../playa-frontend/src/pages/Quotas.jsx)
   → marca como pagada con fecha = hoy, **sin confirmación**, sin
   forma de pago, sin monto. Si recibió por TB la semana pasada, no
   tiene cómo registrarlo bien. Si se equivocó de fila — no hay undo,
   tiene que abrir Sales → cuotas → editar manualmente status a
   `pending`.
2. **No puede crear ni editar clientes desde /customers.** La página
   es read-only. Para corregir un `DRV026-0001` rocio tiene que: abrir
   /sales → buscar la venta → abrir edición → "+ Crear" un cliente
   nuevo → reasignar → guardar. El cliente viejo queda zombie con su
   documento basura. Lo mismo en /vehicles para corregir stock.
3. **El WhatsApp link no funciona** (ver #4) y, aunque funcionara,
   142/298 clientes (47.6%) no tienen teléfono. Cuando lo tienen,
   el mensaje sale en formato gringo: `"Recordatorio: Cuota #3 con
   vencimiento el 2026-05-15. Monto: 1500000"` — sin "Sr.", sin saludo,
   sin Gs., con fecha ISO ([sales.py:285](../core/views/sales.py)).

---

## 4. Quick wins (≤30 min cada uno)

1. **Sacar las credenciales demo y la URL técnica del Login.**
   [Login.jsx:99-111](../../playa-frontend/src/pages/Login.jsx).
2. **Cambiar `$` por `Gs.` en el VehicleSearchSelect.**
   [Sales.jsx:1493](../../playa-frontend/src/pages/Sales.jsx) usa
   `' · $' + formatMoney(v.price)` — debería ser `formatGs(v.price)`.
3. **Reemplazar `alert(...)` por toasts.**
   [Quotas.jsx:38,40,51](../../playa-frontend/src/pages/Quotas.jsx) y
   [Users.jsx:58,274](../../playa-frontend/src/pages/Users.jsx). Toast
   ya existe vía `useToast()`.
4. **Confirmar antes de "✓ Pagar".** Modal de confirmación tipo
   "¿Marcar cuota N de venta CMxx como pagada hoy? Esta acción
   afecta el reporte de cobranzas." con botón "Sí, registrar pago" /
   "Cancelar". Atajo: en [Quotas.jsx:127](../../playa-frontend/src/pages/Quotas.jsx)
   envolver `markAsPaid` en un `window.confirm` mientras se arma el
   modal definitivo (ver Plan §7).
5. **Cambiar columna `plan_name` por `sale_number` en /quotas.**
   [Quotas.jsx:100-111](../../playa-frontend/src/pages/Quotas.jsx).
6. **Arreglar WhatsApp con un cambio de línea.** En
   [sales.py:273](../core/views/sales.py) cambiar `methods=['post']`
   por `methods=['get']`, y en [Quotas.jsx:47](../../playa-frontend/src/pages/Quotas.jsx)
   cambiar `response.data.whatsapp_url` por `response.data.whatsapp_link`.
7. **Mensaje WhatsApp con saludo y formato local.** En
   [sales.py:285](../core/views/sales.py):
   `f"Buen día. Le recordamos la cuota N°{quota.quota_number} con vencimiento {quota.due_date.strftime('%d/%m/%Y')} por Gs. {int(quota.amount):,}".replace(',', '.')`.
8. **Normalizar el teléfono para `wa.me`.** En [sales.py:286](../core/views/sales.py)
   sacar todo lo que no sea dígito y prefijar `595` si no empieza con
   `+` o `595`: `re.sub(r'\D', '', customer.phone)` y agregar prefijo
   país si falta.
9. **Cambiar título "Playas de Autos" por "AUTO OFERTAS" en
   Login y Navbar** — el cliente es AUTO OFERTAS, ese es el nombre
   que el dueño quiere ver. [Login.jsx:41](../../playa-frontend/src/pages/Login.jsx),
   [Navbar.jsx:44](../../playa-frontend/src/components/Navbar.jsx).
10. **Mover "+ Nuevo cliente" a /customers como acción primaria.**
    Reusar el `CustomerCreateModal` que ya existe en Sales.jsx.
    Similar para /vehicles con `VehicleCreateModal`.
11. **Mostrar un badge "MIG" en la columna Número de /sales** y
    contador "142 ventas con código de migración pendientes de
    corregir" arriba del listado. [Sales.jsx:262-275](../../playa-frontend/src/pages/Sales.jsx).
12. **Filtro "Solo ventas sin cliente" en /sales.** Re-aprovechar la
    estructura del filtro `search` actual; activar con un chip arriba
    de la tabla.
13. **Aviso en /vehicles cuando hay vehículos `available` referenciados
    por una sale.** Hay 25+ casos. Al menos un banner: "⚠ N vehículos
    figuran disponibles pero ya tienen venta asociada — ver lista".
14. **Sacar marcas "MARCA" y "DUMMY" del dropdown de creación de
    vehículo.** Filtrar en el queryset:
    `Brand.objects.filter(...).exclude(name__in=['MARCA','DUMMY'])`
    en [inventory.py:33-39](../core/views/inventory.py).
15. **Mergear PaymentForm `CRÉDITO` (id=2) y `CREDITO` (id=3).**
    Script: re-asignar la 1 venta que usa id=2 a id=3 y borrar la 2.
    Esto evita que el dashboard salga con dos filas separadas.
16. **Mostrar el "?" en el Navbar para abrir el cheat sheet.**
    El `KeyboardShortcutsProvider` ya escucha `?` y `Ctrl+/`, pero no
    hay un botón visible. Un iconito `?` al lado del usuario en el
    Navbar es 15 min de trabajo.
17. **Eliminar la 2ª llamada redundante después de crear venta.**
    [Sales.jsx:469-473](../../playa-frontend/src/pages/Sales.jsx)
    hace `api.get('/sales/')` con page_size=1000 sólo para encontrar
    el ID que `res.data` ya devolvió. Reemplazar por
    `openEditSale(sale)` directamente.
18. **Cambiar el formato del sale_number auto-generado de
    `V20260512NNNNN` a `CM???/26` o algo que diga "necesita
    completar"** ([sales.py:95](../core/views/sales.py)). El formato
    actual nunca sale en MC/CM y confunde.

---

## 5. Calidad de datos (números reales sobre la BD de hoy)

| Indicador | Valor | Cómo se arregla |
|---|---|---|
| Clientes totales | 298 | — |
| Clientes sin teléfono | **142 (47.6%)** | Por UI (rocio los va completando), filtrado por "documento real" |
| Clientes con documento auto-generado `DRV026-/SUC026-/CUOTA…` | **67 (22.5%)** | Por UI (modal "editar cliente" — aún no existe), o script que cruce con cobranza original |
| Clientes con email `@import.local` | **68** | Quitar default en el migrador o setear `email=''` en script |
| Clientes con teléfono vacío | 142 | Por UI; bloqueante para WhatsApp |
| Ventas totales | 427 | — |
| Ventas con código MIG (placeholder) | **142 (33.3%)** | Por UI: chip "Solo MIGs" + exportar a Excel (existe), pero ningún flujo de "marcar como completada" |
| Ventas sin cliente | **183 (43%)**, 117 en CC + 66 en S1 | Mixto: script para matchear contra ODS + UI para los que queden |
| Ventas sin vehículo | 17 | Por UI; ya hay alerta `⚠ Sin vehículo` |
| Ventas con `seller_id=NULL` | **427/427 (100%)** | Script de backfill por sucursal/intuición + UI |
| Ventas SUC1 sin cliente 2026 | **24 (MC02/26 → MC30/26)** | Crítico — preguntar a marcelo/responsable y completar a mano |
| Ventas con sale_number con espacios | 0 | Ya normalizado |
| Sale_number con `??` o placeholder visible | 1 (`MC??/25`) | UI: ya hay aviso |
| Cuotas totales | 3044 | — |
| Cuotas con `amount=0` | 0 | OK |
| Cuotas con `due_date` en año raro (2021) | 6 | Script: ofrecer corrección 2021→2025 |
| Cuotas `status='pending'` con `due_date<today` (overdue de facto) | **970** | Job/management command: `update status=overdue where status=pending and due_date<today` |
| Cuotas `status='overdue'` (literal) | 62 | Idem ↑ |
| Cuotas `status='paid'` con `payment_date` en futuro | **6** | Script de corrección (typo 2025→2026 al migrar) |
| Cuotas con `plan_name=""` | **1372 (45%)** | Script: completar con `f"{total_plan} cuotas"` |
| Ventas con cuotas asociadas | 164 de 427 | — (las de contado no necesitan) |
| Total cobrado histórico | Gs. 1.623.060.000 | — |
| Vehículos totales | 624 | — |
| Vehículos con `state='available'` | 408 | — |
| Vehículos con `state='available'` pero con sale asociada | **25+** | Script: `update state='sold' where id in (select vehicle_id from core_sale where ...)` |
| Vehículos con VIN basura (`VIN001xxx`, `VIN-DUMMY-*`) | 30+ | Script: marcarlos `is_placeholder=true` o moverlos a estado `maintenance` para excluirlos del stock visible |
| Vehículos con `price=0` | 181 | UI: rocio los va completando; alerta en /vehicles |
| Marcas con nombre genérico (`MARCA`, `DUMMY`) | 2 | Script: borrar marcas no usadas |
| PaymentForm duplicado `CRÉDITO`(id=2) vs `CREDITO`(id=3) | 1 venta apunta a `CRÉDITO` | Script: re-asignar y borrar |
| ExchangeRate cargados | **0** | Bloqueante si alguien quiere cargar un vehículo en USD; la UI lo advierte pero no permite cargar |
| Audit log con `object_id=0` | **15/15** | Bug del middleware: parsear ID del path |
| Audit log con `model_name='mark_as_paid'` (parseo malo) | 2 | Idem |

**Veredicto:** la mayor parte se puede resolver con 4 scripts y 3
mejoras de UI (botón editar cliente, badge MIG, filtro "sin cliente").
Pero ninguna está pre-hecha. Sin esto, papa al primer reporte va a
preguntar "¿quién es Drv026-0001?" y va a perder confianza.

---

## 6. Riesgos para la adopción

**Día 1 — papa entra y abre el sistema:**
- Ve un dashboard con números enormes (cartera vencida muy inflada por
  las 970 cuotas pending overdue, 6 cuotas con vto 2021).
- Va a `/sales` y la primera columna que ve mezcla `CM41/26` con
  `MIG000023` sin distinción visual.
- Hace click en la primera venta moderna y ve "⚠ Sin cliente" en rojo,
  donde antes en su Excel decía "Mario Bogado".
- Va a `/clientes` y ve `DRV026-0001 — drv026-0001@import.local`.
- Volvé al Excel.

**Semana 1 — rocio empieza a usarlo:**
- Marca una cuota como pagada con click rápido — el día siguiente
  papa pregunta "¿cuánto se cobró ayer en TB?" y no hay respuesta
  (no se guarda forma de pago en la cuota).
- Quiere mandar WhatsApp a un cliente — 405 silencioso, no se abre
  nada, **sin mensaje de error visible** (Quotas.jsx hace alert si
  falla pero el axios interceptor ya redirigió a /login antes — peor
  caso).
- Si quiere "buscar todas las cuotas pendientes del cliente X" no
  puede — el filtro por cliente en /quotas no existe.

**Objeción más probable del usuario:** "En el Excel tengo la hoja de
Mario Bogado con todas sus cuotas; el sistema me obliga a abrir
/quotas y hacer scroll de 3000 filas. Volvé al Excel."

**Riesgos técnicos paralelos:**
- Token JWT de 1h sin auto-refresh → sesión cae sola, papa tiene que
  reloguearse cada hora ([api.js:32-48](../../playa-frontend/src/utils/api.js)).
- Supabase free tier puede pausarse → backend lanza `OperationalError`
  → el frontend muestra textarea con JSON.
- 1000 cuotas en una sola request → 200-500 KB JSON, 1-2 s en wifi de
  sucursal.

---

## 7. Plan sugerido pre-lanzamiento

### Fase A — Bloqueantes (3-4 días; HACER SÍ O SÍ antes de mostrar a papa)

1. Limpiar datos:
   - Backfill `status='overdue'` para las 970 cuotas pendientes con
     `due_date<today`. Mejor todavía: borrar el estado `overdue` del
     modelo y calcularlo siempre en runtime (es lo que ya hace el
     dashboard).
   - Script: corregir las 6 cuotas con `due_date=2021` y las 6 con
     `payment_date` en 2026 futuro.
   - Script: completar `plan_name` vacío con `f"{total_plan} cuotas"`.
   - Script: mergear `CRÉDITO`/`CREDITO`. Borrar marcas `MARCA` y
     `DUMMY`.
   - Script: marcar como `sold` los ~25 vehículos `available` que ya
     están en una venta.
   - Mover los 30 VIN basura (`VIN001xxx`, `VIN-DUMMY-*`) fuera del
     listado visible (estado nuevo `placeholder` o flag `is_placeholder`).
2. Arreglar bugs:
   - Permisos `/users/` (3, severidad alta).
   - WhatsApp 405 + nombre del campo (4).
   - Sucursal ignorada al crear (7).
   - Filtro "Vencidas" en /quotas (2).
   - Dashboard respeta `branch` (1).
   - `mark_as_paid` acepta `payment_date` y `payment_form` desde el
     body, con UI tipo modal (5).
   - `seller` capturado al crear y mostrado en /sales + filtro (8).
3. Quick wins de copy y branding (Login, Navbar, Gs., toasts,
   confirmación de pago).
4. Crear management command `python manage.py recalc_quota_status`
   programado para correr 1×/día (Render cron job) que actualice
   `status='overdue'` para `pending+vencidas`.

### Fase B — Posponer pero tener fechado (1ª semana post-lanzamiento)

- "+ Nuevo cliente" / "+ Editar cliente" en /customers; idem
  /vehicles.
- Filtros en /quotas: por cliente, por sucursal, por rango de
  vencimiento.
- Vista cliente: drill-down `/customers/{id}` con sus ventas, sus
  cuotas pagadas/pendientes, su saldo.
- Detalle de pago: agregar `payment_form` y `paid_amount` al modelo
  Quotum (migración + serializer + UI).
- Tour guiado para `papa` la primera vez que entra (tooltip simple en
  cada página).
- Mejor mensaje de error cuando backend está caído: detectar
  `error.code==='ERR_NETWORK'` en el axios response interceptor y
  mostrar un toast tipo "Sistema temporalmente sin conexión, reintentá
  en 1 minuto" en vez del JSON de error.
- Autosave del modal de Nueva Venta a `localStorage` cada 10 s.
- Cron de recalculo de status, alertas automáticas a `papa` por mail
  cuando aparece un cliente con >90 días de atraso.

### Fase C — Se vive con eso (post-launch, mes 1-2)

- Audit log granular (`object_id`, diff de cambios).
- 2FA / cierre por inactividad.
- Refresh automático de tokens JWT (no es bloqueante: con 1h alcanza
  para una sesión típica; pero si va a dejar el navegador abierto
  todo el día, sí).
- ExchangeRate UI para precios USD (el flujo actual es 100% Gs., el
  USD es excepcional).
- Importador de stock vía Excel (`scripts/migracion/`) expuesto como
  endpoint para que rocio no necesite a un dev.
- Reemplazar `LocMemCache` por `DummyCache` (¡desactivar cache!)
  mientras la app esté en 1 worker — la stale data confunde más que
  el ahorro de tiempo. Activar Redis solo si la BD se vuelve cuello.

---

## 8. Métricas para post-lanzamiento (primeras 4 semanas)

Medir semana a semana en la BD (`db.sqlite3` o Postgres directo):

| Métrica | Cómo medirla | Qué dice |
|---|---|---|
| % ventas con cliente asignado | `count(customer_id NOT NULL) / count(*)` | Si baja semana a semana → la gente está cargando ventas mal |
| % ventas con seller_id | idem | ¿Quién está cargando? ¿Es solo rocio o también vendedores? |
| % ventas con MIG en el código | `count(sale_number LIKE 'MIG%')` | Debería ir bajando — si no, nadie está corrigiendo |
| Cuotas marcadas como pagadas / semana | `count(*) where status='paid' and payment_date between …` | Si == 0, rocio nunca registró pagos por el sistema (sigue en Excel) |
| Cuotas con `payment_form` distinto de NULL (cuando exista) | después de la migración del modelo | Si todas en EF → tal vez la UI no ofrece bien la opción |
| Ventas creadas por API en la semana | `count(*) where created_at between …` | Engagement crudo. Esperá ≥10/semana para un negocio activo |
| Logins por usuario distinto | Auditlog filtrado por action=`login` (o agregando un log de login al endpoint) | Si solo entra rocio → papa no adoptó |
| Errores 4xx/5xx en `logs/django.log` por endpoint | grep | Si `/quotas/.../contact_whatsapp/` sigue dando 405 → no aplicaste el fix |
| Tiempo medio de carga del dashboard | `X-Response-Time-ms` header en `/dashboard/summary/` | Si >2 s → cache no está funcionando o Supabase está saturado |
| Clientes con teléfono completo | `count(phone != '')` | Si llega a 80%, el WhatsApp empieza a tener uso real |
| Stock disponible vs vendido por sucursal | `core_vehicle` agrupado | Detección temprana de inconsistencias |

**Señales rojas que deberían disparar una intervención inmediata:**
- 0 cuotas marcadas como pagadas en la semana 1.
- `papa` no se loguea en >5 días.
- Cualquier endpoint con 5xx >5/día.
- Ventas creadas con `seller_id=NULL` después del fix.

---

## Anexo — Hallazgos sueltos que no entraron en el top 10 pero quiero dejar registrados

- **AuditLog inservible.** [middleware.py:81-94](../core/middleware.py)
  no extrae el ID real (`object_id=0`), `model_name` puede ser
  `"mark_as_paid"` o `"412"` según el path. Loguea incluso requests
  fallidos (4xx/5xx) porque no chequea `response.status_code`. En
  /admin un audit log que dice "rocio hizo update sales el 2026-04-25
  10:29 con objeto 412" no sirve para nada.
- **Modales anidados a 3 niveles** en Sales → +CrearVehículo
  → +CrearMarca. Visualmente OK con `z-index:50` pero confunde — falta
  un "stepper" / breadcrumb dentro del modal raíz.
- **`Ctrl+K` global search trae todos los registros sin paginar en
  cada keystroke** ([KeyboardShortcuts.jsx:78-101](../../playa-frontend/src/components/KeyboardShortcuts.jsx)).
  Con 3044 cuotas + 624 vehículos + 427 ventas + 298 clientes, son
  3-4 MB en cada tipeo. Debounce de 250 ms + endpoint de búsqueda
  servidor-side haría falta. Mientras tanto, al menos `debounce`.
- **El resultado de Ctrl+K, al hacer click, navega a `/sales` pero
  no abre el modal de la venta clickeada.** Bug "deep link missing"
  ([KeyboardShortcuts.jsx:130-136](../../playa-frontend/src/components/KeyboardShortcuts.jsx)).
- **Iconos emoji en Sidebar** (🚗💰📋👥📊⚙️) — para un dueño de 60+
  años en una concesionaria seria puede leerse infantil. No es
  crítico, pero un set de íconos SVG monocromos (Heroicons via
  inline SVG) le daría más seriedad.
- **`Sidebar.jsx:36`** muestra "Usuarios" solo si `isAdmin`, pero la
  validación está en frontend. La protección real depende del fix #3.
- **No hay vista "Stock por sucursal valorizado" en el dashboard**,
  aunque el endpoint existe en [inventory.py:194-209](../core/views/inventory.py).
  Para papa esto es una métrica de cabecera.
- **La `dashboard_cache(60)` y `dashboard_cache(300)` en
  [dashboard.py:17-23](../core/views/dashboard.py) usan LocMemCache.**
  Con varios workers (Render usualmente arranca 2-4) cada uno tiene
  su propio cache → papa puede ver "Gs. 1.500.000.000" y refrescar
  para ver "Gs. 1.200.000.000". Mejor desactivar mientras esté en
  baja escala.
- **El `top_morosos`** [dashboard.py:280-289](../core/views/dashboard.py)
  hace N+1 queries (1 por cada cliente para encontrar la cuota más
  vieja). En Supabase São Paulo cada query agrega 200-500 ms.
  Refactor a un single GROUP BY con MIN(due_date).
- **Modal "Editar venta"** ([Sales.jsx:333-437](../../playa-frontend/src/pages/Sales.jsx))
  cuando hay un `error` muestra un textarea con JSON crudo. Está
  pensado para que copies y pegues, OK, pero ante errores comunes
  como "VIN duplicado" o "Cliente sin documento" debería traducirse a
  un mensaje en español.
- **`Vehicles.jsx`** no tiene botón de edición por fila — sólo
  filtros. Para corregir un VIN basura no hay UI.
- **El input "Entrega inicial" es un `<input type="number">`** sin
  formato — el usuario ve "10000000" mientras tipea y solo al guardar
  ve "Gs. 10.000.000". Para una empresa donde los montos son siempre
  millones, conviene un input enmascarado con formateo en vivo.
- **`UserCreateModal`** [Users.jsx:206](../../playa-frontend/src/pages/Users.jsx)
  tiene `<input type="text">` para el password ("mínimo 6 caracteres")
  — debería ser `type="password"` aunque sea el admin creando para
  otro, para no mostrarlo en pantalla.
