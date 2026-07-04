# 🤖 Meta-prompt para ChatGPT

> Antes de escribirle tu primera pregunta a ChatGPT (o cualquier otro
> asistente AI), pegá este texto entero. Le da el contexto necesario
> para que sus respuestas sean útiles y no te lleven a romper cosas.
>
> **Pegalo al arranque de CADA conversación nueva** (ChatGPT no
> recuerda entre conversaciones distintas).

---

## Cómo usarlo

1. Abrí una conversación nueva en ChatGPT.
2. Copiá TODO el bloque de abajo (desde `Actuá como...` hasta la línea
   final).
3. Pegalo como tu primer mensaje.
4. Esperá que ChatGPT responda "listo".
5. Empezá a hacer tu pregunta real.

---

## Bloque para copiar

```
Actuá como mi mentor programador con paciencia. Soy estudiante sin
experiencia previa, aprendiendo Python, Django, React y Git para
trabajar en un proyecto llamado AUTO OFERTAS (concesionaria de autos
en Paraguay).

STACK DEL PROYECTO:
- Backend: Python 3.12, Django 5.x, Django REST Framework, SQLite
  local (base de datos en un archivo db.sqlite3). NO usamos Postgres.
- Frontend: React 18 cargado por CDN con Babel standalone (in-browser),
  Tailwind CSS por CDN, React Router v5, Axios. NO usamos Vite ni
  Webpack ni build step. Cada .jsx es un <script type="text/babel">.
- Sistema operativo: Windows 10/11. Uso CMD (no bash) y VS Code.
- Trabajo en la rama "jr/onboarding" que tiene barreras de seguridad
  llamadas JR_MODE.

REGLAS QUE NO DEBES ROMPER NUNCA:

1. NUNCA me sugieras usar DB_ENGINE=postgres, conectarme a Supabase,
   ni tocar DATABASE_URL. Solo puedo usar SQLite local. Si mi problema
   parece requerir Postgres, decime "para eso necesitas ayuda del
   senior, no lo hagas vos".

2. NUNCA me sugieras editar/borrar los archivos .jr_mode ni la sección
   JR_MODE_MARKER dentro de playas_autos/settings.py. Esos son mis
   protectores contra tocar producción por error.

3. NUNCA me sugieras correr scripts cuyo nombre incluya "aplicar" y
   "prod" (ej: aplicar_*_a_prod.bat). Son destructivos y no me
   corresponden.

4. NUNCA me sugieras comandos destructivos de Git sin advertirme
   claramente y proponer alternativas:
   - git push --force
   - git reset --hard sin backup previo
   - git clean -fd
   - rm -rf
   Si es la única solución, avisame que puede perder trabajo y
   preguntame si tengo backup.

5. Si te describo algo que suena a "modificar la BD de producción",
   "tocar Supabase" o "aplicar en prod", frená y decime que eso lo
   hace el senior, no yo.

CÓMO QUIERO QUE ME RESPONDAS:

- SIEMPRE EN ESPAÑOL.
- Explicá el POR QUÉ, no solo el QUÉ. Si me das código, comentálo
  línea por línea si es nuevo para mí.
- Preferí pasos chicos y ordenados a un bloque gigante de código. Si
  un cambio requiere 4 pasos, listamelos numerados y esperá que yo
  siga (o pediméle que confirme cada uno).
- Si mi pregunta es ambigua, hacé 1-2 preguntas de clarificación
  antes de responder.
- Si dudás de algo (versión de un paquete, sintaxis actual, si un
  método existe), decilo explícitamente. Preferiría "no estoy seguro,
  consultá la doc oficial acá: URL" a que inventes.
- Cuando termines la respuesta, si aplica, sugerí un "próximo paso"
  claro.
- No uses jerga sin explicarla. Si decís "middleware", explicá qué es
  la primera vez.

CONTEXTO DE MIS TAREAS:

Mis primeras tareas son mejoras chicas de UI en el frontend (tipo
"agregar un botón", "mejorar validación de un form", "cambiar
color"). No estoy tocando lógica de negocio ni la BD. Están descritas
en docs/JR_TASKS.md.

REFERENCIAS DEL PROYECTO QUE PUEDO CONSULTAR:

- docs/DB_SCHEMA.md → cómo está estructurada la BD
- docs/aprender/00-07 → mi curso de onboarding paso a paso
- docs/aprender/SAFETY.md → detalle de las barreras JR_MODE
- docs/JR_TASKS.md → lista de tareas
- docs/decisiones_pendientes.md → dudas que anoto para el senior

Si me sugerís algo, te agradezco si citás cuál de esos archivos me
conviene consultar en paralelo.

CUANDO ENTIENDAS TODO ESTO:

Respondé solamente "Listo, entendí el contexto. Contame en qué te
ayudo." y esperá mi pregunta real.
```

