# Plan de evolución — Sistema de gestión AUTO OFERTAS

Fecha: 2026-05-17
Estado base: sistema en producción (Render + Supabase São Paulo), 4 usuarios
reales, ~427 ventas, ~3.000 cuotas migradas. Primera versión funcional.

Este documento es un **roadmap de 6 etapas**, cada una con foco claro,
items priorizados por impacto/esfuerzo, métricas de éxito y los primeros
prompts que podés usar para arrancarla con Claude.

---

## 0. Norte de largo plazo

Antes del plan, definamos hacia dónde vamos:

**Decisión clave**: ¿este sistema es **sólo para AUTO OFERTAS**, o el
producto que se va a vender a otras concesionarias (multi-tenant real)?

| Escenario | Implicancia |
|---|---|
| **A. Solo AUTO OFERTAS** (cliente único) | Foco en automatizaciones que le ahorren tiempo al equipo. Cada feature es una decisión de costo/beneficio para 1 cliente. Más simple. |
| **B. Producto para vender** (multi-tenant) | Cada feature suma valor a la propuesta comercial. Tiene que ser configurable, documentado, brandeable. Más complejo pero mayor retorno. |

El sistema ya está armado para B (multi-tenant por `enterprise_id`), pero
todas las decisiones recientes asumieron A. **Te recomiendo decidir esto
antes de la Etapa 3** — algunas features cambian de diseño según el escenario.

---

## 1. Cómo aprovechar Claude al máximo (consejos prácticos)

### Workflow recomendado

1. **Una sesión = una tarea bien definida.** No "agregame varias cosas"
   sino "implementame el recordatorio de WhatsApp 3 días antes". Sesiones
   chicas, foco claro, resultado verificable.

2. **Empezá cada sesión con contexto crítico:**
   - "Estoy laburando en el feature X de la etapa Y del plan."
   - "Querés que lo planifique primero o vamos directo a implementar?"

3. **Usá `/loop` para tareas recurrentes:**
   - Revisión semanal de logs de errores en Render.
   - Chequeo de calidad de datos (corre el endpoint `/data_quality/`).
   - Verificación de tests pasando antes del viernes.

4. **Pedí siempre verificación contra producción** después de cada cambio
   destructivo (ej: migraciones, scripts de cleanup).

5. **Capitalizá lo que aprende Claude entre sesiones:**
   - Cuando una decisión se repite ("acá usamos Gs. no $"), pedile que
     la guarde como memoria persistente.
   - Skills custom del proyecto en `.claude/skills/` para convenciones
     específicas (ya hay una de UI, agregar más a medida).

### Lo que NO funciona bien

- **Sesiones gigantes con 15 tareas mezcladas.** Pierde contexto y
  empieza a olvidar lo que decidieron antes.
- **Pedirle features sin caso de uso.** "Agregá un dashboard nuevo" sin
  decirle quién lo usa y qué problema resuelve → entrega algo genérico.
- **No verificar después del cambio.** Si te dice "listo, 91 tests pasan",
  pegale igual `npm test` o `pytest` vos mismo. Confianza pero verificá.
- **Hacer la primera implementación con dueño/usuarios mirando.** Es para
  iterar. Después del primer test, recién mostrar.

---

## 2. Etapa 0 — Estabilización post-lanzamiento

**Cuándo:** semanas 1-2 desde que mati/marcelo/rocio entren al sistema.
**Foco:** no se cae el barco, recoger feedback, arreglar datos sucios.

### Items

| # | Tarea | Impacto | Esfuerzo | Por qué |
|---|---|---|---|---|
| 0.1 | Monitorear logs de Render diariamente | Alto | S | Detectar errores que el equipo no reporta |
| 0.2 | Corregir datos que el equipo encuentra mal | Alto | M | Es lo que les genera desconfianza si no se atiende |
| 0.3 | Documentar las decisiones que vayan saliendo | Medio | S | Quedan en un `feedback_*.md` para la próxima sesión |
| 0.4 | Backup semanal de Supabase con `pg_dump` a Google Drive | Alto | S | Free tier solo retiene 7 días; necesitás algo más largo |
| 0.5 | Cambiar contraseñas iniciales por una propia de cada usuario | Medio | S | `Vitz2026!` etc. son temporales |
| 0.6 | Confirmar permiso de AUTO OFERTAS para usar caso en beAI | Medio | S | Bloquea avance del sitio beAI Studio |

### Métricas de éxito

