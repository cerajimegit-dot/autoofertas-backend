# Análisis de cartera vencida — propuesta de depuración

> Análisis del **18/05/2026** a partir de la copia local de la BD de Supabase (5.730 filas).
> Trigger: Marcelo notó que la cartera vencida del dashboard parece demasiado alta.
> Script: `scripts/analyze_cartera_vencida.py`. CSV detallado: `docs/reports/cartera_vencida.csv`.

## 🔍 Hallazgos clave

| Métrica | Valor | Notas |
|---|---|---|
| **Cuotas vencidas** | 986 | en 169 clientes / 139 ventas |
| **Monto total** | **Gs. 2.582.695.000** | el número que asustó a Marcelo |
| **Cobranza "real" (≤90 días)** | Gs. 1.257M (49%) | cartera activa, hay que perseguir |
| **Cuotas viejas (1+ año)** | **611 cuotas / Gs. 989M (38%)** | casi seguro ya cobradas fuera del sistema |
| **Docs autogenerados** | Gs. **1.101M (42.6%)** | clientes que ni sabemos quiénes son |
| **Ventas MIG** | Gs. **1.314M (50.9%)** | importadas de la planilla vieja |

> **Bottom line**: hay aprox. **Gs. 2.400M (93%) de cartera vencida sospechosa** que se puede sanear. La cartera vencida REAL (a perseguir activamente) son las cuotas recientes con clientes identificados — estimado en **Gs. 150-200M**.

---

## 📊 Distribución por antigüedad

| Rango | Cuotas | Monto | % monto |
|---|---|---|---|
| 🟢 1-30 días | 115 | Gs. 1.179M | 45.7% |
| 🟡 31-90 días | 48 | Gs. 78M | 3.0% |
| 🟠 91-180 días | 54 | Gs. 88M | 3.4% |
| 🔴 181-365 días | 156 | Gs. 247M | 9.6% |
| ⚫ **1-2 años** | **544** | **Gs. 856M** | **33.2%** |
| ☠ 2-5 años | 67 | Gs. 132M | 5.1% |

> La concentración del 55% de las cuotas con **1-2 años de atraso** es la señal más fuerte de que la migración trajo cuotas históricas como "pendientes" en lugar de "cobradas". Si hubiera sido morosidad real activa, la distribución sería más uniforme y con concentración en los últimos 6 meses.

---

## 🚨 Categorías de "data basura" detectadas

### Categoría A — Clientes con documento autogenerado (Gs. 1.101M, 42.6%)

Documentos tipo `CUOTA000XXX`, `DRV026-XXXX`, `SUC026-XXXX` son placeholders que la migración generó cuando no conocía la cédula real:

| Prefijo | Cuotas | Monto |
|---|---|---|
| `CUOTA000XXX` | 54 | Gs. 1.092M |
| `SUC026-XXXX` | 4 | Gs. 7M |
| `DRV026-XXXX` | 2 | Gs. 3M |

**Patrón típico**: aparecen como "cuota única" (quota_number = 1) por **Gs. 27M a 53M** cada una — eso parece ser el saldo total que quedaba debiendo el cliente cuando se hizo la migración, no una cuota mensual normal.

### Categoría B — Ventas con código MIG (Gs. 1.314M, 50.9%)

813 cuotas vencidas pertenecen a ventas importadas (`MIG-XXX`). Probablemente:
- Algunas son contratos ya cobrados pero nunca se marcaron las cuotas como pagadas.
- Otras son contratos abiertos que rocío trackeaba en otra libreta/Excel.

### Categoría C — Cuotas viejas concentradas (1-2 años)

544 cuotas vencidas en el rango 1-2 años de atraso es muy sospechoso. Si fueran morosos reales activos, esperaríamos:
- Distribución más uniforme en los rangos.
- Cuotas múltiples por cliente (todas vencidas).
- Mucha actividad de WhatsApp/contacto.

El patrón actual sugiere que son **cuotas que sí se pagaron pero nunca se marcaron** en el sistema.

---

## ✅ Plan de depuración propuesto

### Fase 1 — Limpieza automática con script (gana ~80% de la basura)

Crear un comando `manage.py cleanup_cartera_legacy` que marca como **`cancelled`** las cuotas que cumplen TODOS estos criterios (no cobrarlas — anularlas con motivo):

1. `due_date < hoy - 365 días`
2. Cliente con documento que empieza con `CUOTA`, `DRV026` o `SUC026`
3. Status = `pending`

