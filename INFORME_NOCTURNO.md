# Informe nocturno — Pack 2

> Bitácora de trabajo autónomo mientras dormís. Última actualización: en progreso.

## Reglas que estoy siguiendo

1. **Cero cambios en la BD de producción**. Todo va a `staging` en ambos repos.
2. **Tests obligatorios** para cada endpoint backend. Frontend se prueba con la
   suite Django + revisión manual cuando despertés.
3. **Commits atómicos**: una feature = un commit en cada repo (cuando aplica).
4. **Migraciones** se escriben pero NO se aplican; el script `migrate` lo
   correremos juntos cuando definamos la ventana de deploy.
5. **Si encuentro algo riesgoso** (delete masivo, refactor grande, decisión
   ambigua), paro, lo anoto acá y sigo con otra cosa.

## Estado actual de las branches

- Backend `staging` parte de `main` + Pack 1 ya pusheado.
- Frontend `staging` idem.
- Para deploy: `git checkout main && git merge staging --ff-only && git push`.

## Trabajo del Pack 1 (resumen, ya pusheado)

| # | Feature | Estado |
|---|---|---|
| B1 | Export CSV de flujo de caja | ✅ 8 tests verdes |
| B7 | Búsqueda fuzzy de clientes (pg_trgm) | ✅ 10 tests verdes, migración 0010 sin aplicar |
| F4 | Palette global Ctrl+K | ✅ 9 tests verdes |
| B2 | PDF cronograma de cuotas | ✅ frontend-only |
| B4 | Sugerencia de precio | ✅ 6 tests verdes |

---

## Trabajo del Pack 2 (en progreso)

(Esta sección la voy actualizando turno a turno.)

