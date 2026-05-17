# Análisis arquitectural — AUTO OFERTAS (Playas de Autos)

Fecha: 2026-05-15
Stack revisado: Django 5.1.4 + DRF + djangorestframework-simplejwt +
drf-spectacular + Postgres 15 (Supabase, São Paulo, transaction pooler)
+ React 18 UMD + Babel-standalone + Tailwind CDN.
BD analizada: 298 clientes, 427 ventas, 3.044 cuotas, 624 vehículos, 9
usuarios, 2 sucursales (CASA CENTRAL + SUCURSAL 1), 1 empresa activa
(AUTO OFERTAS, `enterprise_id=3`).

Notas previas:
- El [UX_AUDIT](UX_AUDIT.md) cubrió usabilidad y calidad de datos.
- En las últimas sesiones se aplicaron quick-wins (lazy-load,
  permisos `/users/`, WhatsApp, sucursal-aware en dashboard, panel de
  inconsistencias).
- Lo que sigue son los hallazgos **arquitecturales** —
  decisiones que sobreviven a los quick-wins y van a definir si el
  sistema crece bien o se vuelve un nido.

---

## 1. Arquitectura del sistema

### Fortalezas

- **Modelado multi-tenant explícito** vía `enterprise_id` (FK
  obligatoria en todos los modelos de negocio). El filtro está
  centralizado en cada `get_queryset` y nunca se filtra en el cliente.
  Para una concesionaria-única hoy es overkill, pero **abre la puerta
  a que el dueño venda el sistema** a otra concesionaria sin reescribir.
- **Separación física frontend/backend**: el backend es un API DRF
  consumible desde web, mobile o un kiosco. Hoy se consume desde un
  React no-build, pero podría hacerse desde Flutter/Tauri mañana sin
  tocar el backend.
- **Schema documentado vía drf-spectacular** ([urls.py:36](../playas_autos/urls.py)):
  `/api/docs/` y `/api/redoc/` generan OpenAPI 3.0. Cualquier
  desarrollador externo puede integrar sin leer código Python.
- **Models y views están bien separados por dominio** (`core/models/base.py`,
  `inventory.py`, `sales.py`; idem en `core/views/`). Esto fue una
  refactorización temprana que ahora paga dividendos.

### Debilidades

- **Frontend no-build** (`React UMD + Babel standalone` cargado desde
  CDN, [index.html:32](../../playa-frontend/index.html)). Mortal en
  producción: Babel-standalone interpreta JSX **en cada carga del
  browser**, cuesta ~1-3 s la primera vez. No hay tree-shaking, no hay
  code-splitting, no hay hot-reload. Funciona porque el proyecto es
  chico — colapsa al duplicarse de tamaño.
- **Lógica de negocio en los `views`, no en `services`**. Por
  ejemplo, el cálculo de "días de atraso máximo" del cliente está en
  [dashboard.py:323](../core/views/dashboard.py), no en un módulo
  reusable. Si mañana se quiere ese cálculo desde un management
  command o desde un Celery beat, hay que duplicarlo.
- **No hay capa de "domain events"**. Cuando se crea una `Sale`, no
  pasa nada automático: el vehículo NO cambia a `sold`, las cuotas NO
  se generan, no se manda ninguna notificación. Todo eso lo decide el
  usuario manualmente. Es propenso al error humano (de hecho ya hay
  25+ vehículos `available` que están vendidos — ver UX_AUDIT §5).
- **`AuditLogMiddleware` graba pero no captura el ID del objeto**
  ([middleware.py:81-94](../core/middleware.py)): `object_id=0` siempre.
  En la práctica el audit log es decorativo.
- **No hay procesos background**: nada de Celery, RQ, ni siquiera un
  management command corrido por cron. Las cosas que conceptualmente
  son recurrentes (recalcular cuotas vencidas, enviar recordatorios,
  refrescar cotización USD) requieren que alguien abra el sistema.
- **Cache local-mem con varios workers en producción**
  ([dashboard.py:17](../core/views/dashboard.py)). En Render con 2-4
  workers, cada uno tiene su propio cache → resultados inconsistentes
  entre refreshes.

### Recomendaciones

