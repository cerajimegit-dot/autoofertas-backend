# 📖 Recursos externos para seguir aprendiendo

> Terminaste los archivos 00-06. Ahora tenés lo mínimo para arrancar
> con las tareas. Este archivo son **recursos para seguir aprendiendo
> por tu cuenta** cuando quieras profundizar.

---

## Python

### Cursos gratuitos en español
- **Programming for Everybody (Coursera / Universidad de Michigan)**
  https://www.py4e.com/
  El más recomendado para empezar. Subtitulado en español.

- **CS50P (Harvard)**
  https://cs50.harvard.edu/python/
  Curso muy bueno, más profundo. Requiere inglés.

- **YouTube — "Python en Español" con Fernando Herrera**
  Buenos videos de temas específicos.

### Libros
- **Automate the Boring Stuff with Python** (Al Sweigart)
  Gratis online: https://automatetheboringstuff.com/
  Muy práctico, aprende resolviendo problemas reales.

- **Python Crash Course** (Eric Matthes)
  Para arrancar de cero. Hay traducción al español.

### Playgrounds
- https://replit.com/ — probar Python online sin instalar
- https://www.pythontutor.com/ — visualizador de código paso a paso

---

## Django

### Cursos gratuitos
- **Django Girls Tutorial (español)**
  https://tutorial.djangogirls.org/es/
  El más recomendado para empezar. 4-6 horas.

- **Django for Everybody (Coursera)**
  https://www.dj4e.com/
  Del mismo autor que py4e.

### Documentación oficial
- https://docs.djangoproject.com/en/5.0/
  En inglés. Muy bien escrita, referencia obligatoria.

- **Tutorial oficial** (parte del sitio anterior):
  https://docs.djangoproject.com/en/5.0/intro/tutorial01/
  6 partes. Vas a construir un mini-sistema.

### YouTube
- **Coding for Entrepreneurs** (Justin Mitchel) — proyectos con Django
- **CodingWithMitch** — más avanzado

### Django REST Framework (para APIs)
- https://www.django-rest-framework.org/
  Docs oficiales. Tienen un tutorial guiado.

---

## React

### Cursos gratuitos
- **React docs oficiales** (en español)
  https://es.react.dev/
  Las nuevas docs son excelentes, con ejemplos interactivos.

- **YouTube — midudev**
  Muchos cursos completos de React en español.

- **YouTube — Fazt Code**
  Buenas explicaciones de temas específicos.

### Playgrounds
- https://codesandbox.io/ — probar React online
- https://stackblitz.com/ — otro playground

---

## JavaScript (fundamentos)

### Cursos
- **JavaScript.info** (en español)
  https://es.javascript.info/
  Curso muy completo y bien estructurado.

- **freeCodeCamp**
  https://www.freecodecamp.org/espanol/learn/
  Aprende con ejercicios prácticos.

---

## Git

### Cursos
- **Learn Git Branching** (gratis, interactivo)
  https://learngitbranching.js.org/?locale=es_AR
  El mejor recurso para entender branches visualmente.

- **Pro Git book** (gratis, en español)
  https://git-scm.com/book/es/v2

### Referencia rápida
- https://ohshitgit.com/es/ — "oh mierda, git" — soluciones a problemas comunes
- https://cheat-sheets.tips/git/ — cheatsheet

---

## Bases de datos y SQL

Aunque Django ORM te evita escribir SQL, entender SQL básico ayuda
mucho:

- **SQLBolt (en español a veces)**
  https://sqlbolt.com/
  Interactivo, 18 lecciones.

- **SQLZoo**
  https://sqlzoo.net/

---

## VS Code

- **Guía oficial de VS Code**
  https://code.visualstudio.com/docs

- **YouTube — "Setup de VS Code"** (varios canales)
  Buscá tutoriales de configuración con extensiones.

---

## Postman / Insomnia (probar APIs)

Herramientas para probar endpoints del backend sin usar el frontend:

- **Insomnia** (más simple): https://insomnia.rest/
- **Postman** (más popular): https://www.postman.com/

Muy útil para debuggear cuando un endpoint no anda.

---

## Cheatsheets útiles

Guardá estos links a mano:

- **Python built-in functions**: https://docs.python.org/3/library/functions.html
- **Django ORM queries**: https://docs.djangoproject.com/en/5.0/topics/db/queries/
- **DRF ViewSets**: https://www.django-rest-framework.org/api-guide/viewsets/
- **React hooks reference**: https://es.react.dev/reference/react/hooks
- **Tailwind CSS**: https://tailwindcss.com/docs

---

## Comunidad

Cuando te trabás y ya buscaste, podés preguntar:

- **Stack Overflow (en español)**
  https://es.stackoverflow.com/
  Preguntas técnicas específicas.

- **Reddit r/learnpython**
  https://www.reddit.com/r/learnpython/
  Comunidad de estudiantes de Python.

- **Discord**:
  - Python en Español
  - React en Español
  - Django en Español

Buscá "discord python español" en Google.

---

## Cómo estudiar bien

### Lo que funciona
- **Escribir código a mano**. No copiar y pegar. Ni siquiera de este doc.
- **Explicar en voz alta lo que estás haciendo** ("estoy creando una variable llamada X porque...")
- **Enseñar a otro**. Aunque no haya nadie, imaginate que le explicás
- **Descansos activos**: 45 min estudio + 10 min caminar

### Lo que NO funciona
- Videos de fondo mientras hacés otras cosas
- Copiar código sin escribirlo
- Estudiar 6 horas seguidas sin parar
- Rendirse al primer error (todos, absolutamente todos, tenemos errores)

---

## Ritmo sugerido

### Semana 1
- Terminar los archivos 00-06
- Ejercicios de Python básico
- Empezar T1.3 (botón volver arriba)

### Semana 2
- T1.1, T1.2, T1.4 (más tareas de UI)
- Empezar a leer código del proyecto (Dashboard.jsx, Sales.jsx)

### Semana 3
- Sprint 2 (T2.1 - T2.5)
- Curso Django Girls en paralelo

### Semana 4
- Sprint 3 (backend)
- Practicar Django ORM en shell

### Mes 2 en adelante
- Sprint 4-5
- Features más grandes

---

## Cuando te frustres

Es normal. Todos pasamos por eso. Cosas que te van a pasar:

- Un error que no entendés y buscás durante 2 horas
- Un cambio que hacés y "no toma efecto" (spoiler: la caché del browser)
- Un test que no pasa y "no debería fallar"
- Un componente que se re-renderiza infinito

Cuando eso pase:
1. Levantate de la silla
2. Salí a caminar 10 minutos
3. Volvé
4. Releé el error DESDE EL PRINCIPIO (no del final)
5. Si sigue sin salir, escaláme

En serio, tomarse un descanso resuelve el 60% de los bugs.

---

## Tu primera tarea

Ahora que tenés todo:

1. Andá a `docs/JR_TASKS.md`
2. Leé el enunciado de **T1.3** (botón "volver arriba")
3. Creá tu rama:
   ```cmd
   git checkout jr/onboarding
   git pull
   git checkout -b jr/T1.3-volver-arriba
   ```
4. Hacé el cambio
5. Commit + push
6. Abrí PR
7. Avisame

Suerte. Vas a poder.

---

*Fin de la guía inicial. Cualquier pregunta, escalá.*
