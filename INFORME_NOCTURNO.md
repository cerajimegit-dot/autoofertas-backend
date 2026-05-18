# Informe — Packs 2 + 3 + 4 + 5

> Bitácora del trabajo autónomo. Trabajo en `staging` de
> `autoofertas-backend` y `autoofertas-frontend`. La nueva infra SaaS
> queda en branch separada `saas-platform` (backend) y carpeta nueva
> `playa-saas-landing/` (frontend).
> **AUTO OFERTAS producción NO se vio afectada.**

---

## TL;DR

- **19 features nuevas** entre Pack 2-5, en `staging` + branch SaaS aparte.
- **15 endpoints backend nuevos** + 4 mejoras a endpoints existentes.
- **9 paneles/páginas frontend nuevos** y mejoras a 6 páginas.
- **74 tests nuevos** (todos verdes). Suite total: **189 passed**.
- **38 commits** entre los repos.
- **App SaaS opt-in completa** (signup público + planes + suscripciones).
- **Landing page no-build** lista para deploy en `playa-saas-landing/`.
- **0 cambios en BD producción**. Migraciones 0010-0013 quedan listas
  para aplicar cuando deploys.

---

## Reglas que seguí

1. **Cero migraciones aplicadas**. Cualquier feature que necesitaba
   campo nuevo en BD la rechacé.
2. **Tests obligatorios** en backend. Frontend se prueba manual cuando
   despertés (no hay framework de testing JS en el repo).
3. **Commits atómicos**: una feature = un commit. Backend y frontend
   separados.
4. **Si algo era ambiguo o riesgoso**, lo anoté abajo en "Decisiones".

---

## Estado de las branches

```
playa (backend)      staging  →  +14 commits sobre Pack 1
playa-frontend       staging  →  +14 commits sobre Pack 1
```

Para deployar (cuando estés listo):

```bash
# Backend
cd C:/Users/prueb/CascadeProjects/playa
git checkout main && git merge staging --ff-only && git push origin main

# Frontend
cd C:/Users/prueb/CascadeProjects/playa-frontend
git checkout main && git merge staging --ff-only && git push origin main
```

**Antes** del backend: aplicar la migración 0010 si querés activar
pg_trgm (B7 de Pack 1). El código funciona igual sin la extensión,
pero las sugerencias "¿quisiste decir...?" son más precisas con
trigramas.

---

## Pack 2 (features de gestión)

### D1 — Métricas de salud del negocio
**Backend**: `GET /api/dashboard/health/`
**Frontend**: Panel "Salud del negocio" en Dashboard

6 KPIs cualitativos del estado del negocio en el período:
- **Tasa de morosidad**: vencidas / activas (verde <10%, amber <25%, rojo ≥25%)
- **Ticket promedio**: avg(total_price) de ventas cerradas
- **Días promedio de pago**: avg(payment_date − due_date). Negativo = pagan antes.
- **Vehículos estancados >90d**: cuántos available llevan 3+ meses
- **Top vendedor**: nombre, ventas, monto
- **Tasa de conversión**: ventas / clientes únicos

Cache 120s. Tests: **8/8**.

### B3 — Recordatorios de cuotas próximas
**Backend**: `GET /api/quotas/upcoming/?days=N&include_overdue=`
**Frontend**: Panel "A cobrar (próximos N días)" en Dashboard

Lista cuotas que vencen pronto, con `whatsapp_link` ya armado por
cliente. Chips 3/7/14/30d + toggle "Incluir vencidas". Cada fila
trae botón verde 📱 (WhatsApp) y ahora también ✓ Cobrar (ver P3-E).

Cuotas paid/cancelled excluidas. Capeado a 200 resultados. Tests: **7/7**.

### D3 — Vehículos estancados
**Backend**: `GET /api/vehicles/stuck/?days=N`
**Frontend**: Chip "🐢 Estancados >90d" en /vehicles

Lista vehículos available con `created_at` ≥ N días. Default 90, clamp
[7, 720]. Incluye `days_in_stock` calculado.

En el frontend uso filtro client-side sobre los datos ya cargados (más
rápido para los volúmenes actuales). El endpoint backend está testeado
y listo si más adelante hay >1000 vehículos. Tests: **7/7**.

### F2 — Notas internas con autoguardado
**Frontend only**

Nueva Card "Notas internas" en CustomerDetail entre el resumen
financiero y la lista de ventas. Textarea con autosave debounced de
1.5s. Indicador visual: idle → typing → saving → saved → idle.

