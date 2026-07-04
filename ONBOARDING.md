# Onboarding — desarrollo Jr en AUTO OFERTAS

> Esta guía te lleva de **PC vacía a productivo en ~2 horas**. Después
> tenés 8 patrones concretos para revisar a mano en los datos.
>
> **⚠ Si sos estudiante sin experiencia previa**: NO empieces por acá.
> Andá primero a **[`docs/aprender/00_INICIO_AQUI.md`](docs/aprender/00_INICIO_AQUI.md)**
> que es una guía progresiva de 10 horas cubriendo Python, Django,
> React y Git desde cero. Cuando termines esa, volvé acá.

---

## Parte 1 — Setup (45 min)

### 1.1 Requisitos
- Windows 10/11 (también funciona Mac/Linux con ajustes menores)
- Python 3.11 o 3.12 instalado (3.13/3.14 funcionan pero hay warnings)
- Git
- Editor de código: VS Code recomendado
- (Opcional) DBeaver o TablePlus para inspeccionar SQLite directo

### 1.2 Clonar repos

```cmd
mkdir C:\Users\TUUSUARIO\CascadeProjects
cd C:\Users\TUUSUARIO\CascadeProjects
git clone https://github.com/cerajimegit-dot/autoofertas-backend.git playa
git clone https://github.com/cerajimegit-dot/autoofertas-frontend.git playa-frontend
```

(Acordate de pedir acceso a los repos a marcelo antes — son privados.)

### 1.3 Backend — venv y dependencias

```cmd
cd C:\Users\TUUSUARIO\CascadeProjects\playa
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Esperá 2-3 min. Si tira errores con `psycopg2`, usar `pip install psycopg2-binary` en su lugar.

### 1.4 `.env` para uso local con SQLite

```cmd
copy .env.example .env
```

Editá `.env` y dejalo con:
```
DB_ENGINE=sqlite
DEBUG=True
SECRET_KEY=cualquier-cosa-larga-de-50-caracteres
```

⚠ **NO toques `DATABASE_URL`** — eso es la conexión a Supabase prod. Por default queda comentado/vacío, y mientras uses `DB_ENGINE=sqlite` no se usa.

### 1.5 Pedir el `db.sqlite3` y los archivos `STOCK/`, `ventas/`, `cuotas/`

Estos archivos NO están en git (tienen datos reales). Pediselos a quien te onboarde:
- `db.sqlite3` (al root del repo)
- Carpetas `STOCK/`, `ventas/`, `cuotas/` (con sus subcarpetas)

Si no los conseguís, hacé una BD vacía con datos de prueba:
```cmd
venv\Scripts\python.exe manage.py migrate
venv\Scripts\python.exe manage.py createsuperuser
venv\Scripts\python.exe manage.py loaddata core/fixtures/sample_data.json  REM si existe
```

### 1.6 Levantar el backend

```cmd
scripts\run_local.bat
```

Esto:
- Setea `DB_ENGINE=sqlite` (fuerza no tocar prod)
- Setea `PYTHONUTF8=1` (evita bug de Windows con caracteres como →)
- Levanta `manage.py runserver 8001`

Deberías ver `Starting development server at http://127.0.0.1:8001/`.

### 1.7 Levantar el frontend

En otra terminal:
```cmd
cd C:\Users\TUUSUARIO\CascadeProjects\playa-frontend
python server.py
```

Abrí http://localhost:3000/ → login con `admin / admin123` (o pedir credenciales si distintas).

### 1.8 Test rápido

Si después de loguearte ves el Dashboard con datos (cartera, ventas, etc), está OK.

Si en consola del browser hay errores tipo `ERR_CONNECTION_REFUSED` → backend no está corriendo. Revisá la otra terminal.

---

## Parte 2 — Modelo de datos (20 min)

### 2.1 Entidades principales

```
Enterprise (1)
├── Branch (N: "CASA CENTRAL", "SUCURSAL 1")
├── Brand → VehicleModel → Vehicle
├── Customer
├── Sale (cliente FK + vehículo FK)
│   └── Quotum (cuota de pago, N por venta)
├── CashMovement (movimiento de caja)
└── CustomUser (usuarios del sistema)
```

### 2.2 Tablas clave a memorizar

| Tabla | Qué guarda | Campos importantes |
|---|---|---|
| `core_customer` | Clientes | `document_number` (CI/RUC), `first_name`, `last_name`, `phone`, `email` |
| `core_vehicle` | Vehículos | `vin` (chasis), `state` (available/sold/reserved), `brand_id`, `model_id`, `year`, `price` |
| `core_sale` | Ventas | `sale_number` (CM01/24, MC42/26), `customer_id`, `vehicle_id`, `total_price`, `status` (pending/completed/cancelled), `payment_form_id` |
| `core_quotum` | Cuotas | `sale_id`, `quota_number`, `total_plan`, `amount`, `due_date`, `payment_date`, `status` (pending/paid/overdue/cancelled) |
| `core_cashmovement` | Caja | `kind` (cobro_cuota/venta_contado/gasto_playa/etc), `direction` (in/out), `amount`, `sale_id`, `quota_id` |