1. **A 1 sucursal de tamaño actual**: dejar la arquitectura como está
   con dos cambios chicos pero importantes:
   - Pasar la cache de `LocMemCache` a `DummyCache` (desactivada)
     hasta que el throughput justifique un Redis.
   - Mover el cálculo de "estado overdue" a un management command
     `python manage.py recalc_quota_status` ejecutado por `cron` o
     Render Scheduled Jobs (1×/día). Borrar el campo redundante
     `Quotum.status='overdue'` o que ese command lo mantenga al día.
2. **Capa `core/services/`** con funciones puras: `register_sale`,
   `mark_paid`, `generate_quota_plan`. Hoy esa lógica está duplicada
   entre frontend (generador de preview en `Sales.jsx`) y backend
   (validación en serializers). Mover al backend para tener una sola
   fuente de verdad.
3. **Frontend con build real** cuando se justifique (>500 ventas/mes
   o un segundo desarrollador). Vite + React + react-router 7 + esbuild.
   No hace falta TypeScript en V1, pero sí un bundle único.
4. **Auditoría útil**: parsear el ID real del path (regex sobre
   `request.path`) y guardar `request.data` truncado en `new_values`.
   Para acciones tipo `mark_as_paid` extraer el `pk` del kwargs del view.

---

## 2. Gestión de inventario

### Fortalezas

- **`Vehicle` tiene un set de campos pensado** para la operación:
  `vin`, `license_plate`, `color`, `mileage`, `fob`, `container`,
  `dispatch`, `cam_vol`, `price`, `currency`, `state`. Refleja el
  flujo real de importación desde Japón.
- **Costos extras flexibles** vía `VehicleCost` con `concept`
  libre. Permite cargar "Flete interno", "Honorarios", etc., sin migración.
- **Estado de vehículo** (`available`, `reserved`, `sold`, `maintenance`)
  con badges visuales y filtros funcionando.
- **Orden por defecto: disponibles primero** ([inventory.py:154](../core/views/inventory.py)).
  Lo que el vendedor necesita ver primero está arriba.
- **Búsqueda fuzzy posible**: hay GIN trigram en
  [scripts/migracion/create_indexes.py:69](../scripts/migracion/create_indexes.py)
  para `core_customer (first_name || ' ' || last_name)`. (Falta
  replicar a `vehicle.vin / brand_name / model_name`, pero el
  patrón está.)

### Debilidades

- **Validación mínima**. `vin` se acepta vacío, con dígitos
  arbitrarios, con espacios, sin chequeo de longitud:
  hoy hay 30+ VIN tipo `VIN001000`, `IS`, `''` ([UX_AUDIT §5](UX_AUDIT.md)).
  No hay validador para chasis japonés (formato estándar 17 chars
  alfanuméricos).
- **`year` se acepta entre 1900 y 2100** ([Sales.jsx:696](../../playa-frontend/src/pages/Sales.jsx)).
  Real: 1980-2026 alcanza. Permitir 1900 acepta typos como `1925`
  para un Toyota.
- **`price = 0` es válido**. Hay 181 vehículos con `price=0` (29%
  del stock). El sistema los muestra y los suma a stats sin
  advertir, hasta el panel de inconsistencias agregado en el
  último cambio.
- **No hay flujo de baja de inventario**: borrar un vehículo es
  `DELETE` directo y la `Sale.vehicle` queda `null` (FK con
  `on_delete=SET_NULL`). Mejor: soft-delete con flag `is_active`
  y filtrar.
- **Sin estado `in_transit`**: no se puede registrar "comprado en
  Japón, todavía no llegó". Hoy se crean en `available` desde el
  día 1.
- **Sin foto del vehículo**. Un campo `ImageField` o `URLField`
  hacia un Cloudinary/Supabase Storage sería un golazo para
  WhatsApp marketing.
- **Marcas/Modelos sobrepoblado**: 7 marcas + 44 modelos para una
  concesionaria que mueve ~80 ventas/año. El selector `<select>`
  alcanza, pero no hay merge si el usuario crea "Toyota Vitz 1.0"
  y después "TOYOTA VITZ 1.0".

### Recomendaciones

1. **Validar `vin` en el serializer**: ≥10 chars, regex
   `^[A-HJ-NPR-Z0-9]+$` (sin I, O, Q), advertencia (no bloqueo) si
   no tiene 17 chars (autos japoneses pre-2000 a veces son cortos).
2. **`price` requerido > 0** en serializer (no en model, para no
   romper migración). Bloquear en UI también.
