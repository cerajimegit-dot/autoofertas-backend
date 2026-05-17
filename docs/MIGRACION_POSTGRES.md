# Migracion SQLite -> Postgres (Supabase)

## Pre-requisitos

1. **Connection string de Supabase** ya esta en `.env` (no se commitea).
2. **Variable `DB_ENGINE`** controla que motor usa Django:
   - `DB_ENGINE=sqlite` -> usa `db.sqlite3` local (default)
   - `DB_ENGINE=postgres` -> usa `DATABASE_URL` (Supabase)

## Como migrar

Desde la raiz del proyecto:

```cmd
scripts\migracion\migrate_to_postgres.bat
```

O directo:

```cmd
pip install psycopg2-binary dj-database-url
python scripts\migracion\migrate_to_postgres.py
```

El script:

1. Prueba la conexion a Supabase
2. Hace backup de `db.sqlite3` -> `backups/db_pre_postgres_YYYYMMDD_HHMMSS.sqlite3`
3. Genera dump JSON de toda la data (excluye contenttypes, permissions, sessions)
4. Crea el schema en Postgres con `migrate`
5. Vacia tablas auto-pobladas (`django_content_type`, `auth_permission`) para evitar conflictos al cargar
6. Carga el dump JSON con `loaddata`
7. Resetea sequences de Postgres al `MAX(id)+1` de cada tabla
8. Compara conteos SQLite vs Postgres para confirmar

## Despues de la migracion

Para que la app use Postgres, editar `.env`:

```
DB_ENGINE=postgres
```

Para volver a SQLite (rollback):

```
DB_ENGINE=sqlite
```

El backup en `backups/` permite restaurar el SQLite original copiandolo sobre `db.sqlite3`.

## Troubleshooting

### "could not translate host name"
Problema de DNS. Verificar que la connection string es correcta y que tenes internet.

### "FATAL: Tenant or user not found"
Problema de auth. Verificar usuario/password en `DATABASE_URL`. El usuario incluye el project ID (`postgres.NMELUKKL...`).

### "could not connect to server"
Supabase puede estar pausado (free tier). Entrar al dashboard y reactivar.

### Error al loaddata sobre auth_user / users
Los usuarios viejos pueden tener passwords no compatibles. Si hay error, exportar usuarios aparte:

```cmd
python manage.py dumpdata core.CustomUser --indent 2 > users.json
```

### Sequences corruptas (errores de PK al insertar nuevos registros)
Re-correr solo el paso 7 del script:

```cmd
python -c "
import os, psycopg2
from decouple import config
conn = psycopg2.connect(config('DATABASE_URL'))
conn.autocommit = True
cur = conn.cursor()
cur.execute('''SELECT 'SELECT setval(pg_get_serial_sequence(''''public.' || tablename || '''''', ''id''), COALESCE((SELECT MAX(id) FROM public.' || tablename || '), 1));' FROM pg_tables WHERE schemaname=''public''  AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=''public'' AND table_name=pg_tables.tablename AND column_name=''id'')''')
for r in cur.fetchall(): cur.execute(r[0])
"
```

## Snapshot esperado post-migracion

Conteos al momento de la migracion (2026-05-11):
- core_enterprise: 3
- core_branch: 2
- core_customuser: ~5 usuarios
- core_customer: 298
- core_sale: 427
- core_quotum: 3044
- core_vehicle: 631
- core_brand: 7
- core_vehiclemodel: ~45
