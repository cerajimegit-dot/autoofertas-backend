# Metaprompt — Sitio de beAI Studio

Este metaprompt está diseñado para entregárselo a un agente de codigo
(Claude Code, Cursor, v0, Bolt) que va a construir el sitio web de la
consultora.

**Audiencia del sitio: dueños y gerentes de PyMEs latinoamericanas**
(50-200 empleados, facturan en Gs/USD, manejan su negocio en Excel/ODS).
NO se le habla a desarrolladores, ni a agencias que vayan a revender
software. Se le habla a la persona que **firma el cheque** y siente todos
los días el dolor de no tener visibilidad de su propio negocio.

Tomá el caso AUTO OFERTAS como ejemplo concreto. No inventes métricas —
las que están abajo son reales.

---

## Contexto del negocio

**beAI Studio** (nombre tentativo — ver propuestas al final) es una
consultora que **ordena negocios que crecieron en Excel**.

Le entregamos a la empresa **un sistema propio**, hecho a la medida de
su forma de trabajar, en 3-6 semanas. No es un SaaS genérico; no es un
módulo enlatado tipo SAP. Es **un sistema diseñado para la empresa**,
con su flujo, su lenguaje, sus reportes.

El cliente lo usa internamente — administradores, vendedores, dueño.
No lo revende ni lo distribuye.

**Diferencial respecto a lo que el mercado ofrece hoy**:

| Lo que hay hoy en el mercado | Lo que hacemos nosotros |
|---|---|
| SaaS enlatado tipo Holded/Siigo: te adaptás vos al sistema | El sistema se adapta a tu forma de trabajar |
| Agencia grande: 6 meses, 3 personas, USD 60.000 | 3-6 semanas, equipo chico, costo menor |
| Freelancer: barato pero no termina o desaparece | Empresa establecida, contrato claro, código tuyo |
| Implementación SAP: te quema el presupuesto y el ánimo | Tu mismo equipo lo usa desde la semana 3 |

**Mercado primario**: Paraguay, Argentina, Uruguay, Chile.
PyMEs familiares o regionales de 5-200 empleados. Sectores donde el
Excel todavía es la herramienta principal: concesionarias de autos,
distribuidoras, cooperativas, retailers regionales, constructoras
medianas, agencias de viajes.

---

## El cliente que estamos buscando

Cuando alguien aterriza en el sitio, queremos que se sienta visto.
Estas son las situaciones reales del mercado al que apuntamos:

- "Mi contadora me manda un Excel todos los meses con saldos, y para
  cuando lo veo ya pasaron 30 días."
- "Tengo 2 sucursales y nunca sé en tiempo real cuánto stock hay en
  cada una."
- "Cada vez que un cliente pregunta por su saldo, mi secretaria abre
  3 planillas distintas."
- "Tengo 50 cuotas vencidas pero no sé cuáles porque están mezcladas
  con todo lo demás."
- "Mi cuñado me hizo el sistema hace 5 años y ya no me contesta los
  mensajes."

El sitio NO debe hablar de:
- "Arquitectura escalable"
- "API REST"
- "Stack tecnológico"
- "Microservicios"
- "Multi-tenant"
- "AI agents"
- "Lighthouse score"

El sitio SÍ debe hablar de:
- "Ver tu negocio en una pantalla"
- "Saber lo que pasó hoy, sin esperar al cierre del mes"
- "Que tu equipo deje de copiar y pegar de un Excel a otro"
- "Que el sistema te avise antes de que un cliente se atrase"

---

## Especificaciones del sitio

### Stack y entorno (interno, no visible al cliente)

- **Framework**: Astro (preferido por velocidad) o Next.js 15.
- **Estilo**: Tailwind CSS v3. shadcn/ui o Radix para primitivas.
- **Animaciones**: framer-motion. Sutiles, NO carruseles infinitos.
- **Tipografía**: Inter o similar para body; titulares con peso 600-700.
  Nada de tipografías "tech" tipo Geist Mono visibles al usuario.
- **Idioma**: español rioplatense (PY/AR). Voseo.
- **Hosting**: Vercel/Netlify/Cloudflare Pages.

### Estilo visual

