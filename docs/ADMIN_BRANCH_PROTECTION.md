# Configuración de branch protection (admin senior)

> Este archivo es para el senior/dueño del repo, no para el Jr.
> Documenta cómo activar las reglas de protección en GitHub para que
> el check `Jr Safety Barriers` sea obligatorio antes de mergear.

---

## Por qué activarlo

El GitHub Action `.github/workflows/jr-safety-check.yml` corre
automáticamente en cada PR. **Pero por default, GitHub no bloquea el
merge si el check falla** — solo lo reporta. Un admin con permisos
puede mergear igual "Merge anyway".

Para que el check sea **bloqueante**, hay que activar branch
protection en la UI de GitHub. Se hace una sola vez.

---

## Pasos (~3 minutos)

### En el repo `autoofertas-backend`

1. Ir a https://github.com/cerajimegit-dot/autoofertas-backend/settings/branches
2. Click **"Add branch protection rule"**
3. Configurar:
   - **Branch name pattern**: `jr/**`
   - Tildar:
     - [x] **Require a pull request before merging**
     - [x] **Require status checks to pass before merging**
       - Buscar y agregar el check: `Verificar barreras Jr`
     - [x] **Require branches to be up to date before merging**
     - [x] **Do not allow bypassing the above settings**
4. Click **"Create"** o **"Save changes"**

También agregar otra rule para las branches destino (staging, main):
1. Click **"Add rule"** de nuevo
2. **Branch name pattern**: `staging`
3. Mismos checks:
   - [x] Require PR + status checks (`Verificar barreras Jr`)
4. Save

Y otra para `main`:
1. **Branch name pattern**: `main`
2. Mismas configs + adicionalmente:
   - [x] **Require signed commits** (opcional, buena práctica)
   - [x] **Require linear history** (evita merge commits desordenados)

### En el repo `autoofertas-frontend`

Repetir los mismos pasos (el workflow no está ahí pero por si acaso).

---

## Verificación

Después de configurar, hacé un PR de prueba desde `jr/onboarding` con
un cambio mínimo. Deberías ver:

- ✅ El check `Verificar barreras Jr` corre automáticamente
- ✅ Si pasa, el botón "Merge" está habilitado
- ✅ Si falla, el botón dice "Merge blocked" y no se puede mergear (ni siquiera vos como admin, salvo que desactives la protección temporalmente)

---

## Bypass en emergencias

Si hay una emergencia real (ej. bug crítico en prod y necesitás mergear
rápido saltando el check):

1. Settings → Branches → tu rule
2. Temporarily disable: **Allow specified actors to bypass**
3. Agregarte a la lista
4. Mergear
5. Volver a quitarte de la lista

Preferí **arreglar el problema** antes que bypasear. El check está
para protegerte a vos también.

---

## Alerta si el workflow se rompe

Podés agregar una notificación en Settings → Notifications para
recibir email cuando falla un GitHub Action. Así te enterás rápido si
alguien tira un PR malicioso o accidental.

---

*Este archivo NO forma parte de la guía del Jr — es sólo para el
mantenedor del repo.*
