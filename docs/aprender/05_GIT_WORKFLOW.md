# 🌿 Git — cómo trabajamos con el código

> Git es el sistema que permite colaborar en el mismo código sin
> pisarse. Este archivo cubre el **flujo específico de este proyecto**.
>
> Si Git te resulta abstracto, es normal — se entiende con la práctica.

---

## 1. Los 3 lugares donde vive tu código

```
┌─────────────────────┐     ┌───────────────────┐     ┌──────────────────┐
│ Working Directory   │     │  Staging Area     │     │   Repository     │
│ (archivos en disco) │ --> │  (git add)        │ --> │   (git commit)   │
└─────────────────────┘     └───────────────────┘     └──────────────────┘
                                                              │
                                                              │ git push
                                                              ▼
                                                     ┌──────────────────┐
                                                     │  GitHub          │
                                                     │  (remoto)        │
                                                     └──────────────────┘
```

1. Trabajás en tus archivos normalmente
2. Con `git add archivo.py`, decís "voy a incluir este archivo en el próximo commit"
3. Con `git commit -m "mensaje"`, guardás la foto de lo que agregaste
4. Con `git push`, subís los commits a GitHub

---

## 2. Setup inicial (una sola vez)

Ya lo hiciste en `01_HERRAMIENTAS.md`:
```cmd
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
```

Verificá:
```cmd
git config --global user.name
git config --global user.email
```

---

## 3. Clonar el repo (una sola vez)

Cuando empezás con un proyecto:
```cmd
cd C:\Users\TUUSUARIO\CascadeProjects
git clone https://github.com/cerajimegit-dot/autoofertas-backend.git playa
git clone https://github.com/cerajimegit-dot/autoofertas-frontend.git playa-frontend
```

Eso descarga TODO el historial + código a tu PC.

---

## 4. Estructura de branches del proyecto

```
main         (producción — lo que ve la empresa)
  │
  └── staging   (nuevos features en testing)
        │
        └── jr/onboarding   (tu rama de trabajo)
              │
              ├── jr/T1.3-volver-arriba    (branch por tarea)
              ├── jr/T1.4-empty-state      (branch por tarea)
              └── ...
```

**Regla**:
- **NUNCA** hagas push directo a `main` o `staging`
- Siempre trabajás en una rama tipo `jr/T1.3-...`
- Para mergear a `jr/onboarding` o `staging`, abrís un **Pull Request**

---

## 5. Workflow diario paso a paso

### 5.1 Empezar una tarea nueva

```cmd
cd C:\Users\TUUSUARIO\CascadeProjects\playa
git checkout jr/onboarding      REM cambiarte a la rama base
git pull                          REM traer últimos cambios
git checkout -b jr/T1.3-volver-arriba    REM crear rama nueva desde donde estás
```

`git checkout -b` crea una rama nueva Y se cambia a ella.

### 5.2 Trabajar y commitear

Editás archivos con VS Code. Cuando algo funciona:

```cmd
git status
```

Te muestra qué archivos cambiaste. Ejemplo:
```
modified:   src/components/BackToTop.jsx
modified:   src/App.jsx
```

Agregarlos al staging:
```cmd
git add src/components/BackToTop.jsx src/App.jsx
```

O agregar todo lo modificado de una:
```cmd
git add .
```

⚠ **Ojo**: `git add .` puede incluir archivos que no querés. Preferí
agregar por nombre cuando puedas.

Commitear:
```cmd
git commit -m "T1.3: agregar boton volver arriba con scroll"
```

**Regla de mensajes**:
- En imperativo: "agregar", "fix", "refactorizar" (no "agregué", "arreglé")
- Corto pero descriptivo (< 70 chars)
- Empezar con el código de tarea si aplica

### 5.3 Push (subir a GitHub)

La primera vez que hacés push de una rama nueva:
```cmd
git push -u origin jr/T1.3-volver-arriba
```

Después, en la misma rama:
```cmd
git push
```

### 5.4 Abrir Pull Request

1. Andá a https://github.com/cerajimegit-dot/autoofertas-backend
2. Vas a ver un banner amarillo "You recently pushed to jr/T1.3-... — Compare & Pull Request"
3. Click ahí
4. **Base branch**: `jr/onboarding` (o `staging`, según lo que te diga el senior)
5. **Título**: mismo que el commit
6. **Descripción**: completá el template
7. Click "Create pull request"
8. Avisale al senior por mensaje

