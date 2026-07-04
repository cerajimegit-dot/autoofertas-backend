# ⚛ React — el frontend

> React es la librería de JavaScript que usa nuestro frontend. Este
> archivo cubre lo mínimo para leer, entender y modificar
> componentes del proyecto.

---

## 1. Contexto — cómo usamos React acá

React normalmente se **compila** con un tool tipo Vite o Webpack. En
este proyecto usamos una **variante más simple para prototipar**:

- El `index.html` carga React desde CDN
- Cada archivo `.jsx` es un `<script type="text/babel">`
- Babel **compila el JSX en el browser** al vuelo

Es **más simple** pero **más lento** en carga. Suficiente para nuestro
tamaño de proyecto.

Los archivos del frontend están en:
```
playa-frontend/
├── index.html          <- entrada
├── config.js           <- URL del backend
├── server.py           <- servidor HTTP simple para local
└── src/
    ├── pages/          <- páginas (Login, Dashboard, Sales, ...)
    ├── components/     <- componentes reutilizables (Button, Card, ...)
    ├── context/        <- estado global (Auth, Branch, Toast)
    └── utils/          <- helpers (api, format, storage, ...)
```

---

## 2. Un componente React básico

Un **componente** es una función que devuelve HTML (llamado JSX).

```jsx
function Saludo() {
    return <h1>Hola mundo</h1>;
}
```

Para usarlo:
```jsx
<Saludo />
```

Es igual a HTML pero se cierra con `/>`.

---

## 3. JSX — HTML dentro de JavaScript

```jsx
function Bienvenida() {
    const nombre = "Juan";
    return (
        <div>
            <h1>Hola, {nombre}</h1>
            <p>Bienvenido al sistema</p>
        </div>
    );
}
```

Reglas de JSX:
- Un componente devuelve **UN solo elemento raíz** (usar `<div>` o `<></>` para agrupar)
- Los atributos usan `camelCase` en vez de `kebab-case`:
  ```jsx
  // HTML normal
  <input onclick="handler()" class="rojo">

  // JSX
  <input onClick={handler} className="rojo" />
  ```
- Para insertar JavaScript, usás `{expresión}`

---

## 4. Props — datos que entran al componente

```jsx
function Saludo({ nombre, edad }) {
    return (
        <div>
            <p>Hola {nombre}, tenés {edad} años</p>
        </div>
    );
}

// Uso
<Saludo nombre="Juan" edad={25} />
```

Las props son **inmutables** — el componente no las modifica, solo
las lee.

---

## 5. useState — estado interno

Un componente puede tener **estado** (datos que cambian) usando el hook
`useState`:

```jsx
function Contador() {
    const [count, setCount] = React.useState(0);

    return (
        <div>
            <p>Contador: {count}</p>
            <button onClick={() => setCount(count + 1)}>+1</button>
        </div>
    );
}
```

- `count` es el valor actual
- `setCount` es la función para actualizarlo
- Cuando cambia, React **re-renderiza** el componente

---

## 6. useEffect — efectos y side effects

```jsx
function UsuarioActual() {
    const [nombre, setNombre] = React.useState('');

    React.useEffect(() => {
        // Se ejecuta cuando el componente se monta
        api.get('/users/me/').then(res => setNombre(res.data.username));
    }, []);   // el [] vacío = solo una vez al montar

    return <p>Hola, {nombre}</p>;
}
```

`useEffect` sirve para:
- Hacer llamadas al backend
- Suscribirse a eventos
- Limpiar recursos

El segundo argumento (array de dependencias) controla cuándo re-ejecuta:
- `[]` → solo al montar
- `[valor]` → cada vez que `valor` cambia
- (no lo pases) → después de cada render (peligroso!)

---

## 7. Manejo de listas

```jsx
function ListaClientes({ clientes }) {
    return (
        <ul>
            {clientes.map(c => (
                <li key={c.id}>{c.nombre}</li>
            ))}
        </ul>
    );
}
```

- `map` recorre el array y devuelve JSX por cada elemento
- **SIEMPRE** poné `key` con un valor único (ayuda a React a optimizar)

---

## 8. Condicionales

```jsx
function Status({ activo }) {
    // Con operador ternario
    return <span>{activo ? 'ON' : 'OFF'}</span>;
}

function Alerta({ mensaje }) {
    // Con &&
    return (
        <div>
            {mensaje && <p className="alert">{mensaje}</p>}
        </div>
    );
}

// Con if
function Panel({ user }) {
    if (!user) {
        return <p>No hay usuario</p>;
    }
    return <p>Hola, {user.name}</p>;
}
```