### 2.3 Estados y sus transiciones

**Vehicle.state**: cambiado automáticamente por `Sale.save()` hook
- `available` → libre para vender
- `reserved` → venta `pending` apuntando
- `sold` → venta `completed` apuntando

**Sale.status**:
- `pending` = reserva con seña, contrato no firmado
- `completed` = venta cerrada, contrato firmado (puede seguir cobrando cuotas durante meses)
- `cancelled` = anulada, vehículo vuelve a available

**Quotum.status**:
- `pending` = no cobrada todavía
- `paid` = cobrada (debe tener `payment_date`)
- `overdue` = legacy, **no se usa nuevo** (la lógica calcula vencidas como `pending + due_date < hoy` dinámicamente)
- `cancelled` = cuota anulada (raro)

### 2.4 Cómo inspeccionar la BD rápido

**Opción A: Django shell**
```cmd
set DB_ENGINE=sqlite
venv\Scripts\python.exe manage.py shell
>>> from core.models import Sale, Customer, Quotum
>>> Sale.objects.filter(sale_number__startswith='CM').count()
>>> Customer.objects.get(document_number='48679178')
```

**Opción B: DBeaver / TablePlus**
- Abrir el archivo `db.sqlite3` con cualquiera de los dos
- Tabs sobre la izquierda con cada tabla

**Opción C: scripts de reporte**
```cmd
set DB_ENGINE=sqlite
set PYTHONUTF8=1
venv\Scripts\python.exe scripts\print_cartera_state.py
venv\Scripts\python.exe scripts\print_stock_state.py
venv\Scripts\python.exe scripts\health_check.py
```

---

## Parte 3 — Reglas de seguridad antes de tocar nada (5 min)

### 3.1 Las 3 reglas de oro

1. **Nunca corras scripts con `--confirm` contra `DB_ENGINE=postgres` sin permiso explícito**. Postgres = producción.
2. **Antes de cualquier cambio destructivo en local**, hacé backup:
   ```cmd
   copy db.sqlite3 backups\db_sqlite3_pre_TUOPERACION_%date:~6,4%%date:~3,2%%date:~0,2%.bak
   ```
3. **Todo cambio se prueba en local primero** (SQLite). Si funciona, recién después se replica a prod via el `.bat` correspondiente.

### 3.2 Cuando algo no estás seguro

- Pasalo al senior antes de aplicar `--confirm`.
- Si ya aplicaste algo y rompiste data en local, restaurás:
  ```cmd
  copy backups\db_sqlite3_pre_*.bak db.sqlite3
  ```

---

## Parte 4 — Los 8 casos a chequear a mano

Estos son patrones que el sistema NO puede resolver solo. Para cada uno
te explico **qué buscar**, **cómo identificarlo** y **qué decisión tomar**.

### Caso #1 — Vehículos del STOCK sin chasis (17 casos)

**Qué es**: hay 17 filas en los archivos `STOCK/*.ods` donde el `chasis` está vacío. El script `stock_apply.py` los saltea porque no puede crear `Vehicle` sin VIN.

**Cómo identificarlos**:
```cmd
venv\Scripts\python.exe scripts\stock_apply.py
```
Mirá la sección "Salteados" al final. Cada línea dice qué fila del archivo y por qué.

**Cómo verificarlos a mano**:
1. Abrir el archivo `STOCK/STOCK AUTOOFERTAS-CASA CENTRAL.ods` con LibreOffice.
2. Buscar la fila del vehículo. Generalmente faltan el VIN porque están en tránsito (Iquique) o tienen seña.
3. Si rocío ya tiene el VIN → completar el archivo, guardar, re-correr `stock_apply.py --confirm`.
4. Si NO tiene VIN aún → dejar pasar, no hay nada que hacer.

**Escalá si**: el archivo dice "CANCELADO" en la condición del vehículo (tema separado, no es stock activo).

---

### Caso #2 — Ventas sin vehículo en BD (1+ casos)

**Qué es**: en el archivo `ventas/*.ods` hay una venta (ej. `CM40/26`) cuyo chasis no matchea ningún Vehicle en BD.

**Cómo identificarlos**:
```cmd
venv\Scripts\python.exe scripts\import_sales_from_file.py
```
Mirar la sección "Sin match de vehicle (revisar manual)".