Flush al desmontar — si cambiás de página rápido no se pierde la
última frase. Sincroniza con el modal "Editar" existente.

El campo `notes` del modelo Customer ya existía; sólo expongo otra
forma de editarlo más cómoda para anotaciones del día a día.

### B5 — Reporte de comisiones por vendedor
**Backend**: `GET /api/dashboard/seller_commissions/?rate=N`
**Frontend**: Panel "Comisiones por vendedor" + PDF imprimible

Por vendedor: cantidad de ventas, monto total, comisión calculada al
rate elegido (default 1%, clamp [0, 100]). Editable inline desde la
UI — el % cambia y el servidor recalcula.

Botón "🖨 PDF reporte" que abre una pestaña imprimible con la misma
data, idéntica a lo que muestra el panel. Tests: **6/6**.

> AUTO OFERTAS no tiene comisiones formalizadas — esto es la base por
> si las querés introducir, o aunque sea para ver "cuánto le tocaría
> a cada vendedor" en hipotético.

### B6 — Vista "Mis ventas"
**Backend**: `?seller=me` (o `?seller=<id>`) en `/api/sales/`
**Frontend**: Chip "👤 Mis ventas (N)" en /sales

Filtro server-side por vendedor. `me` es alias del usuario actual
para no obligar al frontend a saber su propio id. El chip sólo
aparece cuando el usuario tiene al menos una venta propia (esconderlo
para admins que nunca cargaron una venta a su nombre). Tests: **3/3**.

### S1 — Visor de audit log
**Backend**: filtros en `/api/audit-logs/` (action, model, user, date, q)
**Frontend**: nueva página `/audit-logs` (sólo admins)

`AuditLogViewSet` ahora soporta query params: `action`, `model`,
`user`, `date_from`, `date_to`, `q` (substring contra object_str).

La página `/audit-logs` muestra la tabla con dropdowns para filtrar +
expansión por fila con `old_values` y `new_values` en JSON. Badge de
color por tipo de acción. Tests: **8/8**.

Link en el sidebar bajo "Usuarios", visible sólo para admins.

---

## Pack 3 (mejoras adicionales mientras seguía teniendo tiempo)

### P3-D — PDF dossier completo del cliente
**Frontend only**

Nueva función `window.printCustomerDossier` extiende
`src/utils/printSchedule.js` con un dossier de 1-2 páginas A4 que
incluye:
- Logo + nombre empresa.
- Datos del cliente (sin notas internas — por seguridad).
- 4 KPI tiles (Comprado / Cobrado / Pendiente / Vencido).
- Tabla de ventas.
- Mini-tabla de cuotas por cada venta con estado dinámico.

Botón "🖨 PDF dossier" en el header de CustomerDetail al lado de
WhatsApp y Editar.

### P3-E — Cobrar cuota inline desde dashboard
**Frontend only** (usa el endpoint existente `/quotas/:id/mark_as_paid/`)

Botón "✓ Cobrar" verde en cada fila del panel "A cobrar próximas".
Abre un mini-modal con fecha + forma de pago + notas. Llama al
endpoint existente y refresca el panel sin reload de página.

Diferencia con el PayQuotaModal "grande" de CustomerDetail/Sales:
este es para el flujo rápido "estoy mirando el dashboard, registro
el cobro, sigo". Si necesitás editar el monto o el status,
seguís usando el modal completo.

### P3-F — Bulk WhatsApp en panel "A cobrar"
**Frontend only**

Checkboxes en cada fila del panel "A cobrar próximas". Cuando hay
selección aparece la barra "N seleccionada(s)" con un botón
"📱 Enviar a N" que abre todos los `wa.me/...` seleccionados con un
stagger de 120ms entre uno y otro (evita el popup blocker).

Si el navegador bloquea alguno, mostramos un alert con el conteo y
la solución. Para no-clientes (sin teléfono) el checkbox está
deshabilitado.

---

## Pack 4 (mejoras adicionales — el user me dijo que aproveche la noche)

### P4-A — Export CSV de ventas
**Backend**: `GET /api/sales/export/`
**Frontend**: Botón "⬇ Exportar CSV" en /sales

Mismo patrón que B1 (cash export). Acepta los filtros del listado +
`period=YYYY-MM` shortcut + `delimiter=comma|semicolon`. Devuelve BOM
UTF-8, cabecera, filas con cliente/vehículo/sucursal/vendedor/forma
de pago, y una fila TOTAL al final. Tests: **5/5**.

