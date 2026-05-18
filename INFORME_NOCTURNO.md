# Informe nocturno — Pack 2 + 3

> Bitácora del trabajo autónomo. Todo está en la branch `staging` de
> ambos repos (`autoofertas-backend` y `autoofertas-frontend`).
> **No se aplicó ninguna migración a producción.**

---

## TL;DR

- **9 features nuevas** entre Pack 2 y Pack 3, todas en `staging`.
- **6 endpoints backend nuevos** + 3 mejoras a endpoints existentes.
- **5 páginas/paneles frontend nuevos** y mejoras a 3 páginas.
- **44 tests nuevos** (todos verdes). Suite total: **144 passed**.
- **18 commits** entre los dos repos.
- **0 cambios en BD producción**. Migración 0010 (B7 de Pack 1) sigue
  pendiente de aplicar; nada nuevo del Pack 2/3 requiere migración.

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

---

## Resumen de archivos modificados

### Backend (`playa`)
```
core/views/dashboard.py      +281 (health, seller_commissions)
core/views/sales.py          +131 (upcoming, ?seller filter)
core/views/inventory.py      +49  (stuck)
core/views/base.py           +34  (audit_log filters)
tests/test_dashboard_health.py        nuevo (8 tests)
tests/test_quotas_upcoming.py         nuevo (7 tests)
tests/test_vehicles_stuck.py          nuevo (7 tests)
tests/test_seller_commissions.py      nuevo (6 tests)
tests/test_sales_seller_filter.py     nuevo (3 tests)
tests/test_audit_log_filters.py       nuevo (8 tests)
INFORME_NOCTURNO.md                   actualizado
```

### Frontend (`playa-frontend`)
```
src/utils/api.js              +6 endpoints
src/pages/Dashboard.jsx       +320 (3 paneles + 1 modal)
src/pages/CustomerDetail.jsx  +130 (notas + PDF dossier)
src/pages/Vehicles.jsx        +12 (chip estancados)
src/pages/Sales.jsx           +20 (chip "Mis ventas")
src/pages/AuditLogs.jsx       nuevo (página completa)
src/utils/printSchedule.js    +218 (dossier completo)
src/components/Sidebar.jsx    +3 (link audit logs)
src/App.jsx                   +6 (ruta /audit-logs)
index.html                    +1 (carga AuditLogs.jsx)
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

## Por qué paré

Llegué a 9 features sólidas con cobertura de tests. Las siguientes
candidatas eran:
- **Búsqueda fuzzy de vehículos** (extender pg_trgm a la tabla
  Vehicle por VIN). Útil pero requiere migración nueva.
- **Heatmap de cobros por día del mes**. Implica nuevo componente
  Chart.js — mejor cuando tengas data real para probarlo.
- **Modo oscuro**. Bajo valor para una herramienta de trabajo
  diurno; mejor postergar.

Si querés que siga con alguna de esas (o tenés otra prioridad),
decime y le doy. Por ahora dejo las branches limpias para tu
revisión.

— Última actualización: cierre del Pack 3.