3. **`state='in_transit'`**: agregar a las choices y excluir del
   stock disponible visible.
4. **Soft-delete**: `is_active=BooleanField(default=True)`.
   `get_queryset` filtra `is_active=True` por defecto, admin lo ve
   todo.
5. **Foto del vehículo**: `image = URLField(blank=True)` apuntando
   a Supabase Storage o Cloudinary. La UI del modal de venta lo
   muestra al vendedor; el mensaje de WhatsApp lo puede adjuntar.
6. **Normalizar marca/modelo al crear**: `.upper().strip()` en el
   serializer; advertencia si ya existe una con `iexact` match.

---

## 3. Interfaz de usuario

### Fortalezas

- **Componentes reutilizables**: `Button`, `Card`, `Badge`,
  `EmptyState`, `Skeleton`, `ResponsiveTable`, `FormField`. La
  paleta visual es consistente.
- **`formatGs` global** garantiza moneda paraguaya en todos los
  montos. Los usuarios no ven `$` (excepto un caso que fue
  arreglado en quick-wins).
- **`formatDate` evita el bug de TZ**: parsea string ISO sin
  ofset, devuelve DD/MM/YYYY ([format.js:54](../../playa-frontend/src/utils/format.js)).
  En Paraguay (UTC-3) el clásico `new Date('2026-01-05').toLocaleDateString()`
  devuelve 04/01 — esto está bien resuelto.
- **Atajos de teclado** con cheat sheet (`?` o `Ctrl+/`) y buscador
  global (`Ctrl+K`).
- **Selector de sucursal global** con persistencia en
  `localStorage` ([BranchContext.jsx:20](../../playa-frontend/src/context/BranchContext.jsx)).
  Después del fix, filtra dashboard, sales, quotas, vehicles, customers.
- **Panel de inconsistencias** en el dashboard con drill-down
  navegando a las páginas filtradas — ver UX_AUDIT y los quick-wins.

### Debilidades

- **Modales anidados a 3 niveles**: Sales → +CrearVehículo →
  +CrearMarca. Visualmente funcionan, pero un usuario senior se
  pierde. Ideal: wizard inline o stepper.
- **Sin atajos de acción**: no hay `Ctrl+N` para Nueva venta, ni
  `Ctrl+S` para guardar. Los vendedores acostumbrados al Excel
  pierden velocidad.
- **Inputs monetarios sin formateo en vivo**: el usuario tipea
  `10000000` y solo al confirmar ve `Gs. 10.000.000`. Riesgo de
  agregar/quitar un cero sin notar.
- **No hay vista "perfil de cliente"** con TODO su historial
  (ventas + cuotas + saldos). Es la pantalla que reemplaza la
  hoja del Excel — la más extrañada por papa.
- **No hay impresión / PDF**. Para entregar al cliente un recibo
  o cronograma de cuotas, hoy no se puede.
- **Globalmente solo 4 atajos de teclado** y muchos clicks
  redundantes (ver UX_AUDIT §3).
- **Loading states inconsistentes**: algunos endpoints muestran
  `TableSkeleton`, otros pantalla en blanco con `<div className="loading">`,
  otros saltan directo al EmptyState. Da sensación de "se rompió".
- **Sin "lista vacía rica"** en /quotas — los EmptyStates ya están
  en la mayoría pero falta el de Users.

### Recomendaciones

1. **Vista `/customers/:id`** (drill-down) con: datos personales,
   ventas (con sale_number y monto), cuotas pendientes/pagadas,
   saldo, botón WhatsApp directo. Es el pedido más obvio del
   dueño. Esfuerzo: ~4-6 hs.
2. **PDF cronograma de cuotas** — para entregar al cliente al
   firmar. Generador simple con `weasyprint` o `xhtml2pdf` desde
   un template Django, descargable desde el modal de cuotas.
   Esfuerzo: ~3 hs.
3. **Atajos `Ctrl+N` y `Ctrl+F`** dependientes de la ruta:
   en `/sales` abre Nueva Venta; en `/quotas` enfoca el buscador.
   ~30 min.
4. **Input monetario formateado** con un `<NumberFormat>` propio
   simple (~20 líneas) que formatea con `.` mientras tipea y
   guarda número limpio.

---

## 4. Proceso de venta

### Fortalezas

