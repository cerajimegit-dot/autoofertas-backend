# Flujo de caja — análisis y plan de integración al sistema

Fecha: 2026-05-15
Origen: archivo `52-FLUJO DE CAJA FEBRERO 2.026 -.ods` (hoja única,
67 filas de movimientos).

---

## 1. Anatomía del archivo actual

Estructura de columnas:

| Col | Contenido |
|---|---|
| A | FECHA — `dd/mm/yy` |
| B | OPERACIÓN — texto libre |
| C | MONTO — Gs. positivo (ingreso) o negativo (egreso) |
| D–F | (vacías) |
| G | CONDICIÓN — `CONTADO` / `CREDITO` / `CANCELADO` / `A/CUENTA` / `TC 6.600.-` (tipo cambio cuando hay USD) |
| H | Notas extra (banco, observaciones) |

**Totales de febrero 2026:**

| | Filas | Total Gs. |
|---|---|---|
| Ingresos | 57 | **531.250.000** |
| Egresos  | 9  | **-350.981.480** |
| Neto del mes | — | **+180.268.520** |

**Clasificación heurística de las 66 filas con monto:**

| Categoría | N | Total Gs. | Origen del dato |
|---|---|---|---|
| `venta_contado`      | 9  | 366.500.000 | Ya en `Sale` con `payment_form=CONTADO` |
| `cobro_cuota`        | 45 | 99.750.000  | Ya en `Quotum.mark_as_paid` |
| `seña_credito`       | 3  | 65.000.000  | Hoy se anota en `Sale.down_payment` pero no genera movimiento |
| `compra_exterior`    | 4  | -257.686.000 | NO está en el sistema (proveedores Japón/Corea/PY) |
| `transporte`         | 2  | -62.895.480 | NO está en el sistema (cigüeña, despachos) |
| `gasto_playa`        | 2  | -22.000.000 | NO está en el sistema (gastos operativos) |
| `alquiler`           | 1  | -8.400.000  | NO está en el sistema |

**De los 66 movimientos, 57 (86%) ya están en el sistema** como ventas o
cobros de cuota; pero los **9 egresos críticos** (las compras al exterior
y los gastos operativos) viven sólo en este Excel. Por eso el dueño
todavía depende del archivo para tener el saldo real.

## 2. Formatos sutiles que aparecen

- **Pagos múltiples en una fila**:
  `"PAGO CUOTA N° 6 7 8 9 10 11 12 13 14 15/15 ANDREA CELESTE..."` →
  10 cuotas canceladas en un solo asiento de Gs. 25.000.000.
  Hoy el sistema marcaría cada una por separado, lo cual es **mejor**
  para trazabilidad — pero al cruzar contra el Excel hay que matchear
  por monto+fecha+cliente.
- **Tipo de cambio**: cuando el operación es en USD se anota
  `"TC 6.600.-"` o `"TC 6.460.-"` en la columna G. El monto en Gs. ya
  está convertido. **Sin embargo el USD original también se ve en el
  texto** (`"15.431$ + 90$ TOTAL 15.521$"`). Útil para auditar.
- **Notas que indican estado**: `"545$ A FAVOR EN COREA AUTOWINI"` —
  saldo a favor con un proveedor. Hoy no hay forma de registrarlo.
- **Referencia cruzada a operación**: `"PAGO CUOTA N° 10/24 FABIOLA
  RAMIREZ SOTELO (OP 169)"` y otra fila idéntica `(OP 186)` — el mismo
  cliente con 2 operaciones (ventas) distintas y mismas cuotas. La
  referencia `OP N` es el sale_number del sistema viejo.
- **Observaciones que niegan el movimiento**:
  `"OBS: ESTA VENTA NO SE CARGO EN EL FLUJO DE CAJA MES DE ENERO 2.026"`
  — fila explicativa sin monto. El operador la usa para sí mismo.

## 3. Lo que falta para reemplazar el archivo

| Necesidad | Hoy en el sistema | Cambio propuesto |
|---|---|---|
| Registrar cobranza de cuota | ✅ `Quotum.mark_as_paid` | (ya está — falta auto-crear el movimiento) |
| Registrar venta contado | ✅ `Sale.create(payment_form=CONTADO)` | (idem) |
| Registrar seña | ✅ `Sale.down_payment` | Auto-crear movimiento por la seña |
| Pagar gasto operativo (GASTOS PLAYA, alquiler) | ❌ | **Nuevo: modelo `CashMovement` con `kind='gasto'`** |
| Pagar compra al exterior (USD) | ❌ | **Nuevo: `CashMovement` con `kind='compra_exterior'` + USD + TC** |
| Pagar transporte (cigüeña) | ❌ | **Nuevo: `CashMovement` con `kind='transporte'`** |
| Listar todos los movimientos del mes con saldo | ❌ | **Endpoint + UI** |
| Importar el flujo de febrero ya cargado a mano | — | Script de migración del ODS |

