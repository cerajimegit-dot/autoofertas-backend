# 🛠 Herramientas — VS Code, terminal, Git

> Antes de escribir código, necesitás 3 herramientas instaladas y
> saber usarlas al mínimo.

---

## 1. Editor de código: VS Code

### Qué es
Un programa donde escribís código. Es **gratuito**, hecho por Microsoft,
y es lo que usa el 70% de programadores en el mundo.

### Instalar
1. Andá a https://code.visualstudio.com/
2. Bajá "Windows" y ejecutá el instalador
3. Aceptá defaults
4. Al abrir, cerrá cualquier tutorial que aparezca

### Extensiones que necesitás
Abrí VS Code → click en el ícono de bloques (izquierda) → buscá y
instalá una por una:

1. **Python** (de Microsoft) — resalta sintaxis, autocompleta
2. **Prettier** — formatea código
3. **Django** (de Baptiste Darthenay) — para templates
4. **ESLint** — chequea código JavaScript
5. **GitLens** (opcional) — mejora la vista de Git

### Configuración recomendada
Menú `File → Preferences → Settings`:
- Buscá "Format on save" → tildar
- Buscá "Auto save" → cambiar a "afterDelay"
- Buscá "Tab size" → poner **4** (Python usa 4 espacios)

### Atajos que vas a usar todo el tiempo
- `Ctrl + P` — buscar archivo por nombre
- `Ctrl + Shift + F` — buscar texto en TODO el proyecto
- `Ctrl + /` — comentar / descomentar línea
- `Ctrl + D` — seleccionar la próxima ocurrencia (útil para renombrar)
- `Ctrl + ` (backtick) — abrir terminal integrada
- `F5` — correr / debug

---

## 2. Terminal (CMD o PowerShell)

### Qué es
Una ventana negra donde escribís comandos. Suena rara pero es
**esencial** — todo programador la usa el 40% del tiempo.

### Cómo abrir
- Windows: tecla Windows → escribí "cmd" → Enter
- O dentro de VS Code: `Ctrl + ` (backtick)

### Comandos básicos que vas a usar

| Comando | Qué hace | Ejemplo |
|---|---|---|
| `cd` | Cambiar de carpeta | `cd C:\Users\prueb\playa` |
| `cd ..` | Subir un nivel | `cd ..` |
| `dir` | Ver qué hay en la carpeta | `dir` |
| `mkdir` | Crear carpeta | `mkdir nueva_carpeta` |
| `del archivo.txt` | Borrar archivo | `del temp.txt` |
| `type archivo.txt` | Ver contenido de un archivo | `type README.md` |
| `cls` | Limpiar pantalla | `cls` |

### Ejercicio práctico
1. Abrí terminal
2. Escribí `cd C:\Users\TUUSUARIO` (poné tu usuario) + Enter
3. Escribí `dir` → deberías ver tus carpetas
4. Escribí `mkdir prueba` + Enter → crea una carpeta
5. Escribí `cd prueba` → entra a esa carpeta
6. Escribí `dir` → vacía
7. Escribí `cd ..` → volvé atrás
8. Escribí `rmdir prueba` → borra la carpeta que creaste

Si algo falla, decime.

---

## 3. Git — control de versiones

### Qué es
Git es lo que permite que **muchos programadores trabajen en el mismo
código sin pisarse**. Guarda un historial de todos los cambios.

### Instalar
1. https://git-scm.com/download/win
2. Ejecutar el instalador
3. En "Choose the default editor" → elegí "Use Visual Studio Code"
4. En "Adjusting the name of the initial branch" → dejá "main"
5. Resto de opciones → dejá los defaults

Después de instalar, verificá:
```cmd
git --version
```
Debería mostrar algo como `git version 2.40.1`.

### Configuración inicial (una sola vez)
```cmd
git config --global user.name "Tu Nombre Completo"
git config --global user.email "tu@email.com"
```

Usá el mismo email de tu cuenta de GitHub.

### Conceptos básicos (leelos 2 veces)

**Repository (repo)**: la carpeta con todo el código + historial.

**Commit**: una foto del estado del código en un momento. Cada vez que
"guardás" un cambio, hacés un commit.

**Branch (rama)**: como un universo paralelo del código. Sirve para
probar cosas sin romper el proyecto principal.

**Remote (remoto)**: una copia del repo en un servidor (GitHub).

**Clone**: descargar un repo del servidor a tu PC.

**Push**: subir tus commits al servidor.

**Pull**: bajar los commits nuevos del servidor.

Vamos a ver esto en detalle en `05_GIT_WORKFLOW.md`. Por ahora alcanza
con saber que existen.

### Prueba rápida
```cmd
git --version
git config --global user.name
git config --global user.email
```

Los últimos dos deberían devolver tu nombre y email.

---

## 4. Python

### Qué es
El lenguaje de programación que usa este proyecto en el backend.
Vas a aprender la sintaxis básica en el próximo archivo.

### Instalar
1. Andá a https://www.python.org/downloads/
2. Bajá **Python 3.12** (no bajés 3.14 ni versiones raras)
3. Ejecutar el instalador
4. ⚠ **MUY IMPORTANTE**: al principio, tildá la casilla que dice
   **"Add python.exe to PATH"**. Si te olvidás, tenés que reinstalar.
5. Click "Install Now"

Verificá:
```cmd
python --version
```
Debería mostrar `Python 3.12.x`.

Si dice "no se reconoce el comando python", reinstalá con la casilla
"Add to PATH" tildada.

---

## 5. Node.js (para el frontend)

### Qué es
Necesario para instalar ciertos paquetes del frontend.

### Instalar
1. https://nodejs.org/
2. Bajá "LTS" (la versión de largo soporte)
3. Instalar con defaults

Verificá:
```cmd
node --version
npm --version
```

---

## 6. Cuenta de GitHub

Si aún no tenés:
1. https://github.com/signup
2. Crear cuenta con el mismo email de git config
3. Confirmar por email
4. Pedime que te agregue como colaborador a los repos:
   - `autoofertas-backend`
   - `autoofertas-frontend`

---

## Chequeo final

Después de este archivo, deberías tener:

- [ ] VS Code abierto y con las 4 extensiones
- [ ] Terminal (CMD) que abre y responde a comandos básicos
- [ ] `git --version` funciona
- [ ] `python --version` funciona (3.12.x)
- [ ] `node --version` funciona (18.x o superior)
- [ ] Cuenta de GitHub creada
- [ ] Acceso a los 2 repos confirmado

Si algún ítem falla, no sigas — arreglalo primero. Preguntame.

---

## Próximo paso

Cuando todos los ítems del chequeo pasen: abrí `02_PYTHON_BASICO.md`.