---

## 9. Formularios

```jsx
function CrearCliente() {
    const [nombre, setNombre] = React.useState('');
    const [email, setEmail] = React.useState('');

    async function handleSubmit(e) {
        e.preventDefault();   // evita que la página recargue
        await api.post('/customers/', { nombre, email });
        alert('Creado!');
    }

    return (
        <form onSubmit={handleSubmit}>
            <input
                value={nombre}
                onChange={e => setNombre(e.target.value)}
                placeholder="Nombre"
            />
            <input
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="Email"
            />
            <button type="submit">Crear</button>
        </form>
    );
}
```

---

## 10. Estilos con Tailwind CSS

El proyecto usa **Tailwind CSS** — cada clase es un estilo:

```jsx
<div className="bg-white p-4 rounded shadow">
    <h2 className="text-2xl font-bold text-gray-900">Título</h2>
    <p className="mt-2 text-sm text-gray-600">Subtítulo</p>
</div>
```

- `bg-white` = fondo blanco
- `p-4` = padding 4 (1rem = 16px)
- `rounded` = bordes redondeados
- `text-gray-900` = color texto gris muy oscuro
- `mt-2` = margin-top 2 (0.5rem)

Referencia completa: https://tailwindcss.com/docs

---

## 11. Componentes reutilizables del proyecto

Ya tenemos hechos:

| Componente | Ubicación | Uso |
|---|---|---|
| `Card` | `src/components/Card.jsx` | Panel con sombra + padding |
| `Button` | `src/components/Button.jsx` | Botón estilado |
| `Badge` | `src/components/Badge.jsx` | Chip / pill |
| `FormField` | `src/components/FormField.jsx` | Input con label + error |
| `Skeleton` | `src/components/Skeleton.jsx` | Loading placeholder |
| `EmptyState` | `src/components/EmptyState.jsx` | Vacío con call to action |
| `Toast` | `src/components/Toast.jsx` | Notificación temporal |
| `ResponsiveTable` | `src/components/ResponsiveTable.jsx` | Tabla que se adapta a mobile |

Ejemplo:
```jsx
<Card title="Ventas del mes">
    <Button variant="primary" onClick={handleClick}>
        Ver detalle
    </Button>
</Card>
```

---

## 12. Llamadas al backend con axios

En `src/utils/api.js` está configurado un cliente axios que ya maneja:
- Base URL del backend
- Token de autenticación
- Errores 401 (redirige a login)

```jsx
import { api } from './utils/api';

// GET
const res = await api.get('/customers/');
const clientes = res.data;

// POST
await api.post('/customers/', { nombre: 'Juan' });

// PUT (actualizar)
await api.put(`/customers/${id}/`, { nombre: 'Carlos' });

// DELETE
await api.delete(`/customers/${id}/`);
```

---

## 13. Un componente completo del proyecto (mirar y entender)

Abrí en VS Code: `playa-frontend/src/pages/Customers.jsx`

Vas a ver:

```jsx
function Customers() {
    const [customers, setCustomers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    useEffect(() => {
        fetchCustomers();
    }, []);

    async function fetchCustomers() {
        setLoading(true);
        const res = await api.get('/customers/');
        setCustomers(res.data.results);
        setLoading(false);
    }

    const filtered = customers.filter(c =>
        c.first_name.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div>
            <h1>Clientes</h1>
            <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Buscar..."
            />
            {loading ? (
                <Skeleton />
            ) : (
                <table>
                    ...
                </table>
            )}
        </div>
    );
}
```

Reconocés todos los conceptos:
- `useState` para estado interno
- `useEffect` para cargar al montar
- `map` implícito en filter+render
- Condicional con ternario
- Handler de input controlado

---

## Ejercicios (opcional pero recomendado)

### Ejercicio 1: contador
Creá un archivo `test.jsx` con un componente que:
- Muestra un número (empieza en 0)
- Tiene un botón "+1" y otro "-1"
- Muestra "PAR" o "IMPAR" según el número

### Ejercicio 2: lista de tareas
Creá un componente que:
- Tiene un input para escribir tareas
- Un botón "Agregar" que la mete en una lista
- Cada tarea de la lista tiene un botón "Borrar"

---

## Recursos para profundizar

- **React docs oficiales (en español)**: https://es.react.dev/
- **YouTube**: canal "midudev" (buenos tutoriales en español)
- **Tailwind docs**: https://tailwindcss.com/docs

---

## Próximo paso

Abrí `05_GIT_WORKFLOW.md`.