- **Modelo `Sale` cubre los casos reales**: `unit_price`,
  `discount`, `total_price`, `down_payment`, `payment_form`,
  `seller`, `notes`. Refleja el flujo "entrega + cuotas".
- **Generador de plan de cuotas** ([Sales.jsx:1535](../../playa-frontend/src/pages/Sales.jsx))
  con preview editable, suma en vivo, comparación con
  "a financiar". Es la mejor parte del producto.
- **`mark_as_paid` acepta fecha real y nota** (tras quick-win).
  Permite registrar pagos retroactivos.
- **WhatsApp con teléfono normalizado** y mensaje en español PY.
- **Refuerzos como concepto editable** vía el campo "Nota" en
  cada cuota del preview — flexible pero requiere disciplina.

### Debilidades

- **El cierre de venta no marca el vehículo como `sold`**. El
  vehículo queda `available` aunque su FK aparezca en una `Sale`.
  Es el bug raíz de las 25+ inconsistencias detectadas.
- **No hay estado `Sale.reserved`**. Si un cliente seña un auto,
  se lo registra como `Sale.status='pending'`, pero el vehículo no
  pasa a `reserved`. Cualquier otro vendedor puede revenderlo.
- **No hay flujo de "negociación"**: el `discount` se anota como
  monto final, no como historia. Si el cliente tiró 3 ofertas, no
  queda registro.
- **No hay documentación adjunta**: no se puede subir foto de
  cédula, contrato firmado, comprobante de transferencia. Esto va
  a ser bloqueante si la empresa pide trazabilidad notarial.
- **Forma de pago de cuota va en `notes`** como `[EF]`, `[TB]`,
  `[CJ]`, `[AC]` (workaround del quick-win). El modelo `Quotum`
  todavía no tiene `payment_form FK`.
- **Sin integración con cobranza bancaria** (boleta, link de
  pago, débito automático). Toda cobranza es manual.
- **Sin financiamiento de terceros**: si la concesionaria empieza
  a operar con una financiera (común en Paraguay), no hay nada en
  el modelo para registrar acreedor.

### Recomendaciones

1. **Transición automática del vehículo al guardar la Sale**:
   en `SaleSerializer.save()` o `Sale.save()`, si `status='completed'`
   poner `vehicle.state='sold'`; si `pending` (= reserva), poner
   `reserved`. Cuando se cancela la venta, volver a `available`.
   *Crítico*. Esfuerzo: 1 hora + script de backfill.
2. **Migrar `[EF]/[TB]/CJ/AC`** del campo notes a un FK
   `Quotum.payment_form`. Crear la migración + serializer + UI del
   modal "Pagar cuota". ~2 hs.
3. **Adjuntos**: campo `attachment = URLField` en Sale y Quotum,
   guardando referencia a Supabase Storage. Permite subir foto de
   comprobante de transferencia desde el celular.
4. **Recibo PDF de pago de cuota** — al marcar pagada, descargar
   un recibo numerado para el cliente.
5. **Flujo de seña**: botón "Reservar" además de "Vender".
   Reserva = `Sale.status='pending'` + `vehicle.state='reserved'`
   + fecha límite de seña (default 7 días) + monto de seña.

---

## 5. Seguridad

### Fortalezas

- **JWT con simplejwt**: rotation de refresh, access de 1 h. OK
  para la escala.
- **Multi-tenant por `enterprise_id`** evita filtración entre
  empresas (vital para si se vende como SaaS).
- **`set_password` reservado a admin** ([base.py:117](../core/views/base.py)).
- **Permisos `/users/`** tras el fix exigen `IsAdmin` para
  list/update/destroy. Antes era un agujero.
- **`AUTH_PASSWORD_VALIDATORS` activos**: longitud mínima,
  password común, similitud al usuario. (Aunque el password
  inicial `autoofertas2026` no cumpliría si fuese validado al
  setearlo — Django no valida en `create_user`.)
- **Logout** documentado como "descartar token en cliente". Aceptable
  pero no real (no hay blacklist).

### Debilidades

- **No hay blacklist de refresh tokens**: si alguien se roba el
  refresh token, sigue válido hasta vencer (1 día). `simplejwt`
  trae blacklist como módulo opcional; está sin activar.
- **Sin rate limiting**: alguien puede botear `/api/users/login/`
  sin freno. Brute-force factible. `django-ratelimit` o
  `drf-ratelimiter` resuelven en 30 min.