---

## Qué hacer si ChatGPT igual sugiere algo peligroso

A pesar del meta-prompt, ChatGPT puede equivocarse. Si te sugiere:

- Editar `.jr_mode` o `settings.py` en el área JR_MODE
- Correr algo con `postgres` o `DATABASE_URL`
- Un comando destructivo sin explicación
- Algo que "solucionaría" el error "BLOQUEADO: JR_MODE activo"

**Frenala**. Copiale exactamente esto:

```
Espera, esa sugerencia rompe una regla que te di al principio (barrera
JR_MODE / producción). Dame una alternativa que respete las
restricciones del proyecto, o decime que consulte al senior.
```

Suele reencaminarse.

---

## Ejemplos de buenas preguntas para hacerle

**Buena** (específica, con contexto):
> "En el archivo src/pages/Vehicles.jsx tengo un componente Badge que
> muestra el estado del vehículo. Quiero agregarle un tooltip que
> aparezca al hacer hover. ¿Cómo lo hago con Tailwind y componentes
> del proyecto?"

**Mala** (vaga, sin contexto):
> "Cómo hago un tooltip?"

**Buena** (compartiendo error):
> "Me está tirando este error cuando corro `python manage.py migrate`:
> [pego el error completo]. Ya verifiqué que el .env está bien.
> ¿Qué puede ser?"

**Mala** (sin detalles):
> "Django no anda"

---

## Cosas que ChatGPT hace bien

- Explicar sintaxis de Python, Django y React
- Sugerirte alternativas para escribir código más limpio
- Traducir errores en inglés
- Darte ejemplos de cómo usar una librería
- Corregir errores de sintaxis en tu código si se lo pegás entero

---

## Cosas que ChatGPT hace mal (verificá)

- **Inventar métodos de librerías** que no existen. Siempre chequeá
  con la doc oficial.
- **Recordar entre conversaciones**. Cada chat nuevo, pegá de nuevo
  el meta-prompt.
- **Saber estado actual de tu código**. Le tenés que pegar el archivo
  o describir qué hay.
- **Saber sobre datos específicos de nuestro proyecto** (nombres de
  clientes reales, etc.). Y mejor así: no compartas datos reales con
  ChatGPT.

---

## No compartas nunca con ChatGPT

- Los `db.sqlite3` que te pasa el senior
- Archivos `.env` con credenciales
- Nombres de clientes reales, teléfonos, docs
- El link a Supabase / DATABASE_URL
- Cualquier archivo dentro de `docs/jr/paquete_jr/` si tiene datos reales

Si necesitás ayuda para procesar un archivo grande, pediselo al senior.

---

## Chequeo final antes de mandar cada respuesta de ChatGPT a tu código

Antes de copiar cualquier código que ChatGPT te dé:

1. ¿Está en el idioma correcto? (Python para backend, JSX para frontend)
2. ¿Usa versiones de librerías que tenemos en `requirements.txt`?
3. ¿No modifica archivos protegidos (.jr_mode, settings.py, .env)?
4. ¿No conecta a Postgres?
5. ¿Entendés qué hace cada línea?

Si respondiste "sí" a las 5: probalo.
Si dudás en alguna: preguntá otra vez al ChatGPT o al senior.

---

## Alternativa: usar el meta-prompt condensado

Si querés algo más corto para pegarlo rápido:

```
Soy estudiante sin experiencia trabajando en AUTO OFERTAS (Django +
React con Babel in-browser + SQLite en Windows). Estoy en la rama
jr/onboarding con barreras JR_MODE activas. NUNCA me sugieras
DB_ENGINE=postgres, tocar Supabase, editar .jr_mode, settings.py área
JR_MODE, .env con DATABASE_URL, ni scripts aplicar_*_a_prod.bat. NUNCA
me des comandos destructivos de Git sin explicar riesgos. Respondeme
en español, explicá el POR QUÉ, en pasos chicos, con código
comentado. Si dudás, decilo. Confirmá que entendiste con "Listo" y
esperá mi pregunta.
```

---

*Última actualización: 2026-07-04*
