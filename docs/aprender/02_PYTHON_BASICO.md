# 🐍 Python básico — lo mínimo para arrancar

> Este archivo no reemplaza un curso de Python. Es un **repaso rápido
> de lo que necesitás** para leer y modificar código de este proyecto.
>
> Si nunca programaste, hacé el curso de https://www.py4e.com/ (curso
> gratuito en español, 5-6 horas) ANTES de seguir con este archivo.

---

## Cómo probar código Python

Abrí terminal y tipeá:
```cmd
python
```

Se abre un modo interactivo (verás `>>>`). Ahí podés escribir código y
ver el resultado enseguida:
```python
>>> 2 + 3
5
>>> print("Hola")
Hola
```

Para salir: `exit()` o `Ctrl+Z` + Enter.

Otra forma: crear un archivo `prueba.py`, escribir código, correr:
```cmd
python prueba.py
```

---

## 1. Variables y tipos

```python
# Números
edad = 25              # entero (int)
altura = 1.75          # decimal (float)
precio = 1_500_000     # los _ son separadores visuales, se ignoran

# Texto (string)
nombre = "Juan"
mensaje = 'Hola mundo'   # comillas simples o dobles, da igual

# Booleano
activo = True
oculto = False

# Nada / vacío
resultado = None
```

Ver el tipo de una variable:
```python
>>> type(edad)
<class 'int'>
>>> type(nombre)
<class 'str'>
```

---

## 2. Operaciones básicas

```python
# Aritmética
1 + 2      # 3
10 - 3     # 7
4 * 5      # 20
10 / 3     # 3.333...
10 // 3    # 3        (división entera)
10 % 3     # 1        (resto)
2 ** 8     # 256      (potencia)

# Comparaciones (devuelven True/False)
5 > 3      # True
5 == 3     # False
5 != 3     # True     (!= es "distinto")
"abc" == "abc"    # True

# Lógica
True and False    # False
True or False     # True
not True          # False
```

---

## 3. Strings (texto)

```python
nombre = "Juan"
apellido = "Pérez"

# Concatenar
completo = nombre + " " + apellido    # "Juan Pérez"

# Con f-string (moderno y recomendado)
edad = 25
saludo = f"Hola, soy {nombre} y tengo {edad} años"
# "Hola, soy Juan y tengo 25 años"

# Métodos útiles
nombre.upper()       # "JUAN"
nombre.lower()       # "juan"
nombre.replace("J", "K")   # "Kuan"
"  hola  ".strip()   # "hola"     (quita espacios)
len("abcde")         # 5
"abc" in "xabcy"     # True       (contiene?)
```

---

## 4. Listas

Una colección ordenada de cosas.

```python
frutas = ["manzana", "banana", "naranja"]

# Acceder por posición (empieza en 0)
frutas[0]      # "manzana"
frutas[1]      # "banana"
frutas[-1]     # "naranja"   (último)

# Modificar
frutas[0] = "pera"

# Agregar
frutas.append("uva")            # al final
frutas.insert(0, "kiwi")        # en posición 0

# Quitar
frutas.remove("banana")         # por valor
del frutas[0]                   # por posición

# Longitud
len(frutas)

# Recorrer
for fruta in frutas:
    print(fruta)
```

---

## 5. Diccionarios

Colección de clave-valor.

```python
cliente = {
    "nombre": "Juan",
    "edad": 25,
    "activo": True,
}

# Acceder
cliente["nombre"]        # "Juan"
cliente.get("email")     # None (si no existe, no falla)

# Agregar / modificar
cliente["email"] = "juan@example.com"
cliente["edad"] = 26

# Quitar
del cliente["activo"]

# Recorrer
for clave, valor in cliente.items():
    print(f"{clave}: {valor}")
```

---

## 6. Control de flujo — if / else

```python
edad = 20

if edad >= 18:
    print("Mayor de edad")
elif edad >= 13:
    print("Adolescente")
else:
    print("Menor")
```

⚠ **Súper importante**: Python usa **indentación** (espacios al inicio
de línea) para agrupar código. Todo lo que está indentado dentro del
`if:` corre solo si el `if` es True. **Usá siempre 4 espacios**.

```python
# CORRECTO
if edad >= 18:
    print("Adulto")
    print("Puede votar")

# MAL — falta indentación
if edad >= 18:
print("Adulto")   # error!
```

---

## 7. Loops — for y while

```python
# for con una lista
for numero in [1, 2, 3, 4, 5]:
    print(numero)

# for con range (0 al 9)
for i in range(10):
    print(i)

# for con range(inicio, fin, paso)
for i in range(1, 11, 2):    # 1, 3, 5, 7, 9
    print(i)

# while (mientras)
contador = 0
while contador < 5:
    print(contador)
    contador += 1    # equivale a contador = contador + 1
```

**Palabras clave dentro de loops**:
- `break` — sale del loop inmediatamente
- `continue` — salta a la siguiente iteración

---

## 8. Funciones