- **`CORS_ALLOW_ALL_ORIGINS=True`** habitual en dev — chequear que
  en producción está en una whitelist. (No verifiqué la config
  de prod en este review.)
- **Audit log roto**: como ya dije, `object_id=0` siempre. No sirve
  para forensics.
- **Mensajes de error filtran datos**: `JSON.stringify(err.response.data)`
  termina en pantalla, a veces con info sensible. El usuario podría
  pegarlo a Whatsapp sin pensar.
- **Tokens JWT en `localStorage`**: vulnerables a XSS. Tailwind CDN
  + Babel inline aumentan la superficie de XSS si alguien inyecta
  HTML por un campo (notes, address). Mitigación real: validar y
  escapar lado backend, o moverse a httpOnly cookies (cambio grande).
- **No hay 2FA**, ni siquiera para el usuario admin. Para una app
  con montos en Gs. de cientos de millones, es deuda.
- **Sin auditoría de logins**: no hay registro de "papa entró el
  martes 14 a las 9:30". El AuditLog actual sólo registra mutaciones.
- **Falta validación de teléfono / email en serializer**: aceptan
  cualquier string. WhatsApp ya se rompía con teléfonos mal
  cargados (mitigado en quick-win, pero el problema raíz sigue).

### Recomendaciones

1. **Rate limit en login**: 5 intentos por IP/minuto. `django-ratelimit`
   con decorador en la action `login`. ~20 min.
2. **Activar SIMPLE_JWT BLACKLIST**: `INSTALLED_APPS` + migrar +
   logout invalida refresh. ~30 min.
3. **Auditar logins**: log dedicado o reusar `AuditLog` con
   `action='login'`. ~30 min.
4. **2FA para admin y dueño** vía `django-otp` con TOTP (Google
   Authenticator). ~3 hs.
5. **Sanear errores antes de mostrarlos al usuario**: traducir
   mensajes técnicos a humanos en un interceptor de axios o en
   las páginas.
6. **CORS whitelisting** explícito en producción (no `_ALL_`).
7. **Validators** en serializers para `phone` (regex
   `^\+?[0-9\s\-\(\)]{6,20}$`), `email` (ya valida con
   `EmailField`).

---

## 6. Integraciones externas

### Fortalezas

- **WhatsApp link directo** ya está y funciona (post-quick-win).
- **drf-spectacular** expone OpenAPI 3.0 estándar — cualquier
  herramienta (Postman, Zapier, n8n) puede consumir.

### Debilidades

- **No hay integración real**: no WhatsApp Business API (solo el
  link), no email, no contabilidad, no SET (sistema impositivo
  paraguayo), no IVA/timbrado, no facturación electrónica
  (el "FE Paraguay" se vuelve obligatorio progresivamente).
- **Sin webhook de pagos**: si quisieran aceptar pagos de cuotas
  por link (Bancard, Pago Express), no hay receptor.
- **No hay exportación contable** estándar (CSV de movimientos
  para entregar al contador externo).
- **ExchangeRate** ([models/inventory.py](../core/models/inventory.py))
  tiene tabla y endpoint pero **0 cotizaciones cargadas**. Cualquier
  precio en USD se rompe silenciosamente.
- **Sin notificaciones push / email automáticas**: cuotas que
  vencen, ventas cerradas, alertas al dueño — todo es manual.

### Recomendaciones

1. **Importador de cotización USD/PYG** automatizado: 1 management
   command que lee del BCP (Banco Central) o de un scraper simple
   diario y crea un `ExchangeRate`. ~1 hora.
2. **Notificaciones de cuotas próximas a vencer**: cron diario que
   manda un mail/WhatsApp template al cliente 3 días antes del
   vencimiento. Esfuerzo medio; alto retorno emocional ("el sistema
   me ayuda a cobrar"). ~6 hs (sin enviar realmente — generando
   solo los mensajes y dejándolos en una cola visible).
3. **Export CSV de movimientos** mensual para entregar al
   contador. Endpoint `/api/exports/monthly_movements?month=…`.
   ~2 hs.
4. **Facturación electrónica (FE Paraguay)** vía un proveedor
   (Faktur, Wsfe, etc.) — no se hace en una semana. Empezar
   modelando un `Invoice` separado de la `Sale` cuando llegue el
   momento.