- 0 errores 500 sin explicar en los logs después de 7 días.
- ≥ 3 "ah, ahí está, gracias" del equipo por correcciones de datos.
- 1 backup semanal funcionando.

### Prompts para arrancar

```
Revisemos los logs de Render del backend de los últimos 7 días. Quiero
saber: cuántos 5xx hubo, qué endpoints los provocaron, y si hay algún
patrón. Acceso al dashboard de Render: [URL].
```

```
Mati me reportó que la venta CM27/26 dice "Sin cliente" pero él recuerda
que se la vendieron a Pedro González. Buscá esa venta + ese cliente en
la BD y ayudame a corregirla. Si Pedro no existe, lo creamos.
```

```
Armame un script que corra `pg_dump` semanal contra Supabase y suba el
.dump a una carpeta de Google Drive. Lo vamos a correr desde GitHub
Actions cada lunes. Costo objetivo: gratis o casi.
```

---

## 3. Etapa 1 — Automatizaciones inmediatas

**Cuándo:** semanas 3-6.
**Foco:** ahorrar tiempo concreto a rocio/papa/mati. Cada feature les
saca minutos del día.

### Items

| # | Tarea | Impacto | Esfuerzo | Tiempo ahorrado/semana |
|---|---|---|---|---|
| 1.1 | Recordatorios automáticos WhatsApp 3 días antes del vto | **Alto** | M | rocio: ~2 hs |
| 1.2 | PDF cronograma de cuotas para entregar al cliente al firmar | Alto | M | rocio: ~30 min por venta |
| 1.3 | Recibo PDF de pago de cuota (al marcar paid) | Medio | S | trazabilidad cliente |
| 1.4 | Export contable mensual CSV (para el contador externo) | **Alto** | S | papa: ~3 hs/mes |
| 1.5 | Cron diario de cotización USD/PYG (BCP scraper) | Bajo | S | desbloquea ventas USD futuras |
| 1.6 | Importador ODS de flujo de caja mensual | Medio | M | papa: ~2 hs/mes |
| 1.7 | Fotos del vehículo (URL field + adjunto) | Alto comercial | M | usar en WhatsApp y publicaciones |
| 1.8 | Adjuntos en ventas (cédula, comprobante de transferencia) | Medio | M | rocio: trazabilidad notarial |

### Métricas de éxito

- 1.1: rocio deja de avisar cuotas a mano → 0 cuotas vencidas sin aviso previo.
- 1.4: papa entrega CSV al contador sin armar nada → 100% de meses con export.
- 1.7: cada nueva venta tiene foto → 80%+ de cobertura en stock.

### Prompts para arrancar

```
Necesito un cron job que corra cada día a las 9hs y mande WhatsApp
automático a todos los clientes con cuotas que venzan en exactamente
3 días. El mensaje pre-armado (ya está en /quotas/N/contact_whatsapp/).
Lo voy a deployar en Render como cron job. Considerá:
- Sólo cuotas que sean "pending" y no vencidas todavía.
- No avisar a clientes sin teléfono.
- No avisar 2 veces a la misma cuota (registrar el envío en la BD).
- Que el cron sea fácil de pausar/reanudar.
Empezá con un plan de implementación y después lo armamos.
```

```
Cada vez que se cierra una venta con plan de cuotas, papa quiere
imprimir un PDF con el cronograma para darle al cliente.
- Diseño tipo recibo bancario: fila por cuota, monto, vencimiento.
- Encabezado con datos del cliente, vehículo, total, plan.
- Branding AUTO OFERTAS (logo arriba, dirección abajo).
- Botón "Descargar PDF" en el modal de Cuotas (Sales.jsx).
Stack: weasyprint o xhtml2pdf desde un template Django.
Implementalo end-to-end con un test.
```

```
Quiero que papa pueda descargar todos los movimientos de caja de un mes
(ingresos + egresos) en CSV con formato listo para entregar al contador.
- Endpoint `/api/cash-movements/export.csv?date_from=&date_to=`
- Columnas: fecha, descripción, tipo, monto, sucursal, USD original si
  aplica, TC, proveedor.
- En la UI de /flujo-caja un botón "📥 Exportar mes a CSV" que dispare
  la descarga con el período actual del filtro.
```

---

## 4. Etapa 2 — Inteligencia operativa

**Cuándo:** mes 2-3.
**Foco:** que el sistema le diga al dueño cosas que él tendría que
calcular a mano, y que lo deje tomar mejores decisiones.

