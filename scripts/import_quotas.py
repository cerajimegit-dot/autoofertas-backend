"""
Script para importar cuotas desde archivo Excel
Uso: python scripts/import_quotas.py <file.xlsx> <enterprise_id>
"""

import os
import sys
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

import openpyxl
from decimal import Decimal
from core.models import Quotum, Sale, Customer, Enterprise


def import_quotas(file_path, enterprise_id):
    """Importar cuotas desde archivo Excel"""
    
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
    
    print(f"\n📋 Importando cuotas desde: {file_path}")
    print(f"   Empresa: {enterprise.name}")
    print("-" * 80)
    
    # Iterar filas
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=False), start=2):
        try:
            values = [cell.value for cell in row]
            
            # Mapear valores
            numero_venta = values[0]
            cliente_nombre = values[1]
            numero_doc_cliente = values[2]
            numero_cuota = values[3]
            plan = values[4]
            total_cuotas = values[5]
            monto_cuota = Decimal(str(values[6]))
            interes = Decimal(str(values[7] or 0))
            fecha_vencimiento = values[8]
            notas = values[9] or ''
            
            # Validaciones
            if not all([numero_venta, numero_cuota, monto_cuota, fecha_vencimiento]):
                raise ValueError("Falta datos requeridos")
            
            # Obtener venta
            sale = Sale.objects.filter(
                enterprise=enterprise,
                sale_number=numero_venta
            ).first()
            
            if not sale:
                raise ValueError(f"Venta no encontrada ({numero_venta})")
            
            # Obtener cliente
            if not numero_doc_cliente or numero_doc_cliente == 'GENÉRICO':
                customer = sale.customer
            else:
                customer = Customer.objects.filter(
                    enterprise=enterprise,
                    document_number=numero_doc_cliente
                ).first()
                
                if not customer:
                    customer = sale.customer
            
            # Convertir fecha si es needed
            if isinstance(fecha_vencimiento, str):
                try:
                    fecha_vencimiento = datetime.strptime(fecha_vencimiento, '%Y-%m-%d').date()
                except:
                    raise ValueError(f"Formato de fecha inválido: {fecha_vencimiento}")
            else:
                fecha_vencimiento = fecha_vencimiento
            
            # Crear cuota
            quotum = Quotum.objects.create(
                enterprise=enterprise,
                sale=sale,
                customer=customer,
                quota_number=numero_cuota,
                plan_name=plan,
                total_plan=total_cuotas,
                amount=monto_cuota,
                interest=interes,
                due_date=fecha_vencimiento,
                status='pending',
                notes=notas
            )
            
            print(f"   ✓ Cuota creada: #{numero_cuota} - Venta {numero_venta} - ${monto_cuota}")
            success += 1
            
        except Exception as e:
            errors += 1
            print(f"   ✗ Fila {row_idx}: {str(e)}")
    
    print("-" * 80)
    print(f"✅ Importación completada: {success} cuotas creadas, {errors} errores")
    print()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python import_quotas.py <archivo.xlsx> <enterprise_id>")
        print("Ejemplo: python import_quotas.py sample_quotas.xlsx 1")
        sys.exit(1)
    
    file_path = sys.argv[1]
    enterprise_id = int(sys.argv[2])
    
    import_quotas(file_path, enterprise_id)
