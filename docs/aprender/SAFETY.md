# 🔒 SAFETY — cómo se protege la BD de producción

> Este archivo explica por qué **es imposible que te conectes por error
> a la BD real de la empresa** desde esta rama.
>
> Si alguna vez te aparece un error mencionando "JR_MODE bloqueado",
> este archivo te dice qué pasó y cómo seguir.

---

## Por qué existe JR_MODE

La empresa AUTO OFERTAS tiene una BD real en Supabase con:
- Datos personales de clientes reales
- Montos de ventas y cuotas reales
- Información financiera sensible

Vos estás aprendiendo. Puede pasar que:
- Copies mal una config
- Corras un script equivocado
- Se te "cuele" una variable de entorno vieja
- Alguien te pase un `.env` mal armado

Cualquiera de esos errores, sin protección, podría hacer que tu Django
**lea o escriba** la BD real. **No queremos eso**.

Por eso pusimos 3 barreras que te van a proteger.

---

## Las 3 barreras

### Barrera 1 — Archivos peligrosos no están en la rama

Los scripts que aplican cambios a producción (`aplicar_*_a_prod.bat`)
**no existen** en la rama `jr/onboarding`. Si clonás esta rama, no
podés correrlos porque no están.

Solo el senior los tiene en otras ramas.

### Barrera 2 — Bloqueo en `settings.py`

En la raíz del repo hay un archivo `.jr_mode` (que no debés borrar).
Cuando Django arranca, chequea si existe:

- Si existe → fuerza `DB_ENGINE=sqlite` y bloquea `DB_ENGINE=postgres`
- Si tratás de usar Postgres, Django tira un error claro y no arranca

Código de la barrera (en `playas_autos/settings.py`, buscá `JR_MODE_MARKER`):

```python
JR_MODE_MARKER = BASE_DIR / '.jr_mode'
if JR_MODE_MARKER.exists():
    if config('DB_ENGINE', default='sqlite') == 'postgres':
        raise ImproperlyConfigured('BLOQUEADO: JR_MODE activo...')
    DB_ENGINE = 'sqlite'
```

No importa qué haya en tu `.env` — Django ignora `DB_ENGINE=postgres`.

### Barrera 3 — El `.env.example` no menciona Postgres

Cuando copiás `.env.example` como `.env`, no vas a ver ni siquiera
la variable `DATABASE_URL`. No hay tentación de completarla ni pistas
de que exista una BD remota.

---

## ¿Qué pasa si veo el error "BLOQUEADO: JR_MODE activo"?

Significa que algo intentó usar Postgres. Puede ser:

- **Un script**: te pasaron uno que setea `DB_ENGINE=postgres` sin
  saber que estás en la rama Jr. Corregilo o pediselo al senior.
- **Tu `.env`**: podrías haber puesto `DB_ENGINE=postgres` sin darte
  cuenta. Cambialo a `sqlite` (o mejor, borralo y volvé a copiar de
  `.env.example`).
- **Variables de entorno del sistema**: alguien puede haber seteado
  `set DB_ENGINE=postgres` en tu terminal. Cerrala y abrí una nueva.

En cualquier caso: **la barrera te salvó**. Nada llegó a la BD real.

---

## ¿Qué NO debo hacer nunca?

1. **NO borres el archivo `.jr_mode`**. Es la barrera principal.
2. **NO edites** `playas_autos/settings.py` para desactivar la barrera.
3. **NO pidas** al senior la connection string de Supabase. No la
   necesitás para nada.
4. **NO uses** `DB_ENGINE=postgres` en ningún script, aunque veas
   `--help` mencionándolo.

---

## ¿Cómo verifico que estoy bien protegido?

Corré esta prueba:

```cmd
cd C:\Users\TUUSUARIO\CascadeProjects\playa
set DB_ENGINE=postgres
venv\Scripts\python.exe manage.py check
```

Deberías ver un error tipo:

```
django.core.exceptions.ImproperlyConfigured:
BLOQUEADO: JR_MODE activo (.jr_mode existe en la raiz del repo).
DB_ENGINE=postgres esta prohibido en esta rama de trabajo.
```

Si en cambio Django arranca sin quejarse, **avisale al senior
INMEDIATAMENTE** — la barrera falló y no debería.

Después limpiá:
```cmd
set DB_ENGINE=sqlite
```

---

## ¿Y si legítimamente necesito tocar Postgres?

**No es tu tarea**. El senior es quien toca la BD de producción, no vos.

Si te asignan una tarea que aparentemente necesita prod, es un
malentendido. Escaláme.

---

## Preguntas frecuentes

### "¿Puedo probar cosas contra la BD de otro Jr / desarrollo compartido?"
No en el arranque. Si en el futuro montamos una BD "staging" para tests
compartidos, te la vamos a dar de manera controlada. Por ahora,
sólo tu SQLite local.

### "¿Y si mi trabajo depende de tener datos reales de referencia?"
Se puede generar un `db_jr.sqlite3` con datos reales ofuscados usando
`scripts/obfuscate_db.py`. Eso lo hace el senior y te lo pasa. Nunca
te conectas a la fuente.

### "¿Puedo usar Docker con Postgres para simular prod?"
Sí, técnicamente. Pero no lo hagas por ahora — SQLite es más que
suficiente para las tareas iniciales.

### "¿Qué pasa si el proyecto un día necesita algo que sqlite no soporta?"
Ese momento (por ejemplo, `pg_trgm` para búsqueda fuzzy) es una excusa
para escalar al senior, no para desactivar la barrera. El senior te
va a proponer una alternativa (fixture pre-generada, mock, etc.).

---

## Cambios y merge

Cuando el senior mergea tu rama `jr/T1.3-...` a `staging` o `main`,
los cambios que aplican son SOLO los que hiciste vos en código.
El archivo `.jr_mode` **no se propaga** — solo existe en `jr/onboarding`.

Es decir: `main` y `staging` NO tienen la barrera activa (por diseño,
porque el senior sí necesita usar Postgres a veces). Vos NUNCA
trabajás desde esas ramas.

---

## Resumen ultra-corto

- No borres `.jr_mode`
- No edites `settings.py`
- No preguntes por la URL de Supabase
- Trabajás siempre con SQLite local
- Ante duda, escaláme