5. **WhatsApp Business API** (no el link `wa.me`): permite
   plantillas aprobadas, foto del vehículo adjunta, automatización
   masiva. Solo cuando justifique el costo mensual.

---

## 7. Mantenibilidad del código

### Fortalezas

- **`MEMORY.md`** dentro de `~/.claude` mantiene convenciones
  acumuladas (formato Gs., códigos CM/MC, workflow de BD).
- **Docs en `playa/docs/`** (MIGRACION_PLAYBOOK, PLAN_PERFORMANCE,
  DELTA_REPORT, UX_AUDIT, este mismo doc) — buena costumbre.
- **`scripts/migracion/`** organizado y reproducible (check_data,
  create_indexes, import_stock, bench_apis). Está al nivel de un
  data engineer.
- **drf-spectacular** ya está integrado: documentación API
  autogenerada.
- **Estructura de `core/views/{base,inventory,sales,dashboard}.py`**
  es clara.
- **Frontend dividido por archivos** (un pages/X.jsx por pantalla).

### Debilidades

- **`pytest.ini` está mal formado** (cabecera `[pytest]"""` mezclada
  con docstring, addopts en una sola línea ilegible). `pytest`
  probablemente no parsea bien la config.
- **Tests reales**: 1 solo archivo (`tests/test_models.py`,
  156 líneas) cubriendo creación básica de `CustomUser`. No hay
  test de ningún viewset, permission, serializer, action,
  `mark_as_paid`, `data_quality`, ni del flujo de creación de
  venta. La cobertura efectiva es muy baja.
- **Archivos sueltos en la raíz** del backend: `CRM_FINAL_REPORT.md`,
  `CRM_VERIFICATION_FINAL.md`, `FIX_DASHBOARD_ERROR.md`,
  `link_all_data.py`, `link_enterprise.py`, `do_link.py`, etc. La
  raíz tiene >80 archivos sueltos. Eso entorpece la lectura para
  alguien nuevo.
- **Comentarios excesivos** en algunos lados, ausentes en otros.
  En particular `core/permissions.py` tiene un permiso medio armado
  (`CanViewOwnBranchData`) que termina con `return True` para
  vendedores — la intención no queda clara y es engañosa.
- **Frontend sin linter**: ESLint/Prettier no están corriendo. Los
  estilos de código varían entre archivos.
- **Sin CI**: no hay `.github/workflows/` ni similar. Cambios
  rompedores entran a `main` sin testear.
- **`migrate_legacy_data.py` y `migrate_quotas.py`** sueltos en la
  raíz. Cuando se borren los datos viejos, ¿quién decide qué se
  borra?
- **Sin pre-commit hooks**: el commit del `pytest.ini` mal armado
  no fue detectado por nadie.

### Recomendaciones

1. **Limpiar la raíz del backend**: mover los `*.md` antiguos a
   `docs/archive/`, los scripts a `scripts/oneoff/`. Mantener solo
   `manage.py`, `requirements.txt`, `README.md`, `pyproject.toml`
   (si se usa), `.env.example`, `Dockerfile`, etc. ~30 min.
2. **Arreglar `pytest.ini`** formato real:
   ```ini
   [pytest]
   DJANGO_SETTINGS_MODULE = playas_autos.settings
   python_files = tests.py test_*.py *_tests.py
   addopts = --cov=core --cov-report=term-missing
   testpaths = tests core
   ```
   Y arrancar coverage real.
3. **Tests críticos**: que existan al menos:
   - `test_mark_as_paid_accepts_payment_date`
   - `test_perform_create_respects_branch`
   - `test_user_permission_blocks_non_admin`
   - `test_data_quality_filters_by_branch`
   - `test_whatsapp_normalizes_phone`
   Estos cubren los bugs que ya pasaron. Esfuerzo: medio día.
4. **CI simple** con GitHub Actions: en push a `main`, correr
   `pytest` + `python manage.py check`. ~30 min.
5. **Pre-commit hook**: `black` + `isort` + `python manage.py check`.
   ~20 min.
6. **README activo**: un solo doc en la raíz que diga "cómo
   levanto esto, dónde está la BD, cómo corro tests, cómo despliego".
   Hoy hay 12 archivos `*READY*.md`, `*COMPLETE*.md`, `*FINAL*.md`
   compitiendo.

---

## 8. Innovación tecnológica

### Postura honesta

