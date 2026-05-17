# Checklist pre-producción — AUTO OFERTAS

Última actualización: 2026-05-17

Antes de exponer el sistema en internet, recorré este checklist. Cada
ítem tiene un check de verificación que podés correr.

---

## 1. Variables de entorno (`.env`)

| Variable | Valor de prod | Por qué |
|---|---|---|
| `DEBUG` | `False` | Con `DEBUG=True` Django muestra el traceback completo + datos sensibles ante cualquier error 5xx. |
| `SECRET_KEY` | string random de 50+ chars | Firma cookies, tokens CSRF y JWT. Si se filtra, alguien puede forjar sesiones. |
| `ALLOWED_HOSTS` | `autoofertas.com.py,api.autoofertas.com.py` (sin localhost) | Bloquea ataques de Host header injection. |
| `DB_ENGINE` | `postgres` | — |
| `DATABASE_URL` | URL del **transaction pooler** de Supabase (puerto 6543) | El session pooler (5432) limita a 60 conexiones — se agota rápido. |
| `CORS_ALLOWED_ORIGINS` | sólo el dominio real del frontend (https) | Sin esto cualquier origen puede llamar a la API con la cookie del usuario. |
| `SECURE_SSL_REDIRECT` | `True` | Redirige http→https. |
| `SECURE_HSTS_SECONDS` | `3600` (1h) la primera semana, después `31536000` (1 año) | El browser memoriza que tu dominio es https-only. |

**Cómo verificar:**
```bash
python -c "from playas_autos import settings; \
  print('DEBUG:', settings.DEBUG); \
  print('PROD:', settings.IS_PRODUCTION); \
  print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS); \
  print('CORS:', settings.CORS_ALLOWED_ORIGINS)"
```

`IS_PRODUCTION` debe ser `True`.

Si `DEBUG=False` y `SECRET_KEY` empieza con `django-insecure-`, Django **falla al iniciar** con un `RuntimeError` claro. Ese guard ya está.

---

## 2. JWT — rotación y blacklist

Ya implementado:
- `ROTATE_REFRESH_TOKENS = True` — cada vez que el cliente renueva, recibe un refresh nuevo.
- `BLACKLIST_AFTER_ROTATION = True` — el refresh viejo queda inservible.
- `token_blacklist` app activa + migraciones aplicadas.
- Endpoint `POST /api/users/logout/` con `{"refresh": "..."}` invalida el refresh enviado.

**Cómo verificar:**
```bash
# Test automático
python manage.py test tests.test_security.TestJWTBlacklist
```

**Frontend**: `AuthContext.logout()` llama al endpoint pasando el refresh — ya está.

---

## 3. Rate limiting

| Endpoint | Límite | Variable |
|---|---|---|
| `/api/users/login/` | 5/min por IP | `THROTTLE_LOGIN` |
| `/api/users/register/` | 3/min por IP | `THROTTLE_REGISTER` |
| `/api/quotas/{id}/contact_whatsapp/` | 30/min por IP | `THROTTLE_WHATSAPP` |
| Cualquier request anónimo | 60/min | `THROTTLE_ANON` |
| Cualquier request autenticado | 600/min | `THROTTLE_USER` |

Si alguien intenta brute-force el login, después del 5° intento en 60s recibe `429 Too Many Requests` por 1 minuto. Cada login fallido se loguea en `logs/django.log` con `level=WARNING` y prefijo `security:` (incluye IP del cliente).

**Atención**: el throttle vive en el cache. En producción con varios workers de Gunicorn, **usar Redis** (no LocMemCache). Mientras estés en LocMem, los límites son por-worker, no globales. Si tenés 4 workers, el atacante puede hacer 4×5 = 20 intentos antes de que el primer worker lo frene.

**Cómo verificar:**
```bash
# Hacer 10 logins fallidos rápido — los últimos 5 deben devolver 429.
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST https://api.autoofertas.com.py/api/users/login/ \
    -H 'Content-Type: application/json' -d '{"username":"x","password":"y"}'
done
# Esperado: 401 401 401 401 401 429 429 429 429 429
```

---

## 4. Cache compartido (para throttling y dashboard)

**ACCIÓN REQUERIDA antes de prod**: cambiar `LocMemCache` por Redis.