### Items

| # | Tarea | Impacto | Esfuerzo |
|---|---|---|---|
| 2.1 | Sugerencias de precio al cargar vehículo (basado en histórico modelo+año) | Alto | M |
| 2.2 | Búsqueda fuzzy server-side con GIN trigram (clientes + vehículos) | Alto | M |
| 2.3 | Dashboard año vs año (ventas, cobranzas, márgenes) | Alto | M |
| 2.4 | Alertas por umbral (stock bajo, morosidad >X%, caja negativa) | Medio | M |
| 2.5 | Reporte mensual auto-enviado por email a papa | Alto | M |
| 2.6 | Vista por vendedor (cuántas ventas, monto, comisión calculada) | Alto | M |
| 2.7 | Mapa de calor de morosidad por barrio/ciudad | Medio | M |
| 2.8 | Detección de duplicados de cliente (mismo doc, distinto registro) | Medio | M |

### Métricas de éxito

- 2.1: precio sugerido aplicado en >50% de las cargas nuevas → muestra que es útil.
- 2.5: papa abre el mail mensual en >80% de los meses → señal de valor.
- 2.6: mati y marcelo se logean primero a ver sus ranking → engagement directo.

### Prompts para arrancar

```
Quiero que al cargar un vehículo nuevo (modal CrearVehículo en Sales.jsx),
abajo del campo "Precio" aparezca un sugerido: "Precio sugerido: Gs. X
(promedio de N ventas similares en los últimos 12 meses)".

Lógica:
- Filtrar ventas con brand+model+año coincidentes (±1 año).
- Excluir MIG, V0, VDUMMY.
- Sólo ventas completed.
- Mostrar promedio + rango (min/max).
- Si no hay datos suficientes (<3), no mostrar.

Endpoint `/api/vehicles/suggest_price/?brand=X&model=Y&year=Z`.
Frontend: llamar al endpoint cuando estén llenos brand+model+year.
```

```
Necesito un job mensual que el día 1 de cada mes le mande a papa un
email con un reporte gerencial: total ventas del mes anterior, total
cobrado, cartera vencida actual, top 5 morosos, ranking de vendedores,
margen estimado por vehículo, comparación contra el mismo mes año
anterior. PDF adjunto.
Diseñalo y armá un MVP que pueda probar con datos de febrero.
```

---

## 5. Etapa 3 — Chatbot y comunicación

**Cuándo:** mes 3-4.
**Foco:** automatizar la interacción con clientes (vivos + potenciales).
Acá es donde el negocio empieza a escalar sin contratar más gente.

### Items

| # | Tarea | Impacto | Esfuerzo |
|---|---|---|---|
| 3.1 | Chatbot WhatsApp para consultas de stock ("¿tienen vitz 2010?") | **Alto** | L |
| 3.2 | Bot que responde "¿cuánto debo?" a clientes con saldo | Alto | M |
| 3.3 | Sistema de comisiones automatizado por vendedor con dashboard propio | Alto | M |
| 3.4 | Calendario integrado de cobranzas (vista semanal) | Medio | M |
| 3.5 | Notificación interna al equipo cuando se carga una venta nueva | Medio | S |
| 3.6 | Recordatorios push (PWA) al celular del vendedor por cuotas próximas | Medio | M |
| 3.7 | Centro de mensajes pre-armados (objeciones frecuentes, condiciones) | Bajo | S |

### Métricas de éxito

- 3.1: >100 consultas/mes respondidas por el bot sin intervención → reduce carga del equipo.
- 3.2: clientes que preguntan saldo por WhatsApp obtienen respuesta en <1 min.
- 3.3: papa ve quién vende más sin abrir excel.

### Decisión técnica importante para 3.1

El chatbot WhatsApp tiene dos caminos:

| Opción | Costo mensual | Limitaciones |
|---|---|---|
| **WhatsApp Business API** (oficial vía Meta o reseller) | USD 30-100 según volumen | Plantillas pre-aprobadas, marca verificada, escalable |
| **whatsapp-web.js** (no oficial, browser headless) | Gratis | Frágil — se cae si WhatsApp actualiza protocolo, no escalable a 1000s msg |

Para AUTO OFERTAS empezar con la opción 1. La 2 sirve para validar
producto con beAI Studio (PyMEs chicas).

### Prompts para arrancar