A nivel **negocio**, AUTO OFERTAS hace ~80 ventas/año. El ROI de
microservicios, IA, search vectorial, etc. es **negativo** acá.
La innovación útil es la que reduce fricción al vendedor, no la
que suena bien en un brochure.

Dicho esto, hay 3 lugares donde un toque de "tech moderno" sí
pagaría:

1. **Búsqueda fuzzy de clientes** ya tenés GIN trigram en Postgres
   ([create_indexes.py:69](../scripts/migracion/create_indexes.py)).
   Falta usarlo desde el viewset: en `CustomerViewSet.get_queryset`,
   aceptar `?search=` y filtrar por similarity, no por LIKE. Cuando
   rocio escribe "Bogad" debería encontrar "Bogado".
2. **Sugerencias de precio**: cuando se carga un vehículo nuevo,
   sugerir precio basado en el histórico de modelos similares
   (marca + modelo + año ±1) — promedio del último año. Es 20
   líneas de Django ORM, no requiere ML.
3. **Detección automática de inconsistencias**: el endpoint
   `/data_quality/` que ya creamos. Es un "system smell detector"
   simple. Mañana podría agregar un score "salud del sistema".

### Lo que NO recomiendo (todavía)

- **Microservicios**: 427 ventas no justifican romper el monolito.
- **GraphQL**: DRF + OpenAPI alcanza; cambiar a GraphQL sólo
  agregaría complejidad.
- **Embeddings + búsqueda semántica**: para 624 vehículos un
  `vin ILIKE '%xxx%'` + GIN trigram alcanza. Volvé en 10× más datos.
- **Generador de descripciones con LLM**: tentador, pero los
  vendedores describen el auto en persona; no hay "publicación"
  en el sistema (no se publica a MercadoLibre). Sin canal, no hay
  retorno.
- **Reconocimiento de voz para cargar ventas**: gimmick. Más
  rápido tipear.
- **Predicción de mora con ML**: con 1.000 cuotas pagadas el
  modelo overfittea. La regla actual (días de atraso) ya da el
  90% de la señal.

### Recomendaciones realmente útiles

1. **Activar trigram en `?search=` de Customer y Vehicle**. ~2 hs.
2. **Endpoint `/vehicles/suggest_price/`** que dado brand+model+year
   devuelve `{avg, min, max, count}` del histórico. ~1 hora. La UI
   del modal "Crear vehículo" lo consume y muestra "Sugerido:
   Gs. X.XXX.XXX (basado en N ventas similares)".
3. **`Sale.tags`** (campo `JSONField` con lista de tags libres
   tipo `"financiación bancaria"`, `"venta directa al cliente"`,
   `"refuerzos cada 6 meses"`). Sin modelo nuevo, sin migración
   pesada. Permite categorizar para reportes después.

---

## 9. Rendimiento

### Fortalezas

- **17 índices Postgres creados** ([create_indexes.py](../scripts/migracion/create_indexes.py))
  incluyendo composite `(branch_id, status)` para Sale,
  `(status, due_date)` para Quotum, `(branch_id, state)` para
  Vehicle. Bien pensado.
- **`select_related` en los viewsets críticos**: Sale carga
  customer, vehicle, brand, model, branch, payment_form, seller
  en una sola query.
- **Conexión Postgres con `conn_max_age=600` + health checks**:
  reusa la conexión TCP/SSL entre requests, evita los ~2 s de
  handshake por request.
- **`DISABLE_SERVER_SIDE_CURSORS`** correctamente seteado para el
  transaction pooler de Supabase.
- **`TimingMiddleware`** loguea endpoints >500 ms y agrega
  header `X-Response-Time-ms`. Excelente para detectar regresiones.
- **`bench_apis.py`** automatiza un benchmark — está al nivel de
  un team con SRE.

### Debilidades

- **`top_morosos`** era N+1 (15 queries dentro del loop) — ya
  arreglado en quick-win.
- **`CustomerSerializer.sales_count`** era N+1 (~300 queries por
  carga de Sales) — ya arreglado.
- **`CustomerViewSet`** sin `select_related('enterprise')` →
  ~300 queries adicionales por carga de la lista — ya arreglado.
- **`Sales.jsx` cargaba 5 endpoints en paralelo** trayendo ~2-3 MB
  cuando solo necesitaba `/sales/` — ya arreglado (lazy load).