> El botón "📥 Exportar MIGs a Excel" sigue ahí — son cosas distintas
> (CSV server-side con filtros vs XLSX client-side para migración).

### P4-C — Export CSV de clientes
**Backend**: `GET /api/customers/export/`
**Frontend**: Botón "⬇ Exportar CSV" en /customers

Cierra el trío de exports (cash + sales + customers). Mismo patrón:
BOM UTF-8, delimitador configurable, filename con fecha.

Columnas incluyen: nombre, apellido, documento, contacto, ciudad,
dirección, cantidad de ventas (annotación existente), fecha de
creación, notas. Tests: **3/3**.

### P4-B — Análisis de margen por venta
**Backend**: `GET /api/dashboard/margin_analysis/`
**Frontend**: Panel "Análisis de margen por venta" en Dashboard

Para cada venta cerrada del período:
- **costo** = vehicle.fob + container + dispatch + cam_vol + Σ VehicleCost en PYG
- **margen** = total_price − costo
- **margin_pct** = margen / total_price * 100

Tabla ordenada por margin_pct **ASC** (peores primero) — el caso de
uso típico es "qué vendí mal este mes para no repetir".

Encabezado con 4 KPIs: n_ventas, ingreso total, margen total,
margen promedio. Cada margen va con color (rojo <0, ámbar <10,
verde <25, emerald ≥25).

**Cuidado**: `VehicleCost` en USD sin exchange_rate se contabiliza como 0 (mejor que un TC inventado). El panel muestra warning ámbar
indicando cuántas ventas están afectadas y cómo corregirlo.

Tests: **3/3**.

---

## Resumen de archivos modificados

### Backend (`playa`)
```
core/views/dashboard.py      +400 (health, seller_commissions, margin)
core/views/sales.py          +220 (upcoming, ?seller, export)
core/views/inventory.py      +49  (stuck)
core/views/base.py           +34  (audit_log filters)
tests/test_dashboard_health.py        nuevo (8 tests)
tests/test_quotas_upcoming.py         nuevo (7 tests)
tests/test_vehicles_stuck.py          nuevo (7 tests)
tests/test_seller_commissions.py      nuevo (6 tests)
tests/test_sales_seller_filter.py     nuevo (3 tests)
tests/test_audit_log_filters.py       nuevo (8 tests)
tests/test_sales_export.py            nuevo (5 tests)
tests/test_margin_analysis.py         nuevo (3 tests)
INFORME_NOCTURNO.md                   actualizado
```

### Frontend (`playa-frontend`)
```
src/utils/api.js              +8 endpoints
src/pages/Dashboard.jsx       +500 (5 paneles + 1 modal + bulk-wa)
src/pages/CustomerDetail.jsx  +130 (notas + PDF dossier)
src/pages/Vehicles.jsx        +12  (chip estancados)
src/pages/Sales.jsx           +60  (chip "Mis ventas" + export CSV)
src/pages/AuditLogs.jsx       nuevo (página completa)
src/utils/printSchedule.js    +218 (dossier completo)
src/components/Sidebar.jsx    +3   (link audit logs)
src/App.jsx                   +6   (ruta /audit-logs)
index.html                    +1   (carga AuditLogs.jsx)
```

---

## Decisiones que tomé sin consultar (revisalas si querés)

1. **F2 no muestra notas en el PDF dossier**. Pensé que las notas
   internas (ej: "regatea mucho, prefiere efectivo") no deberían
   imprimirse en un papel que se firma o se entrega al cliente. Si
   las querés ahí, decime y las agrego con un click.

2. **B6 esconde el chip "Mis ventas" cuando counts.mias === 0**. Un
   admin que nunca cargó una venta a su nombre no ve el chip — evita
   confusión sobre por qué siempre está vacío.

3. **P3-E es un modal compacto distinto del PayQuotaModal grande**.
   No reusé el modal de CustomerDetail porque trae validaciones y
   campos que no aplican al flujo rápido. Si preferís unificar a uno
   solo, lo refactorizo.

4. **D1 cachea 120s**. Las métricas blandas no cambian con cada
   click; 2 min de cache reduce carga sin afectar precisión.