---

## 6. Comandos de navegación

### Ver qué rama estás
```cmd
git branch --show-current
```

### Ver todas las ramas
```cmd
git branch          REM locales
git branch -a       REM incluye remotas
```

### Cambiar de rama
```cmd
git checkout nombre-de-rama
```

⚠ Si tenés cambios sin commitear, `git checkout` puede fallar o los
puede arrastrar. Preferí commitear o guardar en stash antes de cambiar.

### Ver el historial
```cmd
git log --oneline -20
```

### Ver un commit específico
```cmd
git show 0470099
```

---

## 7. Situaciones comunes

### Situación 1 — "Me olvidé de crear rama y empecé a modificar en main"

Solución:
```cmd
git checkout -b jr/T1.3-nombre    REM crea rama con tus cambios
```

Los cambios no commiteados se llevan a la rama nueva.

### Situación 2 — "Necesito bajar cambios que hicieron mientras yo trabajaba"

```cmd
git checkout jr/onboarding
git pull
git checkout tu-rama
git merge jr/onboarding    REM trae los cambios nuevos a tu rama
```

Si hay conflictos, ver sección 8.

### Situación 3 — "Cometí un error en el último commit y ya lo pushié"

Preferí NO reescribir historia. En lugar de eso, hacé otro commit con
el fix:
```cmd
git add archivo.py
git commit -m "fix: corrección de T1.3"
git push
```

Es más fácil y no rompe nada.

### Situación 4 — "Quiero ver qué cambié pero aún no commiteé"

```cmd
git diff
```

Con espacio para pasar de página, `q` para salir.

### Situación 5 — "Metí un archivo por error en el commit"

Antes de pushear:
```cmd
git reset HEAD~1        REM deshacer el último commit (los cambios quedan)
```

Después ajustás y volvés a commitear.

Si ya pushiaste, hacé un commit nuevo que borre lo agregado — no
reescribas historia pushiada.

---

## 8. Conflictos de merge

**Un conflicto** pasa cuando vos y otra persona modificaron la MISMA
línea del MISMO archivo.

Git te avisa así:
```
CONFLICT (content): Merge conflict in src/App.jsx
```

Abrí el archivo. Vas a ver algo como:
```
<<<<<<< HEAD
tu versión del código
=======
la versión del otro
>>>>>>> jr/onboarding
```

Editá el archivo dejando SOLO lo que querés que quede. Borrá las
líneas `<<<<<<<`, `=======`, `>>>>>>>`.

Después:
```cmd
git add archivo
git commit
git push
```

Si no sabés cuál lado dejar: escaláme.

---

## 9. Buenas prácticas

### Do
- Hacer commits chicos y frecuentes
- Mensajes de commit descriptivos
- Pushear al menos 1 vez al día (backup)
- Actualizar tu rama con `pull` seguido antes de empezar a trabajar
- Revisar `git status` antes de cada commit

### Don't
- NO commitear archivos gigantes (BD, videos, PDFs pesados)
- NO commitear `.env` o archivos con passwords
- NO commitear con mensajes tipo "cambio", "wip", "asdf"
- NO trabajar en `main` o `staging` directamente
- NO forzar push (`git push --force`) — puede romper cosas de otros

---

## 10. Alias útiles para tu terminal

Podés crearte atajos:

```cmd
git config --global alias.s status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.l "log --oneline -20"
```

Después:
```cmd
git s          REM = git status
git co main    REM = git checkout main
git l          REM = git log --oneline -20
```

---

## 11. Cuando algo te confunde

Git tiene MUCHOS comandos. Nadie los sabe todos. Los que necesitás
para tu día a día son:

```
git status
git add
git commit -m
git push
git pull
git checkout
git checkout -b
git branch
git log --oneline
git diff
```

Con esos 10, cubrís el 90% de casos.

Para el resto, googleá "git how to X" en inglés (mejores resultados).

---

## Chequeo

Después de leer este archivo, deberías poder responder:

- ¿Qué es un branch?
- ¿Qué hace `git commit`?
- ¿Qué hace `git push`?
- ¿Cuándo abrís un Pull Request?
- ¿Por qué no se hace push directo a `main`?

Si alguna te queda confusa, releé la sección.

---

## Próximo paso

Abrí `06_ESTRUCTURA_PROYECTO.md`.
