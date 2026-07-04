# Tarea Jr — verificar cuotas pagadas del flujo de caja

> Trabajás con una **BD ofuscada** (nombres, documentos y teléfonos
> reemplazados por placeholders) y un **CSV de trabajo** que lista las
> ~48 cuotas del flujo de caja de mayo 2026 que el sistema no pudo
> auto-procesar.
>
> **Tu tarea**: para cada fila del CSV, verificar que el match propuesto
> es correcto y reportar si el CashMovement asociado está en BD o falta.

---

## 1 — Por qué importa esta tarea

El sistema procesa el archivo de flujo de caja para marcar cuotas como
paid. Para cada línea "PAGO CUOTA N° X/Y CLIENTE":
- Si encuentra la cuota → la marca paid y crea un CashMovement
- Si no la encuentra (porque ya está paid, o hay algún detalle) → la
  salta y queda en una lista para revisión manual

Ese "no encuentro" puede pasar por varias razones:
1. **La cuota ya está paid** (el caso más común — alguien la marcó antes)
2. La cuota no existe para ese cliente con ese X/Y
3. El nombre del cliente en el flujo no matchea ningún customer en BD

Tu trabajo es revisar cada fila y dar tu opinión sobre el match
propuesto. Después el senior toma tus respuestas y aplica las
correcciones que correspondan.

---

## 2 — Setup inicial (30 min)

### 2.1 Lo que te paso por separado

| Archivo | Para qué |
|---|---|
| `db_jr.sqlite3` | BD ofuscada con todos los datos |
| `flujo_unmatched.csv` | Tu lista de trabajo (48 filas) |
| `README_JR.md` | Cómo arrancar (este archivo) |
| `JR_CASH_MATCHING.md` | Esta guía |
| `DB_SCHEMA.md` | Documentación del modelo de datos |

### 2.2 Instalar Python y clonar el repo

