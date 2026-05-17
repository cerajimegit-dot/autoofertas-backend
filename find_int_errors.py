import os
import re
import sys
from pathlib import Path

# Buscar patrones de conversión int() con números decimales

print("\n" + "="*80)
print("🔍 BUSCANDO ERRORES DE CONVERSIÓN int()")
print("="*80 + "\n")

project_root = Path(__file__).parent

# Patrones peligrosos
dangerous_patterns = [
    r'int\s*\(\s*[a-zA-Z_][a-zA-Z0-9_]*\s*(?:\.\w+)?\s*\)',  # int(variable) o int(variable.field)
    r'int\s*\(\s*["\']?\d+\.\d+["\']?\s*\)',  # int('100.00') or int(100.00)
]

found_issues = []

# Buscar en archivos Python
for py_file in project_root.rglob('*.py'):
    # Saltar migraciones y __pycache__
    if 'migrations' in str(py_file) or '__pycache__' in str(py_file):
        continue
    
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Buscar int( 
                if 'int(' in line and not line.strip().startswith('#'):
                    # Revisar contexto
                    if any(pattern in line for pattern in ['int(', 'int (']):
                        # Filtrar falsos positivos
                        if 'Integer' not in line and 'int_' not in line:
                            found_issues.append({
                                'file': str(py_file.relative_to(project_root)),
                                'line': line_num,
                                'content': line.strip()
                            })
    except Exception as e:
        pass

# Mostrar resultados
print(f"Se encontraron {len(found_issues)} potenciales conversiones int()\n")

if found_issues:
    print("📌 UBICACIONES CON int():")
    print("-" * 80)
    
    for issue in found_issues[:20]:  # Mostrar primeras 20
        print(f"\n{issue['file']}:{issue['line']}")
        print(f"  {issue['content']}")
else:
    print("✅ No se encontraron conversiones int() sospechosas en código Python")

print("\n" + "="*80)
print("💡 NOTA: El error 'invalid literal for int() with base 10' ocurre cuando")
print("intenta convertir una cadena con decimales a int() sin pasar por float():")
print("\n  ❌ INCORRECTO: int('100.00')  → ValueError")
print("  ✅ CORRECTO:  int(float('100.00'))  → 100")
print("="*80 + "\n")
