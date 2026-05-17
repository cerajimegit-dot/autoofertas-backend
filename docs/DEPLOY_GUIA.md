# Guía de deploy — GitHub + Render

Esta guía cubre dos pasos:

1. Subir el código a GitHub (dos repos: backend + frontend).
2. Conectar Render a esos repos para que cada `git push` redeploye solo.

Pre-requisitos:
- Cuenta en [github.com](https://github.com).
- Cuenta en [render.com](https://render.com) (gratis).
- Cuenta en [supabase.com](https://supabase.com) (gratis) con la BD lista.
- Git instalado localmente (`git --version` para confirmar).

Antes de empezar, leé también [PRODUCCION_CHECKLIST.md](PRODUCCION_CHECKLIST.md)
— las defensas (rate limit, HTTPS, etc.) ya están en código; este doc se
enfoca en cómo subirlo bien.

---

## Parte 1 — Subir a GitHub

### 1.1. Verificar que no se filtre nada sensible (¡importante!)

Antes de hacer `git add`, **revisar qué archivos quedarían incluidos**.
Si subís `.env`, `db.sqlite3`, `credenciales.txt` o cualquier archivo con
contraseñas, **es un incidente de seguridad** — Github indexa esos
commits casi inmediatamente y los bots los escanean.

El `.gitignore` ya está configurado para excluir:

**Lo más pesado y peligroso:**
- `venv/`, `env/`, `.venv` — el virtualenv de Python (143 MB en local)
- `node_modules/`, `dist/`, `build/` — del frontend (cuando exista)
- `__pycache__/`, `*.pyc`, `.pytest_cache/` — caches de Python
- `staticfiles/`, `media/`, `logs/` — generados en runtime

**Datos sensibles del negocio:**
- `.env`, `.env.local`, `.env.postgres` — secrets
- `db.sqlite3` y todos los `db.sqlite3.backup.*` — la base de datos local
- `backups/` — backups históricos de la BD (4.4 MB con datos reales)
- `archivos_playa/`, `cuotas/`, `sucursal/`, `ventas/` — Excels del negocio
- `52-FLUJO DE CAJA*.ods` — flujo de caja real
- `credenciales.txt`, `USUARIOS_ACCESO.txt`, `*.pem`, `*.key`

**Logs viejos de migración inicial** (referencia histórica, no útil para el repo):
- `migration_log*.txt`, `migration_final.txt`, etc.

**Verificación obligatoria antes del primer push:**

```bash
# 1. Cuánto pesa el repo (debería ser ~1.5 MB el backend, ~0.5 MB el frontend)
git ls-files | while read -r f; do du -k "$f" 2>/dev/null; done \
  | awk '{s+=$1} END {printf "Repo total: %.2f MB en %d files\n", s/1024, NR}'

# 2. ¿Hay secretos ahí adentro?
git ls-files | grep -iE "\.env$|credenciales|password|secret|\.key$|\.pem$"
# Esperado: vacío.

# 3. ¿Hay datos del negocio?
git ls-files | grep -iE "^(backups|archivos_playa|cuotas|sucursal|ventas)/"
# Esperado: vacío.

# 4. ¿Está el virtualenv?
git ls-files | grep -E "^(venv|env|\.venv)/" | head -3
# Esperado: vacío.
```

Si alguno devuelve resultados, **agregar al `.gitignore` y des-trackear
con `git rm -r --cached <archivo>`** antes de hacer push. Si ya hiciste
push, el archivo queda en el historial y hay que reescribir historia con
`git filter-repo` — preferible evitar.

### 1.2. Crear los repos en GitHub

Dos repos separados (backend y frontend) porque Render los trata como
servicios distintos.

1. En github.com, crear repo **privado** `autoofertas-backend` (sin
   README, sin .gitignore — los tenés en local).
2. Crear repo **privado** `autoofertas-frontend` (igual).

> ⚠ Privados: aunque el código en sí no tiene secrets (gracias al
> .gitignore), mantenerlo privado es buena práctica para un sistema con
> datos del negocio. Render conecta a repos privados sin problema.

### 1.3. Inicializar y subir el backend

```bash
cd C:/Users/prueb/CascadeProjects/playa

# Si nunca se commiteó este repo todavía:
git init
git branch -M main

# Confirmar el remoto (cambiar tu-usuario)
git remote add origin https://github.com/tu-usuario/autoofertas-backend.git

# Verificar otra vez que no haya secretos
git status

# Primer commit
git add .
git commit -m "Initial commit — AUTO OFERTAS backend"
git push -u origin main
```

Si hace falta autenticarte, usar un **personal access token** (GitHub →
Settings → Developer settings → Personal access tokens → Fine-grained →
crear con permiso `Contents: Read/Write` sobre el repo).

### 1.4. Subir el frontend

```bash
cd C:/Users/prueb/CascadeProjects/playa-frontend

git init
git branch -M main
git remote add origin https://github.com/tu-usuario/autoofertas-frontend.git
git add .
git commit -m "Initial commit — AUTO OFERTAS frontend"
git push -u origin main
```

### 1.5. Workflow después del primer push

A partir de acá, cada cambio:

```bash
git add <archivo>
git commit -m "explicación breve del cambio"
git push
```

Render lo detecta y redeploya automáticamente (~2-5 minutos).

---

## Parte 2 — Configurar Supabase

Si todavía no lo tenés:

1. Crear proyecto en supabase.com (región **South America (São Paulo)**
   por latencia desde Paraguay).
2. Cuando termine de crearse, ir a **Settings → Database → Connection
   pooling**.
3. Copiar la **Connection string** del **Transaction pooler** (puerto
   **6543**, no el 5432). Se verá tipo:
   ```
   postgresql://postgres.xxx:[PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
   ```
4. Reemplazar `[PASSWORD]` con la contraseña real de la DB (la podés
   resetear en la misma pantalla si no la tenés).
5. Guardar esa URL — la vas a pegar en Render como `DATABASE_URL`.

> ⚠ **Por qué puerto 6543 y no 5432**: el pooler de transacciones
> reusa conexiones (necesario porque Render free tier solo da 60-100
> conexiones totales). El session pooler en 5432 las consume todas en
> minutos. Esto ya está documentado en `playas_autos/settings.py`.

---

## Parte 3 — Deploy del backend en Render

### 3.1. Crear el servicio

1. En render.com → **New +** → **Blueprint**.
2. Seleccionar el repo `autoofertas-backend`.
3. Render detecta el `render.yaml` y propone crear `playa-backend` como
   web service.
4. Revisar la lista de variables: las que dicen `sync: false` aparecen en
   blanco — hay que completarlas.

### 3.2. Completar variables de entorno

En el dashboard del servicio, pestaña **Environment**, completar:

| Variable | Valor |
|---|---|
| `DATABASE_URL` | la URL del pooler de Supabase (puerto 6543) |
| `ALLOWED_HOSTS` | `<nombre-del-servicio>.onrender.com` (ej: `playa-backend.onrender.com`). Si tenés dominio propio, agregalo separado por coma. |
| `CORS_ALLOWED_ORIGINS` | URL completa del frontend con https, ej: `https://playa-frontend.onrender.com` |

Las otras variables (`SECRET_KEY`, `JWT_SECRET`, `THROTTLE_*`, `SECURE_*`)
ya quedaron configuradas por el `render.yaml`.

### 3.3. Build y deploy

Render arranca el build automáticamente. El log debería mostrar:

```
==> Installing dependencies from requirements.txt
==> Running 'python manage.py collectstatic --noinput'
==> Running 'python manage.py migrate'
==> Starting 'gunicorn playas_autos.wsgi:application ...'
==> Your service is live at https://playa-backend.onrender.com
```

### 3.4. Verificación post-deploy

```bash
# 1. Health check (sin auth)
curl https://playa-backend.onrender.com/api/users/health/
# Esperado: {"status":"ok","db":"ok"}

# 2. HTTPS forzado
curl -I http://playa-backend.onrender.com/api/users/health/
# Esperado: 301/302 redirect a https

# 3. Login funciona
curl -X POST https://playa-backend.onrender.com/api/users/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
# Esperado: 200 con access + refresh

# 4. Rate limit del login
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code} " https://playa-backend.onrender.com/api/users/login/ \
    -X POST -H 'Content-Type: application/json' -d '{"username":"x","password":"y"}'
done
echo
# Esperado: 401 401 401 401 401 429 429 429 429 429
```

### 3.5. Problemas comunes

| Síntoma | Causa probable |
|---|---|
| Build falla en `migrate` con "permission denied" | El pooler de Supabase a veces no tiene permiso para `CREATE SCHEMA` durante migración. Solución: correr `python manage.py migrate` localmente apuntando a la BD prod antes del primer deploy. |
| 502 Bad Gateway al entrar | Gunicorn no arrancó. Mirar **Logs** en Render — suele ser `SECRET_KEY` faltante o `DATABASE_URL` mal pegada. |
| Login devuelve 500 | `ALLOWED_HOSTS` no incluye el dominio que recibe la request. |
| Frontend recibe CORS error | `CORS_ALLOWED_ORIGINS` no tiene el dominio exacto (con `https://`, sin `/` al final). |
| Después de redeploy el rate limit "se reinició" | Esperado: el LocMemCache se borra al reiniciar workers. Para persistencia agregar Redis (ver checklist). |

---

## Parte 4 — Deploy del frontend en Render

### 4.1. Configurar `config.js` con la URL del backend

Antes del primer push del frontend, editar
`playa-frontend/config.js` para apuntar al backend de prod:

```javascript
// config.js
window.API_BASE_URL = 'https://playa-backend.onrender.com/api';
```

Subir el cambio:

```bash
cd C:/Users/prueb/CascadeProjects/playa-frontend
git add config.js
git commit -m "Apuntar config.js al backend de Render"
git push
```

### 4.2. Crear el static site en Render

1. **New +** → **Blueprint** → repo `autoofertas-frontend`.
2. Render detecta el `render.yaml` y crea `playa-frontend` como static
   site (sin build, sirve los archivos tal cual).
3. **Deploy**.

### 4.3. Verificación post-deploy

Abrir https://playa-frontend.onrender.com en el browser:

- Debe verse el **logo de AUTO OFERTAS** en el login.
- Login con `admin / admin123` (o el usuario que crearas).
- Después del login, en el navbar arriba a la izquierda debe estar el
  logo + "AUTO OFERTAS".
- Probar 1 página de cada (Dashboard, Ventas, Clientes, Flujo de caja).
- Mirar DevTools → Network: las requests al backend deben ser
  `https://playa-backend.onrender.com/api/...` (no localhost).

---

## Parte 5 — Mantenimiento

### Cómo redeployar después de un cambio

```bash
# Backend o frontend, el flujo es el mismo:
git add .
git commit -m "Descripción del cambio"
git push
# Render redeploya en 2-5 min, sin downtime (rolling deploy).
```

### Cómo correr migraciones de Django nuevas en producción

Las migraciones se aplican **automáticamente** en cada deploy gracias a:

```yaml
buildCommand: |
  pip install -r requirements.txt
  python manage.py collectstatic --noinput
  python manage.py migrate     # ← acá
```

Si una migración es destructiva o necesita confirmación, correrla
manualmente desde tu máquina apuntando a la BD prod:

```bash
# Solo para casos especiales — el flujo normal es vía deploy
DATABASE_URL='<la URL de Supabase>' python manage.py migrate
```

### Cómo ver logs en vivo

Dashboard de Render → servicio → pestaña **Logs**. Filtrar por nivel
(WARNING/ERROR) para encontrar problemas rápido. El logger `security`
muestra los intentos de login fallidos con la IP.

### Cómo conectarse a la BD desde local para hacer queries

```bash
# Necesitás psql instalado
psql 'postgresql://postgres.xxx:[PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres'
```

O usar el Table Editor de Supabase desde el browser.

### Cómo agregar Redis para que el throttling sea global

1. En Render: **New +** → **Redis** → plan free (25 MB).
2. Copiar el **Internal URL** que muestra (empieza con `redis://`).
3. En el servicio del backend, agregar variable `REDIS_URL` con ese valor.
4. Descomentar el bloque `CACHES` en `playas_autos/settings.py` (líneas
   ya documentadas en PRODUCCION_CHECKLIST §4).
5. Commit + push → redeploy.

### Backups periódicos

Supabase free tier hace daily snapshots con 7 días de retención. Para
algo más serio, agendar un dump semanal local:

```bash
pg_dump --no-owner --no-acl -Fc "$DATABASE_URL" > backup_$(date +%Y%m%d).dump
```

Guardar en Google Drive / Dropbox / S3. Mes vencido = 4 archivos al año.

---

## Parte 6 — Después del primer launch

Pasos sugeridos las primeras 48 hs:

1. **Verificar todos los flujos críticos** una vez en prod:
   - Login con cada usuario real (`papa`, `mati`, `marcelo`, `rocio`).
   - Cargar una venta de prueba completa.
   - Cobrar una cuota con forma de pago.
   - Generar un link de WhatsApp.
   - Cargar un gasto manual en `/flujo-caja`.
2. **Limpiar los datos sucios** documentados en
   [UX_AUDIT §5](UX_AUDIT.md): clientes con doc autogenerado, ventas MIG,
   vehículos available que ya están vendidos. La mayoría se hace desde
   la UI.
3. **Cambiar contraseñas iniciales**. `admin/admin123` y
   `autoofertas2026` son débiles — pedirle a cada usuario que use
   `/users` (admin) o `set_password` para poner una propia.
4. **Subir HSTS a 1 año** cuando hayas validado 1 semana sin problemas:
   `SECURE_HSTS_SECONDS=31536000` en el dashboard de Render → Save.
5. **Monitorear `logs/django.log`** en Render por 1 semana para detectar
   patrones de error o ataques (login_failed repetidos desde la misma IP).

---

## Anexo — Resumen de URLs

Después del deploy tendrías 4 URLs en juego:

| Servicio | URL |
|---|---|
| Frontend | `https://playa-frontend.onrender.com` |
| Backend API | `https://playa-backend.onrender.com/api/` |
| Backend Admin Django | `https://playa-backend.onrender.com/admin/` (sólo super-users) |
| Supabase Dashboard | `https://app.supabase.com/project/xxx` |

Si compraran un dominio propio (ej: `autoofertas.com.py`), apuntarlo al
servicio en Render → **Custom Domain** → seguir las instrucciones de DNS
que Render muestra. Tarda 5-30 min en validarse + propagar.
