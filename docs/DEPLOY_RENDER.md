# Guia de despliegue en Render

Arquitectura: dos servicios en Render + BD en Supabase

```
                +----------------------+
                |  Supabase (Postgres) |
                +----------+-----------+
                           ^
                           |
              +------------+-----------+
              | playa-backend (Django) |   web service en Render
              | https://playa-backend  |
              |    .onrender.com       |
              +------------+-----------+
                           ^
                           | (API REST + JWT)
                           |
              +------------+-----------+
              | playa-frontend (HTML) |   static site en Render
              | https://playa-front    |
              |    end.onrender.com    |
              +------------------------+
```

## Pre-requisitos

1. Cuenta en Render (gratis).
2. Repos `playa` y `playa-frontend` pusheados a GitHub.
3. BD Supabase ya migrada con datos.
4. Conocer el `DATABASE_URL` de Supabase.

## 1. Backend - playa

### 1.1 Pre-deploy local

Verificar que arranca contra Postgres antes de subir:

```cmd
cd C:\Users\prueb\CascadeProjects\playa
copy .env.example .env  REM si no existe
notepad .env
```

En el `.env`:

```
DEBUG=False
DB_ENGINE=postgres
DATABASE_URL=postgresql://postgres.NMELUKKL...@aws-1-sa-east-1.pooler.supabase.com:5432/postgres
SECRET_KEY=<algo-random-largo>
JWT_SECRET=<algo-random-largo>
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

Probar local:

```cmd
venv\Scripts\activate
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8001
```

En otra terminal:

```cmd
python scripts\migracion\smoke_test_apis.py
```

Si todos los endpoints responden OK, listo para deploy.

### 1.2 Push a GitHub

Verifica que `.env` NO se commitee (esta en `.gitignore`):

```cmd
cd C:\Users\prueb\CascadeProjects\playa
git status        REM .env NO debe aparecer
git add render.yaml requirements.txt playas_autos/settings.py scripts docs
git commit -m "feat: soporte Postgres + despliegue Render"
git push origin main
```

### 1.3 Deploy en Render

**Opcion A - Blueprint (recomendado):**

1. Render Dashboard -> New -> Blueprint
2. Conectar el repo `playa`
3. Render detecta `render.yaml` y crea el servicio
4. Despues completar variables marcadas `sync: false`:
   - `DATABASE_URL` -> el string de Supabase
   - `ALLOWED_HOSTS` -> `playa-backend.onrender.com` (se rellena el subdominio que Render asigne)
   - `CORS_ALLOWED_ORIGINS` -> `https://playa-frontend.onrender.com` (URL del frontend, lo conoces despues del paso 2)

**Opcion B - Manual:**

1. Render -> New -> Web Service
2. Conectar el repo `playa`
3. Configurar:
   - **Name:** playa-backend
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start Command:** `gunicorn playas_autos.wsgi:application --bind 0.0.0.0:$PORT`
   - **Plan:** Free
4. Variables de entorno (Environment tab):

| Variable | Valor |
|---|---|
| DEBUG | False |
| SECRET_KEY | (Render puede autogenerar) |
| JWT_SECRET | (Render puede autogenerar) |
| JWT_ALGORITHM | HS256 |
| DB_ENGINE | postgres |
| DATABASE_URL | postgresql://postgres.NMELUKKL...@aws-1-sa-east-1.pooler.supabase.com:5432/postgres |
| ALLOWED_HOSTS | playa-backend.onrender.com |
| CORS_ALLOWED_ORIGINS | https://playa-frontend.onrender.com |
| PYTHON_VERSION | 3.12.5 |

5. Click **Create Web Service**. Render hace el primer build (~3-5 min).

### 1.4 Verificar deploy

Render asigna URL: `https://playa-backend.onrender.com` (o el nombre que elegiste).

```cmd
curl https://playa-backend.onrender.com/api/schema/
```

Deberia responder con el schema OpenAPI.

## 2. Frontend - playa-frontend

### 2.1 Configurar URL del backend

Edita `config.js` del frontend con la URL que te dio Render:

```javascript
window.API_BASE_URL = 'https://playa-backend.onrender.com/api';
```

### 2.2 Push a GitHub

```cmd
cd C:\Users\prueb\CascadeProjects\playa-frontend
git status
git add config.js render.yaml index.html src/utils/api.js
git commit -m "feat: API URL configurable en runtime + Render static site"
git push origin main
```

### 2.3 Deploy en Render como Static Site

**Opcion A - Blueprint:** importar `render.yaml` desde el repo.

**Opcion B - Manual:**

1. Render -> New -> Static Site
2. Conectar el repo `playa-frontend`
3. Configurar:
   - **Name:** playa-frontend
   - **Build Command:** dejar vacio (no hay build)
   - **Publish Directory:** `.`
4. Rewrite Rules (Settings -> Redirects/Rewrites):
   - Source: `/*`
   - Destination: `/index.html`
   - Action: Rewrite

5. Create Static Site. Render lo despliega en ~1 min.

### 2.4 Actualizar CORS del backend

Volver al backend y agregar la URL definitiva del frontend a `CORS_ALLOWED_ORIGINS`:

```
https://playa-frontend.onrender.com
```

Render auto-redeploys cuando cambias env vars.

## 3. Verificacion final end-to-end

1. Abrir `https://playa-frontend.onrender.com`
2. Login con `admin / admin123`
3. Probar:
   - Dashboard carga datos
   - Inventario muestra los 624 vehiculos
   - Listado de ventas muestra 427
   - Listado de cuotas funciona
4. Abrir DevTools (F12) -> Network -> verificar que los requests van a `playa-backend.onrender.com/api/...`

## Troubleshooting

### Backend devuelve 502/503
- El plan free de Render duerme tras 15 min de inactividad. Primer request tarda 30-50s.
- Solucion: pasar a plan Starter ($7/mes) o usar un cron job que pingee cada 10 min.

### "CSRF verification failed"
- Agregar el dominio del frontend a `CSRF_TRUSTED_ORIGINS` en `settings.py` (no implementado todavia — solo si pasa).

### "DisallowedHost"
- Falta el dominio en `ALLOWED_HOSTS`. Agregarlo y redeployar.

### Frontend carga pero las APIs dan CORS error
- `CORS_ALLOWED_ORIGINS` no incluye el origen del frontend. Agregar y redeployar.

### Base de datos: too many connections
- Supabase free tier limita conexiones. Reducir `conn_max_age` o usar el connection pooler de Supabase (el URL del pooler ya esta configurado: puerto 5432 con `pooler.supabase.com`).

### Migrate falla al desplegar
- El backend NO corre `migrate` automaticamente; el schema ya esta en Supabase de la migracion previa. Si en algun momento agregas modelos nuevos, agrega `python manage.py migrate --noinput` al `buildCommand` del backend.

## Roll back

Para volver a desarrollo local con SQLite:

```
DB_ENGINE=sqlite
```

Para apagar el frontend y volver a localhost: editar `config.js` y comentar la linea de `window.API_BASE_URL`, o ignorar — el frontend en localhost igual usa default.

## Costos

| Servicio | Plan | Costo |
|---|---|---|
| playa-backend | Render Free | $0 (con sleep) o $7/mes Starter |
| playa-frontend | Render Static Free | $0 |
| Supabase Postgres | Free | $0 (500MB) |

Total free tier: $0/mes con caveat del sleep. Recomendado pagar el backend ($7/mes) para evitar el cold start.
