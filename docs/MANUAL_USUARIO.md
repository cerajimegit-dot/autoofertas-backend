# Manual de uso — AUTO OFERTAS

Sistema de gestión de la playa de autos. Multi-sucursal, con
clientes, vehículos, ventas, cuotas, cobranzas y flujo de caja.

> Este manual cubre lo que está **publicado en producción hoy**. Hay
> mejoras adicionales en `staging` que se incorporarán en el próximo
> deploy y serán documentadas después.

---

## Índice

1. [Cómo entrar y salir del sistema](#1-cómo-entrar-y-salir-del-sistema)
2. [La pantalla principal](#2-la-pantalla-principal)
3. [Cargar un vehículo nuevo](#3-cargar-un-vehículo-nuevo)
4. [Cargar un cliente nuevo](#4-cargar-un-cliente-nuevo)
5. [Registrar una venta](#5-registrar-una-venta)
6. [Generar el plan de cuotas](#6-generar-el-plan-de-cuotas)
7. [Cobrar una cuota](#7-cobrar-una-cuota)
8. [Mandar recordatorio por WhatsApp](#8-mandar-recordatorio-por-whatsapp)
9. [Movimientos de caja](#9-movimientos-de-caja)
10. [Casos comunes a resolver](#10-casos-comunes-a-resolver)
11. [Atajos y tips](#11-atajos-y-tips)

---

## 1. Cómo entrar y salir del sistema

![Pantalla de login](imagenes/01-login.png)

Entrá al sitio y tipeá **usuario** y **contraseña**. Si los datos son
correctos vas directo al panel principal. Si te equivocaste 5 veces en
un minuto, el sistema te bloquea unos minutos para evitar intentos
maliciosos — esperá y volvé a probar.

Para salir, hacé clic en el círculo con tu inicial arriba a la derecha
y elegí **"Cerrar sesión"**.

![Menú de usuario abierto](imagenes/01-logout.png)

---

## 2. La pantalla principal

![Dashboard completo](imagenes/02-dashboard.png)

Apenas entrás, ves el **dashboard** con un resumen del negocio:

- **Vehículos**: total y disponibles en stock.
- **Ventas del período**: cantidad y monto.
- **Cobrado del período**: cuántas cuotas y por qué monto.
- **Cartera vencida**: cuotas que ya pasaron de fecha sin cobrar.

Arriba a la izquierda está la **barra lateral** con todas las
secciones:
- 📊 Dashboard
- 🚗 Vehículos
- 💰 Ventas
- 👥 Clientes
- 📋 Cuotas
- 💵 Flujo de caja
- ⚙️ Usuarios (solo admin)

Arriba al medio aparece el **selector de sucursal** (sólo si tu
empresa tiene más de una). Cuando elegís una, todas las pantallas
filtran por ella. "Todas" muestra el agregado de las dos sucursales.

> Nota: el dropdown del selector de sucursal es nativo del navegador
> y se renderiza a nivel del sistema operativo, por lo que no aparece
> en capturas de pantalla del browser. En la imagen del dashboard ya
> se ve el botón con "CASA CENTRAL" como sucursal activa.

### Filtro de período

En la parte superior del dashboard hay un filtro de **fechas** (desde
/ hasta) con accesos rápidos: Este mes, Mes anterior, Este año, Año
anterior. Todos los KPIs respetan ese período.

---

## 3. Cargar un vehículo nuevo

Andá a **🚗 Vehículos** en la barra lateral y hacé clic en
**"+ Nuevo vehículo"**.

![Inventario de vehículos con chips de calidad](imagenes/03-vehiculos-lista.png)

> Nota: el botón **"+ Nuevo vehículo"** sólo aparece para usuarios con
> rol **administrador**. Los vendedores ven la lista en modo lectura.

Campos obligatorios:
- **Marca**: elegí del dropdown. Si no está, usá el botón verde **+** al
  lado para crearla.
- **Modelo**: depende de la marca elegida.
- **Año**: año del vehículo (ej. 2018).
- **VIN**: el código único del chasis. **No se puede repetir** en el
  sistema.
- **Precio** y **Moneda** (PYG o USD).
- **FOB / Container / Despacho / Cam-Vol**: los 4 costos estándar de
  importación. Si no los tenés todavía, dejá 0 y completalos después
  desde "Editar".

Opcionales:
- Patente, color, kilometraje.
- **Conceptos extras de costo**: si tuviste flete interno, patente,
  honorarios o cualquier otro gasto que no entra en los 4 estándar,
  agregalos abajo con el botón "+". Cada uno con concepto + monto +
  moneda.
- Descripción libre.

> 💡 **Tip**: el **costo total** del vehículo se calcula automáticamente
> sumando FOB + Container + Despacho + Cam-Vol + extras. Lo ves en la
> vista de detalle.

Clic en **"Crear vehículo"**. Vuelve a la lista y el nuevo aparece arriba.

---

## 4. Cargar un cliente nuevo

Andá a **👥 Clientes** y hacé clic en **"+ Nuevo cliente"**.

![Modal "Nuevo cliente"](imagenes/04-cliente-nuevo.png)

Campos obligatorios:
- **Nombre** y **Apellido**.
- **Tipo de documento**: Cédula / RUC / Pasaporte.
- **N° documento**: no se puede repetir en la empresa.

Opcionales pero **muy recomendados**:
- **Teléfono**: sin él no se pueden mandar recordatorios por WhatsApp.
- **Email**: para confirmaciones y resumen mensual.
- **Ciudad** y **Dirección**.
- **Notas**: cualquier observación útil (ej. "prefiere ser contactado
  al mediodía", "es cliente desde 2018").

Clic en **"Crear cliente"**.

> ⚠️ **Si el cliente ya existe** (mismo documento) el sistema te avisa
> con un error. Andá a la lista, buscalo y editalo en lugar de crearlo
> duplicado.

---

## 5. Registrar una venta

![Lista de ventas con chips de calidad](imagenes/05-ventas-lista.png)

Andá a **💰 Ventas** y hacé clic en **"+ Nueva venta"**.

![Modal "Nueva venta"](imagenes/05-venta-nueva.png)

Pasos:

1. **Cliente**: buscalo escribiendo en el campo (nombre / documento /
   teléfono). Si no existe, hacé clic en **"+ Nuevo cliente"** y se
   abre el formulario para crearlo sin perder los datos de la venta.
2. **Vehículo**: elegí uno del stock disponible. Igual que con cliente,
   podés crear uno nuevo desde el botón.
3. **N° de venta**: convención típica `CM/26-001` (Cerrada Mes-año-
   número) o `MC/26-001` para Mixto. Si lo dejás vacío el sistema
   asigna `??/26-001` que después podés corregir.
4. **Fecha de venta**: por default hoy.
5. **Forma de pago**: Contado, Crédito o Mixto.
6. **Entrega inicial** (seña): sólo si Crédito/Mixto. Es el monto que
   el cliente paga al momento de la venta.

Clic en **"Crear venta"**.

> 💡 Si la venta es a **Crédito**, después del create vas a querer
> generar el plan de cuotas. Ver siguiente sección.

---

## 6. Generar el plan de cuotas

Desde **💰 Ventas** hacé clic en el ícono de cuotas (📋) de la fila de
tu venta. Se abre el modal **"Cuotas de la venta CM/26-XXX"**.

![Modal de cuotas de una venta](imagenes/06-cuotas-modal.png)

Abajo del modal, en la sección **"Generar plan de cuotas"**, completá:
- **Cantidad de cuotas**: ej. 12, 18, 24.
- **1er vencimiento**: usualmente 30 días después de la venta.
- **Monto por cuota**: el sistema te sugiere uno calculado (total −
  seña / cantidad). Lo podés ajustar.
- **Nombre del plan** (opcional): ej. "Plan 12 meses sin interés".

Clic en **"🎯 Generar preview"**. Vas a ver una lista con las N cuotas
proyectadas:

> Captura de "Preview de cuotas" pendiente — se ve cuando completás
> los inputs (cantidad, fecha, monto) y clickeás "🎯 Generar preview".

Verificá que:
- ✅ La **suma total** del preview cuadra con el monto a financiar
  (sale.total − seña).
- ✅ Las **fechas** son correctas (1 cuota por mes en general).

Si está bien, clic en **"💾 Guardar cuotas"** y se crean en el
sistema. Si necesitás ajustar, cambiá los inputs y dale otra vez a
"Generar preview".

> ⚠️ Si **ya tenés cuotas** y querés agregar más (planes parciales
> tipo "primero 6 cuotas, después negociar otras 6"), el sistema lo
> permite — sólo escribe encima del modelo "Cuotas existentes".

---

## 7. Cobrar una cuota

Hay 2 caminos:

### A. Desde el modal de cuotas de una venta

En la tabla de cuotas, fila por fila, vas a ver el botón **"💵 Pagar"**
en las cuotas que están pendientes.

![Tabla de cuotas con botones "Pagar"](imagenes/07-cuotas-tabla.png)

Hacé clic y se abre el formulario:

![Modal "Registrar pago"](imagenes/07-pagar-modal.png)

Completá:
- **Fecha de pago**: hoy por default.
- **Forma de pago**: Efectivo / Transferencia bancaria / Caja / Acuerdo.
- **Notas** (opcional): ej. "Pagó con USD al cambio del día".

Clic en **"Confirmar pago"**.

> 💡 Cuando cobrás una cuota, el sistema **automáticamente** genera un
> movimiento de ingreso en el flujo de caja. No tenés que cargarlo a
> mano.

### B. Desde el detalle del cliente

Andá a **👥 Clientes** → buscalo → clic en su nombre. Ves todas sus
ventas y cuotas. La columna "Acción" tiene el mismo botón "💵 Pagar".

Esta vista es más cómoda cuando vino el cliente al local y querés
revisar todo su historial al mismo tiempo.

![Detalle de un cliente](imagenes/07-cliente-detalle.png)

---

## 8. Mandar recordatorio por WhatsApp

Si una cuota está cerca del vencimiento o ya venció, podés mandarle
recordatorio al cliente con un click.

> Captura del botón WhatsApp por cuota: pendiente. En el detalle del
> cliente (sección 7) se ve el botón "💬 WhatsApp" verde arriba a la
> derecha que cumple la misma función a nivel del cliente.

En la columna de acción de la cuota, clic en **"📱 WhatsApp"**.
El sistema:
1. **Normaliza** el teléfono del cliente al formato internacional
   (`0981123456` → `595981123456`).
2. **Arma el mensaje** en español:
   > "Buen día Juan, le recordamos la cuota N°3 con vencimiento
   > 15/05/2026 por Gs. 1.500.000. Cualquier consulta estamos a las
   > órdenes. AUTO OFERTAS."
3. Abre **WhatsApp Web / app** con el mensaje listo. Sólo tenés que
   apretar enviar.

> ⚠️ Si el cliente **no tiene teléfono cargado**, el botón no aparece.
> Tenés que editarlo primero para agregar el número.

---

## 9. Movimientos de caja

Andá a **💵 Flujo de caja**.

![Flujo de caja: KPIs + distribución + tabla](imagenes/09-flujo-caja.png)

Hay 3 KPIs arriba:
- **Ingresos** del período (verde).
- **Egresos** del período (rojo).
- **Saldo neto** (verde si positivo, rojo si negativo).

Y abajo, la tabla con cada movimiento del período. Los movimientos
**generados automáticamente** (cobros de cuotas, señas, ventas
contado) aparecen marcados con ⚙ auto — esos no se pueden borrar a
mano, se ajustan automáticamente cuando cambias la venta o cuota
original.

Los movimientos **manuales** se cargan con el botón **"+ Nuevo
movimiento"**:

![Modal "Nuevo movimiento"](imagenes/09-nuevo-movimiento.png)

Completá:
- **Fecha**, **Sucursal**.
- **Tipo**: Cobro de cuota / Venta contado / Seña / Pago a cuenta /
  Gasto / Alquiler / Sueldo / Comisión / Compra al exterior /
  Transporte / Impuesto / Ajuste / Otro.
- **Dirección**: Ingreso (verde) o Egreso (rojo).
- **Monto** en Gs (o USD con tipo de cambio).
- **Operación**: descripción libre, ej. "PAGO DE ALQUILER FEBRERO/26".
- **Proveedor** (opcional, útil para compras al exterior: AUTOWINI,
  DADANI, etc.).

Clic en **"Crear"**.

> 💡 **Filtros de período rápidos** arriba: Este mes / Mes anterior /
> Este año / Año anterior. Útiles cuando el contador te pide "el flujo
> de mayo".

---

## 10. Casos comunes a resolver

A medida que usás el sistema vas a encontrarte con cosas para
arreglar. Acá los casos típicos y cómo proceder.

### 10.1. Cuotas vencidas sin pagar

**Cómo detectarlas:**

- En el **dashboard** mirá el KPI rojo **"Cartera vencida"** —
  cantidad y monto total.
- En el dashboard también hay un panel **"Clientes morosos (top 15)"**.
  Cada cliente moroso linkea a su detalle.

![Panel "Clientes morosos" del dashboard](imagenes/10-morosos.png)

- En **📋 Cuotas** podés filtrar por **estado = Vencidas** para ver
  todas las cuotas atrasadas.

**Qué hacer:**

1. **Contactar al cliente**: usá el botón **📱 WhatsApp** de la cuota
   con el mensaje preformateado.
2. Si el cliente **vino y pagó**: registrá el cobro con el botón **💵
   Pagar** (sección 7). El sistema actualiza automáticamente el saldo
   y el flujo de caja.
3. Si el cliente **pidió posponer**: editá la cuota cambiando el
   **vencimiento** a la nueva fecha. La cuota deja de aparecer como
   vencida hasta que pase la nueva fecha.
4. Si el cliente **no responde** después de 2-3 intentos: marcá el
   caso en las **notas del cliente** ("3 mensajes sin respuesta el
   X/Y/Z") y considerá acciones legales.

> ⚠️ **NO** "marques pagada" una cuota si no recibiste el dinero. Eso
> rompe el flujo de caja y los reportes.

### 10.2. Ventas sin cliente

Pasa por:
- Importaciones viejas que no asociaron la venta a una persona.
- Cargas apuradas donde se olvidó el campo.

**Cómo detectarlas:**

En **💰 Ventas**, hay chips de calidad arriba de la tabla. Clic en
**"⚠ Sin cliente"** para filtrar.

> Los chips de calidad se ven arriba de la tabla en la imagen de
> [Ventas](#5-registrar-una-venta) — incluyen **Todas / Solo reales /
> Códigos MIG / Placeholder / Sin cliente / Sin vehículo**.

**Cómo arreglarlas:**

1. Clic en el ícono de **edición (✏)** de la venta.
2. En el campo **Cliente**, buscá el cliente real (si lo conocés
   verbalmente — buscá por nombre o documento).
3. Si nunca registraste a esa persona, **creala** desde el mismo
   modal (botón "+ Nuevo cliente").
4. **Guardar**.

> 💡 Si **no sabés** quién compró ese auto (caso de migración vieja),
> dejala con cliente "Cliente General" o creá uno temporal con doc
> autogenerado, hasta que aclares la duda con el papelerío físico.

### 10.3. Ventas con código MIG

Las ventas migradas de la planilla Excel vieja llegan con números tipo
**`MIG-001`**, **`MIG-2018-XX`**, etc. Eso indica que se importaron
desde la planilla histórica.

**Qué hacer con ellas:**

- Si la venta está **cerrada y cobrada** y los datos están bien,
  **dejala como está**. El código `MIG` solo identifica el origen.
- Si tiene **datos incompletos** (sin cliente, sin vehículo, fecha
  rara, monto 0): editala completando lo que falte.
- Si querés cambiarle el código a uno del formato actual `CM/26-001`,
  hacelo desde Editar → campo "N° de venta".

> ⚠️ **NO** las borres en masa aunque parezcan basura. Muchas tienen
> cuotas pendientes de cobro reales — perderías esa cartera.

### 10.4. Vehículos con VIN basura o sin precio

Mismo patrón: chips de calidad en **🚗 Vehículos**:

- **"⚠ Sin precio"**: vehículos con price = 0. Editalos y poné el
  precio real.
- **"⚠ VIN placeholder"**: VIN con formato `VIN-DUMMY` o `VIN12345`
  generado automáticamente. Si conseguís el VIN real, reemplazalo.

> Los chips de calidad de vehículos se ven en la imagen de
> [Vehículos](#3-cargar-un-vehículo-nuevo) — incluyen
> **Todos / Sin precio / VIN placeholder**.

### 10.5. Clientes con documento autogenerado

Cuando se migró de la planilla vieja, varios clientes quedaron con
docs tipo **`DRV026-001`**, **`SUC026-XXX`** o **`CUOTA-XX`** —
placeholders que la migración generó porque no se conocía la cédula
real.

**Cómo detectarlos:**

En **👥 Clientes** → chip **"⚠ Doc autogenerado"**.

**Cómo arreglarlos:**

1. Clic en el cliente.
2. Pedile la cédula real al cliente (por teléfono o cuando vuelva al
   local).
3. Editalo: campo "N° documento" con el dato real.

> 💡 Estos clientes **funcionan perfectamente** en el sistema; el
> documento placeholder es sólo cosmético. Reemplazarlo es bueno
> para reportes y filtros pero no urgente.

### 10.6. Clientes sin teléfono

Chip **"⚠ Sin teléfono"** en /clientes.

Sin teléfono no podés mandar WhatsApp ni llamar para cobranza. Cada
vez que el cliente venga, pedí el número y editalo.

### 10.7. Una venta tiene los datos equivocados

(ej. el vendedor cargó el modelo o cliente equivocado)

1. En **💰 Ventas**, buscala por número.
2. Clic en **✏ Editar**.
3. Corregí lo que esté mal.
4. Guardar.

Si el cambio incluye el **vehículo**, el sistema libera al vehículo
viejo (vuelve a estado "Disponible") y marca al nuevo como "Vendido".

> ⚠️ Si cambiás el **monto** de una venta que ya tenía cuotas
> generadas, las cuotas **NO** se recalculan automáticamente.
> Tenés que entrar al modal de cuotas y ajustarlas (o borrarlas y
> regenerar el plan).

### 10.8. Borraste algo por error

El sistema tiene **audit log** que registra todas las acciones
(crear/editar/borrar). Para casos críticos de pérdida de datos
contactá al admin del sistema — tenemos backups semanales que se
pueden restaurar.

---

## 11. Atajos y tips

### Ctrl + K — Buscador global

![Buscador global Ctrl+K con resultados](imagenes/11-ctrl-k.png)

Apretá **Ctrl + K** (o **Cmd + K** en Mac) desde cualquier pantalla.
Se abre un buscador que mira a la vez en **ventas, clientes y
vehículos**. Tipeá lo que sea — N° de venta, nombre, VIN, marca — y
clickeá el resultado para ir directo.

Útil cuando alguien te dice "vino el cliente Pérez de la venta tal"
y no querés navegar por menús.

### Selector de sucursal

Si tu empresa tiene 2 sucursales (ej. CASA CENTRAL y Suc B), el
selector arriba del navbar filtra **todos los reportes y listados**
por la elegida. "Todas" muestra el agregado.

Cambiarla NO afecta a otros usuarios — cada uno tiene su propio
filtro.

### Filtros de período

Casi todas las pantallas con métricas (Dashboard, Ventas, Flujo de
caja) tienen el filtro **desde / hasta** con quick ranges. Cambiarlo
solo afecta lo que ves vos — no toca los datos.

### Backups

El sistema tiene backups automáticos semanales (cada lunes 03:00 UTC,
mientras el GitHub Action esté configurado con los secrets correctos).
También podés generar uno manual:

```bash
python scripts/backup_db.py
```

Los backups quedan en `backups/snapshot_<fecha>.json.gz` y **NO se
suben a GitHub** (contienen datos personales).

### Si algo no funciona

- **Una página no carga**: refrescá con `F5`. Si sigue mal, hacé
  logout y volvé a entrar.
- **Te muestra "Error 401"**: tu sesión venció, hacé login otra vez.
- **No te deja crear algo**: leé el mensaje rojo arriba del formulario
  — usualmente dice qué campo está mal.
- **Necesitás ayuda**: contactá al admin del sistema.

---

## Cómo guardar las imágenes de este manual

Las capturas las tomé directamente del sistema en producción durante
una sesión de Chrome MCP. Quedaron embebidas en la conversación del
chat con Claude.

**Para que el manual se vea con imágenes**, guardá cada captura del
chat con el nombre exacto que aparece en la tabla siguiente, dentro
de la carpeta `C:\Users\prueb\CascadeProjects\playa\docs\imagenes\`.

Procedimiento en el chat:
1. Buscá la captura que corresponde al ítem (por la descripción).
2. Hacé clic derecho sobre la imagen → **"Guardar imagen como..."**.
3. Navegá a `docs\imagenes\` y guardala con el nombre indicado.

| # | Nombre de archivo | Estado | Descripción de la captura |
|---|---|---|---|
| 1 | `01-login.png`              | ✅ OK | Pantalla `/login` vacía. |
| 2 | `01-logout.png`             | ✅ OK | Menú de usuario abierto con "Cerrar sesión". |
| 3 | `02-dashboard.png`          | ✅ OK | Dashboard con KPIs (sólo agregados, sin datos sensibles). |
| 4 | `03-vehiculos-lista.png`    | ✅ OK | Inventario vehículos con chips "Sin precio" y "VIN placeholder". |
| 5 | `04-cliente-nuevo.png`      | ✅ OK | Modal "Nuevo cliente" con form vacío. |
| 6 | `05-ventas-lista.png`       | ⚠ Tiene datos | Lista de ventas con chips MIG / Sin cliente / etc. (nombres de clientes visibles — re-tomar con ofuscación antes de publicar). |
| 7 | `05-venta-nueva.png`        | ✅ OK | Modal "Nueva venta" con form vacío. |
| 8 | `06-cuotas-modal.png`       | ✅ OK | Modal "Cuotas de la venta CM36/26" (sólo montos genéricos). |
| 9 | `07-cliente-detalle.png`    | ⚠ Tiene datos | Detalle del cliente con sus ventas y cuotas (nombre real visible — re-tomar). |
| 10 | `07-cuotas-tabla.png`      | ✅ OK | Tabla de cuotas de un cliente con botones "✓ Pagar". |
| 11 | `07-pagar-modal.png`       | ⚠ Tiene datos | Modal "Registrar pago" mostrando datos de la cuota (nombre del cliente — re-tomar). |
| 12 | `09-flujo-caja.png`        | ⚠ Tiene datos | Flujo de caja con tabla de operaciones (nombres de clientes — re-tomar). |
| 13 | `09-nuevo-movimiento.png`  | ✅ OK | Modal "Nuevo movimiento" con form vacío. |
| 14 | `10-morosos.png`           | ✅ OK | **Panel "Clientes morosos" YA OFUSCADO** (versión ofuscada del chat). |
| 15 | `11-ctrl-k.png`            | ⚠ Tiene datos | Palette Ctrl+K mostrando resultados (clientes visibles — re-tomar). |

### Re-tomar las capturas con ofuscación (cuando puedas)

Las 5 marcadas con ⚠ tienen datos reales sin ofuscar todavía. Para
ofuscarlas vos mismo en el navegador antes de capturar, pegá esto en
la consola del browser (F12 → Console) en la página correspondiente:

```javascript
(function(){
  const W=new Set(['AUTO','OFERTAS','CASA','CENTRAL','SUCURSAL','TOYOTA',
    'HONDA','NISSAN','KIA','CHEVROLET','SUZUKI','FORD','MAZDA','HYUNDAI',
    'VITZ','RACTIS','SIENTA','AURIS','ALLION','SPORTAGE','PASSO','RAV4',
    'COROLLA','FIT','CIVIC','MARCH','PLATA','NEGRO','BLANCO','GRIS',
    'ROJO','AZUL','VERDE','BEIGE','DORADO','MARRON','CELESTE',
    'PYG','USD','EF','TB','CJ','AC','MIG']);
  function isW(t){return W.has(t)||t.split(/\s+/).every(w=>W.has(w));}
  function obf(t){
    if(!t||t.length<6||isW(t))return false;
    return /^[A-ZÁÉÍÓÚÑ]+(\s+[A-ZÁÉÍÓÚÑ]+){1,5}$/.test(t)
      ||/^CUOTA\d{4,}$/i.test(t)
      ||/^DRV\d{3}-\d+$/i.test(t)
      ||/^SUC\d{3}-\d+$/i.test(t)
      ||/^\d{6,10}$/.test(t)
      ||/^0\d{3}[\s-]?\d{6,7}$/.test(t)
      ||/^09\d{2}[\s-]?\d{3}[\s-]?\d{4}$/.test(t)
      ||/^0\d{9,10}$/.test(t);
  }
  function walk(n){
    if(n.nodeType===3){const t=n.textContent.trim();if(obf(t))n.textContent='█'.repeat(Math.min(t.length,18));}
    else if(n.nodeType===1&&!['SCRIPT','STYLE','INPUT','TEXTAREA','SELECT','OPTION'].includes(n.tagName)){
      for(const c of [...n.childNodes])walk(c);
    }
  }
  walk(document.body);
})();
```

Después usá `Win+Shift+S` para recortar y guardar la captura en
`docs\imagenes\<nombre>.png`.

### Capturas opcionales (no incluidas)

Estas las podés sacar después si querés enriquecer el manual:

| Sugerencia | Cuándo viene bien |
|---|---|
| `06-cuotas-preview.png` | Después de clickear "Generar preview" en el modal de cuotas. |
| `08-whatsapp-cuota.png` | Acercamiento al botón WhatsApp de una cuota individual. |
| `10-chips-vehiculos.png` | Detalle de los chips de calidad de vehículos. |
| `10-chips-ventas.png`   | Detalle de los chips de calidad de ventas. |

---

## Versión

Manual versión 1.0 — corresponde al sistema desplegado en producción
hasta los commits:
- Backend  `e1610c6` (Sale: distinguir status del contrato vs estado de cobranza)
- Frontend `1f59b18` (Fix: BranchContext espera isAuthenticated antes de fetchear branches)

Las mejoras de las ramas `staging` (recordatorios automáticos, PDF de
cronograma, búsqueda fuzzy, etc.) no están cubiertas acá — se
documentarán en la versión 2.0 del manual cuando se haga el próximo
deploy.
