#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de migración de datos de stock.db a db.sqlite3 (Django)
Migra: Clientes, Ventas, Cuotas y relacionados
"""
import os
import sys
import django
import sqlite3
from datetime import datetime
import io

# Fijar codificación de salida
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import (
    Enterprise, Customer, Brand, VehicleModel, Vehicle, 
    PaymentForm, Sale, Quotum, Branch
)
from decimal import Decimal

# Configuración
OLD_DB = r'C:\Users\prueb\CascadeProjects\playa\stock.db'
AUTO_SALE_NUMBER_PREFIX = 'MIG'

def get_enterprise():
    """Obtener la empresa de destino"""
    ent = Enterprise.objects.first()
    if not ent:
        raise Exception("No hay empresa configurada en el sistema")
    return ent

def get_branch(enterprise):
    """Obtener o crear la sucursal por defecto"""
    branch, created = Branch.objects.get_or_create(
        enterprise=enterprise,
        defaults={'name': 'Sucursal Principal', 'location': 'Principal'}
    )
    return branch

def migrate_customers():
    """Migrar clientes de la base de datos antigua"""
    print("\n" + "=" * 60)
    print("MIGRANDO CLIENTES")
    print("=" * 60)
    
    enterprise = get_enterprise()
    old_conn = sqlite3.connect(OLD_DB)
    old_conn.row_factory = sqlite3.Row
    old_c = old_conn.cursor()
    
    try:
        # Obtener clientes de la BD antigua
        old_c.execute("SELECT id, nombre, apellido, numero_documento, telefono, direccion, fecha_nacimiento FROM cliente ORDER BY id")
        old_customers = old_c.fetchall()
        
        customer_map = {}  # Para mapear IDs antiguos a nuevos
        migrated = 0
        skipped = 0
        
        for old_cust in old_customers:
            try:
                # Validar datos mínimos
                if not old_cust['numero_documento']:
                    print(f"  SKIP: Cliente sin documento: {old_cust['nombre']} {old_cust['apellido']}")
                    skipped += 1
                    continue
                
                # Verificar que no exista ya
                if Customer.objects.filter(document_number=old_cust['numero_documento']).exists():
                    existing = Customer.objects.get(document_number=old_cust['numero_documento'])
                    customer_map[old_cust['id']] = existing.id
                    print(f"  EXISTE: {old_cust['nombre']} {old_cust['apellido']} ({old_cust['numero_documento']})")
                    continue
                
                # Crear cliente
                cust = Customer.objects.create(
                    enterprise=enterprise,
                    first_name=old_cust['nombre'][:100],
                    last_name=old_cust['apellido'][:100],
                    document_type='ci',
                    document_number=str(old_cust['numero_documento']),
                    phone=old_cust['telefono'] or '',
                    address=old_cust['direccion'] or '',
                    notes=f"Migrado de stock.db | Fecha nacimiento: {old_cust['fecha_nacimiento']}"
                )
                
                customer_map[old_cust['id']] = cust.id
                print(f"  OK: {cust.full_name} ({cust.document_number})")
                migrated += 1
                
            except Exception as e:
                print(f"  ERROR: {old_cust['nombre']} - {str(e)}")
                skipped += 1
        
        old_conn.close()
        
        print(f"\nRESULTADO: {migrated} clientes migrados, {skipped} omitidos")
        return customer_map
        
    except Exception as e:
        print(f"ERROR en migración de clientes: {e}")
        import traceback
        traceback.print_exc()
        return {}

def migrate_brands_and_models():
    """Verificar/Mapear marcas y modelos de la BD antigua"""
    print("\n" + "=" * 60)
    print("MAPEANDO MARCAS Y MODELOS")
    print("=" * 60)
    
    enterprise = get_enterprise()
    old_conn = sqlite3.connect(OLD_DB)
    old_conn.row_factory = sqlite3.Row
    old_c = old_conn.cursor()
    
    try:
        # Mapeo de marcas
        old_c.execute("SELECT id, nombre FROM marca ORDER BY id")
        old_brands = old_c.fetchall()
        
        brand_map = {}
        for old_brand in old_brands:
            # Buscar marca existente
            brand = Brand.objects.filter(
                enterprise=enterprise,
                name__iexact=old_brand['nombre']
            ).first()
            
            if brand:
                brand_map[old_brand['id']] = brand.id
                print(f"  MAPEO Marca: {old_brand['nombre']} -> BD nueva ID: {brand.id}")
            else:
                print(f"  ADVERTENCIA: Marca no encontrada en BD nueva: {old_brand['nombre']}")
        
        # Mapeo de modelos
        old_c.execute("SELECT id, nombre, marca_id FROM modelo ORDER BY id")
        old_models = old_c.fetchall()
        
        model_map = {}
        for old_model in old_models:
            brand_id = brand_map.get(old_model['marca_id'])
            if not brand_id:
                print(f"  SKIP Modelo: {old_model['nombre']} (marca no mapeada)")
                continue
            
            # Buscar modelo en BD nueva
            model_obj = VehicleModel.objects.filter(
                enterprise=enterprise,
                brand_id=brand_id,
                name__iexact=old_model['nombre']
            ).first()
            
            if model_obj:
                model_map[old_model['id']] = model_obj.id
                print(f"  MAPEO Modelo: {old_model['nombre']} → BD nueva ID: {model_obj.id}")
            else:
                print(f"  ADVERTENCIA: Modelo no encontrado: {old_model['nombre']}")
        
        old_conn.close()
        return brand_map, model_map
        
    except Exception as e:
        print(f"ERROR en mapeo de marcas/modelos: {e}")
        import traceback
        traceback.print_exc()
        return {}, {}

def migrate_vehicles():
    """Migrar vehículos (productos) de la BD antigua"""
    print("\n" + "=" * 60)
    print("MIGRANDO VEHÍCULOS")
    print("=" * 60)
    
    enterprise = get_enterprise()
    branch = get_branch(enterprise)
    
    # Obtener mapeos
    _, (brand_map, model_map) = (None, (None, None))
    
    old_conn = sqlite3.connect(OLD_DB)
    old_conn.row_factory = sqlite3.Row
    old_c = old_conn.cursor()
    
    # Obtener marcas y modelos
    old_c.execute("SELECT id, nombre FROM marca ORDER BY id")
    old_brands = {row['id']: row['nombre'] for row in old_c.fetchall()}
    
    old_c.execute("SELECT id, nombre, marca_id FROM modelo ORDER BY id")
    old_models = {row['id']: row for row in old_c.fetchall()}
    
    # Mapear
    brand_map = {}
    for old_id, name in old_brands.items():
        brand = Brand.objects.filter(enterprise=enterprise, name__iexact=name).first()
        if brand:
            brand_map[old_id] = brand.id
    
    model_map = {}
    for old_id, model_data in old_models.items():
        if model_data['marca_id'] in brand_map:
            model_obj = VehicleModel.objects.filter(
                enterprise=enterprise,
                brand_id=brand_map[model_data['marca_id']],
                name__iexact=model_data['nombre']
            ).first()
            if model_obj:
                model_map[old_id] = model_obj.id
    
    vehicle_map = {}
    migrated = 0
    skipped = 0
    
    try:
        # Obtener productos (vehículos)
        old_c.execute("""
            SELECT id, numero_chasis, marca_id, modelo_id, [año_fabricacion], color, precio_venta
            FROM producto
            ORDER BY id
        """)
        old_products = old_c.fetchall()
        
        for old_prod in old_products:
            try:
                # Validar datos
                if not old_prod['numero_chasis']:
                    print(f"  SKIP: Producto sin chasis")
                    skipped += 1
                    continue
                
                # Verificar que no exista VIN
                vin = str(old_prod['numero_chasis'])[:50]
                if Vehicle.objects.filter(vin=vin).exists():
                    existing = Vehicle.objects.get(vin=vin)
                    vehicle_map[old_prod['id']] = existing.id
                    skipped += 1
                    continue
                
                # Obtener marca y modelo
                brand_id = brand_map.get(old_prod['marca_id'])
                model_id = model_map.get(old_prod['modelo_id'])
                
                if not brand_id:
                    print(f"  SKIP: Vehículo sin marca mapeada: {vin}")
                    skipped += 1
                    continue
                
                # Crear vehículo
                vehicle = Vehicle.objects.create(
                    enterprise=enterprise,
                    branch=branch,
                    brand_id=brand_id,
                    model_id=model_id,
                    year=old_prod['año_fabricacion'] or 2000,
                    vin=vin,
                    color=old_prod['color'] or '',
                    price=Decimal(str(old_prod['precio_venta'])) if old_prod['precio_venta'] else Decimal('0'),
                    currency='PYG',
                    fob=Decimal(str(old_prod['precio_venta'])) if old_prod['precio_venta'] else Decimal('0'),
                    state='available'
                )
                
                vehicle_map[old_prod['id']] = vehicle.id
                print(f"  OK: VIN {vin} - {old_brands[old_prod['marca_id']]} (Precio: {old_prod['precio_venta']})")
                migrated += 1
                
            except Exception as e:
                print(f"  ERROR: Producto {old_prod.get('numero_chasis')} - {str(e)}")
                skipped += 1
        
        old_conn.close()
        print(f"\nRESULTADO: {migrated} vehículos migrados, {skipped} omitidos")
        return vehicle_map
        
    except Exception as e:
        print(f"ERROR en migración de vehículos: {e}")
        import traceback
        traceback.print_exc()
        return {}

def migrate_payment_forms():
    """Crear o mapear formas de pago"""
    print("\n" + "=" * 60)
    print("CONFIGURANDO FORMAS DE PAGO")
    print("=" * 60)
    
    enterprise = get_enterprise()
    
    payment_forms = ['credito', 'contado', 'mixto']
    payment_map = {}
    
    for form_name in payment_forms:
        pf, created = PaymentForm.objects.get_or_create(
            enterprise=enterprise,
            name__iexact=form_name,
            defaults={'name': form_name.upper(), 'is_active': True}
        )
        payment_map[form_name.lower()] = pf.id
        status = "CREADA" if created else "EXISTE"
        print(f"  {status}: {pf.name} (ID: {pf.id})")
    
    return payment_map

def migrate_sales(customer_map, vehicle_map, payment_map):
    """Migrar ventas"""
    print("\n" + "=" * 60)
    print("MIGRANDO VENTAS")
    print("=" * 60)
    
    enterprise = get_enterprise()
    old_conn = sqlite3.connect(OLD_DB)
    old_conn.row_factory = sqlite3.Row
    old_c = old_conn.cursor()
    
    sale_map = {}
    migrated = 0
    skipped = 0
    counter = 1
    
    try:
        old_c.execute("""
            SELECT id, codigo_interno, cliente_id, producto_id, fecha, tipo_pago, entrega_inicial, total
            FROM venta
            ORDER BY id
        """)
        old_sales = old_c.fetchall()
        
        for old_sale in old_sales:
            try:
                # Validar cliente y producto
                customer_id = customer_map.get(old_sale['cliente_id'])
                vehicle_id = vehicle_map.get(old_sale['producto_id'])
                
                if not customer_id or not vehicle_id:
                    print(f"  SKIP: Venta sin cliente ({customer_id}) o vehículo ({vehicle_id})")
                    skipped += 1
                    continue
                
                # Obtener forma de pago
                payment_type = (old_sale['tipo_pago'] or 'credito').lower()
                payment_form_id = payment_map.get(payment_type, payment_map.get('credito'))
                
                # Generar número de venta único
                sale_number = f"{AUTO_SALE_NUMBER_PREFIX}{counter:06d}"
                counter += 1
                
                # Crear venta
                sale = Sale.objects.create(
                    enterprise=enterprise,
                    sale_number=sale_number,
                    customer_id=customer_id,
                    vehicle_id=vehicle_id,
                    unit_price=Decimal(str(old_sale['total'])) if old_sale['total'] else Decimal('0'),
                    total_price=Decimal(str(old_sale['total'])) if old_sale['total'] else Decimal('0'),
                    payment_form_id=payment_form_id,
                    sale_date=old_sale['fecha'] or datetime.now(),
                    status='completed',
                    notes=f"Entrega inicial: {old_sale['entrega_inicial']} | Migrado de stock.db"
                )
                
                sale_map[old_sale['id']] = sale.id
                print(f"  OK: Venta #{sale_number} - {old_sale['total']} ({payment_type})")
                migrated += 1
                
            except Exception as e:
                print(f"  ERROR: Venta antigua #{old_sale.get('id')} - {str(e)}")
                skipped += 1
        
        old_conn.close()
        print(f"\nRESULTADO: {migrated} ventas migradas, {skipped} omitidas")
        return sale_map
        
    except Exception as e:
        print(f"ERROR en migración de ventas: {e}")
        import traceback
        traceback.print_exc()
        return {}

def migrate_quotas(sale_map):
    """Migrar cuotas"""
    print("\n" + "=" * 60)
    print("MIGRANDO CUOTAS")
    print("=" * 60)
    
    enterprise = get_enterprise()
    old_conn = sqlite3.connect(OLD_DB)
    old_conn.row_factory = sqlite3.Row
    old_c = old_conn.cursor()
    
    migrated = 0
    skipped = 0
    
    try:
        old_c.execute("""
            SELECT id, venta_id, importe, fecha_vencimiento, pagado, fecha_pago
            FROM cuota
            ORDER BY venta_id, id
        """)
        old_quotas = old_c.fetchall()
        
        # Agrupar por venta
        quotas_by_sale = {}
        for quota in old_quotas:
            sale_id = quota['venta_id']
            if sale_id not in quotas_by_sale:
                quotas_by_sale[sale_id] = []
            quotas_by_sale[sale_id].append(quota)
        
        # Migrar cuotas
        for old_sale_id, quotas in quotas_by_sale.items():
            new_sale_id = sale_map.get(old_sale_id)
            if not new_sale_id:
                print(f"  SKIP: Venta {old_sale_id} no encontrada en mapeo")
                skipped += len(quotas)
                continue
            
            # Obtener venta y cliente
            try:
                sale = Sale.objects.get(id=new_sale_id)
            except Sale.DoesNotExist:
                print(f"  SKIP: Venta con ID {new_sale_id} no existe")
                skipped += len(quotas)
                continue
            
            # Procesar cuotas de esta venta
            for quota_num, old_quota in enumerate(quotas, 1):
                try:
                    # Determinar estado
                    if old_quota['pagado']:
                        status = 'paid'
                    else:
                        status = 'pending'
                    
                    # Crear cuota
                    quotum = Quotum.objects.create(
                        enterprise=enterprise,
                        sale=sale,
                        customer=sale.customer,
                        quota_number=quota_num,
                        total_plan=len(quotas),
                        amount=Decimal(str(old_quota['importe'])) if old_quota['importe'] else Decimal('0'),
                        due_date=old_quota['fecha_vencimiento'].split(' ')[0] if old_quota['fecha_vencimiento'] else '2099-12-31',
                        payment_date=old_quota['fecha_pago'].split(' ')[0] if old_quota['fecha_pago'] else None,
                        status=status,
                        notes=f"Migrado de stock.db"
                    )
                    
                    print(f"  OK: Cuota #{quota_num}/{len(quotas)} - Venta #{sale.sale_number} - {old_quota['importe']} ({status})")
                    migrated += 1
                    
                except Exception as e:
                    print(f"  ERROR: Cuota venta {old_sale_id} - {str(e)}")
                    skipped += 1
        
        old_conn.close()
        print(f"\nRESULTADO: {migrated} cuotas migradas, {skipped} omitidas")
        return migrated
        
    except Exception as e:
        print(f"ERROR en migración de cuotas: {e}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    """Ejecutar migración completa"""
    print("\n" + "=" * 60)
    print("INICIANDO MIGRACIÓN DE DATOS")
    print("=" * 60)
    
    try:
        # 1. Migrar clientes
        customer_map = migrate_customers()
        
        # 2. Mapear marcas y modelos
        brand_map, model_map = migrate_brands_and_models()
        
        # 3. Migrar vehículos
        vehicle_map = migrate_vehicles()
        
        # 4. Configurar formas de pago
        payment_map = migrate_payment_forms()
        
        # 5. Migrar ventas
        sale_map = migrate_sales(customer_map, vehicle_map, payment_map)
        
        # 6. Migrar cuotas
        quota_count = migrate_quotas(sale_map)
        
        # Resumen final
        print("\n" + "=" * 60)
        print("RESUMEN DE MIGRACIÓN")
        print("=" * 60)
        print(f"\nClientes migrados: {len(customer_map)}")
        print(f"Vehículos migrados: {len(vehicle_map)}")
        print(f"Ventas migradas: {len(sale_map)}")
        print(f"Cuotas migradas: {quota_count}")
        print("\nMIGRACION COMPLETADA")
        
        return True
        
    except Exception as e:
        print(f"\nERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