Archivo: `playas_autos/settings.py` (agregar):
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL'),  # ej: redis://...:6379/0
    }
}
```

Y en `.env`: `REDIS_URL=...`. Render ofrece Redis gratis hasta 25MB — alcanza.

Sin esto: throttling no es global (cada worker tiene su propio contador) y los dashboards se ven inconsistentes entre refreshes.

---

## 5. Cookies seguras + headers

Cuando `IS_PRODUCTION=True`, automáticamente se activan:
- `SESSION_COOKIE_SECURE=True` — cookies sólo por https.
- `CSRF_COOKIE_SECURE=True`.
- `X_FRAME_OPTIONS='DENY'` — no se puede embeber el sitio en un iframe.
- `SECURE_CONTENT_TYPE_NOSNIFF=True`.
- `SECURE_BROWSER_XSS_FILTER=True`.

**Cómo verificar:**
```bash
curl -I https://autoofertas.com.py | grep -iE "strict-transport|x-frame|content-type-options"
# Esperado:
#   Strict-Transport-Security: max-age=3600
#   X-Frame-Options: DENY
#   X-Content-Type-Options: nosniff
```

---

## 6. Permisos y aislamiento multi-tenant

- `/api/users/` requiere admin para list/create/update/destroy. `me/` y `login` son públicos.
- Todos los viewsets filtran por `enterprise=request.user.enterprise`. Probado con `test_retrieve_404_for_other_enterprise`.
- Vendor no puede borrar ventas (`CanDeleteSale`).
- Movimientos de caja auto-generados no se pueden borrar vía API.

**Cómo verificar:**
```bash
python manage.py test tests.test_customer_detail.TestCustomerRetrieve
python manage.py test tests.test_cash_movements.TestManualMovements.test_cannot_delete_auto_movement
```

---

## 7. Base de datos

- Postgres con índices (17 creados — ver `scripts/migracion/create_indexes.py`).
- Backups: Supabase free tier hace daily backup de 7 días retenidos.
  Para retención mayor, configurar `pg_dump` semanal manual o pasar a tier paid.
- `conn_max_age=600` + `conn_health_checks=True` ya configurado.
- `DISABLE_SERVER_SIDE_CURSORS=True` (requerido por el transaction pooler).

**Recomendación**: agendar un cron job semanal:
```bash
pg_dump --no-owner --no-acl -Fc "$DATABASE_URL" > backup_$(date +%Y%m%d).dump
```

---

## 8. Logs y monitoreo

- Logs de Django en `logs/django.log`. En Render, redirigir stdout (config en `render.yaml`).
- Logger `security` para login fallidos.
- Logger `perf` para requests >500ms (middleware `TimingMiddleware`).
- Header `X-Response-Time-ms` en cada response — útil para debuggear desde el browser.

**Pendiente (no bloqueante para launch)**:
- Sentry / Rollbar para tracking de excepciones en producción.
- Healthcheck endpoint `/api/health/` que verifique DB + cache + readyness.

---

## 9. Frontend

- `index.html` apunta al backend de prod (cambiar `window.API_BASE_URL` en `config.js`).
- Quitar `console.log` de debug — opcional, no es bloqueante.
- Si querés un build real con Vite, ver §1 del ARQUITECTURA_REVIEW. No es urgente.

---

## 10. Datos sucios pendientes

Antes de mostrar el sistema al dueño, idealmente:

| Tarea | Script |
|---|---|
| Recalcular cuotas con status='overdue' deprecated | El cálculo dinámico ya las cubre — no urgente |
| Limpiar 67 clientes con doc autogenerado `DRV026-`/`SUC026-`/`CUOTA` | Manual desde UI (`/customers` chip "doc autogenerado") |
| 142 ventas con código MIG | Reemplazar manual desde `/sales` chip "MIG" — usar export Excel |
| 25+ vehículos `available` que ya tienen venta | Script: `python manage.py shell` y `Vehicle.objects.filter(...).update(state='sold')` — o usar el sync automático que ya está |
| Mergear PaymentForm `CRÉDITO` (id=2) y `CREDITO` (id=3) | Script de 1 línea |

Detalle completo en [UX_AUDIT.md](UX_AUDIT.md) §5.

---

## 11. Test smoke contra producción (después del deploy)

```bash
# 1. Health
curl -I https://api.autoofertas.com.py/admin/login/  # debe 302 o 200

# 2. CORS
curl -i -H "Origin: https://no-deberia-pasar.com" \
  https://api.autoofertas.com.py/api/users/login/
# Esperado: NO debe haber Access-Control-Allow-Origin con ese valor

# 3. HTTPS forzado
curl -I http://api.autoofertas.com.py/  # debe redirigir 301/302 a https

# 4. Login válido
curl -X POST https://api.autoofertas.com.py/api/users/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"..."}' | jq

# 5. Rate limit del login (10 intentos malos)
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code} " https://api.autoofertas.com.py/api/users/login/ \
    -X POST -H 'Content-Type: application/json' -d '{"username":"x","password":"y"}'
done
echo
# Esperado: 401 401 401 401 401 429 429 429 429 429
```

---

## 12. Lo que NO está y se puede vivir sin (al menos el día 1)

- **2FA / TOTP**: importante a futuro, no bloqueante para una concesionaria de 9 usuarios.
- **Audit log con `object_id` real**: hoy graba `object_id=0`. Para forensics serio hace falta — ver UX_AUDIT §6.
- **Sentry**: useful, optional.
- **Healthcheck endpoint**: para load balancers — agregar si Render lo pide.
- **Backup off-site**: Supabase tiene backups internos pero un backup propio semanal es prudente.

---

## Resumen — listo para deploy

✅ Hardening de settings (env vars, no hardcoded)
✅ Rate limiting con scopes (login 5/min, register 3/min, whatsapp 30/min, anon 60/min, user 600/min)
✅ JWT con rotación + blacklist + logout real
✅ Permisos por rol probados (admin only en /users/, etc.)
✅ Multi-tenant aislado y probado
✅ HTTPS + HSTS + cookies seguras (auto-on cuando IS_PRODUCTION=True)
✅ Logging de login fallidos
✅ 91 tests pasando

⚠ **Bloqueante antes de prod**: Redis para cache distribuido (para que el throttling funcione con varios workers).
⚠ **Cambiar default**: `THROTTLE_LOGIN=5/min` puede ser molesto si el dueño olvida la contraseña. Considerar `10/min` y avisar al usuario cuando se aproxima al límite.