```python
def saludar(nombre):
    """Saluda a alguien por nombre."""
    return f"Hola, {nombre}"


# Llamar
mensaje = saludar("Juan")
print(mensaje)      # "Hola, Juan"


# Con múltiples parámetros y default
def calcular_precio(base, descuento=0):
    return base - descuento

calcular_precio(1000)              # 1000
calcular_precio(1000, 100)         # 900
calcular_precio(1000, descuento=200)   # 800  (nombrado)
```

**Regla**: las funciones **hacen una cosa y devuelven un valor**. Si
tenés una función que hace 3 cosas distintas, probablemente conviene
dividirla en 3 funciones.

---

## 9. Imports

Python organiza el código en módulos (archivos .py). Para usar cosas
de otro archivo:

```python
# Importar un módulo entero
import math
math.sqrt(16)      # 4.0

# Importar cosas específicas
from math import sqrt, pi
sqrt(16)           # 4.0
pi                 # 3.14159...

# Con alias (renombrar)
import pandas as pd
```

En este proyecto vas a ver mucho:
```python
from core.models import Customer, Sale, Quotum
from django.db.models import Q, Sum
```

---

## 10. Manejo de errores

```python
try:
    numero = int(input("Escribí un número: "))
    resultado = 10 / numero
    print(resultado)
except ValueError:
    print("Eso no es un número")
except ZeroDivisionError:
    print("No podés dividir por cero")
except Exception as e:
    print(f"Otro error: {e}")
```

`try` intenta correr el código. Si tira error, ejecuta el `except`
que matchee.

---

## 11. Clases (bases)

Una clase es como un molde para crear objetos.

```python
class Perro:
    def __init__(self, nombre, edad):
        """Se ejecuta cuando creamos un Perro nuevo."""
        self.nombre = nombre
        self.edad = edad

    def ladrar(self):
        return f"{self.nombre} dice ¡Guau!"


# Crear objetos (instancias)
firulais = Perro("Firulais", 3)
laika = Perro("Laika", 5)

print(firulais.nombre)         # "Firulais"
print(firulais.ladrar())       # "Firulais dice ¡Guau!"
```

**En este proyecto** las clases son **modelos de Django**. Por ejemplo:

```python
class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    document_number = models.CharField(max_length=50)
```

Eso define una tabla en la BD llamada `core_customer` con 3 columnas.
Ver detalles en `03_DJANGO_INTRO.md`.

---

## 12. Cosas de Python que vas a ver mucho en el proyecto

### List comprehensions (comprensiones de lista)
Forma compacta de crear listas:
```python
# Con for tradicional
numeros = []
for i in range(10):
    numeros.append(i * 2)

# Con comprensión (equivalente)
numeros = [i * 2 for i in range(10)]
```

### Comprensiones con filtro
```python
# Solo pares
pares = [i for i in range(20) if i % 2 == 0]
# [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
```

### f-strings con formato
```python
precio = 1500000
f"Gs. {precio:,}"        # "Gs. 1,500,000"
f"Gs. {precio:,}".replace(",", ".")   # "Gs. 1.500.000"

fecha = "2026-07-04"
f"Hoy es {fecha}"
```

### Decoradores
Son las líneas que empiezan con `@`:
```python
@action(detail=False, methods=['get'])
def cuotas_del_mes(self, request):
    ...
```

Por ahora **no te preocupes en entenderlos** — Django los usa mucho,
vos solo los copiás cuando hacen falta.

---

## Ejercicios (hacelos!)

Crear un archivo `ejercicios.py` en tu escritorio y escribí:

### Ejercicio 1
```python
# Pedir 2 números al usuario y mostrar la suma
a = int(input("Primer número: "))
b = int(input("Segundo número: "))
print(f"La suma es {a + b}")
```

### Ejercicio 2
```python
# Dada una lista de precios, calcular el total
precios = [1500, 2300, 4500, 800, 12000]

total = 0
for p in precios:
    total += p
print(f"Total: {total}")
```

### Ejercicio 3
```python
# De una lista de clientes con edades, mostrar solo los mayores de 18
clientes = [
    {"nombre": "Ana", "edad": 25},
    {"nombre": "Luis", "edad": 16},
    {"nombre": "Carlos", "edad": 30},
    {"nombre": "Sofía", "edad": 14},
]

adultos = [c for c in clientes if c["edad"] >= 18]
for c in adultos:
    print(c["nombre"])
```

Si los 3 te salen: pasás Python básico.

---

## Recursos para profundizar

Si sentís que necesitás más:
- **Curso gratuito en español**: https://www.py4e.com/ (Programming for Everybody, U. Michigan, subtitulado)
- **Python.org tutorial**: https://docs.python.org/3/tutorial/index.html (inglés)
- **YouTube**: canal "Python en Español" (Fernando Herrera)

---

## Próximo paso

Cuando puedas leer y escribir estos ejercicios sin ayuda: pasá a
`03_DJANGO_INTRO.md`.
