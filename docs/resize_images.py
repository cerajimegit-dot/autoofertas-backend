"""Redimensiona las screenshots del manual a un ancho óptimo para Word.

Las screenshots originales son de ~1500px de ancho. Word respeta el
tamaño nativo de las imágenes al abrir HTML; si la imagen es más ancha
que el área útil de A4 (~680-720px a 96dpi con márgenes 1.5cm), se
corta o desborda la página.

Resize target: 800px de ancho. Eso es:
  - Suficiente para leer texto pequeño dentro de las screenshots.
  - Apenas más ancho que el área útil A4 (Word lo escala mínimamente).
  - Tamaño de archivo aceptable (<200KB cada uno).

NO redimensiona si la imagen ya tiene 800px o menos.
"""

from pathlib import Path
from PIL import Image

TARGET_WIDTH = 800
DIR = Path(__file__).parent / 'imagenes'

if not DIR.exists():
    raise SystemExit(f'No existe {DIR}')

total = 0
for png in sorted(DIR.glob('*.png')):
    if 'morosos.png10-morosos.png' in png.name:
        # Archivo con nombre duplicado por accidente al guardar; lo saltamos.
        print(f'  SKIP (nombre raro): {png.name}')
        continue

    with Image.open(png) as img:
        w, h = img.size
        if w <= TARGET_WIDTH:
            print(f'  OK (ya pequeña {w}x{h}): {png.name}')
            continue
        new_h = round(h * TARGET_WIDTH / w)
        resized = img.resize((TARGET_WIDTH, new_h), Image.LANCZOS)
        # Sobrescribir el archivo original con la versión chica.
        # PNG con optimize=True para que pese menos.
        resized.save(png, 'PNG', optimize=True)
        print(f'  {w}x{h} -> {TARGET_WIDTH}x{new_h}: {png.name}')
        total += 1

print(f'\nResize completo. {total} imágenes redimensionadas.')
