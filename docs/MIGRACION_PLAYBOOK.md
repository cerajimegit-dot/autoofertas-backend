# Playbook de migración de datos

Este documento describe el proceso de migración de datos legacy al sistema
Playas de Autos. Pensado para reproducirse en futuras importaciones.

## Contexto

Los datos vienen de tres fuentes paralelas:
1. **Sistema viejo** (Flask + SQLite) — `stock.db` con tablas `venta`, `cliente`, `producto`, `cuota`.
2. **Planillas anuales** — un Excel por año por sucursal con todas las ventas (`VENTAS YYYY.xlsx` u `.ods`).
3. **Archivos individuales por cliente** — `.ods` con el detalle de cuotas (`NN - NOMBRE.ods`).

## Orden estándar

```
1. Crear sucursal nueva (si corresponde)  →  manual o vía /api/branches/
2. Importar stock                          →  import_stock.py
3. Importar ventas                         →  import_ventas.py
4. Importar cuotas                         →  import_cuotas.py
5. Cruzar con planilla anual               →  update_costos.py (opcional)
6. Recuperar fechas reales                 →  fix_dates.py (opcional)
7. Crear usuarios para la sucursal         →  manual o desde UI admin
```

## Estructura de archivos esperada

### Stock (`STOCK.ods`)

```
[Header]
TIPO DE CAMBIO X.YYY
COMPRAS RORO/CONTENEDOR DD/MM/YYYY
| MARCA | MODELO | COLOR | AÑO | CHASISS | PRECIO IQ | CIGÜEÑA | DESPACHO | GAS APROX | COSTO TOTAL | PRECIO |
| 1     | TOYOTA | VITZ  | NEG | 2008    | KSP90-... | 2400    | 575     | 12000000  | 2000000    | 33336000  | 42000000 |
...
[Otra compra]
TIPO DE CAMBIO X.YYY
COMPRAS RORO ...
| MARCA | ... |
```

- Las filas válidas tienen un **número correlativo** en la columna 0.
- Pueden haber múltiples grupos de compras separados por headers.
- Saltar filas que no empiecen con número.

### Ventas anuales (`VENTAS YYYY.xlsx`)

Header en R2 (R0/R1 son títulos):
```
| C/I | MARCA | MODELO | COLOR | AÑO | CHASISS | PRECIO IQ | CIGÜEÑA | DESPACHO | GAS APROX | COSTO TOTAL | VENTA | GANANCIA | CONDICION | FECHA |
| MC 01/25 | TOYOTA | VITZ 1.3 | PLATA | 2011 | NSP130-... | 2622 | 575 | 10536000 | 2000000 | 37785860 | 50000000 | 12214140 | CREDITO | 2025-05-14 |
```

- Casa Central usa códigos `CMNN/YY` (sin espacio).
- Sucursal 1 usa códigos `MC NN/YY` o `MC NN/YYYY` (con espacio).
- El normalizador unifica todo a `XX##/YY`.

### Cuotas individuales (`NN - NOMBRE.ods`)

```
R0: NOMBRE COMPLETO DEL CLIENTE
R1: CEL/TEL: <numero>
R2: <descripción vehículo> CHASIS: <chasis>
R3: VTO | DOC | MONTO | FECHA | FORMA
R4..N: <fecha vto> | "1/N" o "1/N." | <monto> | <fecha pago opcional> | "EFE/TB/CHEQUE"
[fila vacía]
DEUDA TOTAL | <monto>
MC NN/YYYY  ← código de la venta
ENTREGA <monto>
SALDO N CUOTAS DE <monto>
VENTA TOTAL <monto>
```

- Las cuotas con **fecha en columna FECHA** están **pagadas**.
- "VENCIDO" o vacío = no pagada.
- El número de cuota puede tener punto al final (`'1/8.'`).

## Casos especiales detectados

### Bug del parser de fechas
Pandas devuelve `Timestamp` que extiende `datetime`. NUNCA pasar la fecha por
`pd.to_datetime(str(s), dayfirst=True)` porque invierte día y mes en strings ISO.
Usar `date(s.year, s.month, s.day)` directo.

**Síntoma:** las cuotas que deberían ser día 10 quedan como mes 10. Por ejemplo
`2026-02-10` (10 feb) se guarda como `2026-10-02` (2 oct).

**Affectados originalmente:** 20 ventas de Casa Central + 1 de Sucursal 1 (MC01/26).
Todas reparadas con el script de re-import.

### Bug de la regex de cuotas
Algunas planillas escriben `"1/8."` con punto al final. La regex original
`r'\s*([0-9]+)\s*/\s*([0-9]+)\s*$'` no aceptaba el punto y se saltaba esas filas.

**Síntoma:** una venta que debería tener 8 cuotas aparece con 4 (las primeras
con punto se perdieron).

**Detectados:** MC56/25 (Emigdio Fariña Rodríguez) — 4 cuotas perdidas.
MC13/26 (Juan Gilberto Moreno) — 2 cuotas perdidas.

**Fix:** usar `r'\s*([0-9]+)\s*/\s*([0-9]+)\s*[.]?\s*$'`.

### Placeholders de cuotas huérfanas
Durante una migración previa quedaron 21 ventas con sale_numbers `V000001`-`V000020`
y `VDUMMY` que tienen VINs falsos como `VIN-DUMMY-QUOTAS` y `VIN001NNN`. Estas
ventas no son reales — son cáscaras para preservar cuotas que no se podían
asignar a ninguna venta concreta.

**Para excluirlas del dashboard:**
```python
.exclude(vehicle__vin__startswith='VIN-DUMMY')
.exclude(vehicle__vin__regex=r'^VIN[0-9]+$')
```

Si más adelante se les asigna un VIN real, automáticamente vuelven a contar.

## Constantes del proyecto

| Concepto | Valor |
|---|---|
| Enterprise AUTO OFERTAS | id = 3 |
| Branch CASA CENTRAL | id = 1 (code = CC) |
| Branch SUCURSAL 1 | id = 2 (code = S1) |
| PaymentForm CONTADO | id = 1 |
| PaymentForm CREDITO | id = 3 (sin tilde, el principal) |
| PaymentForm MIXTO | id = 4 |
| Brand TOYOTA | id = 1 |
| Brand HYUNDAI | id = 2 |
| Brand SUBARU | id = 3 |
| Brand KIA | id = 5 |

## Workflow seguro de BD

Ver `scripts/migracion/00_helpers.py` (funciones `backup_db`, `fresh_copy`,
`write_back`). El procedimiento es:

1. **Backup nominado** con timestamp.
2. **Copia a `/tmp/w.db`** vía la backup API de SQLite.
3. **Trabajar en `/tmp/w.db`** (escrituras).
4. **`PRAGMA integrity_check`** antes de copiar de vuelta.
5. **`cat /tmp/w.db > db.sqlite3`** (no `cp`).

## Rollback

Si algo sale mal:
```bash
ls -lt db.sqlite3.backup.* | head
cp db.sqlite3.backup.pre_<accion>_YYYYMMDD_HHMMSS db.sqlite3
```

## Próximas migraciones

Cuando lleguen archivos nuevos:
1. Verificar la estructura de los archivos contra los formatos descritos arriba.
2. Si hay columnas extra o headers distintos, ajustar el script correspondiente.
3. Hacer un dry-run primero (comentar los `INSERT` y revisar el output).
4. Aplicar el import.
5. Verificar contadores antes/después en la BD.
6. Probar la UI con una venta de muestra.