```cmd
mkdir C:\Users\TUUSUARIO\CascadeProjects
cd C:\Users\TUUSUARIO\CascadeProjects
git clone https://github.com/cerajimegit-dot/autoofertas-backend.git playa
cd playa
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2.3 Configurar BD

1. Copiá la BD ofuscada al root del repo:
   ```cmd
   copy "C:\donde\guardaste\db_jr.sqlite3" db.sqlite3
   ```
2. Crear `.env`:
   ```
   DB_ENGINE=sqlite
   DEBUG=True
   SECRET_KEY=cualquier-string-largo-aleatorio-de-50-chars
   ```

### 2.4 Levantar el sistema (opcional pero útil para visualizar)

```cmd
set DB_ENGINE=sqlite
set PYTHONUTF8=1
venv\Scripts\python.exe manage.py runserver 8001
```

En otra terminal:
```cmd
cd C:\Users\TUUSUARIO\CascadeProjects
git clone https://github.com/cerajimegit-dot/autoofertas-frontend.git playa-frontend
cd playa-frontend
python server.py
```

Browser: http://localhost:3000/ — login con cualquier usuario y password `demo1234`.

---

## 3 — Conceptos clave antes de empezar (15 min)

Leé la sección 1 y 3 de `DB_SCHEMA.md` para entender:
- Qué es una Sale, una Quotum, un CashMovement
- Cómo se relacionan (Sale → Quotum, Quotum → CashMovement vía quota_id)
- Por qué un CashMovement `cobro_cuota` debería siempre tener `quota_id` seteado

---

## 4 — Las columnas del CSV de trabajo

Abrí `flujo_unmatched.csv` en Excel/LibreOffice. Vas a ver 15 columnas:

| Columna | Qué contiene |
|---|---|
| `file_row_id` | Identificador único (1, 2, 3...) — referite a éste cuando me reportes |
| `fecha` | Fecha del pago según el flujo de caja |
| `amount` | Monto del pago según el flujo |
| `quota_X` | Número de cuota parseado (el "X" de "X/Y") |
| `quota_X2` | Si la línea decía "X y X2/Y" (pago doble cuota), el segundo número |
| `quota_Y` | Total del plan parseado |
| `cliente_anon` | Nombre anonimizado (Cliente_A, Cliente_B...) — único por cliente |
| `reason` | Por qué el sistema no auto-matcheó |
| `candidates_quota_ids` | IDs de cuotas candidatas (separadas por coma) |
| `candidates_detail` | Detalle de cada candidato con score |
| **`top_candidate_cm_status`** | **Si el top candidato ya tiene CashMovement asociado o no** |
| `jr_decision` | ⬅ **VOS COMPLETÁS**: `OK` / `WRONG` / `NO_PUEDO` |
| `jr_chosen_quota_id` | ⬅ **VOS COMPLETÁS**: el ID de Quotum correcto (si distinto al top) |
| `jr_confidence` | ⬅ **VOS COMPLETÁS**: `alta` / `media` / `baja` |
| `jr_notes` | ⬅ **VOS COMPLETÁS**: cualquier nota libre |

---

## 5 — Workflow paso a paso

Para cada fila:

### Paso A — Leer el `candidates_detail` del top candidato

Formato:
```
Q#2512(score=250, cust=244, X/Y=10/24, amt=1400000, due=2026-05-05, pay=2026-05-02, status=paid)
```

Significa:
- ID de Quotum: 2512
- Score: 250 (cuánto matcheo)
- Customer ID: 244
- Plan: cuota 10 de 24
- Monto: Gs.1.400.000
- Vence: 2026-05-05
- Pagada: 2026-05-02
- Status: paid

### Paso B — Comparar con la fila del CSV

¿El candidato matchea bien con lo del flujo?
- `quota_X` del CSV vs `X/Y` del candidato → ¿coincide el X y el Y?
- `amount` del CSV vs `amt` del candidato → ¿están dentro del mismo orden de magnitud?
- `fecha` del CSV vs `pay` del candidato → ¿es la misma fecha o muy cercana?

### Paso C — Mirar `top_candidate_cm_status`

Esta columna te dice si el CashMovement ya está en BD:

| Valor | Significado | Acción del Jr |
|---|---|---|
| `CM#NNNN date=YYYY-MM-DD amount=NNNN` con fecha igual a la del CSV | ✅ Todo OK, el CM existe correctamente | `jr_decision = OK` |
| `CM#NNNN date=YYYY-MM-DD amount=NNNN` con fecha distinta | ⚠ Existe CM pero con fecha distinta | `jr_decision = OK` + nota explicando |
| `NINGUN_CM_LINKEADO` | 🔴 Falta crear el CashMovement | `jr_decision = OK` + nota "FALTA_CM" |
| `sin_top` (sin candidatos) | 🟡 No hay match obvio | `jr_decision = NO_PUEDO` + nota |

### Paso D — Investigar a mano si no estás seguro

Si dudás, abrí Django shell:
```cmd
set DB_ENGINE=sqlite
venv\Scripts\python.exe manage.py shell
```

```python
from core.models import Customer, Quotum, CashMovement

# Ver el candidato 2512 con toda su info
q = Quotum.objects.get(id=2512)
print(f'Cliente: {q.customer} (id={q.customer_id})')
print(f'Sale: {q.sale.sale_number}')
print(f'Cuota: {q.quota_number}/{q.total_plan}')
print(f'Amount: {q.amount}, Status: {q.status}, Due: {q.due_date}, Paid: {q.payment_date}')

# Ver TODOS los CashMovements de esa quota
cms = CashMovement.objects.filter(quota_id=q.id)
for cm in cms:
    print(f'  CM#{cm.id}: date={cm.date}, kind={cm.kind}, amount={cm.amount}, is_auto={cm.is_auto}')

# Ver TODAS las cuotas del mismo cliente (a veces hay varias plans)
for q2 in Quotum.objects.filter(customer_id=q.customer_id).order_by('sale_id', 'quota_number'):
    print(f'  Q#{q2.id}: sale={q2.sale.sale_number}, {q2.quota_number}/{q2.total_plan}, amt={q2.amount}, status={q2.status}')
```

### Paso E — Completar las 4 columnas del CSV

| Columna | Valores posibles |
|---|---|
| `jr_decision` | `OK` (todo coincide), `WRONG` (el top no es, propongo otro), `NO_PUEDO` (no sé cuál es) |
| `jr_chosen_quota_id` | Vacío si OK con el top, sino el ID del que sí matchea |
| `jr_confidence` | `alta` / `media` / `baja` |
| `jr_notes` | Cualquier observación, ej. "FALTA_CM", "fechas difieren 3d", "amount difiere 5%" |