## 4. Modelo propuesto

```python
class CashMovement(models.Model):
    """Movimiento de caja: ingreso o egreso.

    Algunos se crean automáticamente (cobros, ventas contado, señas);
    otros son manuales (gastos, alquileres, compras al exterior).
    """

    KIND_CHOICES = (
        ('cobro_cuota',     'Cobro de cuota'),
        ('venta_contado',   'Venta contado'),
        ('seña_credito',    'Seña de crédito'),
        ('pago_a_cuenta',   'Pago a cuenta'),
        ('gasto_playa',     'Gasto playa'),
        ('alquiler',        'Alquiler'),
        ('sueldo',          'Sueldo'),
        ('comision',        'Comisión / honorario'),
        ('compra_exterior', 'Compra al exterior'),
        ('transporte',      'Transporte / despacho'),
        ('impuesto',        'Impuesto'),
        ('ajuste',          'Ajuste de caja'),
        ('otro',            'Otro'),
    )

    DIRECTION_CHOICES = (
        ('in',  'Ingreso'),
        ('out', 'Egreso'),
    )

    enterprise = models.ForeignKey('Enterprise', ...)
    branch     = models.ForeignKey('Branch', null=True, ...)

    date          = models.DateField()
    kind          = models.CharField(max_length=20, choices=KIND_CHOICES)
    direction     = models.CharField(max_length=3, choices=DIRECTION_CHOICES)
    description   = models.TextField()

    # Monto SIEMPRE positivo. El signo lo da `direction`.
    amount        = models.DecimalField(max_digits=14, decimal_places=2)
    currency      = models.CharField(max_length=3, default='PYG')  # PYG | USD
    # Si currency=USD, guardamos el monto en USD y el TC aplicado para
    # auditar contra el Excel.
    amount_usd    = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Trazabilidad
    provider      = models.CharField(max_length=100, blank=True)
    sale          = models.ForeignKey('Sale',   null=True, blank=True, related_name='cash_movements')
    quota         = models.ForeignKey('Quotum', null=True, blank=True, related_name='cash_movements')

    # ¿Quién lo creó?
    created_by    = models.ForeignKey('CustomUser', null=True, ...)
    is_auto       = models.BooleanField(default=False)  # ¿se creó por sale/mark_as_paid o manual?

    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
```

**Por qué `direction` separado de signo de `amount`**:
- En el Excel el monto puede ser negativo. Internamente es más limpio
  guardarlo positivo y derivar el signo en la presentación, y permite
  agregaciones tipo `SUM(amount) WHERE direction=in` directas.
- También simplifica la validación en serializer (siempre `amount > 0`).

**Por qué `kind` y no sólo `direction`**:
- Reportes por categoría: "¿cuánto gasté en transporte este año?"
- Ya hay 13 kinds identificados en la primera muestra; no es una taxonomía
  hipotética.

## 5. Auto-creación desde Sale y Quotum

```python
# En core/models/sales.py — al final de Sale.save() / Quotum.save()

def _create_cash_movement_for_sale(sale):
    """Generar movimiento automático cuando se cierra una venta."""
    if sale.status != 'completed':
        return
    pf = (sale.payment_form.name or '').upper() if sale.payment_form else ''
    if 'CONTADO' in pf:
        CashMovement.objects.update_or_create(
            sale=sale, kind='venta_contado',
            defaults={
                'enterprise': sale.enterprise, 'branch': sale.branch,
                'date': sale.sale_date.date(),
                'direction': 'in',
                'amount': sale.total_price,
                'description': f'Venta contado {sale.sale_number}',
                'is_auto': True,
            },
        )
    # Si hay down_payment (seña) — siempre se cobra al firmar la venta.
    if sale.down_payment and sale.down_payment > 0:
        CashMovement.objects.update_or_create(
            sale=sale, kind='seña_credito',
            defaults={
                'enterprise': sale.enterprise, 'branch': sale.branch,
                'date': sale.sale_date.date(),
                'direction': 'in',
                'amount': sale.down_payment,
                'description': f'Seña venta {sale.sale_number}',
                'is_auto': True,
            },
        )

def _create_cash_movement_for_paid_quota(quota):
    """Generar movimiento automático al marcar una cuota como cobrada."""
    if quota.status != 'paid':
        return
    CashMovement.objects.update_or_create(
        quota=quota, kind='cobro_cuota',
        defaults={
            'enterprise': quota.enterprise, 'branch': quota.sale.branch,
            'date': quota.payment_date,
            'direction': 'in',
            'amount': quota.amount,
            'description': f'Cuota {quota.quota_number}/{quota.total_plan} '
                           f'venta {quota.sale.sale_number} — '
                           f'{quota.customer.full_name if quota.customer else "sin cliente"}',
            'is_auto': True,
        },
    )
```

**`update_or_create`** garantiza idempotencia: si la venta o la cuota se
edita varias veces, el movimiento queda 1 sólo, actualizado.

## 6. API y UI

