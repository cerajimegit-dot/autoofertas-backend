# Backups del sistema AUTO OFERTAS

Esta carpeta contiene snapshots completos de la base de datos en
formato JSON portable (Django `dumpdata`). Cada archivo `.json.gz` es
una copia completa de:

- Empresas, Sucursales, Usuarios
- Clientes (con docs, teléfonos, emails)
- Vehículos (con costos extras)
- Marcas y Modelos
- Ventas + Cuotas + Cobranzas
- Movimientos de caja (Ingresos / Egresos)
- Audit Log

**No incluye**: tokens JWT vivos (no sirven después de restore),
extensiones de Postgres, schema (eso está en `core/migrations/`).

> ⚠ Estos archivos contienen **datos personales reales** (nombres,
> documentos, teléfonos, montos). NO commitearlos al repo público
> de GitHub. La carpeta `backups/` ya está en `.gitignore`.

---

## Cuándo se generan

| Método | Frecuencia | Dónde quedan |
|---|---|---|
| Manual (`python scripts/backup_db.py`) | Cuando lo corras vos | `backups/snapshot_<TS>.json.gz` |
| GitHub Action automática | Cada lunes 03:00 UTC | Artifact del workflow (90 días) |
| Antes de cada deploy importante | Manual, recomendado | Idem |

---

## Cómo generar uno nuevo (manual)

Desde la raíz del repo:

```bash
python scripts/backup_db.py
```

Salida típica:
```
=== Generando backup → backups/snapshot_2026-05-17_132107.json ===
  ✓ 3,083,419 bytes en 45.2s
  Verificando integridad...
  ✓ 5,725 filas parseables
  ✓ Comprimido: 124,331 bytes (24.8× reducción)
  ✓ MD5: b9faee9a143817c4eb2128ad7a6d705e

Archivo final: backups/snapshot_2026-05-17_132107.json.gz
```

Para borrar backups antiguos al mismo tiempo:

```bash
python scripts/backup_db.py --keep-last 30   # deja sólo los 30 más recientes
```

---

## Cómo verificar un backup sin restaurar

```bash
python scripts/restore_backup.py backups/snapshot_xxx.json.gz --dry-run
```

Eso valida que el archivo sea legible y muestra el resumen, sin tocar
nada.

---

## Cómo restaurar (3 escenarios)

### A. Restore COMPLETO a una BD local de testing

Lo más seguro. Crea/usa SQLite local sin tocar Supabase.

```bash
# Borrar BD local previa (si existe) y empezar limpio
rm -f db.sqlite3
DB_ENGINE=sqlite python manage.py migrate
DB_ENGINE=sqlite python scripts/restore_backup.py backups/snapshot_xxx.json.gz
```

Después podés correr `DB_ENGINE=sqlite python manage.py runserver` y
explorar la BD restaurada sin riesgo.

### B. Restaurar SÓLO algunas tablas a producción

Útil si alguien borró por error las ventas pero no quieren tocar el
resto. Restaura sólo `core.sale` y `core.quotum`.

```bash
python scripts/restore_backup.py backups/snapshot_xxx.json.gz \
    --tables core.sale,core.quotum \
    --confirm-prod
```

Django va a hacer "upsert" por primary key: las ventas que ya están en
prod las actualiza, las que faltan las inserta.

### C. RESTORE TOTAL a producción (escenario catastrófico)

⚠ **Esto borra lo que esté en prod y reemplaza por el backup.** Sólo en
caso real de desastre (alguien borró toda la BD por accidente).

```bash
python scripts/restore_backup.py backups/snapshot_xxx.json.gz \
    --truncate \
    --confirm-prod
```

El script te pide confirmación explícita dos veces ("SI RESTAURAR" y
"SI BORRAR") antes de tocar nada.

---

## Después de un restore en Postgres: resetear secuencias

Postgres usa secuencias para los `id` auto-incrementales. `loaddata` no
las actualiza. Si insertás nuevas filas después del restore podés ver:

```
duplicate key value violates unique constraint "core_sale_pkey"
```

Solución (correr una sola vez):

```bash
python manage.py shell -c "
from django.db import connection
TABLES = ['core_sale', 'core_quotum', 'core_customer', 'core_vehicle',
          'core_cashmovement', 'core_brand', 'core_vehiclemodel',
          'core_paymentform', 'core_branch', 'core_enterprise',
          'core_customuser', 'core_auditlog']
with connection.cursor() as c:
    for t in TABLES:
        c.execute(f\"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE(MAX(id), 1)) FROM {t}\")
        print(f'  reset {t}.id_seq')
"
```

---

## Estrategia de retención sugerida

| Backup | Retener |
|---|---|
| Daily | 7 últimos (manual o cron) |
| Semanal | 4 últimos meses (GitHub Action artifact = 90 días) |
| Mensual | 12 meses (descargar artifact y guardar en Google Drive) |
| Anual | Indefinido (un .gz por año, ~150 KB cada uno) |

Total: ~30 archivos, <10 MB. Costo: $0.

---

## Anti-tips (cosas que NO hacer)

- **No commitear** los .json.gz al repo. Datos sensibles.
- **No restaurar a prod sin probar primero en local** (escenario A).
- **No editar el .json a mano** antes de restaurar. Si necesitás cambiar
  algo, hacé el restore a local, editá ahí, y volvé a hacer dumpdata.
- **No saltearse `--confirm-prod`**. El flag existe para que tu dedo se
  detenga 1 segundo antes de hacer algo irreversible.
- **No dependas SÓLO de los backups automáticos de Supabase**. El plan
  free retiene 7 días y no es descargable. Tu propio snapshot semanal
  vive en tus manos.

---

## Snapshots disponibles

Listalos con:

```bash
ls -lh backups/snapshot_*.json.gz
```

Cada uno mostrará: nombre, tamaño, fecha de creación.
