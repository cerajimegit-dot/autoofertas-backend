# 📚 Empezá acá — plan de aprendizaje

> Sos estudiante y no tenés experiencia todavía. Perfecto.
> Esta carpeta tiene una guía paso a paso para que en 2-3 semanas
> puedas hacer aportes reales al proyecto.
>
> No trates de leer todo de una — cada archivo te dice cuándo pasar al
> siguiente.

---

## Cómo usar esta guía

Los archivos están numerados. Andá **en orden**.

Cada uno:
- Es corto (~15-20 min de lectura)
- Tiene ejemplos concretos del proyecto (no genéricos)
- Termina con "próximo paso" claro

Si te trabás en uno, **NO saltees al siguiente**. Anotá la duda en
`docs/decisiones_pendientes.md` y pedime ayuda.

---

## El plan

| # | Archivo | Qué vas a aprender | Tiempo |
|---|---|---|---|
| **01** | `01_HERRAMIENTAS.md` | VS Code + terminal + Git básico | 1 hora |
| **02** | `02_PYTHON_BASICO.md` | Variables, listas, funciones, ifs | 3 horas |
| **03** | `03_DJANGO_INTRO.md` | Qué es Django y cómo lo usamos | 2 horas |
| **04** | `04_REACT_INTRO.md` | Componentes y JSX | 2 horas |
| **05** | `05_GIT_WORKFLOW.md` | Cómo trabajamos con Git en el proyecto | 1 hora |
| **06** | `06_ESTRUCTURA_PROYECTO.md` | Recorrido guiado por las carpetas | 1 hora |
| **07** | `07_RECURSOS_EXTERNOS.md` | Cursos, libros, docs para profundizar | referencia |

**Total**: ~10 horas de estudio antes de arrancar con la primera tarea.

---

## Bonus — ChatGPT como asistente

Si vas a usar ChatGPT (versión gratis) para consultarle dudas, leé
antes **`CHATGPT_METAPROMPT.md`**. Tiene un texto para pegar al inicio
de cada conversación que le da contexto de tu setup y evita que te
sugiera cosas peligrosas (como conectar a Postgres).

También te da tips de cómo hacer buenas preguntas y qué respuestas
no aceptar.

---

## Después de terminar

Cuando termines el archivo 07:
1. Volvé a `docs/JR_TASKS.md`
2. Empezá con **T1.3** (botón "volver arriba" — es de 1 hora)
3. Cuando termines, hacé PR y avísame

---

## Reglas importantes

1. **Preguntar es bueno**. Preferí preguntar 5 veces al día que quedarte
   trabado sin decir nada.
2. **Anotar todo**. Cada duda, cada aprendizaje, cada decisión.
3. **No romper prod**. Todo se prueba local con SQLite. Nunca corras
   scripts con `DB_ENGINE=postgres` sin permiso explícito del senior.
4. **Commit chico y frecuente**. Cada cambio que "funciona" es un
   commit — no esperes a terminar todo para commitear.

---

## Herramientas que vas a instalar

Antes de arrancar con `01_HERRAMIENTAS.md`, prepará:

- **Windows 10 u 11** (o Mac/Linux, funciona igual con ajustes menores)
- **Google Chrome** o **Edge** (para el frontend)
- Cuenta de **GitHub** con acceso al repo (te lo doy)
- 2-3 GB libres en disco
- Buena conexión a internet (algunos pasos descargan cosas)

---

## FAQ rápido

**"¿Puedo usar Windows?"**
Sí. Todos los ejemplos son en Windows (CMD/PowerShell).

**"¿Necesito saber inglés?"**
Un poco. Las docs oficiales de Python/Django están en inglés, pero yo
te preparé todo en español acá.

**"¿Voy a tocar plata real?"**
No. Trabajás con datos ficticios generados con Faker (nombres inventados,
montos random). Nunca ves clientes reales de la empresa.

**"¿Cuánto tiempo lleva llegar a hacer una tarea?"**
Con la guía completa: ~1 semana. Sin la guía, meses. Por eso está esto.

**"¿Puedo hacer todo desde el celular?"**
No, necesitás PC. Programar en el celular es imposible.

---

## Próximo paso

Abrí **`01_HERRAMIENTAS.md`** y seguí.

---

*Última actualización: 2026-07-04.*
