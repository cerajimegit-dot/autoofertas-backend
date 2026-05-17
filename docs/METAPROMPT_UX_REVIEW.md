# Metaprompt — Revisión UX y adopción pre-producción (hidratado)

Copiá este prompt en una nueva conversación para que Claude haga un análisis holístico
del sistema con foco en experiencia de usuario y riesgos de adopción. Está
hidratado con los datos concretos del estado actual del proyecto.

---

## PROMPT

Vas a hacer un **diagnóstico de UX, calidad de datos y riesgos de adopción** del
sistema **Playas de Autos / AutoOfertas** antes de lanzarlo a producción. No me
devuelvas un reporte genérico — quiero un análisis crítico, accionable y específico
para ESTE sistema y ESTOS usuarios.

### Contexto del negocio

- Concesionaria multi-sucursal de autos usados en Paraguay (Asunción + interior).
  Empresa familiar.
- Antes del sistema: planillas ODS/Excel por venta, una hoja por cliente.
  Cada hoja tiene un header con cliente + chasis + CM/MC y una grilla de cuotas
  (VTO, DOC, MONTO, FECHA, FORMA). El sistema reemplaza esa planilla.
- Empresa: **AUTO OFERTAS** (enterprise_id=3 en BD).
- Sucursales: **CASA CENTRAL** (id=1, códigos `CM` ej `CM21/26`) y
  **SUCURSAL 1** (id=2, códigos `MC` ej `MC22/26`).
- Operación: vehículos importados de Japón (Toyota Vitz, Ractis, Allion,
  Sienta, Auris, Hyundai Tucson, Kia Sportage). Ventas mayoritariamente a
  crédito con entrega + 12-30 cuotas, a veces con refuerzos (cuotas más grandes
  cada 12 meses).
- Formas de pago de cuota usadas: **EF** (efectivo), **TB** (transferencia
  bancaria), **CJ** (caja), **AC** (acuerdo).
- Idioma: español de Paraguay. Montos en **guaraníes (Gs.)** con separador de
  miles y sin decimales.

### Usuarios reales

Estos son los usernames en BD (todos enterprise_id=3, password
`autoofertas2026` salvo `admin/admin123`):

- `admin` — usuario administrador de pruebas.
- `papa` — el dueño, 60+ años, viene del Excel + papel. Va a usar el sistema
  para verificar saldos y reportes generales. **Persona crítica de adopción.**
- `mati` — vendedor.
- `marcelo` — vendedor.
- `rocio` — administradora/secretaria, registra ventas y cobranzas.

Todos tienen acceso multi-sucursal por el M2M `branches_visible`.

### Estado actual del sistema (datos reales en BD Postgres Supabase)

- **427 ventas** migradas (CM/MC). Las últimas son hasta `CM41/26` y `MC32/26`.
- **3044 cuotas** asociadas, con mezcla de `paid`, `pending`, `overdue`.
- **624 vehículos** en `core_vehicle`, varios con estado `available`,
  otros con `sold`, `reserved`, `maintenance`.
- **298 clientes** en `core_customer`. **Atención:** los clientes creados por
  migración tienen documentos auto-generados tipo `DRV026-0001`,
  `SUC026-0001`, `CUOTA000161` y emails sintéticos
  `drv026-0001@import.local`.
- **9 usuarios** activos.
- **2 sucursales**, **3 enterprises** (sólo AUTO OFERTAS está en uso real).
- **44 modelos** de vehículo, **7 marcas**.
- **0 ExchangeRates** cargados (la app tiene endpoints pero nadie los usó).
- **4 PaymentForm** (CONTADO, CREDITO, CRÉDITO con tilde duplicado, MIXTO).

### Stack y arquitectura

**Backend:**
- Django 5.1.4 + DRF + djangorestframework-simplejwt + drf-spectacular.
- Postgres en Supabase (São Paulo) — usa transaction pooler (puerto 6543).
- Autenticación JWT con `Bearer` tokens, refresh de 1 día, access de 1 hora.
- Multi-tenant por `enterprise_id`, con filtro automático en todos los viewsets.
- Filtro adicional por `branch_id` cuando el query param lo pide.
- Middleware custom: `AuditLogMiddleware` (registra POST/PUT/DELETE en
  `core_auditlog`) y `TimingMiddleware` (loguea endpoints >500ms con header
  `X-Response-Time-ms`).