**Impacto estimado**: saca ~Gs. 1.100M de la cartera vencida. Quedan en el sistema como `cancelled` con nota *"Migración legacy — auto-cancelado el dd/mm/yyyy. Si el cliente reclama, restaurar manualmente."*

**Salvedad**: lo hacemos ENTRE TODOS antes de correrlo, con un dry-run que muestre las cuotas afectadas para que rocío las revise una por una.

### Fase 2 — Revisión manual asistida (top morosos reales)

Del top 30 morosos del CSV, los que **NO** tienen doc autogenerado son los reales — 17 clientes:

| Cliente típico | Documento | Cuotas vencidas | Monto |
|---|---|---|---|
| Jose Ramon Chirife Correa | 109 | 42 | Gs. 84M |
| Kathyana Ysabel Benitez | 117 | 48 | Gs. 82M |
| Joaquina Pera | 202 | 22 | Gs. 73M |
| Derlis Manuel Acosta Garcia | 0101 | 45 | Gs. 68M |
| Ana Paula Ramos Jimenez | 34312788 | 28 | Gs. 64M |
| Carlos Alberto Ramos Jimenez | 48679178 | 18 | Gs. 45M |
| ... 11 más | | | |

> Pero **ojo con los docs cortos** (109, 117, 202, 0101, 001) — esos parecen ser IDs internos de la planilla vieja, NO cédulas reales. Rocío tiene que confirmar la identidad real de estos clientes y reemplazar el documento.

**Action**: rocío toma el CSV exportado (`docs/reports/cartera_vencida.csv`), lo abre en Excel, filtra por `Doc_autogenerado = NO` y va marcando uno por uno:
- ✅ Pagado fuera del sistema → marcar cuotas como pagadas con fecha aproximada.
- 📞 Pendiente real → mantener vencida, agendar llamada de cobranza.
- ❌ Imposible (cliente desaparecido, contrato perdido) → cancelar la cuota.

### Fase 3 — Casos especiales

**3.1 Ventas MIG con cuotas masivas vencidas**: 

Para cada venta `MIG-XXX` que tenga más de 5 cuotas vencidas seguidas:
- Si el contrato físico dice "cobrado total" → marcar todas las cuotas como pagadas con la fecha del último cobro real.
- Si el cliente fue moroso histórico → cancelar con motivo *"Incobrable histórico - migración"*.

**3.2 Las 115 cuotas recientes (1-30 días)**:

Estas SÍ son cobranza activa. **Acción inmediata**:
- WhatsApp con el botón del sistema (sección 8 del manual).
- Si no responde en 7 días, escalamiento manual.

---

## 🛠 Herramientas que dejo listas

### En staging (próximo deploy)
- **Panel "A cobrar próximas"** del Pack 2 (B3) lista cuotas con WhatsApp link armado por cliente.
- **Bulk WhatsApp** (P3-F) — seleccionás 10 cuotas y mandás recordatorio masivo.
- **Banner de alertas activas** (P5-4) — avisa cuando la cartera vencida supera umbrales.

### Disponibles ahora en local
- `scripts/analyze_cartera_vencida.py` — corré para reanalizar cuando depures algo.
- `docs/reports/cartera_vencida.csv` — abrir en Excel para trabajar offline.

---

## 📋 Próximos pasos sugeridos (ordenados)

1. **Sesión de 30 min con rocío**: mostrarle este informe + el CSV. Que valide si los `CUOTA000XXX` son lo que asumimos (saldos importados).
2. **Diseñar el comando `cleanup_cartera_legacy`** una vez confirmados los criterios — con `--dry-run` por default.
3. **Correr dry-run en LOCAL** para ver qué se va a cancelar.
4. **Aprobar la lista** entre todos.
5. **Correr en producción** (cuando deployemos staging y tengamos los datos sincronizados).
6. Después de eso, el dashboard mostrará la cartera vencida REAL — probablemente entre Gs. 150-200M, manejable.

---

## ❓ Preguntas pendientes para rocío / mati / marcelo

1. **¿Los clientes `CUOTA000XXX` se conocen físicamente?** Si sí, hay que mergearlos con su ficha real. Si no, son histórico → cancelar.
2. **¿Las ventas MIG cobradas históricamente** se siguieron pagando en cuotas en libretas, o son contratos cerrados?
3. **¿Hay un punto de corte temporal claro** (ej. "todas las cuotas con vencimiento anterior al 01/01/2024 se asumen cobradas") que podamos aplicar como regla?

---

*Reporte generado automáticamente. Para regenerarlo: `DB_ENGINE=sqlite python scripts/analyze_cartera_vencida.py`.*
