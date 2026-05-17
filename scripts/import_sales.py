"""
Script para importar ventas desde archivo Excel
Uso: python scripts/import_sales.py <file.xlsx> <enterprise_id>
"""

import os
import sys
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

import openpyxl
from decimal import Decimal
from django.contrib.auth import get_user_model
from core.models import (
    Sale, Customer, Vehicle, PaymentForm, Enterprise, Branch
)

User = get_user_model()


def import_sales(file_path, enterprise_id):
    """Importar ventas desde archivo Excel"""
    
    try:
        enterprise = Enterprise.objects.get(id=enterprise_id)
    except Enterprise.DoesNotExist:
        print(f"❌ Error: Empresa no encontrada (ID: {enterprise_id})")
        return
    
    # Obtener primer branch o crear genérico
    branch = enterprise.branches.first()
    if not branch:
        print("❌ Error: No hay sucursal en la empresa")
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
    
    print(f"\n💰 Importando ventas desde: {file_path}")
    print(f"   Empresa: {enterprise.name}")
    print(f"   Sucursal: {branch.name}")
    print("-" * 80)
    
    # Iterar filas
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=False), start=2):
        try:
            values = [cell.value for cell in row]
            
            # Mapear valores
            numero_venta = values[0]
            fecha_venta = values[1]
            cliente_nombre = values[2]
            numero_doc_cliente = values[3]
            vin = values[4]
            precio_unit = Decimal(str(values[5]))
            descuento = Decimal(str(values[6] or 0))
            precio_total = Decimal(str(values[7]))
            forma_pago_nombre = values[8]
            vendedor_username = values[9]
            notas = values[10] or ''
            
            # Validaciones
            if not all([numero_venta, vin, precio_unit, precio_total]):
                raise ValueError("Falta datos requeridos")
            
            # Obtener o crear cliente
            if not numero_doc_cliente or numero_doc_cliente == 'GENÉRICO':
                # Cliente genérico
                customer = Customer.objects.filter(
                    enterprise=enterprise,
                    is_generic=True
                ).first()
                
                if not customer:
                    customer = Customer.objects.create(
                        enterprise=enterprise,
                        first_name='Cliente',
                        last_name='Genérico',
                        document_number='0',
                        is_generic=True
                    )
            else:
                customer = Customer.objects.filter(
                    enterprise=enterprise,
                    document_number=numero_doc_cliente
                ).first()
                
                if not customer:
                    # Crear cliente
                    customer = Customer.objects.create(
                        enterprise=enterprise,
                        first_name=cliente_nombre.split()[0] if cliente_nombre else 'Cliente',
                        last_name=' '.join(cliente_nombre.split()[1:]) if cliente_nombre and len(cliente_nombre.split()) > 1 else 'Importado',
                        document_number=numero_doc_cliente
                    )
            
            # Obtener vehículo
            vehicle = Vehicle.objects.filter(vin=vin).first()
            if not vehicle:
                raise ValueError(f"Vehículo no encontrado (VIN: {vin})")
            
            # Obtener forma de pago
            payment_form = PaymentForm.objects.filter(
                enterprise=enterprise,
                name=forma_pago_nombre
            ).first()
            
            if not payment_form:
                # Crear forma de pago si no existe
                payment_form = PaymentForm.objects.create(
                    enterprise=enterprise,
                    name=forma_pago_nombre
                )
            
            # Obtener vendedor
            seller = User.objects.filter(username=vendedor_username).first()
            if not seller:
                seller = enterprise.users.filter(role='vendor').first()
            
            # Generar número de venta único si es necesario
            if Sale.objects.filter(sale_number=numero_venta).exists():
                numero_venta = f"{numero_venta}_{row_idx}"
            
            # Crear venta
            sale = Sale.objects.create(
                enterprise=enterprise,
                branch=branch,
                sale_number=numero_venta,
                sale_date=datetime.fromisoformat(str(fecha_venta)) if isinstance(fecha_venta, str) else datetime.now(),
                customer=customer,
                vehicle=vehicle,
                unit_price=precio_unit,
                discount=descuento,
                total_price=precio_total,
                payment_form=payment_form,
                seller=seller,
                status='completed',
                notes=notas
            )
            
            # Marcar vehículo como vendido
            vehicle.state = 'sold'
            vehicle.save()
            
            print(f"   ✓ Venta creada: {numero_venta} - {customer.full_name} - ${precio_total}")
            success += 1
            
        except Exception as e:
            errors += 1
            print(f"   ✗ Fila {row_idx}: {str(e)}")
    
    print("-" * 80)
    print(f"✅ Importación completada: {success} ventas creadas, {errors} errores")
    print()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python import_sales.py <archivo.xlsx> <enterprise_id>")
        print("Ejemplo: python import_sales.py sample_sales.xlsx 1")
        sys.exit(1)
    
    file_path = sys.argv[1]
    enterprise_id = int(sys.argv[2])
    
    import_sales(file_path, enterprise_id)