- Cache: `LocMemCache` con decorador `dashboard_cache(seconds)` aplicado a
  varios endpoints del dashboard.
- Indices creados: ver `scripts/migracion/create_indexes.py` (17 índices,
  incluyendo GIN trigram para fuzzy search en clientes).
- Logging: archivo `logs/django.log` con queries lentas.

**Frontend** (no-build, todo CDN):
- React 18 UMD + React Router v5.3 (v6 no tiene UMD).
- Babel standalone para compilar JSX en el browser.
- Tailwind CDN, Chart.js, axios, SheetJS para export Excel.
- Servidor: `server.py` (Python http.server, port 3000).
- URL del backend configurable en `config.js` (window.API_BASE_URL).
- Estructura de pages: Login, Dashboard, Vehicles, Sales, Quotas, Customers, Users.
- Estructura de components: Toast, EmptyState, Skeleton, Badge,
  ResponsiveTable, FormField, KeyboardShortcuts, Card, Button, Navbar, Sidebar.
- Contextos: AuthContext, BranchContext, ToastProvider, KeyboardShortcutsProvider.
- Utils: api.js, auth.js, storage.js, format.js (`formatGs`, `formatMoney`,
  `formatInt`, `formatDate`).

### Lentes de análisis (usá todos)

**1. Usabilidad de la interfaz**
- ¿Cuántos clicks toma hacer las 5 tareas más frecuentes?
  - Cargar una venta nueva (cliente + vehículo + plan de cuotas + refuerzos).
  - Marcar una cuota como pagada (con fecha + forma de pago).
  - Buscar un cliente por nombre o documento.
  - Ver el stock disponible filtrado por sucursal/marca/precio.
  - Ver morosos / cuotas vencidas y mandar WhatsApp.
- Mensajes de error: ¿son entendibles para un no-técnico? Revisá el manejo
  de 401, 500, timeouts y errores de validación en formularios. Ejemplo
  conocido: el interceptor de axios redirige a `/login` ante 401 — ya hay
  un fix para no entrar en loop pero el usuario sigue viendo "saltó al login
  de la nada" sin contexto.
- Estados vacíos: hay un componente `EmptyState`. Verificá que TODAS las
  listas lo usen (Vehicles.jsx ya lo hace, ¿y Sales/Quotas/Customers/Users?).
- Loading: hay `Skeleton` (e.g. `TableSkeleton`). ¿Está aplicado consistente
  o algunos endpoints muestran pantalla en blanco hasta que llegue la data?
  Recordá que con Supabase São Paulo cada query tarda 200-500ms.
- Responsive: usa `ResponsiveTable`. ¿Qué tan bien funciona en mobile? Los
  vendedores van a usar el celular.
- Atajos de teclado: hay un provider, pero ¿se documentan en algún lado?
  ¿Hay un "?" que abra un cheat sheet?
- Confirmaciones destructivas: borrar venta/cuota/cliente, ¿pide confirmar?
  ¿Es reversible? Hoy no hay soft-delete.
- Branding: paleta azul (`--brand-primary: #2563eb`), logo emoji 🚗, nombre
  "Playas de Autos". ¿Coherente con una empresa familiar paraguaya seria?

**2. Calidad de datos migrados**
- Revisá la BD buscando:
  - Clientes con `phone=''`, `document_number=''` o documentos
    auto-generados tipo `DRV026-xxxx`, `SUC026-xxxx`, `CUOTA000xxx`.
  - Ventas con `customer_id IS NULL` (sabemos que `MC27/26` y `MC28/26`
    están así, sin cliente ni cuotas).
  - Ventas con `vehicle_id IS NULL` (los placeholders viejos sí, pero el
    resto debería tener).
  - Chasis con formato raro: `IS`, vacíos, `038036` (corto), o duplicados
    entre dos ventas distintas.
  - Cuotas con `amount=0` o `due_date` con año `2006` (error histórico:
    typo de `2025` → `2006` en algunos archivos del proveedor).
  - Vehículos en estado `available` que en realidad están vendidos (no hay
    venta apuntándolos pero state quedó `available`).
  - Códigos de venta con espacios inconsistentes (`CM 12/25` vs `CM12/25`).
  - PaymentForm duplicado: `CREDITO` (id=3) y `CRÉDITO` con tilde (id=2).
- Para cada problema: ¿se arregla por script, por UI o se vive con eso?

