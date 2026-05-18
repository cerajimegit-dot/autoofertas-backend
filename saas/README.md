# App SaaS — multiempresa con signup público

Esta app es **opcional** y está OFF por default. Activala con:

```bash
SAAS_ENABLED=True   # en el .env de la instancia SaaS
```

## ¿Cuándo activarla?

- **AUTO OFERTAS (instancia privada)**: NO la activés. La empresa ya
  está creada manualmente; el signup público no aplica.
- **Instancia SaaS pública** (en otro dominio, ej. `app.misistema.com`):
  Activala. El signup público crea Enterprise + User + Subscription
  trial para cualquier visitante.

## Endpoints expuestos

Cuando `SAAS_ENABLED=True`, se montan en `/api/saas/`:

| Método | Path | Auth | Descripción |
|---|---|---|---|
| GET  | `/api/saas/plans/`          | público | Catálogo de planes (trial/starter/pro/enterprise) |
| POST | `/api/saas/signup/`         | público | Crea Enterprise + User admin + Subscription trial 14d. Devuelve JWT |
| GET  | `/api/saas/me/subscription/`| JWT     | Estado de la suscripción de la empresa del usuario |
| POST | `/api/saas/upgrade/`        | JWT     | Solicita upgrade a un plan pago (placeholder Stripe) |

## Modelos

- **`Subscription`**: 1-a-1 con `Enterprise`. Plan + status + fechas.
- **`SignupRequest`**: para confirmación por email futura (placeholder).

## Planes y límites

Hardcoded en `saas/models.py`:

| Plan | Precio | Vehículos | Sucursales | Usuarios | Cuotas/mes |
|---|---|---|---|---|---|
| Trial 14d | $0    | 50  | 2 | 3  | 200 |
| Starter   | $29   | 100 | 2 | 5  | 500 |
| Pro       | $79   | 500 | 5 | 20 | 5.000 |
| Enterprise| $199  | sin límite | sin límite | sin límite | sin límite |

## Migración

La primera vez que la actives en una instancia:

```bash
SAAS_ENABLED=True python manage.py migrate saas
```

Crea las tablas `saas_subscription` y `saas_signuprequest`. No toca
ninguna tabla existente de `core`.

## Convivencia con AUTO OFERTAS

Si una misma BD tiene Enterprises creadas manualmente (sin pasar por
signup), la query `Enterprise.subscription` arroja `DoesNotExist`. El
endpoint `/me/subscription/` lo maneja devolviendo 404 con un mensaje
claro. Esos enterprises pueden crear su Subscription a mano o vivir
sin ella.

## Roadmap

- [ ] Integrar Stripe Checkout (`request_upgrade` redirige a sesión Stripe).
- [ ] Webhook Stripe → actualiza `Subscription.status`.
- [ ] Email transactional para confirmar signup (usar `SignupRequest`).
- [ ] Middleware que bloquea endpoints cuando la suscripción no está activa.
- [ ] Trial-end reminder por email (3d antes, 1d antes, día del vencimiento).
- [ ] Dashboard del admin del SaaS para ver MRR, churn, conversiones.
