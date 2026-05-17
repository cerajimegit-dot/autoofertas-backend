# Metaprompt — Landing de beAI Studio

Este metaprompt está diseñado para entregárselo a un agente de codigo (Claude
Code, Cursor, v0, Bolt) que va a construir el sitio web de la consultora.
Tomá el caso AUTO OFERTAS como ejemplo concreto de capacidades; no inventes
métricas — las que están abajo son reales.

---

## Contexto del negocio

**beAI Studio** (nombre tentativo — ver propuestas en la sección final) es una
consultora de software a medida que combina **trabajo de desarrollador senior
con AI augmentation** para entregar sistemas internos completos a PyMEs y
empresas medianas que hoy operan con planillas Excel/ODS.

Diferencial: en vez de vender módulos enlatados (tipo SAP, Bind, Holded),
hacemos un **sistema a la medida del flujo real** del cliente, integrando
con sus archivos, idioma local, y forma de trabajo. Una persona entrega
un sistema completo en **3-6 semanas**, donde una agencia tradicional
necesitaría 6 meses y 3 personas.

**Mercado primario**: Paraguay, Argentina, Uruguay — PyMEs familiares de 5-30
empleados que crecieron a fuerza de Excel y necesitan ordenarse antes de
seguir creciendo.

---

## Especificaciones del sitio

### Stack y entorno

- **Framework**: Astro (preferido por velocidad de carga + SEO) o Next.js 15
  (si necesitás más interactividad en el dashboard de muestra). No usar
  Create React App.
- **Estilo**: Tailwind CSS v3. Sin librerías de componentes pesadas tipo
  Material UI o Ant Design. Si querés primitivas, usá shadcn/ui o Radix.
- **Animaciones**: framer-motion para transiciones; sutiles, no recargado.
  Reveals on scroll OK; carruseles infinitos no.
- **Tipografía**: una sans serif moderna — Inter para body, Cal Sans o
  similar para titulares grandes.
- **Imágenes/screenshots**: optimizar con `@astrojs/image` o `next/image`,
  formatos WebP/AVIF.
- **Hosting**: estático en Vercel/Netlify/Cloudflare Pages.
- **Idioma principal**: español rioplatense (PY/AR). Inglés opcional
  toggleable solo si la empresa apunta a clientes internacionales.

### Estilo visual

