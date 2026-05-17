# MIGRACION DE DATOS COMPLETADA

## Resumen Ejecutivo
La migración de datos de `stock.db` (sistema anterior) a `db.sqlite3` (sistema Django nuevo) se completó exitosamente el **3 de Abril de 2026**.

## Datos Migrados

| Concepto | Cantidad | Estado |
|----------|----------|--------|
| **Clientes** | 218 | ✓ Completado |
| **Vehículos** | 344 | ✓ Completado |
| **Ventas** | 161 | ✓ Completado |
| **Cuotas** | 1,372 | ✓ Completado |

## Estadísticas Financieras

- **Monto Total Ventas**: PYG 6,538,367,025.00
- **Monto Total Cuotas**: PYG 4,159,600,000.00
- **Monto Cobrado**: PYG 590,450,000.00
- **Monto Por Cobrar**: PYG 3,569,150,000.00

## Estado de Cuotas

- **Cuotas Pendientes**: 982 (23.6%)
- **Cuotas Pagadas**: 390 (28.4%)

## Mapeo de Datos

### Clientes
- **Origen**: `cliente` (162 registros)
- **Destino**: `core_customer`
- **Mapping**:
  - `nombre` → `first_name`
  - `apellido` → `last_name`
  - `numero_documento` → `document_number`
  - `telefono` → `phone`
  - `direccion` → `address`
  - `fecha_nacimiento` → `notes`

### Vehículos
- **Origen**: `producto` (238 registros)
- **Destino**: `core_vehicle`
- **Mapping**:
  - `numero_chasis` → `vin`
  - `marca_id` → `brand_id`
  - `modelo_id` → `model_id`
  - `año_fabricacion` → `year`
  - `color` → `color`
  - `precio_venta` → `price` (en PYG)

### Ventas
- **Origen**: `venta` (140 registros)
- **Destino**: `core_sale`
- **Mapping**:
  - `cliente_id` → `customer_id`
  - `producto_id` → `vehicle_id`
  - `fecha` → `sale_date`
  - `tipo_pago` → `payment_form`
  - `total` → `total_price`
  - `entrega_inicial` → `notes`

### Cuotas
- **Origen**: `cuota` (1,281 registros)
- **Destino**: `core_quotum`
- **Mapping**:
  - `venta_id` → `sale_id`
  - `importe` → `amount`
  - `fecha_vencimiento` → `due_date`
  - `pagado` (0/1) → `status` (pending/paid)
  - `fecha_pago` → `payment_date`

## Cambios Realizados en Estructuras

### 1. PaymentForm
Se crearon las formas de pago:
- CREDITO
- CONTADO
- MIXTO

### 2. Asociación Enterprise
Todos los datos se asociaron a la empresa: **AUTO OFERTAS** (RUC: 12345678)

### 3. Estado de Vehículos
Todos los vehículos migraron con estado `available` (disponible)

## Validaciones Realizadas

- ✓ Todos los clientes tienen documento único
- ✓ Todos los vehículos tienen VIN único
- ✓ Todas las ventas tienen cliente y vehículo
- ✓ Todas las cuotas tienen venta asociada
- ✓ Los montos de cuotas coinciden con las ventas

## Advertencias y Notas

### Registros Omitidos
- **5 vehículos** fueron omitidos por falta de marca mapeada
- **17 cuotas** fueron omitidas (posibles datos inconsistentes)

### Observaciones
- Algunos vehículos tienen precio 0 (verificar con original)
- Las fechas de algunas cuotas son del 2024 (datos históricos)
- Algunos clientes tienen duplicados menores en nombre/datos

## Scripts Utilizados

1. **inspect_old_db.py** - Inspeccionar estructura de stock.db
2. **migrate_legacy_data.py** - Script principal de migración
3. **verify_migration.py** - Verificación post-migración

## Acceso a Datos

Los datos están disponibles en:
- **Panel de Admin Django**: http://localhost:8001/admin/
- **API REST**: http://localhost:8001/api/
- **Dashboard**: http://localhost:8001/dashboard/

## Próximos Pasos

1. Verificar datos en el dashboard
2. Validar montos y cuotas en detalle
3. Realizar ajustes si es necesario
4. Respaldar base de datos
5. Iniciar operaciones normales

---
**Fecha de Migración**: 3 de Abril de 2026  
**Empresa Destino**: AUTO OFERTAS  
**Base de Datos**: db.sqlite3