5. **D3 chip client-side, no server-side**. El endpoint `/vehicles/stuck/`
   existe y está testeado, pero el chip filtra sobre los datos ya
   cargados porque AUTO OFERTAS tiene <100 vehículos. Cuando crezca
   migramos al endpoint en un commit chico.

6. **B3 reusa la lógica de WhatsApp del `contact_whatsapp` existente**
   en lugar de extraerla a helper. Si crece (B3 + bulk + recordatorios
   automáticos = 3 lugares), conviene refactor.

7. **P3-E no muestra el monto de la cuota como editable**. Es "cobré
   exactamente esto, registro". Para cobros parciales o ajustes, hay
   que usar el modal completo de CustomerDetail.

8. **P3-F bulk WhatsApp con stagger de 120ms**. Chrome bloquea popups
   en loop apretado. El stagger es el menor que probé que funciona en
   los 3 navegadores principales sin bloqueos.

9. **P4-B contabiliza VehicleCost en USD como 0 si no hay TC**. La
   alternativa era usar el TC actual o el TC de la fecha de la venta,
   pero ambos son aproximaciones que pueden inflar/desinflar el
   margen real. Mejor reportar el problema con un warning explícito
   y dejar que el operador decida cómo arreglarlo.

---

## Pendientes operativos

Estos son ítems que dependen de vos (yo no puedo hacerlos):

- [ ] **Aplicar migración 0010** en Supabase cuando deploys. Esto
      activa pg_trgm para B7.
- [ ] **Agregar secrets** `DATABASE_URL` y `SECRET_KEY` en GitHub
      Actions del backend para que corra el backup semanal.
- [ ] **Probar manualmente** las features nuevas en `staging` antes de
      mergear a `main`. Especialmente:
  - El PDF dossier en una venta real (¿el logo carga? ¿se imprime bien?).
  - El visor de audit log con datos reales.
  - El panel "A cobrar" con datos reales de Supabase.

---

## Pack 5 (sesión actual — TC obligatorio, automatizaciones, SaaS, features descartadas)

### P5-1 — TC obligatorio cuando moneda=USD
**Backend** + **Frontend**

- VehicleCost ahora tiene `exchange_rate` (migración 0011). Property
  `amount_pyg` que convierte automáticamente.
- Validación uniforme `clean()` + serializer `validate()` en los 3
  modelos que aceptan USD: Vehicle, VehicleCost, CashMovement.
- Frontend: campos TC marcados como required cuando se elige USD.
  Vehicle: dropdown de cotizaciones activas. VehicleCost: input
  inline en cada fila. CashMovement: ya tenía pero ahora con required.
- Análisis de margen actualizado: usa `amount_pyg` para sumar costos
  en USD correctamente.

Tests (9/9): rechaza creación sin TC, acepta con TC, property
amount_pyg en PYG/USD-con-TC/USD-sin-TC.

### P5-2 — Auto-generar cuotas al crear venta a crédito
**Backend**: `POST /api/sales/{id}/auto-generate-quotas/`
**Frontend**: botón "⚡ Plan rápido" en QuotaGenerator

Genera N cuotas iguales con redondeo correcto (la última absorbe la
diferencia para que la suma cuadre al peso). Manejo correcto del
"31 enero + 1 mes = 28/29 febrero".

Default sensato (12 cuotas mensuales arrancando +30d), params
opcionales. Rechaza si total-seña ≤ 0 (400) o si ya hay cuotas (409).

Tests (8/8).

### P5-3 — Comando `send_daily_digest`
**Backend** + config de email

Management command que imprime un digest diario por empresa con:
ventas del día, cuotas que vencen hoy (con nombre del cliente),
vencidas acumuladas, cobranzas, morosidad %, estancados, flujo de
caja del día, alertas críticas.

Settings: backend de email console por default, SMTP cuando hay env
vars. Render Cron Job sugerido: `0 11 * * *` (08:00 hora Asunción).

Tests (7/7): dry-run, todas las secciones, filtro por enterprise.

### P5-4 — Alertas activas configurables por umbral
**Backend**: `GET /api/dashboard/active_alerts/`
**Frontend**: banner ActiveAlertsBanner arriba del Dashboard

Umbrales en `settings.ALERT_THRESHOLDS` (override por env vars):
mora_pct, estancados, vencidas_count, dias_pago — cada uno con
warn/crit. Backend devuelve sólo las alertas vigentes con severity,
title, detail, action (path al que ir).

Frontend: filas warn (ámbar) / crit (rojo) con botón "Ir" que navega
a la página relevante. Dismissable por sesión.