**Cómo verificarlos**:
1. Abrir el archivo VENTAS con LibreOffice, buscar la fila por sale_number.
2. Copiar el chasis y buscarlo en `STOCK/*.ods`:
   - Si está en STOCK → el problema es que ese vehículo no se creó en BD. Re-correr `stock_apply.py --confirm` primero, después `import_sales_from_file.py --confirm`.
   - Si NO está en STOCK → es un vehículo "fantasma" (vendido pero nunca cargado). Reportar al senior.

---

### Caso #3 — Cuotas del flujo de caja sin match (42 casos típicos)

**Qué es**: el script `apply_flujo_caja.py` lee líneas tipo "PAGO CUOTA N° X/Y CLIENTE" y trata de marcar la cuota como paid. Cuando dice "no existe" puede ser que:
- (a) Ya está paid (caso común — no hay que hacer nada)
- (b) El plan en BD tiene Y distinto al archivo (ej. archivo dice 15/24 pero en BD la venta tiene 22 cuotas)
- (c) El cliente está duplicado y el match cayó en el customer equivocado

**Cómo identificarlos**:
```cmd
venv\Scripts\python.exe scripts\apply_flujo_caja.py "STOCK\junio2026\FLUJO DE CAJA MAYO 2.026 -.ods"
```
Mirar la sección "Cuotas no matcheadas".

**Cómo verificarlos**:

Por cada línea "no existe":
1. Anotá el cliente y el N° X/Y.
2. Abrir Django shell:
   ```python
   from core.models import Customer, Quotum
   c = Customer.objects.filter(first_name__icontains='NOMBRE', last_name__icontains='APELLIDO').first()
   print(c)
   print(list(Quotum.objects.filter(customer=c).values('quota_number','total_plan','status','due_date','amount')))
   ```
3. Comparar con lo que dice el archivo de flujo.
4. Decidir:
   - Si ya está paid en BD → ignorar (caso (a), todo OK)
   - Si la cuota existe pero con `total_plan` distinto → escalada al senior, posible plan modificado
   - Si la cuota no existe (porque no se generó plan de cuotas) → escalar al senior

**Productividad**: la mayoría son caso (a). Concentrate en los que tienen monto importante (>Gs.1.5M).

---

### Caso #4 — Morosos reales del archivo PENDIENTE A COBRAR (56 casos)

**Qué es**: el archivo `48-PENDIENTE A COBRAR 01-06-26.ods` lista los morosos reales según rocío al 01/06/26 con su monto pendiente. Hay 56 clientes con monto. **Cada uno debería matchear el monto pendiente que tiene en BD**.

**Cómo identificarlos**: hay un script:
```cmd
venv\Scripts\python.exe scripts\reconcile_pendiente_cobrar.py "STOCK\junio2026\48-PENDIENTE A COBRAR 01-06-26.ods"
```
Mirar la sección "MOROSOS REALES — validar manual".

**Cómo verificarlos**:

Por cada cliente con monto pendiente:
1. Anotá el monto del archivo.
2. Calculá su monto pendiente en BD:
   ```python
   from core.models import Customer, Quotum
   c = Customer.objects.filter(first_name__icontains='NOMBRE', last_name__icontains='APELLIDO').first()
   pendiente = sum(int(q.amount or 0) for q in Quotum.objects.filter(customer=c).exclude(status__in=['paid','cancelled']))
   print(f'BD: Gs.{pendiente:,}')
   ```
3. Comparar:
   - **Coinciden** → ✅ todo OK, no tocar.
   - **BD tiene MENOS** → faltó marcar alguna cuota como pendiente. Probable: una cuota se marcó paid erróneamente. Revisar cuotas paid recientes del cliente.
   - **BD tiene MÁS** → faltó marcar alguna como paid. Probable: rocío cobró pero no marcamos. Buscar en el flujo de caja de los últimos meses.

**Escalá** los casos con diferencia mayor a Gs.5M.

---

### Caso #5 — Nombres CANCELADO sin match en BD (99 casos)

**Qué es**: en el archivo PENDIENTE A COBRAR hay 99 clientes marcados "CANCELADO" cuyo nombre no matchea ningún customer en BD. Probable: rocío les vendió contado y no se cargaron como ficha.

**Cómo identificarlos**:
```cmd
venv\Scripts\python.exe scripts\reconcile_pendiente_cobrar.py "STOCK\junio2026\48-PENDIENTE A COBRAR 01-06-26.ods"
```
Sección "SIN MATCH en BD".

**Acción**: típicamente nada. Son clientes históricos de ventas contado sin ficha. **Confirmá** con el senior si vale la pena cargarlos retroactivamente.

---