- **Sin paginación visible**: todo es `page_size=1000`. Con 3.044
  cuotas en `/quotas?status=all` se trae todo. JSON ~1 MB.
- **`Ctrl+K` global search** trae los 1.000 records en cada
  keystroke ([KeyboardShortcuts.jsx:78](../../playa-frontend/src/components/KeyboardShortcuts.jsx)).
  Sin debounce. En conexión mala es agresivo.
- **`LocMemCache`** con varios workers → resultados inconsistentes
  para el mismo usuario (ya mencionado en §1).
- **No hay índice GIN para búsqueda fuzzy en `vehicle.vin`**.
  Búsquedas tipo `vin ILIKE '%abc%'` hacen seq scan.

### Recomendaciones

1. **Paginación real** con `PageNumberPagination` y `page_size`
   default = 50. UI con paginador. Los exports siguen pidiendo
   `page_size=1000` con un flag. Reduce JSON ~10×.
2. **Debounce 250 ms** en `Ctrl+K` antes de disparar las
   queries. ~5 min.
3. **Endpoint dedicado `/api/search/?q=...`** server-side
   (con LIMIT 10 + trigram) que reemplace el cliente que trae
   todo y filtra en JS.
4. **`LocMemCache` → Redis** cuando el throughput justifique;
   mientras tanto, **desactivar cache** del dashboard si causa
   confusión.
5. **Índice GIN trigram en `vehicle.vin`** y `vehicle.license_plate`:
   ```sql
   CREATE INDEX idx_vehicle_vin_trgm ON core_vehicle USING gin (vin gin_trgm_ops);
   ```
6. **Compresión gzip** activa en Render (probablemente ya
   activado, verificar): JSONs grandes bajan 5-10×.

---

## Matriz de impacto y esfuerzo (lo que recomiendo hacer ya, lo que después)

| Recomendación | Impacto | Esfuerzo | Cuándo |
|---|---|---|---|
| Vehículo pasa a `sold` al crear Sale | Alto | S (1h + script) | **Esta semana** |
| Vista `/customers/:id` con historial | Alto | M (4-6h) | **Esta semana** |
| Quotum.payment_form (FK) — migrar `[EF]/...` | Alto | M (3h) | **Esta semana** |
| Management command `recalc_quota_status` diario | Alto | S (1h) | **Esta semana** |
| Rate limit + JWT blacklist | Medio-alto | S (1h c/u) | Próxima |
| Tests críticos (5-10 tests sobre los bugs ya pasados) | Alto en mantenibilidad | M (½ día) | Próxima |
| Paginación real | Medio | M (3h) | Próxima |
| PDF cronograma de cuotas | Alto (cara al cliente) | M (3h) | 2 semanas |
| Importador automático de USD/PYG | Bajo (hoy) / Alto (cuando se cargue USD) | S (1h) | 2 semanas |
| Notificaciones WhatsApp 3 días antes del vto | Alto | L (6h) | Mes 1 |
| Fotos del vehículo + adjuntos | Alto en experiencia | M (4h) | Mes 1 |
| Limpieza raíz + CI + pre-commit | Medio | S (1-2h) | Cuando entre el 2º dev |
| Build real del frontend (Vite) | Medio | M (½ día) | Cuando duela el tiempo de carga |
| Microservicios / ML / GraphQL | — | — | **Hoy: no** |

---

## Conclusión

El sistema está **mejor armado de lo que aparenta para una concesionaria
familiar**: multi-tenant real, índices pensados, schema OpenAPI, scripts de
migración serios, separación frontend/backend, dashboards funcionales.

Lo que falta para que **opere bien sin sobresaltos** no son
features grandes, son **3 acoplamientos faltantes** entre piezas que ya existen:

1. **Sale ↔ Vehicle.state** (al cerrar venta, marcar vendido).
2. **Cuota ↔ forma de pago** (EF/TB/CJ/AC como FK, no como notes).
3. **Cliente ↔ vista de historial** (la pantalla que reemplaza la hoja
   del Excel).

Eso, sumado a los quick-wins ya aplicados (filtro de sucursal,
panel de inconsistencias, WhatsApp, lazy-load, permisos) deja el sistema
listo para que `papa` lo abra el lunes sin volver al Excel. Las cosas
"sexy" (IA, microservicios) se las puede vender el día que se duplique el
volumen — hoy entorpecerían.