Guardá el CSV.

---

## 6 — Ejemplos resueltos

### Ejemplo 1: caso fácil (OK directo)

Fila CSV:
```
file_row_id=1
fecha=2026-05-02, amount=1400000, X/Y=10/24
candidates: Q#2512(score=250, X/Y=10/24, amt=1400000, pay=2026-05-02, status=paid)
top_candidate_cm_status: CM#528 date=2026-05-02 amount=1400000
```

**Análisis**: el candidato Q#2512 coincide perfecto (X/Y, amount, fecha de pago) y el CashMovement CM#528 está creado en la misma fecha con el mismo monto.

**Llenado**:
- `jr_decision = OK`
- `jr_chosen_quota_id = ` (vacío)
- `jr_confidence = alta`
- `jr_notes = ` (vacío)

### Ejemplo 2: caso de FALTA_CM (acción real)

Fila CSV:
```
fecha=2026-05-10, amount=1500000, X/Y=5/12
candidates: Q#3001(score=180, X/Y=5/12, amt=1500000, pay=NULL, status=pending)
top_candidate_cm_status: NINGUN_CM_LINKEADO
```

**Análisis**: la cuota existe pero no está paid en BD, y no tiene CashMovement asociado. El flujo dice que SÍ se pagó. Acción: marcar la cuota como paid y crear el CashMovement.

**Llenado**:
- `jr_decision = OK`
- `jr_chosen_quota_id = 3001`
- `jr_confidence = alta`
- `jr_notes = FALTA_CM — marcar cuota paid + crear CM`

### Ejemplo 3: caso ambiguo (NO_PUEDO)

Fila CSV:
```
fecha=2026-05-15, amount=1300000, X/Y=8/24
candidates: Q#4001(score=140), Q#4002(score=140), Q#4003(score=130)
```

**Análisis**: 3 candidatos con scores muy parecidos, el cliente_anon es ambiguo, fechas similares. No podés desempatar sin más data.

**Llenado**:
- `jr_decision = NO_PUEDO`
- `jr_chosen_quota_id = ` (vacío)
- `jr_confidence = baja`
- `jr_notes = 3 candidatos con score similar, ambiguo`

---

## 7 — Cuándo escalar al senior

Escalá al senior (anotando el `file_row_id`):
- Más de 3 candidatos con score similar y no podés desempatar
- El top candidato tiene amount muy distinto al de la fila (> 20% diferencia)
- El top candidato pertenece a un cliente cuyo `cust=NNN` claramente no es el del flujo
- Encontrás un patrón raro (ej. varias filas con la misma cuota como top candidato — sería raro que el mismo cobro se hiciera 2 veces)

Anotá en `jr_notes` y mandá un mensaje con el `file_row_id`.

---

## 8 — Métricas de tu trabajo

Llevá una pequeña planilla:

| Fecha | Filas revisadas | OK | WRONG | NO_PUEDO | Tiempo |
|---|---|---|---|---|---|
| 2026-06-09 | 20 | 18 | 0 | 2 | 1.5h |

Target inicial: 30-50 filas por día.

---

## 9 — Privacidad y seguridad

- La BD que tenés está **ofuscada**: nombres son `CLIENTE0001`, documentos
  son `DOC000001`, etc. **No es real**.
- El CSV de trabajo tiene **nombres anonimizados** (`Cliente_A`, `Cliente_B`).
- No intentes "des-anonimizar" — el mapping queda con el senior.
- No compartas `db_jr.sqlite3` ni `flujo_unmatched.csv` con nadie fuera del equipo.
- Si por error tenés acceso a una BD real (`DATABASE_URL` apuntando a
  Supabase), no la uses para esta tarea. Avisá al senior.

---

## 10 — Cheatsheet

| Acción | Comando |
|---|---|
| Levantar backend local | `scripts\run_local.bat` (o `manage.py runserver 8001`) |
| Django shell | `manage.py shell` |
| Buscar una Quotum | `Quotum.objects.get(id=N)` |
| Ver CMs de una Quotum | `CashMovement.objects.filter(quota_id=N)` |
| Schema completo | `docs\DB_SCHEMA.md` |

---

*Versión 2.0 — focused on the flujo de caja matching task.*
