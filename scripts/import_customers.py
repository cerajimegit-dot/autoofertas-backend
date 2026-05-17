"""
Script para importar clientes desde archivo Excel
Uso: python scripts/import_customers.py <file.xlsx> <enterprise_id>
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

import openpyxl
from core.models import Customer, Enterprise


def import_customers(file_path, enterprise_id):
    """Importar clientes desde archivo Excel"""
    
    try:
        enterprise = Enterprise.objects.get(id=enterprise_id)
    except Enterprise.DoesNotExist:
        print(f"❌ Error: Empresa no encontrada (ID: {enterprise_id})")
        return
    
    # Cargar workbook
    try:
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
    except Exception as e:
        print(f"❌ Error al abrir archivo: {e}")
        return
    
    success = 0
    errors = 0
    
    print(f"\n👥 Importando clientes desde: {file_path}")
    print(f"   Empresa: {enterprise.name}")
    print("-" * 80)
    
    # Iterar filas (saltar header)
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=False), start=2):
        try:
            values = [cell.value for cell in row]
            
            # Mapear valores
            nombre = values[0]
            apellido = values[1]
            tipo_doc = values[2] or 'ci'
            numero_doc = values[3]
            email = values[4] or ''
            telefono = values[5] or ''
            direccion = values[6] or ''
            ciudad = values[7] or ''
            notas = values[8] or ''
            
            # Validaciones
            if not all([nombre, apellido, numero_doc]):
                raise ValueError("Falta datos requeridos (nombre, apellido, número documento)")
            
            # Validar que no exista cliente duplicado
            if Customer.objects.filter(
                enterprise=enterprise,
                document_number=numero_doc
            ).exists():
                raise ValueError(f"Cliente con número {numero_doc} ya existe")
            
            # Crear cliente
            customer = Customer.objects.create(
                enterprise=enterprise,
                first_name=nombre,
                last_name=apellido,
                document_type=tipo_doc,
                document_number=numero_doc,
                email=email,
                phone=telefono,
                address=direccion,
                city=ciudad,
                notes=notas
            )
            
            print(f"   ✓ Cliente creado: {nombre} {apellido} ({numero_doc})")
            success += 1
            
        except Exception as e:
            errors += 1
            print(f"   ✗ Fila {row_idx}: {str(e)}")
    
    print("-" * 80)
    print(f"✅ Importación completada: {success} clientes creados, {errors} errores")
    print()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python import_customers.py <archivo.xlsx> <enterprise_id>")
        print("Ejemplo: python import_customers.py sample_customers.xlsx 1")
        sys.exit(1)
    
    file_path = sys.argv[1]
    enterprise_id = int(sys.argv[2])
    
    import_customers(file_path, enterprise_id)