**3. Onboarding y primera experiencia**
- Imaginate al `papa` entrando por primera vez después de 30 años de
  Excel. ¿Cuáles son las primeras 3 pantallas que ve después del login?
  ¿Qué entiende, qué no?
- ¿Hay un mensaje de bienvenida, tooltips, tour guiado, video?
- El selector de sucursal (BranchContext) — ¿es obvio dónde está y qué hace?
  Si el usuario lo ignora, ¿el sistema usa una sucursal por defecto?
- Acceso al admin de usuarios: solo para admin/papa. ¿Está claro o aparece
  para todos rompiendo permisos en frontend?

**4. Workflows reales**
Trazá paso a paso (clicks, formularios, errores potenciales) estos flujos
en el código actual:
- **Vender un auto al contado a un cliente nuevo.** ¿Crea cliente desde el
  modal de venta o tiene que ir a /customers primero?
- **Vender un auto a crédito con entrega + 24 cuotas + 2 refuerzos.** ¿Hay
  un generador de plan de cuotas? Sabemos que sí — buscá el componente.
- **Registrar el pago de una cuota recibido por transferencia ayer.**
  ¿Permite poner fecha pasada o solo "hoy"? ¿Pide adjunto/comprobante?
- **Generar el link de WhatsApp** para reclamar una cuota vencida (existe
  endpoint `/quotas/{id}/contact_whatsapp/`, hay un botón "💬 WhatsApp" en
  Quotas.jsx).
- **Cambiar de sucursal activa** y ver cómo cambian los listados.
- **Ver cuántas ventas hizo Marcelo este mes** (¿existe filtro por seller_id?).
- **Importar stock nuevo** (no hay UI todavía — solo scripts en
  `scripts/migracion/`. ¿Cómo lo va a hacer rocio?).

**5. Riesgos de adopción**
- Confianza: ¿el usuario puede VERIFICAR que el sistema tiene los datos
  correctos vs el Excel viejo? Ejemplos críticos:
  - "Mostrame todas las cuotas pagadas de Mario Bogado" → ¿concuerda con
    su ODS?
  - "Total cobrado en mayo" → ¿el dashboard lo muestra desglosado por
    sucursal?
  - "Stock disponible total valorizado" → endpoint `/vehicles/valorized_stock/`.
- Reversibilidad: si meten un dato mal, ¿cómo lo corrigen? Hay audit log
  pero no hay undo. ¿Pueden editar una cuota ya pagada?
- Permisos: si un vendedor entra, ¿puede borrar una venta de otro? ¿Puede
  ver el dashboard del dueño? Verificá `IsEnterpriseOwnerOrAdmin` y
  `CanDeleteSale`.
- Disponibilidad: si Supabase está caído o el plan free se pausa, el
  backend tira `OperationalError`. ¿El frontend muestra algo amigable o
  un error técnico?
- Conectividad: en sucursal con WiFi malo, una venta a medio cargar ¿se
  pierde? ¿Hay autosave o solo "Guardar" final?

### Archivos que tenés que leer (priorizá)