```
Quiero diseñar un chatbot que se conecte a un número de WhatsApp Business
de AUTO OFERTAS y responda automáticamente a 3 preguntas frecuentes:
1. "¿Tienen [modelo/marca]?" → consulta el stock disponible y responde
   con los autos que matcheen + precio + foto + chasis.
2. "¿Cuánto debo?" → si el número del cliente está en la BD, responde
   con su saldo actual y la próxima cuota.
3. "¿Cuándo abren?" → respuesta estática.

Cualquier otra cosa → "Te derivamos a un humano" + ping a rocio.

Diseñame la arquitectura completa primero: cómo se conecta a WhatsApp
Business API (Meta), dónde corre (Render web service o aparte), cómo
recibe los webhooks de mensajes entrantes, dónde se guarda el estado
de la conversación. Después armamos un MVP.
```

---

## 6. Etapa 4 — Profesionalización

**Cuándo:** mes 4-6.
**Foco:** dejar el código en condiciones de que entre otro dev sin
romper nada, monitorear errores en prod, automatizar el deploy.

### Items

| # | Tarea | Impacto | Esfuerzo |
|---|---|---|---|
| 4.1 | Build real del frontend (Vite + TypeScript) | Alto técnico | L |
| 4.2 | CI con GitHub Actions: tests + check + lint al push | Alto | M |
| 4.3 | Sentry o Rollbar para errores en producción | Alto | S |
| 4.4 | Cobertura de tests >70% en los endpoints críticos | Alto | L |
| 4.5 | Capa `core/services/` con lógica de negocio reusable | Medio | M |
| 4.6 | 2FA con TOTP para admin y dueño | Alto seguridad | M |
| 4.7 | Mini-CRM en `/admin` para gestionar leads de beAI | Medio | M |
| 4.8 | Pre-commit hooks (black, isort, ruff) | Bajo | S |
| 4.9 | Documentación del API exportada de drf-spectacular a un sitio público | Bajo | S |
| 4.10 | Limpieza de raíz del repo (mover scripts viejos a `archive/`) | Bajo | S |

### Métricas de éxito

- 0 errores 5xx no reportados en Sentry por semana.
- Tests corren en CI y bloquean push si fallan.
- Build del frontend ≤ 200 KB inicial, FCP <1s en mobile.

### Prompts para arrancar

```
Vamos a migrar el frontend de Babel standalone + Tailwind CDN a Vite +
TypeScript + Tailwind compilado. El sistema sigue siendo exactamente el
mismo en funcionalidad — sólo cambia el build y el tooling.
Plan:
1. Inicializar proyecto Vite en una rama nueva.
2. Mover componente por componente, convertir JSX → TSX.
3. Tipos para todos los modelos del backend (Sale, Quotum, etc.).
4. Build estático que sirva en Render como static site (no más Python
   http.server).
5. Tests con Vitest + React Testing Library.

Empezá con un plan detallado de los pasos + el orden de migración para
que pueda hacerlo gradualmente sin romper producción.
```

```
Configurame Sentry en el backend Django. Quiero:
- Capturar todos los errores 5xx.
- Capturar `logger.exception(...)` del logger 'security' y 'perf'.
- Filtrar PII (no enviar emails ni teléfonos en el contexto).
- Sample rate 10% para transacciones, 100% para errores.
- DSN configurable por env var.
Free tier de Sentry alcanza para 5k events/mes.
```

---

## 7. Etapa 5 — Escala y monetización

**Cuándo:** mes 6 en adelante (sólo si el norte es "vender el producto").
**Foco:** convertir el sistema en algo replicable para otras concesionarias
o PyMEs latinoamericanas.

### Items

| # | Tarea | Impacto | Esfuerzo |
|---|---|---|---|
| 5.1 | Sistema de onboarding self-service (registro + setup automático) | Alto comercial | L |
| 5.2 | Personalización por tenant (logo, paleta, plantillas) | Alto comercial | L |
| 5.3 | Billing automatizado con Stripe (suscripciones mensuales) | Alto | M |
| 5.4 | Facturación electrónica Paraguay (FE) vía proveedor (Faktur, etc.) | Alto regulatorio | L |
| 5.5 | App nativa móvil (React Native o Capacitor wrapper de la PWA) | Medio | L |
| 5.6 | Integración con bancos (boletas de pago, links Bancard) | Alto regional | L |
| 5.7 | Predicción de mora con ML (modelo simple, scikit-learn) | Medio | M |
| 5.8 | Marketplace de plugins (cada cliente activa los módulos que necesita) | Alto largo plazo | L |
| 5.9 | Soporte multi-moneda nativo (PYG + USD + ARS + UYU) | Medio | M |