Profesional pero **cálido**, no dev tool. Referencias:
[tiendanube.com](https://tiendanube.com), [holded.com](https://holded.com),
[siigo.com](https://siigo.com), [bind.com.ar](https://bind.com.ar).

NO copies la estética Linear/Railway/Vercel — esa es para devs y
asusta al dueño de 55 años.

- **Light mode por default**. Dark mode opcional pero NO el default —
  la audiencia espera blanco cuando entra a un sitio "serio".
- **Paleta**: blanco/gris muy claro de fondo, **un azul navy** o
  **un verde botella** como color principal (sugerencia: `#1e3a8a` o
  `#064e3b`). Acento naranja cálido (`#f59e0b`) para CTAs. Evitar:
  - Rojo del logo de AUTO OFERTAS (es del cliente, no de beAI).
  - Violetas/fuxia (lectura "startup tecnológica", no encaja).
  - Negros puros (frío, distante).
- **Imágenes con personas reales**: mejor que ilustraciones abstractas.
  Si hay foto de una concesionaria, un local, una persona usando el
  sistema en una tablet, mejor. Stock photos sobrias OK; "diversidad
  inc. corporativa" NO.
- **Capturas reales del dashboard** del caso AUTO OFERTAS, con datos
  ofuscados o de demo. Eso muestra "esto es real, no maquetas".
- **Spacing**: cómodo, profesional, no demasiado aireado (lectura
  tipo Vercel cansa al lector empresarial; un Holded es ideal).
- **Tipografía grande en los KPIs del caso**. El número 5× más grande
  que el texto, en color de acento. Estilo "infografía de diario".

### Estructura de la página

Una sola página larga con ancla de navegación. Secciones obligatorias
en este orden:

#### 1. Hero (above the fold)

- **Headline**: corto, en lenguaje de negocio. Opciones a iterar:
  > **"Tu negocio no tiene por qué seguir viviendo en planillas."**

  > **"El sistema que necesita tu empresa, en 4 semanas."**

  > **"De Excel al control total de tu negocio."**

- **Subhead** (2 líneas máximo):
  > "Diseñamos y construimos sistemas internos a la medida de cómo
  > trabajás. Tu equipo, tus reportes, tu forma. En semanas, no en
  > años."

- **CTAs**:
  - Primario: **"Pedí una reunión de diagnóstico gratis"** → form o
    Calendly.
  - Secundario: **"Ver cómo lo hicimos para AUTO OFERTAS"** → ancla.

- **Visual del hero**: composición que muestre el contraste. Lado
  izquierdo, una pantalla con planilla Excel desordenada, ojos
  cansados, papeles. Lado derecho, una persona sonriendo viendo un
  dashboard ordenado en una tablet. Sin caricaturas. Foto o
  ilustración semi-realista.

  Alternativa: solo el dashboard, en grande, con el detalle "Vista
  del cobrador, junio 2026" arriba. Mostrar **menos UI técnica y
  más realidad**.

#### 2. ¿Esto es para vos? (validación rápida)

Una sección corta con 4-6 frases tipo "vibe check" para que el lector
se vea reflejado. Estilo lista de checks emocionales.

> **Esto es para vos si...**
>
> ☐ Vivís pegando información de un Excel a otro para que te cuadren
>   los números.
>
> ☐ Tu equipo te pregunta cosas que vos también deberías saber, pero
>   tenés que abrir 3 planillas para responder.
>
> ☐ Sabés que en el banco hay más de lo que tu Excel dice, pero no
>   sabés exactamente cuánto más.
>
> ☐ Ya intentaste un SaaS pero te quedó grande, o demasiado rígido, o
>   no entendía cómo trabajás.
>
> ☐ Hace meses que estás "por hacer ese sistema" pero no encontraste
>   con quién.

Es honesto, conversacional, no agresivo. Crea identificación.

#### 3. Cómo trabajamos

Card visual con 4-5 pasos. Cada paso con icono simple (no flat 3D),
título y 2-3 líneas. La idea es **dar tranquilidad sobre el proceso**.

1. **Conocemos tu negocio (1 semana)**
   Una reunión con vos. Otra con quienes usan las planillas todos los
   días. Vemos cómo trabajás. No te vendemos antes de entender.

2. **Te mostramos el plan (1 semana)**
   Una maqueta navegable de las pantallas principales. Te la
   aprobás antes de que escribamos una sola línea de código.
   Acá decidimos juntos qué SÍ y qué NO va.

3. **Construimos el sistema (2-4 semanas)**
   Trabajamos todos los días. Cada viernes te mostramos lo nuevo.
   Tenés acceso desde el día 5 a un link de prueba — tu equipo
   puede ir mirando, no esperás hasta el final.

4. **Mudamos tus datos**
   Tus Excel históricos pasan al nuevo sistema. Sin perder nada.
   Te entregamos un reporte de las inconsistencias que encontramos
   en tus datos viejos para que las corrijas.

5. **Lanzamos juntos (1 mes de acompañamiento)**
   Capacitamos a tu equipo. Estamos disponibles por WhatsApp el
   primer mes. Cuando algo no funciona, lo arreglamos rápido.

#### 4. Caso real — AUTO OFERTAS (#caso-auto-ofertas)

**Esta es la sección que vende.** Estructurala como una historia
contada desde la perspectiva del dueño, no del desarrollador.

##### El cliente

> AUTO OFERTAS es una concesionaria de autos importados de Japón
> en Asunción. Dos sucursales. Empresa familiar. ~80 ventas al año
> a clientes locales, casi todas a crédito con cuotas de 18 a 36
> meses.

##### El problema

> El dueño tenía **142 planillas de Excel** — una por venta. Cuando
> un cliente llamaba preguntando por su saldo, había que abrir su
> planilla específica. Si era el cliente "Mario Bogado", abrir la
> planilla "Mario Bogado", revisar 24 filas de cuotas, sumar las
> pagadas, restar al total.
>
> Cada mes la administradora pasaba **2 días enteros** consolidando
> las planillas en un Excel resumen. Errores frecuentes: cuotas
> registradas dos veces, vehículos marcados como "disponibles" que
> en realidad estaban vendidos, clientes con saldos que nadie sabía
> que existían.

##### Lo que entregamos

(Sin lenguaje técnico — describir desde el USO, no desde la
implementación.)

> En 5 semanas, el dueño tenía un sistema propio donde:
>
> - Ve **en una pantalla** todas las ventas del mes, con totales por
>   sucursal y vendedor.
> - Cuando un cliente pregunta su saldo, su administradora **busca
>   su nombre y aparece todo** — qué autos compró, cuántas cuotas
>   pagó, cuánto debe, cuándo vence la próxima.
> - El sistema avisa solo cuándo una cuota está por vencer. Y arma
>   el mensaje de WhatsApp para enviarle al cliente, con el monto
>   y la fecha, listo para mandar.
> - Funciona en computadora, tablet y celular. Sus vendedores
>   cargan ventas desde el showroom.
> - **Solo el dueño ve los datos del dueño**. Sus vendedores ven
>   lo que pueden ver. Su secretaria, lo de ella.

##### Los números (visualmente grandes)

Mostrar como 4-6 stats en grilla, cada uno con número 6xl y subtítulo:

> **5 semanas** desde el primer mate hasta el sistema andando.
>
> **142** planillas reemplazadas por un sistema único.
>
> **2 días → 5 minutos** lo que la administradora tarda en consolidar
> el resumen del mes.
>
> **Gs. 31 millones** de cuotas vencidas que aparecieron en el primer
> reporte y nadie sabía que existían.
>
> **24/7** el dueño consulta su negocio desde el celular.

##### Quote del dueño (si conseguís uno con permiso)

Un párrafo en cita grande. Algo tipo:

> "Antes me pasaba el sábado a la mañana abriendo planillas. Hoy
> abro el celular en el desayuno y veo todo. Cambió mi vida más
> que mi mujer."
>
> — *Nombre, AUTO OFERTAS, Asunción*

(Buscar quote real si está autorizado; si no, omitir esta parte —
quote inventada se huele.)

##### Capturas reales del sistema

3-4 screenshots:
1. Dashboard con los KPIs.
2. Ficha del cliente con su historial de ventas y cuotas.
3. Listado de cuotas vencidas con el botón "Mandar WhatsApp".
4. Flujo de caja con ingresos y egresos del mes.

Datos ofuscados (nombres y montos cambiados), pero el diseño real.

#### 5. Qué hacemos

3 cards con servicios. Sin precios en USD visibles (la audiencia local
no tiene el reflejo de pensar en USD). Mejor: rangos descriptivos.

- **Tu sistema, hecho a medida**
  Como AUTO OFERTAS. Diseñamos, construimos y entregamos un sistema
  completo. Tu lógica, tu lenguaje, tus reportes.
  *Proyectos típicos: 4 a 8 semanas. Presupuesto a medida tras una
  reunión de diagnóstico.*

- **Diagnóstico de tu sistema actual**
  Si ya tenés un sistema (propio o un SaaS) y sentís que no te está
  rindiendo, te hacemos una auditoría. Te entregamos un informe
  con qué está funcionando, qué te está costando plata o tiempo,
  y cómo arreglarlo.
  *Entrega: 1-2 semanas. Presupuesto fijo.*

- **Acompañamiento mensual**
  Cuando tu sistema ya funciona, lo mantenemos vivo: features
  nuevas que vayan surgiendo, ajustes, soporte por WhatsApp.
  *Suscripción mensual. Cancelable cuando quieras.*

#### 6. Por qué nos contratan (no "Por qué elegirnos")

3-4 puntos concretos, sin slogans vacíos:

- **El código es tuyo.** Cuando terminamos, te entregamos el sistema
  completo en TU GitHub, con todo documentado. Si mañana querés
  contratar a otro para que lo siga, lo puede hacer. Vos sos el dueño,
  no nosotros.

- **Te dejamos ver mientras trabajamos.** Desde la semana 1 tenés un
  link para ver lo que estamos haciendo. Nada de "esperá 3 meses y
  te muestro". Sabés exactamente en qué van tus pesos.

- **Hablamos tu idioma, no el nuestro.** Si nuestro mail dice
  "implementamos una arquitectura microservicios", tirá el mail.
  Lo que decimos lo entiende cualquier persona de tu equipo.

- **Sabemos que no sos técnico.** Y eso está bien. Vos sos el experto
  en tu negocio. Nosotros somos los expertos en convertir tu
  conocimiento en un sistema. Pongamos cada uno lo nuestro.

#### 7. Preguntas frecuentes

7-9 preguntas que el dueño SÍ se hace antes de firmar. Respuestas
directas, sin esquivar.

- **¿Cuánto sale?**
  Depende de la complejidad. Una venta de autos como AUTO OFERTAS está
  en el rango de Gs. 50-90 millones (USD 6.000-12.000). Una pyme con
  pocas pantallas simples, bastante menos. Te decimos el número
  exacto después de la reunión de diagnóstico (que es gratis).

- **¿Cuánto tarda?**
  Entre 3 y 8 semanas según el tamaño. AUTO OFERTAS tardó 5 semanas.

- **¿Y si me dejan colgado a mitad de camino?**
  Por contrato cobramos 50% al inicio, 50% al entregar. Si no
  entregamos, no cobramos la segunda mitad. Y el código que ya
  escribimos queda en tu cuenta de GitHub.

- **¿Qué pasa cuando ustedes desaparezcan?**
  El sistema sigue funcionando solo. Está hecho con herramientas
  estándar (no algo raro que solo nosotros sabemos). Si mañana
  necesitás un dev, cualquier programador puede tomar el código.

- **¿Migran mis datos viejos?**
  Sí. Es parte del paquete. AUTO OFERTAS arrancó con 427 ventas
  históricas y 1.500 cuotas ya cargadas, sin que tengan que
  cargar nada a mano.

- **¿Trabajan con clientes fuera de Paraguay?**
  Sí. Argentina, Uruguay, Chile, Bolivia. Trabajamos remoto. Para
  empresas del país, las primeras reuniones podemos hacerlas
  presenciales.

- **¿Quién va a poder entrar a mi sistema?**
  Solo las personas que vos autorices. Vos sos el administrador.
  El sistema tiene niveles: el dueño ve todo, el gerente ve su
  sucursal, el vendedor ve sus ventas. Y cada acceso queda
  registrado.

- **¿Funciona en celular?**
  Sí. Diseñado para que un vendedor pueda cargar una venta desde
  el showroom con el teléfono.

- **¿Y si quiero un cambio después?**
  Por eso ofrecemos el acompañamiento mensual. Las pymes cambian
  todo el tiempo — el sistema tiene que cambiar con vos.

#### 8. Formulario de diagnóstico (#diagnostico)

Es **el corazón del funnel**: el CTA primario apunta acá. No es un
formulario de contacto genérico ("tu nombre, tu mensaje, ¡gracias!").
Es un **mini diagnóstico** que cumple dos funciones a la vez:

1. **Califica al lead** antes de la primera reunión — para que el
   equipo de beAI ya entienda con quién va a hablar y no malgaste el
   tiempo en preguntas básicas.
2. **Construye la base de datos** de leads con info útil para
   priorizar, segmentar y hacer follow-up meses después.

##### Reglas de diseño del formulario

- **Multi-step** (wizard de 4 pasos). Mostrar progreso "Paso 2 de 4"
  arriba. Cada paso ~5 preguntas. NO mostrar las 20 de una vez —
  abruma y se pierde el 80% de las respuestas.
- **Solo 3 campos obligatorios**: nombre, email, empresa. Todo lo demás
  es opcional — si el lead se cansa en el paso 3, igual quedó capturado.
- **Preguntas conversacionales**, no de encuesta. "Contame cómo
  laburás hoy" mejor que "Indique la herramienta utilizada actualmente".
- **Sin "select" infinitos**. Para algo como rubro, usar 6-8 opciones
  visibles + "otro" con campo libre.
- **Botón "Guardar y seguir después"** en cada paso — manda email
  con un link para retomar (token único).
- **Mobile-first**: la mitad de leads van a llenar desde el celular.
  Inputs grandes, sin pop-ups, paso a paso fluido.
- **Sin captcha visible**. Usar honeypot field invisible + rate limit.
  Captchas matan conversión.
- **Después de enviar**: thank-you page con (a) calendario embebido
  para agendar la reunión directa, (b) qué pasa después en lenguaje
  claro, (c) link al caso AUTO OFERTAS por si vinieron del Google.

##### Las preguntas (las 20)

**Paso 1 — Conocerte (5 campos)**

1. **Tu nombre** (*obligatorio*, text, max 80 chars)
2. **Tu rol en la empresa** (radio, opciones):
   - Soy el dueño / dueña
   - Gerente general
   - Administrador / administradora
   - Encargado de un área (ventas, finanzas, operaciones...)
   - Otro
3. **Email** (*obligatorio*, validación de formato)
4. **WhatsApp** (text, recomendado pero opcional). Tooltip:
   *"Si lo dejás, te respondemos por acá. Si no, vamos por email."*
5. **¿Cómo nos encontraste?** (select)
   - Un conocido me recomendó
   - Google
   - LinkedIn
   - Instagram / Facebook
   - Otra cosa

**Paso 2 — Tu empresa (5 campos)**

6. **Nombre de la empresa** (*obligatorio*, text)
7. **¿A qué se dedica?** (select con "otro" en campo libre)
   - Venta de vehículos
   - Distribuidora / mayorista
   - Retail / comercio
   - Cooperativa
   - Construcción / inmobiliaria
   - Agencia de viajes
   - Servicios profesionales
   - Industria / fabricación
   - Otro: [text]
8. **Ciudad y país** (text, autocomplete optional)
9. **Cuánta gente trabaja en la empresa** (radio):
   - Somos pocos (1-5)
   - Equipo chico (6-15)
   - Mediano (16-50)
   - Grande (51-200)
   - Más de 200
10. **¿Tienen una sola sede o varias?** (radio):
    - Una sola
    - Dos
    - 3-5
    - Más de 5

**Paso 3 — Tu situación hoy (6 campos — el corazón del diagnóstico)**

11. **¿Cómo gestionan el negocio hoy?** (multi-select, "marcá todo
    lo que aplique"):
    - Excel / Google Sheets / LibreOffice
    - Papel / cuadernos
    - Un sistema enlatado (Holded, SAP, Siigo, Bind, etc.) — *si
      seleccionan esto, aparece input libre: "¿cuál?"*
    - Un sistema hecho a medida hace años — *aparece input: "¿hace
      cuánto tiempo? ¿quién lo hizo?"*
    - WhatsApp y memoria
    - Otra cosa: [text]
12. **¿Qué áreas te están dando más dolor de cabeza?** (multi-select):
    - Ventas / facturación
    - Cobranzas / cuotas / morosos
    - Stock / inventario
    - Finanzas / caja
    - Compras
    - RRHH / sueldos
    - Reportes para tomar decisiones
    - Comunicación con clientes
    - Otra cosa: [text]
13. **De 1 a 5, ¿qué tan rápido podés saber el estado de tu negocio
    HOY mismo?** (slider/radio 1-5)
    - 1 = "Tendría que pedirle a alguien que arme un Excel y esperar
      al final del día"
    - 5 = "Lo veo desde mi celular en este momento"
14. **¿Probaron alguna vez un sistema enlatado o un SaaS y no les
    funcionó?** (radio + text):
    - Sí (campo libre: "¿cuál y por qué?")
    - No
15. **Si tuvieras que arreglar UNA sola cosa con tecnología en tu
    empresa, ¿cuál sería?** (textarea, 2-3 líneas)
16. **¿Hay algo que está disparando este pedido ahora?** (radio):
    - Estamos creciendo y se nos hace inmanejable
    - Tuvimos un problema concreto (perdimos plata, hubo error grave)
    - Un sistema viejo dejó de servirnos
    - Vimos un competidor que lo tiene
    - Lo veníamos pensando hace tiempo

**Paso 4 — Práctico (4 campos)**

17. **¿Cuándo necesitarían tenerlo andando?** (radio):
    - Lo antes posible (1-2 meses)
    - Próximos 3 meses
    - Próximos 6 meses
    - No tengo urgencia, estoy explorando
18. **Rango de inversión que tienen pensado** (radio):
    - Menos de USD 5.000
    - USD 5.000 - 10.000
    - USD 10.000 - 25.000
    - USD 25.000 - 50.000
    - Más de USD 50.000
    - No sé / quiero ver propuesta primero

    Tooltip al lado: *"Saber el rango nos ayuda a ofrecerte algo
    realista. Si no estás seguro, marcá la última opción y lo
    conversamos."*

19. **¿Quién toma la decisión de contratarnos?** (radio):
    - Yo solo
    - Yo con uno o dos socios
    - Necesita aprobación de un directorio / consejo
20. **¿Algo más que sea importante que sepamos antes de la reunión?**
    (textarea, opcional)

##### Consentimiento de datos

Checkbox obligatorio al pie del paso 4:

> ☐ Acepto que beAI Studio guarde estos datos para responderme y,
>   ocasionalmente, mandarme contenido relacionado (artículos del
>   blog, casos nuevos). Puedo pedir que los borren en cualquier
>   momento escribiéndoles.

Link a la política de privacidad (un `/privacidad` simple, 1
página, sin abogado). No CCPA / GDPR strict — el negocio es latam,
no UE.

##### Después de enviar el formulario

1. **Thank-you page** (`/gracias`):
   - "Recibimos tu pedido. Te respondemos en menos de 24 hs hábiles."
   - Calendario embebido (Cal.com o Calendly) para que agende la
     reunión directa si quiere acelerar. Si elige horario, el lead
     queda doblemente capturado.
   - Texto: "Mientras tanto, mirá cómo ayudamos a AUTO OFERTAS" →
     link al case study.
   - NO redirigir a home — el usuario ya tomó la acción, no lo
     mandes a empezar de cero.

2. **Email automático al lead** (template):
   - Asunto: "Recibimos tu pedido — beAI Studio"
   - Cuerpo: resumen breve de lo que respondió (para que se sienta
     escuchado), próximos pasos, info de contacto del responsable
     de cuenta.
   - Enviado vía Resend, Postmark, o el SMTP del dominio.

3. **Notificación al equipo de beAI**:
   - Email a los founders (cc o un alias `nuevoslead@beai.studio`).
   - **O** mejor: webhook a Slack/Discord/Telegram con el resumen
     formateado. Más práctico que el mail.
   - Mensaje con: nombre, empresa, sector, área de dolor, rango de
     inversión, urgencia. **Sin** info de contacto privada en el
     canal (eso queda en la DB).

##### Storage y CRM

El formulario es la cara — atrás necesita una base de datos donde
los leads queden navegables. Opciones, de menor a mayor inversión:

**MVP — Airtable** (recomendado para los primeros 6 meses):
- Tabla `Leads` con todas las columnas mapeadas a las 20 preguntas.
- Vistas filtradas: "Nuevos esta semana", "Hot (presupuesto >25k)",
  "En seguimiento", "Cerrados".
- Form de Airtable embebido en el sitio si se quiere lo más simple.
  Pero esto restringe el diseño — solo si la consultora todavía está
  validando producto.
- Sincronización con Slack y Gmail via Zapier o Make.

**Versión propia — Supabase + Postgres** (recomendado a partir de 50
leads/mes):
- Tabla `lead` con todas las columnas + `created_at`, `updated_at`,
  `status` (nuevo / contactado / agendado / propuesta / cerrado /
  descartado), `notes` (libre).
- Endpoint público en la API (rate limited) que recibe el POST del
  formulario.
- Mini-CRM propio en `/admin` (sólo accesible a la consultora con
  login) para gestionar los leads.
- Esto pone a la consultora **como su propio cliente**. Demuestra
  que practicamos lo que vendemos.

**No usar Salesforce/HubSpot/Pipedrive** a menos que la consultora
crezca a 10+ personas. Es overkill, caro, y el lead se siente
"processed" en vez de "atendido".

##### Validación y anti-spam

- Honeypot field invisible (campo que solo bots ven y rellenan; si
  viene rellenado, descarte silencioso).
- Rate limit por IP: 3 envíos / hora máximo.
- Validación server-side de email (formato + DNS lookup).
- Si el campo "nombre" tiene caracteres no-latinos masivos o el
  "WhatsApp" tiene letras, descarte.
- NO captcha. Si el bot insiste, ban manual de IPs.

##### Diseño visual del formulario

- Una pregunta o pequeño grupo por pantalla — efecto "Typeform-light".
- Animación de transición sutil entre pasos (slide 200ms).
- Mostrar progreso ("Paso 2 de 4") arriba con barra fina.
- Botón "Anterior" / "Siguiente" en cada paso. "Anterior" no debe
  borrar lo respondido (sessionStorage como cache).
- Botón final: **"Enviar — agendá tu reunión"** (no "Submit", no
  "Enviar" a secas).
- Loading state visible al enviar (no doble-click → doble lead).
- Confirmación visual cuando llega al servidor: animación de check
  verde, transición a `/gracias`.

#### 9. CTA final + footer

- Un cierre emocional corto, antes del CTA repetido:
  > Si llegaste hasta acá, probablemente tu negocio merece más
  > orden del que tiene. Hablemos.

- CTA primario repetido (apunta al formulario o a abrir el modal
  con el formulario en su lugar — depende del estilo elegido).
- Datos de contacto alternativos: email + WhatsApp directo
  (para los que prefieren no llenar nada).
- Logo + año + link a política de privacidad.

### Lo que NO querés en el sitio

- **Slider de logos** de "clientes que confían en nosotros" si solo
  tenés AUTO OFERTAS. Es mejor un caso bien contado que 10 logos
  que nadie va a reconocer.
- **Banderas de países** indicando "trabajamos en X países". Es
  patético si la verdad es 1-2 países.
- **Métricas inventadas** ("hemos transformado 500+ empresas"). Si
  tenés 1 cliente, decí 1. Construí confianza con honestidad.
- **Sección "Nuestro equipo"** con 6 caras stock. Si sos vos solo,
  decilo: "soy yo, trabajo con AI moderna y otros profesionales en
  proyectos específicos."
- **Frases de la PNL corporativa**: "innovación", "sinergia",
  "ecosistema", "transformación digital", "soluciones 360".
- **Chatbot de Intercom o widget de Tawk.to**. Para una consultora
  chica con pocos clientes, contraproducente.
- **Tabla de comparación contra otras agencias**. Pone a la
  defensiva, no es necesario.
- **Pop-ups de "10% de descuento si dejás tu email"**. No vendemos
  un curso online.

### Tono y copy

- **Voseo**. Toda la página.
- **Conversacional**, no corporativo. Si la frase suena a brochure
  de banco, está mal.
- **Sin tecnicismos visibles**. Si el lector ve "API", "stack",
  "framework", "deploy" — tirar la línea.
- **Concreto**. "5 semanas" mejor que "rápido". "Gs. 31 millones de
  cuotas vencidas" mejor que "mejoramos visibilidad financiera".
- **Honesto sobre limitaciones**: "no somos una agencia de 50
  personas. Somos un equipo chico. Por eso somos más rápidos y
  más caros por hora, y más baratos por proyecto."

### Lo técnico (interno, no visible al cliente)

#### Performance y SEO

- Lighthouse > 90 en mobile.
- FCP < 2s en 4G.
- Imágenes en WebP/AVIF.
- Fuentes con `font-display: swap`.
- Meta tags + OpenGraph + Twitter Cards.
- Schema.org `Organization` + `LocalBusiness`.
- Sitemap.xml + robots.txt.
- HTTPS obligatorio.

#### Analytics

Tracking básico, sin invasión:

- **Plausible** o **Umami** (privacy-friendly, sin cookies de
  consent).
- Eventos: click CTA primario, scroll a "Caso AUTO OFERTAS",
  expansión de FAQ, click WhatsApp, click email.

NO Google Analytics, NO Facebook Pixel, NO Hotjar a menos que
tengas un motivo concreto.

#### Accesibilidad

- WCAG 2.1 AA mínimo.
- Contraste verificable.
- Navegación por teclado.
- `prefers-reduced-motion` respetado.

---

## Deliverable esperado

El agente que reciba este metaprompt debe generar:

1. Un repositorio nuevo con la estructura del proyecto.
2. La página principal en `/`, además:
   - `/gracias` — thank-you page post-formulario.
   - `/privacidad` — política simple (1 página, sin abogado).
   - `/admin` — opcional, mini-CRM si se elige Supabase.
3. Componentes separados por sección (`Hero`, `Validation` ("¿Esto es
   para vos?"), `Process`, `CaseStudyAutoOfertas`, `Services`, `WhyUs`,
   `FAQ`, `DiagnosticForm`, `Footer`).
4. Datos en archivos `.json` editables (la lista de servicios, FAQ,
   pasos del proceso, opciones de los radio/select del formulario).
   Nada hardcodeado en JSX — para que el copy se pueda iterar sin
   tocar componentes.
5. **Formulario funcional**:
   - Wizard de 4 pasos con animación.
   - Validación server-side y client-side.
   - Honeypot + rate limit.
   - Persistencia (sessionStorage para que el lead pueda volver
     atrás sin perder datos).
   - Endpoint que recibe el POST y guarda en el storage elegido
     (Airtable API o Supabase tabla `lead`).
   - Email transaccional al lead vía Resend/Postmark.
   - Webhook a Slack/Discord/Telegram para el equipo.
   - Redirección a `/gracias` con calendario embebido al confirmar.
6. README con:
   - Cómo correr local (`npm install`, `npm run dev`).
   - Cómo deployar (Vercel/Netlify).
   - Cómo cambiar la copy.
   - Cómo configurar las env vars del formulario (API keys de
     Airtable/Supabase/Resend/Slack).
7. Carpeta `/public/images/` con capturas y assets.
8. NO commitear `.env`, secrets, ni archivos del cliente.
9. `npm run build` debe pasar sin warnings.
10. **Tests mínimos del formulario** (Vitest o Playwright):
    - Validación de email mal formado rechazada.
    - Honeypot rellenado → descarte silencioso.
    - Submit completo → llamada al endpoint + redirección a
      `/gracias`.
    - Datos persisten al volver al paso anterior.

## Cómo NO querés que sea el deliverable

- Una plantilla genérica de Tailwind UI (se nota a la legua).
- Estética "dev tool" (dark mode default, Geist Mono, gradient violeta).
  La audiencia es otra.
- Inglés cuando el target es español PY/AR.
- Animaciones de Framer Motion en todo lo que se mueve (cansa al ojo
  no-técnico).
- Lighthouse < 90.
- "Lorem ipsum" en ningún lado del final (probable, hay que verificar).

---

## Propuestas de nombre con siglas "beAI"

Las que ya hablamos:

| Nombre | Para qué encaja |
|---|---|
| beAI Studio | Boutique, foco en cuidado al cliente |
| beAI Forge | Construir sistemas sólidos |
| beAI Lab | Experimentación + producción |
| beAI Works | Posicionamiento utilitario |
| beAI Craft | Artesanía, código a mano |
| beAI Stack | Audiencia más técnica (no encaja para este pitch) |
| beAI Pilot | Acompañamiento + handoff |
| beAI Foundry | Industrial, escala |
| beAI Spark | Joven, startups |
| beAI Pulse | Dashboards/analytics-first |

Mi recomendación para audiencia empresarial:
- **beAI Studio** (transmite cuidado, boutique, profesional sin
  intimidar). Es el mejor balance.
- **beAI Forge** (transmite solidez, "te construimos algo
  durable").
- **beAI Craft** (transmite artesanía, "te lo hacemos a mano").

`beAI Stack`, `beAI Lab` y `beAI Spark` son mejores para audiencia
técnica — para este sitio no.

**Verificación obligatoria antes de elegir uno**:

1. **Dominio**: `.com`, `.io`, `.dev`, `.studio` libres. Buscar en
   Namecheap o Porkbun.
2. **GitHub org**: libre.
3. **LinkedIn page**: registrable.
4. **Google "beai <nombre>"**: sin colisión con empresa existente.
5. **Marca registrada**: DINAPI (Paraguay) e INPI (Argentina) clase 42.
6. **Pronunciable en español**: probar en voz alta. Si tu mamá no lo
   puede repetir después de oírlo 2 veces, descartar.

---

## Inputs que el agente debe pedirte antes de empezar

### Para el sitio en general

1. Logo (SVG idealmente).
2. Confirmación del nombre elegido (de la lista al final).
3. URL de Calendly/Cal.com (o WhatsApp directo si no usás calendario).
4. Email de contacto + WhatsApp del responsable de leads.
5. **Permiso explícito de AUTO OFERTAS** para citarlos por nombre.
   Sin permiso, decir "una concesionaria multi-sucursal en Asunción".
6. Quote autorizada del dueño (opcional, solo si conseguís uno real).
7. Capturas del sistema con datos ofuscados — confirmación de que
   están listas para hacer públicas.

### Para el formulario y CRM

8. **¿Qué storage para los leads?**
   - Airtable (más rápido, gratis hasta 1000 registros).
   - Supabase Postgres + mini-CRM propio (más profesional, mostrás
     que comés tu propio dogfood).
   - Google Sheets (solo si estás validando muy temprano).

9. **API keys para configurar** (el agente las setea en `.env.example`,
   no las commitea; las recibe vos por canal seguro o las cargás vos
   en Vercel/Netlify):
   - Airtable API key + base ID + table name, **o**
   - Supabase URL + anon key + service role key.
   - Resend / Postmark API key (para email transaccional al lead).
   - Slack webhook URL **o** Discord webhook **o** Telegram bot token
     + chat_id (para notificar al equipo).

10. **Alias de email para los leads nuevos** (ej:
    `nuevoslead@beai.studio`). Cuándo tengas el dominio definitivo,
    configurar SPF/DKIM antes del primer envío para que no caiga en
    spam.

11. **Plantilla del email automático al lead** — el agente puede
    proponer una primera versión, pero conviene que la pulas vos
    antes del primer envío. Debe sentirse personal, no automatizada.

12. **Quién es el responsable de cuenta** que firma el email
    automático (nombre real, foto opcional). El lead se siente
    mejor cuando ve "Te respondo yo, Sebastián" que "El equipo de
    beAI Studio".

---

## Anexo — diferencias respecto a la versión anterior

Si compararas esta versión con una anterior orientada a developers:

| Antes (devs) | Ahora (empresas) |
|---|---|
| "Combinamos desarrolladores senior con AI agents" | "Diseñamos y construimos el sistema que tu empresa necesita" |
| "Stack tecnológico" visible como sección | El stack está oculto, no le importa al lector |
| Dark mode default, estética Linear/Vercel | Light mode, estética Holded/TiendaNube |
| "Sin vendor lock-in", "AI augmentation" | "El código es tuyo", "Te dejamos ver mientras trabajamos" |
| CTAs: "Agendar llamada", "Ver caso" | CTAs: "Pedí una reunión de diagnóstico gratis" |
| Precios en USD desde USD 6.000 | Precios en Gs/USD post-diagnóstico, sin chocar al lector |
| FAQ: "¿Y si el dev desaparece?" (tono dev) | FAQ: "¿Qué pasa cuando ustedes desaparezcan?" (tono dueño) |
| Mostrar logos de tech: Django, FastAPI, etc. | NO mostrar logos de tech. Mostrar capturas del sistema. |
