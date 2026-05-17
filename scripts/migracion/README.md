# Scripts de migración

Conjunto de scripts para importar datos legacy al sistema. Usar **siempre con
backend Django detenido** (sino la BD puede quedar bloqueada).

## Orden de ejecución

1. **`import_stock.py`** — vehículos disponibles (no vendidos aún).
   ```bash
   python scripts/migracion/import_stock.py sucursal/stock/STOCK.ods 2
   ```
   (el segundo argumento es el `branch_id`: 1=CASA CENTRAL, 2=SUCURSAL 1)

2. **`import_ventas.py`** — ventas anuales con sus vehículos asociados.
   ```bash
   python scripts/migracion/import_ventas.py sucursal/ventas/VENTAS_2025.xlsx 2
   python scripts/migracion/import_ventas.py sucursal/ventas/VENTAS_2026.xlsx 2
   ```

3. **`import_cuotas.py`** — cuotas desde archivos individuales por cliente.
   ```bash
   python scripts/migracion/import_cuotas.py sucursal/cuotas/
   ```

## Convenciones importantes

- **Antes de cualquier import**, los scripts hacen backup automático con timestamp
  en el directorio raíz: `db.sqlite3.backup.pre_migracion_YYYYMMDD_HHMMSS`.
- **Trabajan en `/tmp/w.db`** y al final copian con `cat` (no `cp`) sobre la BD
  real para evitar issues con mounts Windows.
- **Tolerantes a duplicados**: si una venta ya existe (sale_number único) o un
  vehículo ya existe (VIN único), se saltea sin error.
- Los **chasis se normalizan** antes de comparar (sin espacios, sin ceros a la
  izquierda, sin sufijo `.0`).

## Helpers compartidos

`00_helpers.py` contiene los parsers reutilizables:
- `parse_fecha(s)` — robusto contra el bug de `dayfirst` que invertía día y mes
- `parse_amount(s)` — maneja `'1.420$'`, `'252$+440$'`, etc.
- `normalize_cm(code)` — unifica `MC 01/2025` → `MC01/25`
- `norm_vin(raw)` — normaliza VIN/chasis
- `extraer_chasis_de_texto(t)` — extrae chasis de descripción "VITZ 2010 CHAS: KSP90-..."
- `DOC_RE` — regex de número de cuota tolerante al punto final (`'1/8.'`)
- `backup_db / fresh_copy / write_back` — workflow seguro de BD

## Cuándo NO usar estos scripts

- Si los archivos nuevos tienen una estructura **distinta** a la documentada en
  `docs/MIGRACION_PLAYBOOK.md`, ajustar el script primero.
- Si la BD está siendo escrita por Django o por DB Browser, **detener** primero.