**Endpoints:**

```
GET  /api/cash_movements/?date_from=&date_to=&kind=&branch=&direction=
POST /api/cash_movements/         # crear manual (gastos, compras)
PATCH/DELETE /api/cash_movements/{id}/

GET  /api/cash_movements/summary/?date_from=&date_to=&branch=
     → {
         total_in: ..., total_out: ..., neto: ...,
         by_kind: [{kind, n, total}, ...]
       }

POST /api/cash_movements/import_ods/   # admin: importa el ODS
```

**UI nueva — `/flujo-caja`:**

- Header con filtro de período (mismos quick ranges que el dashboard) y
  selector de sucursal.
- 3 KPIs: Ingresos, Egresos, Saldo neto.
- Distribución por tipo (gráfico de barras o tabla).
- Tabla de movimientos cronológica: fecha, tipo (badge color),
  descripción, sucursal, monto (verde/rojo según direction).
- Botón "+ Nuevo movimiento" → modal con kind (select), date, amount,
  direction, currency + amount_usd + tc cuando aplica, provider,
  description.
- Las filas auto-generadas (`is_auto=True`) NO se pueden borrar, sólo
  editar la `description` y el `kind`. Para borrar hay que ir a la
  cuota/venta de origen.

## 7. Plan de implementación

**MVP (en este sprint):**
1. Modelo + migración + admin.
2. Auto-creación al guardar `Sale` y `Quotum` (sobre el `save()` existente
   — ya tenemos el patrón para sincronizar `vehicle.state`).
3. Endpoints CRUD + `summary`.
4. Backfill: crear `CashMovement` para todas las ventas `completed` y
   cuotas `paid` que ya están en BD (~430 ventas + 1051 cuotas paid).
5. UI nueva `/flujo-caja` con tabla, filtros, modal de creación manual.

**Fase 2:**
6. Importador del ODS (parsea el archivo y crea los movimientos
   manuales — saltea los que ya están como auto).
7. Reporte mensual exportable a Excel (entrega al contador).
8. Categorías custom (sub-tipos por dentro de `kind` para `gasto_playa`:
   "limpieza", "internet", "papelería", etc.).

**Fase 3 (sólo si se justifica):**
9. Caja por sucursal (saldo diario por branch).
10. Conciliación bancaria (subir extracto del banco y matchear).

## 8. Sobre el archivo del Excel viejo

El ODS de febrero tiene la misma estructura que probablemente usaron en
enero y van a usar en marzo. El importador del ODS:

- Lee filas con fecha + monto válido.
- Clasifica por keywords en la columna B (heurística probada con febrero):
  - `PAGO CUOTA` → `cobro_cuota` (matchear contra Quotum por
    cliente+monto+fecha; si existe, saltear).
  - `AUTOCOM` / `AUTOWINI` / `TURTOLA` / `LAYSOLA` / `DADANI` →
    `compra_exterior`.
  - `DESPACHO` / `CIGÜEÑA` / `CIGUE` → `transporte`.
  - `GASTOS PLAYA` → `gasto_playa`.
  - `ALQUILER` → `alquiler`.
  - Resto → `otro` (operador confirma manualmente).
- Genera reporte: `N matcheados, N nuevos, N para revisar`.
- Se corre 1 vez por mes para "ponerse al día"; después el sistema toma
  el relevo.

## 9. Riesgos y cuestiones abiertas

- **Cobros migrados sin payment_date real**: las cuotas que están como
  `paid` en BD vienen del importer histórico y tienen `payment_date`
  igual a la fecha de migración, no a la fecha real del cobro. El
  backfill va a generar movimientos en fechas falsas. Posibles caminos:
  - Generar los movimientos con `date = payment_date` (lo que sea),
    aceptar el ruido histórico.
  - Marcar esos movimientos con `notes='migrado, fecha aproximada'` para
    distinguirlos.
  - Recomendado: lo segundo.
- **Doble registro**: si el Excel ya tiene una fila de cobro Y la cuota
  está marcada paid en BD, el importador la salteará para no duplicar.
  Match por: `customer + amount + date ± 3 días`.
- **USD a futuro**: el archivo de febrero tiene 4 compras al exterior en
  USD. Hoy el sistema tiene `ExchangeRate` con 0 cotizaciones cargadas.
  El modelo `CashMovement` guarda `amount_usd` + `exchange_rate` literal
  (no FK), así que funciona sin tener cotización oficial cargada. Pero
  conviene también poblar `ExchangeRate` con los TCs históricos para
  reportes de inventario en USD.
- **Versiones del flujo**: si la concesionaria mete una cuota como pagada
  por error y la corrige, ¿qué pasa con el movimiento auto-creado? La
  estrategia `update_or_create` con `quota=quota` actualiza el existente;
  si la cuota vuelve a `pending`, el movimiento queda huérfano. Conviene
  un `post_save` que borre el movimiento auto si la cuota deja de estar
  `paid`.