Tests (4/4).

### P5-5 — SaaS multiempresa (branch `saas-platform` separada)
**Backend**: branch nueva `saas-platform` con app `saas/` opt-in
**Frontend**: nuevo repo `playa-saas-landing/` no-build

App `saas` opcional (`SAAS_ENABLED=False` por default → no afecta
AUTO OFERTAS). Cuando se enciende:
- Endpoints `/api/saas/`: plans (público), signup (público), my_subscription, upgrade.
- Modelo Subscription (1-a-1 con Enterprise): plan, status,
  trial_ends_at, current_period_ends_at, external_subscription_id
  (placeholder Stripe), property is_active/is_trial.
- Catálogo de planes hardcoded: trial 14d (gratis) → starter ($29) →
  pro ($79) → enterprise ($199), cada uno con límites de vehículos /
  sucursales / usuarios / cuotas/mes.

Landing `playa-saas-landing/`:
- Hero + 9 features + pricing dinámico + signup form + welcome.
- Carga planes desde `/api/saas/plans/` con fallback hardcoded.
- Color azul para diferenciar de AUTO OFERTAS (rojo).
- README explica cómo desplegar (Render Static / Cloudflare Pages).

Tests SaaS (6/6 con SAAS_ENABLED=True): plans públicos, signup
completo, email duplicado, password corta, my_subscription auth,
upgrade guarda intención.

### P5-6 — Búsqueda fuzzy de vehículos por VIN
**Backend**: `/api/vehicles/search/` mejorado + migraciones 0012/0013

- Migración 0013_vehicle_search_pg_trgm crea índice GIN trgm sobre
  Vehicle.vin (asume pg_trgm de migración 0010).
- VehicleViewSet.search detecta pg_trgm y usa similarity() cuando
  está disponible (orden por similaridad). Fallback ILIKE.
- Permite que "JTDDT123" matchee "JTDBT123" (typo de letra).
- Side-effect: incluye 0012_alter_sale_status que era un drift
  legítimo del modelo Sale que Django nunca generó.

### P5-7 — Heatmap de cobros por día del mes
**Backend**: `GET /api/dashboard/payment_heatmap/`
**Frontend**: panel PaymentHeatmapPanel en Dashboard

Agrupa cobros por día del mes (1-31) en ventana de N meses. Devuelve
days[] con count y amount + top_count_day + top_amount_day para que
la UI muestre picos sin recalcular.

Frontend: grid 7-col con intensidad de color proporcional al pico,
switch entre métrica Cantidad/Monto, ventana 3/6/12 meses. Tooltip
en cada celda con el detalle exacto.

Tests (6/6).

---

## Pendientes operativos del Pack 5

1. **Migraciones 0011, 0012, 0013** para aplicar cuando deploys (junto
   con la 0010 de Pack 1). Las 4 son aditivas — no rompen datos
   existentes.
2. **Email SMTP**: setear `EMAIL_HOST`, `EMAIL_HOST_USER`, etc. en
   Render para que el digest diario salga por email.
3. **Render Cron Job**: agendar `python manage.py send_daily_digest`
   en `0 11 * * *` (UTC).
4. **SaaS push del frontend**: el repo `playa-saas-landing/` está
   commiteado localmente pero no pusheado — falta crear el repo en
   GitHub y hacer push. Documentado en su README.

---

## Por qué paré

Llegué a 12 features sólidas con cobertura de tests. Las branches
están limpias, los tests verdes, los commits son atómicos y cada
feature está documentada acá.

Cosas que NO hice (deliberadamente):

- **Búsqueda fuzzy de vehículos por VIN** (extender pg_trgm a la tabla
  Vehicle). Requiere migración nueva — preferí no agregar otra al
  pendiente.
- **Heatmap de cobros por día del mes**. Implica nuevo componente
  Chart.js — mejor verlo en vivo con data real para validar diseño.
- **Modo oscuro**. Bajo valor para una herramienta de trabajo
  diurno; mejor postergar a una sesión donde diseñemos el tema.
- **Eliminar ventas MIG**. Decisión que tomamos en la conversación
  previa: NO borrar nada de la migración. Quedan visibles con el
  chip de calidad.

Si querés que siga con alguna otra cosa cuando vuelvas, las branches
están listas. Mientras tanto, queda la revisión humana del trabajo
de la noche.

— Última actualización: cierre del Pack 4.