### Caso #6 — Vehículo "auto perchero" (id=620)

**Qué es**: hay un Vehicle (id=620) con 5 ventas DRV026 colgadas, cada una con monto Gs.0 y cuotas pagadas históricas. Es un "auto perchero" que rocío usaba como placeholder para colgar deuda histórica antes de migrar al sistema.

**Cómo identificarlo**:
```python
from core.models import Sale
list(Sale.objects.filter(vehicle_id=620).values('sale_number','customer__document_number','total_price'))
```

**Acción**: NO tocar sin escalar. Borrar la ficha pierde el historial de cobranza de 5 clientes.

---

### Caso #7 — Patrón A: clientes con dos fichas (real + DRV026)

**Qué es**: clientes que tienen 2 fichas:
- Una con doc real (ej. `48679178`) — la "buena"
- Una con doc `DRV026-XXXX` — placeholder migración

**Cómo identificarlos**: ver `docs/reports/CLIENTES_DUPLICADOS.md` o correr:
```cmd
venv\Scripts\python.exe scripts\find_duplicate_customers.py
```

**Acción**:
1. Identificar la ficha real (la que tiene doc verdadero).
2. Reasignar las ventas/cuotas/CMs de la ficha placeholder a la real.
3. Borrar la ficha placeholder.

Hay un script `scripts/reconcile_morosos.py` que ayuda en algunos casos, pero la reasignación requiere atención manual.

**Escalá** todos antes de aplicar.

---

### Caso #8 — Patrón B: clientes con espacios extras

**Qué es**: clientes cuya `first_name` o `last_name` tienen espacios al principio o final, lo que crea duplicados (ej. `"JUAN "` vs `"JUAN"` son customers distintos).

**Cómo identificarlos**: el script `health_check.py` lo reporta. También:
```python
from django.db.models import Q
Customer.objects.filter(Q(first_name__startswith=' ') | Q(first_name__endswith=' ') | Q(last_name__startswith=' ') | Q(last_name__endswith=' ')).count()
```

**Acción**: correr `scripts/normalize_customer_spaces.py --confirm` en LOCAL. **NO en prod sin senior**.

---

## Parte 5 — Workflow recomendado para el día a día

1. **Por la mañana**:
   ```cmd
   cd C:\Users\TUUSUARIO\CascadeProjects\playa
   git pull
   venv\Scripts\activate
   set DB_ENGINE=sqlite
   set PYTHONUTF8=1
   scripts\run_local.bat
   ```
2. Abrir otra terminal para el frontend (mismo `git pull` y `python server.py`).
3. Abrir http://localhost:3000/ para validar visualmente.
4. Tomar 1 caso de la sección "Parte 4" según prioridad que te indique el senior.
5. Anotar lo que hacés en una hoja / Notion (qué chequeaste, qué decidiste, qué escalaste).

## Parte 6 — Cómo escalar

Cuando no sepas qué hacer:

1. Anotá en `docs/decisiones_pendientes.md`:
   - Fecha
   - Tu nombre
   - Caso (ej. "Patrón A — cliente Juan Pérez doc 12345 / DRV026-0001")
   - Qué estuviste mirando
   - Qué duda tenés
2. Mandá un mensaje al senior con el link al doc.

## Parte 7 — Scripts útiles (cheatsheet)

| Necesito… | Script |
|---|---|
| Ver estado de cartera | `print_cartera_state.py` |
| Ver disponibles por sucursal | `print_stock_state.py` |
| 27 chequeos de integridad | `health_check.py` |
| Reporte detallado de morosos | `report_overdue_sales.py` |
| Detectar ventas duplicadas | `find_duplicate_sales.py` |
| Detectar clientes duplicados | `find_duplicate_customers.py` |
| Aplicar cuotas de un archivo .ods | `apply_cuota_file.py SALE_NUMBER FILE` |
| Reconciliar morosos con archivo de planilla | `reconcile_pendiente_cobrar.py FILE` |
| Cruzar ventas BD vs archivo | `compare_ventas_files.py` |

Todos los scripts soportan `--help` para ver flags y `sin --confirm` para dry-run.

## Parte 8 — Recursos

- `docs/MANUAL_USUARIO.html` — manual del sistema para usuarios finales
- `docs/design/VEHICLE_STATES_PROPOSAL.md` — propuesta de ampliar estados
- `docs/design/INFORME_PENDIENTES_COMMIT.md` — lista de scripts y qué hacen
- `docs/reports/CLIENTES_DUPLICADOS.md` — análisis de duplicados
- `docs/reports/CARTERA_VENCIDA_ANALISIS.md` — análisis original de la cartera

---

*Versión 1.0 — actualizar cuando agreguemos nuevos casos.*