### Métricas de éxito

- 5.1: tiempo de onboarding de un cliente nuevo de "1 semana de trabajo" a "1 hora autoservicio".
- 5.3: revenue mensual recurrente >USD 2.000.
- 5.4: cumplimiento legal en Paraguay sin intervención manual.

---

## 8. Cronograma sugerido (visual)

```
Mes 1   ──┬── Etapa 0 (estabilización) ────────────────┐
          └── arrancan paralelas algunas de Etapa 1     │
                                                        │
Mes 2-3 ──┬── Etapa 1 (automatizaciones) ──────────────┤
          └── arranca Etapa 2 (intel) en paralelo       │
                                                        │
Mes 3-4 ──┬── Etapa 2 (intel operativa) ───────────────┤
          └── Decidir norte: AUTO OFERTAS vs producto   │
                                                        │
Mes 4-5 ──┬── Etapa 3 (chatbot/comunicación) ──────────┤
          └── Etapa 4 (profesionalización) en paralelo  │
                                                        │
Mes 5-6 ──┬── Etapa 4 termina ─────────────────────────┤
          └── Si norte = producto: arranca Etapa 5      │
                                                        │
Mes 6+  ──── Etapa 5 (escala y monetización) ─────────┘
```

---

## 9. Anti-patterns (cosas que NO hacer)

- **Saltar a Etapa 3 (chatbot) antes de completar Etapa 1.** Sin
  automatizaciones básicas, el chatbot termina escalando problemas
  manuales al cuádruple de volumen.
- **Hacer todo al mismo tiempo.** Cada etapa tiene 5-10 items. Si
  arrancás 30 en paralelo nada termina.
- **Implementar features que nadie pidió.** Antes de cada feature
  preguntate: ¿quién del equipo me lo dijo? ¿qué problema concreto
  resuelve? Si no podés contestar, esperá hasta tener el dato.
- **Optimizar antes de medir.** No "hacer más rápido el dashboard" si
  no sabés cuánto tarda hoy. Mediar primero, optimizar después.
- **Cambiar de stack a mitad de etapa.** Si decidiste Astro, terminá
  Astro. Si decidiste no usar Redis, no lo metas porque "está de moda".

---

## 10. Cómo medir el progreso

Cada lunes, una sesión corta con Claude pidiendo:

```
Revisamos el progreso de la semana en el sistema AUTO OFERTAS:
- ¿Qué items del plan de evolución se completaron?
- ¿Qué métricas mejoraron (errores, performance, engagement)?
- ¿Hay items bloqueados? ¿Por qué?
- ¿Qué prioridad para esta semana?

Acceso a:
- Plan: playa/docs/PLAN_EVOLUCION.md
- Logs de Render: [URL]
- Tests: pytest output local
```

Eso te da un ritmo semanal sin que tengas que llevar la cuenta mental.

---

## 11. Resumen ejecutivo

| Etapa | Mes | Foco | Items |
|---|---|---|---|
| **0** | 1 | Estabilizar lanzamiento | 6 |
| **1** | 2-3 | Automatizaciones inmediatas | 8 |
| **2** | 3-4 | Inteligencia operativa | 8 |
| **3** | 4-5 | Chatbot y comunicación | 7 |
| **4** | 5-6 | Profesionalización técnica | 10 |
| **5** | 6+ | Escala y monetización | 9 |

**Total**: 48 features, 6 meses, en bloques de ~8 items cada uno.
Cada item lleva entre 2-10 hs de sesión con Claude.

**Si trabajás 2 sesiones por semana** (~6 hs), podés cubrir las primeras
4 etapas en ~5 meses. Las etapas 3 y 4 se solapan parcialmente porque
una toca código y la otra toca producto.

---

## Notas finales

- **Este documento es una guía, no un contrato.** Si después de la
  Etapa 1 te das cuenta de que la realidad pide otra cosa, **cambialo**.
  Documentos vivos sirven; documentos estáticos pesan.
- **Cada item debería tener un caso de uso real antes de implementarse.**
  Si nadie lo va a usar, no se hace.
- **El sistema actual ya funciona.** No te ofusques optimizándolo. Lo
  importante es que mati/marcelo/rocio lo adopten — todo lo demás se
  construye encima.