Moderno pero serio — apuntá a la estética de [linear.app](https://linear.app),
[railway.com](https://railway.com), [vercel.com](https://vercel.com).

- **Modo oscuro por default**, light toggleable. El target son devs y
  dueños técnicamente curiosos; el dark moderno transmite "sabemos lo
  que hacemos".
- **Paleta**: gris muy oscuro (zinc-950) de fondo, acentos en un color
  vibrante. Sugerencia: un cyan/turquesa (#06b6d4) o un violeta (#8b5cf6)
  como signature. **NO uses el rojo de AUTO OFERTAS** — ese es del cliente,
  no de beAI.
- **Glassmorphism sutil**: cards con `backdrop-blur` + borde de 1px en
  gradient. NO acetatos pastel ni Bootstrap por favor.
- **Gradients animados** en el hero (canvas o conic-gradient + animation),
  pero sin distraer del CTA.
- **Spacing generoso**: secciones de 120-160px de alto en desktop. La
  página tiene que respirar.
- **Code blocks**: monospace (JetBrains Mono o Geist Mono), con syntax
  highlighting. Mostrar ejemplos reales del trabajo.

### Estructura de la página

Una sola página larga (single-page landing) con anclas de navegación.
Secciones obligatorias en este orden:

#### 1. Hero (above the fold)

- Headline corto y directo. Ejemplo a iterar:
  > **"Software a medida para empresas que crecieron con Excel."**

  o más punzante:
  > **"Te entregamos el sistema interno que un SaaS no puede."**

- Subhead de 1-2 líneas:
  > "Combinamos desarrolladores senior con AI agents para construir el
  > backend, la app y el deploy. De Excel a producción en 3-6 semanas."

- 2 CTAs:
  - Primary: "Agendar una llamada" → Calendly link.
  - Secondary: "Ver caso AUTO OFERTAS" → ancla #caso-auto-ofertas.

- Visual del hero: NO un mockup genérico de laptop con dashboard.
  Mejor: una composición animada que muestre el **handoff de Excel → app
  web** (split screen, columna izq con planilla pixelada/desenfocada,
  columna der con dashboard nítido).

#### 2. Cómo trabajamos (proceso en 4-5 pasos)

Cada paso una card con icono simple (Lucide), título, 1 párrafo de 2-3
líneas. Pasos sugeridos:

1. **Diagnóstico (1 semana)** — Te ayudamos a entender cómo trabajás
   hoy. Auditoría de tus planillas, entrevistas con las 3-5 personas
   que las usan, mapa de procesos.
2. **Prototipo navegable (1 semana)** — Maqueta funcional de las 5
   pantallas clave. La aprobás antes de empezar a codear.
3. **Construcción (2-4 semanas)** — Backend + frontend + integraciones.
   Demo cada viernes. Acceso a un staging URL desde el día 5.
4. **Migración de datos** — Importamos tus planillas históricas al
   nuevo sistema. Sin pérdida, con auditoría de inconsistencias.
5. **Lanzamiento + acompañamiento (1 mes)** — Deploy a producción,
   capacitación a usuarios, ajustes finos. Después seguimos disponibles
   por hora o por suscripción.

#### 3. Caso de estudio — AUTO OFERTAS (#caso-auto-ofertas)

**Esta es la sección más importante del sitio.** Construila como una
mini case-study a la altura de los que publica Linear o Stripe.

Información concreta a usar (datos reales del proyecto):

- **Cliente**: AUTO OFERTAS — concesionaria familiar paraguaya, 2 sucursales
  (CASA CENTRAL en Asunción + SUCURSAL 1 en interior).
- **Vehículos manejados**: autos usados importados de Japón (Toyota Vitz,
  Ractis, Sienta, Auris, Hyundai Tucson, Kia Sportage).
- **Volumen**: ~80 ventas/año, 297 clientes, 1.500+ cuotas activas.
- **Estado antes**: 142 planillas ODS/Excel, una por venta, con 86 archivos
  cargados a mano por mes. Cuando un cliente preguntaba por su saldo,
  el dueño tenía que abrir su planilla específica.

**Métricas reales que podés citar** (todas verificables):

| Antes | Después |
|---|---|
| 14 segundos cargar lista de ventas | 0.9 segundos |
| 86 archivos ODS sueltos por mes | 1 dashboard con filtros |
| Cuotas vencidas: 62 visibles, 970 ocultas en otro estado | 979 unificadas con cálculo dinámico |
| 25+ vehículos "disponibles" en stock que ya estaban vendidos | 0 inconsistencias (sync automático Sale ↔ Vehicle) |
| 99 archivos con datos del negocio que se iban a subir a GitHub sin querer | 0 — auditado y bloqueado antes del primer push |
| Sin rate limit en login | 5 intentos/min por IP + JWT blacklist |
| 0 tests automatizados | 91 tests pasando |

**Funcionalidades entregadas** (lista corta para mostrar amplitud):

- Multi-tenant real (la empresa cliente puede vender el sistema a otra
  concesionaria sin reescribir).
- Auto-sync entre estado de venta y estado del vehículo.
- Vista de cliente con historial completo (reemplaza la "hoja del Excel").
- Flujo de caja con ingresos auto-generados + egresos manuales,
  importador desde el ODS existente.
- WhatsApp con mensaje pre-armado y teléfono normalizado.
- Panel de inconsistencias en tiempo real (datos sospechosos detectados
  automáticamente).
- Rate limiting, HTTPS, cookies seguras — listo para producción.

**Time-to-launch**: ~5 semanas de un solo desarrollador.

**Stack del caso** (mostrar como detalle "para los técnicos curiosos"):

- Backend: Django 5.1 + DRF + Supabase Postgres (transaction pooler en
  São Paulo).
- Frontend: React 18 sin build step (Babel standalone + Tailwind CDN).
  Decisión deliberada para que el cliente pueda editar la UI sin
  reinstalar npm.
- Hosting: Render (free tier para empezar, paid cuando justifique).
- 91 tests con pytest + SQLite in-memory.

**Visual de la case study**: 2-3 screenshots del dashboard real (con
datos ofuscados o demo), un block con la métrica más impactante (la de
14s → 0.9s), y un quote del dueño si conseguís uno.

#### 4. Servicios concretos

3 cards de "qué hacemos" con precios indicativos. Sin tarifas exactas
(las negocia ventas), pero rangos para filtrar contactos:

- **Sistema interno completo** — desde USD 6.000.
  Ejemplo: AUTO OFERTAS. Backend + frontend + migración + deploy + 1 mes
  de acompañamiento.

- **Auditoría de UX/arquitectura** — desde USD 800.
  Llegamos a tu sistema actual, hacemos auditoría como la que hicimos
  para AUTO OFERTAS (linkear al documento UX_AUDIT.md público). Entregamos
  un PDF con 30+ hallazgos priorizados.

- **Continuidad mensual** — desde USD 1.500/mes.
  Para clientes con sistema funcionando que necesitan features nuevas,
  bug fixes, monitoreo y mejoras continuas.

#### 5. Stack tecnológico (sección breve)

Un bloque de iconos/logos: Django, FastAPI, React, Next.js, Astro,
PostgreSQL, Supabase, Render, Vercel, AWS, Tailwind, TypeScript.

Subhead: "Elegimos la herramienta correcta para tu proyecto, no la
que está de moda."

#### 6. Equipo (opcional, solo si tenés foto profesional)

1-2 fotos en blanco y negro, nombre + 1 línea de bio. Estilo
[craft.co/about](https://craft.co/about).

#### 7. FAQ

5-7 preguntas. Las que importan al cliente PyME:

- "¿Qué pasa si el desarrollador desaparece?" (respuesta: todo el código
  queda en TU GitHub, no hay vendor lock-in, podés contratar a cualquier
  otro dev senior).
- "¿Y si necesito agregar una feature después del lanzamiento?" (respuesta:
  plan de continuidad).
- "¿Cómo cobran?" (50% al inicio + 50% al deploy, o mensual fijo
  durante el proyecto).
- "¿Migran mis datos viejos?" (sí, es parte del paquete; mostramos cómo
  AUTO OFERTAS arrancó con 427 ventas históricas).
- "¿Trabajan con clientes fuera de Paraguay?" (sí, AR/UY/CL).
- "¿Por qué dicen 'AI augmentation' y no 'AI-built'?" (porque el código
  lo escribe AI pero **un humano senior decide y revisa**. AI sin
  supervisión hace tonterías; con supervisión multiplica velocidad).

#### 8. Footer + CTA final

- Repetir el CTA primario (agendar llamada).
- Email de contacto.
- Links a redes (LinkedIn, GitHub público con repos demo).
- Disclaimer de privacidad básico.

### Lo que NO querés en el sitio

- **Slider de logos de "clientes felices"** que nadie reconoce (es ruido).
- **Testimonios genéricos** ("excelente trabajo, muy recomendado").
  Si tenés un testimonio real con permiso, ponelo; si no, mejor nada.
- **Sección "Por qué elegirnos"** con check marks vagos ("calidad",
  "compromiso", "innovación"). El caso AUTO OFERTAS reemplaza eso.
- **Chatbot o widget de Intercom**. Para una agencia chica, contraproducente.
- **Comparison table contra otras agencias**. Te pone a la defensiva.
- **Stock photos** de gente "trabajando en equipo". Si necesitás imágenes,
  usá ilustraciones abstractas o el dashboard real.

### Performance y SEO

- **Lighthouse score > 95** en mobile y desktop. Es la primera impresión
  para clientes técnicos.
- **First Contentful Paint < 1.5s** sobre 4G simulado.
- **Largest Contentful Paint < 2.5s**.
- Imágenes en WebP/AVIF con fallback.
- Fuentes con `font-display: swap` y subset latino.
- Meta tags + OpenGraph + Twitter Cards completos.
- Schema.org JSON-LD: `Organization` + `Service`.
- Sitemap.xml + robots.txt.
- HTTPS obligatorio.

### Métricas a trackear

Sin instalar 10 SDKs distintos. Mínimo:

- **Plausible** o **Umami** (privacy-friendly, sin cookies de consent).
- Eventos clave: click en CTA primario, scroll a sección "Caso AUTO
  OFERTAS", expansion de FAQ, click en email.

NO Google Analytics 4 a menos que el cliente lo pida explícitamente.

### Copy y tono

- **Conciso**: ningún párrafo de más de 4 líneas en desktop.
- **Concreto**: nunca decir "soluciones innovadoras", "transformación
  digital", "experiencia 360". Si el copy podría aparecer en LinkedIn,
  está mal.
- **Voseo paraguayo cuando aplique** ("te entregamos", "pedinos",
  "agendá"). No "ustedes" salvo en footer formal.
- **Honestidad sobre lo que NO somos**:
  > "No somos una agencia de 50 personas. Somos un equipo chico que
  > escribe código con ayuda de AI. Por eso somos rápidos y caros por
  > hora; baratos por proyecto."

### Accesibilidad

- WCAG 2.1 AA mínimo.
- Contraste verificable con Stark.
- Navegación por teclado completa.
- `aria-labels` en botones con solo iconos.
- `prefers-reduced-motion` respetado (las animaciones se desactivan).

---

## Deliverable esperado

El agente que reciba este metaprompt debe generar:

1. Un repositorio nuevo con la estructura del proyecto (`package.json`,
   `astro.config.mjs` o `next.config.js`, `tailwind.config.js`,
   `tsconfig.json`).
2. La página completa en una sola ruta (`/`).
3. Componentes separados por sección (`Hero`, `Process`, `CaseStudyAutoOfertas`,
   `Services`, `Stack`, `FAQ`, `Footer`).
4. Datos en archivos `.ts`/`.json` editables (la lista de servicios, FAQ,
   pasos del proceso) — NO hardcodeados en JSX para que la copy se cambie
   sin tocar componentes.
5. README breve con:
   - Cómo correr local (`npm install`, `npm run dev`).
   - Cómo deployar (instrucciones de Vercel o Netlify).
   - Cómo editar el copy sin tocar código.
6. Imágenes/iconos en `/public/` con nombres descriptivos.
7. NO commitear `.env`, secrets, ni archivos del negocio del cliente.
8. Tests mínimos: ningún componente, pero sí
   `npm run build` debe pasar sin warnings.

## Cómo NO querés que sea el deliverable

- Una plantilla genérica de Tailwind UI reutilizada (se nota).
- Componentes con 30 props que nadie va a tocar.
- Una single-page-app de 2 MB cuando 200 KB alcanzan.
- Lighthouse score < 90.
- Inglés cuando el target es español PY/AR.

---

## Propuestas de nombre con siglas "beAI"

Las que ya hablamos. Recordatorio:

| Nombre | Para qué encaja |
|---|---|
| beAI Studio | Boutique, foco en UX/diseño |
| beAI Forge | Construir sistemas sólidos para empresas |
| beAI Lab | Experimentación + producción |
| beAI Works | Posicionamiento utilitario |
| beAI Craft | Artesanía, código a mano |
| beAI Stack | Para audiencia técnica |
| beAI Pilot | Acompañamiento + handoff |
| beAI Foundry | Industrial, escala |
| beAI Spark | Joven, startups |
| beAI Pulse | Dashboards/analytics-first |

**Verificación obligatoria antes de elegir uno**:

1. **Dominio**: `.com`, `.io`, `.dev`, `.studio` disponibles. Buscar en
   namecheap o porkbun. Si los 4 están tomados, probar siguiente nombre.
2. **GitHub org**: que esté libre `github.com/beai-<nombre>`.
3. **LinkedIn page**: que se pueda registrar la company.
4. **Buscar "beai <nombre>"** en Google. Si aparece otra empresa
   existente con ese nombre exacto, descartar (riesgo de confusión).
5. **Marca registrada**: en Paraguay (DINAPI) y Argentina (INPI), buscar
   si ya está registrada en la clase 42 (servicios de software).
6. **Pronunciación en español**: "beAI Studio" se dice "be-ay studio" o
   "bei studio"? Probar en voz alta. Si suena raro, descartar.

Mi recomendación si vas con presupuesto chico: **beAI Studio**. Es
clara, profesional, internacional, y deja la puerta abierta a crecer
sin re-branding.

---

## Inputs adicionales que el agente debe pedirte antes de empezar

Si no se los das vos en el primer mensaje:

1. Logo (SVG idealmente) o brief de diseño.
2. Foto de team (si la sección §6 va).
3. URL de Calendly o calendario para el CTA.
4. Email de contacto.
5. Confirmación del nombre elegido (de la lista de arriba).
6. Permiso explícito de AUTO OFERTAS para citarlos por nombre en el
   case study (si no, decir "una concesionaria multi-sucursal en
   Asunción").
7. Foto del propietario o quote autorizado (solo si va).