**Backend Django** (`C:\Users\prueb\CascadeProjects\playa\`):

- `C:\Users\prueb\CascadeProjects\playa\core\views\sales.py` — SaleViewSet, QuotumViewSet, CustomerViewSet, PaymentFormViewSet
- `C:\Users\prueb\CascadeProjects\playa\core\views\inventory.py` — VehicleViewSet, BrandViewSet, VehicleModelViewSet, ExchangeRateViewSet
- `C:\Users\prueb\CascadeProjects\playa\core\views\dashboard.py` — todos los KPIs del dashboard
- `C:\Users\prueb\CascadeProjects\playa\core\views\base.py` — CustomUserViewSet
- `C:\Users\prueb\CascadeProjects\playa\core\serializers.py`
- `C:\Users\prueb\CascadeProjects\playa\core\models\base.py` — Enterprise, Branch, CustomUser
- `C:\Users\prueb\CascadeProjects\playa\core\models\inventory.py` — Vehicle, Brand, VehicleModel, ExchangeRate, VehicleCost
- `C:\Users\prueb\CascadeProjects\playa\core\models\sales.py` — Sale, Quotum, Customer, PaymentForm, AuditLog
- `C:\Users\prueb\CascadeProjects\playa\core\permissions.py`
- `C:\Users\prueb\CascadeProjects\playa\core\middleware.py`
- `C:\Users\prueb\CascadeProjects\playa\core\pagination.py`
- `C:\Users\prueb\CascadeProjects\playa\playas_autos\settings.py`
- `C:\Users\prueb\CascadeProjects\playa\playas_autos\urls.py`

**Frontend React** (`C:\Users\prueb\CascadeProjects\playa-frontend\`):

- `C:\Users\prueb\CascadeProjects\playa-frontend\index.html` — entry point, todos los `<script>` y branding
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\App.jsx` — routing y layout principal

Pages (todas):
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\pages\Login.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\pages\Dashboard.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\pages\Vehicles.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\pages\Sales.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\pages\Quotas.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\pages\Customers.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\pages\Users.jsx`

Components (todos):
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\components\Sidebar.jsx` — navegación principal
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\components\Navbar.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\components\Toast.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\components\EmptyState.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\components\Skeleton.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\components\Badge.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\components\ResponsiveTable.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\components\FormField.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\components\KeyboardShortcuts.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\components\Card.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\components\Button.jsx`

Contextos y utils:
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\context\AuthContext.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\context\BranchContext.jsx`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\utils\api.js`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\utils\auth.js`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\utils\format.js`
- `C:\Users\prueb\CascadeProjects\playa-frontend\src\utils\storage.js`

Skill custom del proyecto (convenciones acumuladas):
- `C:\Users\prueb\CascadeProjects\playa-frontend\.claude\skills\playa-ui-improvements\SKILL.md`

**Documentación del proyecto:**

- `C:\Users\prueb\CascadeProjects\playa\docs\MIGRACION_PLAYBOOK.md` — cómo se migraron los datos
- `C:\Users\prueb\CascadeProjects\playa\docs\MIGRACION_POSTGRES.md` — cómo se pasó de SQLite a Supabase
- `C:\Users\prueb\CascadeProjects\playa\docs\DELTA_REPORT_2026-05-08.md` — última actualización masiva de datos
- `C:\Users\prueb\CascadeProjects\playa\docs\PLAN_PERFORMANCE.md` — optimizaciones pendientes
- `C:\Users\prueb\CascadeProjects\playa\docs\DEPLOY_RENDER.md` — guía de despliegue

**Memorias persistentes del proyecto** (índice + facts acumulados):

- Índice: `C:\Users\prueb\AppData\Roaming\Claude\local-agent-mode-sessions\1ef3b96e-8884-46c8-bb06-f2af0964cce1\7976e158-519f-4886-8d36-a2d3ff4cdc8c\spaces\ada029b9-8884-46c8-bb06-f2af0964cce1\memory\MEMORY.md`
- Carpeta completa: `C:\Users\prueb\AppData\Roaming\Claude\local-agent-mode-sessions\1ef3b96e-8884-46c8-bb06-f2af0964cce1\7976e158-519f-4886-8d36-a2d3ff4cdc8c\spaces\ada029b9-8884-46c8-bb06-f2af0964cce1\memory\`
- Las memorias incluyen: overview del proyecto, IDs de referencia, patrones de migración, feedback acumulado sobre formato de moneda, codigos de venta, workflow de BD.

**Scripts útiles para inspeccionar datos:**

- `C:\Users\prueb\CascadeProjects\playa\scripts\migracion\check_data.py` — conteos + setup admin
- `C:\Users\prueb\CascadeProjects\playa\scripts\migracion\bench_apis.py` — performance de endpoints
- `C:\Users\prueb\CascadeProjects\playa\db.sqlite3` — copia local de la BD (sincronizada con Supabase)

**Queries SQL exploratorias** (correlas en SQLite local o Postgres con
`scripts\migracion\check_data.py` adaptado):

- Clientes sin teléfono ni documento real: `SELECT count(*) FROM core_customer WHERE phone='' OR document_number LIKE 'DRV026-%' OR document_number LIKE 'SUC026-%' OR document_number LIKE 'CUOTA%'`
- Ventas sin cliente: `SELECT id, sale_number FROM core_sale WHERE customer_id IS NULL`
- Cuotas con monto cero: `SELECT count(*) FROM core_quotum WHERE amount = 0`
- Cuotas con due_date en año raro: `SELECT * FROM core_quotum WHERE strftime('%Y', due_date) NOT IN ('2022','2023','2024','2025','2026','2027','2028','2029')`
- Vehículos `available` que ya tienen venta: comparar `core_vehicle.state='available'` con `vehicle_id` que aparezcan en `core_sale`
- Chasis duplicado: `SELECT vin, count(*) FROM core_vehicle GROUP BY vin HAVING count(*) > 1`
- PaymentForm duplicado: `SELECT * FROM core_paymentform` (mirá CREDITO vs CRÉDITO con tilde)

### Deliverable esperado

Generá un único documento markdown en `playa/docs/UX_AUDIT.md` con esta
estructura:

```
# Diagnóstico UX y adopción — Playas de Autos

## 1. Resumen ejecutivo (máx 10 líneas)
Lo más importante que el dueño tiene que saber antes de lanzar.

## 2. Top 10 problemas priorizados
Tabla con: # | Problema | Dónde (archivo:línea) | Severidad (Alta/Media/Baja) |
Esfuerzo (S/M/L) | Quién lo nota
Cada problema con un párrafo de detalle + propuesta concreta de fix.

## 3. Fricción por persona
Una sub-sección por persona (papa, mati/marcelo, rocio) listando los 3
puntos más dolorosos para ESA persona, no en general.

## 4. Quick wins (≤30 min cada uno)
Lista de cambios chicos con altísimo retorno: copia de errores, defaults,
atajos, labels más claros, etc. Con archivo + línea aproximada cuando
sea posible.

## 5. Calidad de datos
Hallazgos concretos sobre los datos migrados, con números (cuántos
clientes sin teléfono, cuántas ventas sin cliente, etc). Para cada
uno: ¿se arregla por script, por UI o se ignora?

## 6. Riesgos para la adopción
¿Qué pasa el primer día? ¿En la primera semana? ¿Qué objeción va a
tener el usuario que justifique "no, dejame seguir con Excel"?

## 7. Plan sugerido pre-lanzamiento
3 fases: lo que SÍ hago, lo que se puede posponer, lo que se vive
con eso.

## 8. Métricas para post-lanzamiento
Qué medir las primeras 4 semanas para saber si la adopción está
funcionando.
```

### Tono y criterios

- **Sé crítico**: el objetivo no es validar, es encontrar problemas. Si
  algo te parece raro, decilo.
- **Sé específico**: "el botón de Guardar es feo" no sirve. "El botón
  de Guardar en `Sales.jsx:142` es del mismo azul que Cancelar, papa
  los va a confundir" sí sirve.
- **Pensá en el contexto cultural**: paraguayos, ventas con trato
  personal, dueño de 60+ años. El sistema no puede sentirse frío,
  gringo, o sobre-tecnológico.
- **Distinguí esfuerzo**: un cambio de copy (S = <30min) vs rediseñar
  el dashboard (L = >4hs).
- **No recomiendes herramientas nuevas** salvo que sea inevitable.
  Quedate dentro de lo que ya hay (React no-build, Tailwind, Chart.js).
- **No agregues features nuevas** salvo que el problema no se pueda
  resolver sin ellas. Primero arreglar lo que está, después extender.
- **Citá archivos y números reales** (los datos están arriba).
  Si decís "muchos clientes sin teléfono", pediste un número.

### Cómo NO querés que sea el deliverable

- Genérico (cualquier sistema podría tener estos consejos).
- Solo positivos ("la UI está bien"). Necesito que me señales lo malo.
- Lista de buenas prácticas sin aplicarlas a este sistema concreto.
- Recomendaciones imposibles ("contratá un diseñador").
- Sin referencias a archivos/líneas/datos reales.
- Sugerencias que ya están implementadas (revisá los archivos antes
  de proponer).

Empezá ya — primero leé los archivos que liste, después armás el
diagnóstico. Si necesitás aclarar algo del negocio, preguntá antes
de inventar.

---

## Cómo usar este metaprompt

**Opción A — En esta misma sesión:** copiá el bloque PROMPT de arriba y
pegámelo como mensaje. Voy a hacer el análisis con todo el contexto
que ya tengo.

**Opción B — En una sesión nueva:** abrí una nueva conversación en Cowork
con la misma carpeta de proyecto seleccionada, pegá el bloque PROMPT.
La sesión nueva arranca leyendo memorias del proyecto y los archivos,
así que el análisis sale "frío" (sin sesgos de lo que hicimos hoy) —
útil si querés una segunda mirada.

**Opción recomendada:** correr ambas en momentos distintos y comparar
los Top 10. Lo que aparece en los dos, es lo que duele.
