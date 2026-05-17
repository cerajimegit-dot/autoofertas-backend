# Arquitectura de Migracion de Cuotas - Playa de Autos

## Diagnostico de los Datos Fuente

### Estructura encontrada en los 55 archivos ODS

Todos los archivos siguen una estructura identica:

| Fila | Contenido | Ejemplo |
|------|-----------|---------|
| 0 | Nombre completo del cliente | `NICOLAS ACOSTA FLEITAS` |
| 1 | Telefono | `CEL. 0972993146.-` |
| 2 | Vehiculo + Chassis | `VITZ 1.3CC 2005 CHAS: SCP90-0014064` |
| 3 | Headers | `VTO / DOC / MONTO / FECHA / FORMA` |
| 4..N | Cuotas | Datos de cada cuota |
| N+1 | DEUDA TOTAL | Saldo pendiente |
| N+2 | Codigo CM | `CM86/24` (referencia interna de venta) |
| N+3 | ENTREGA | Monto de entrega inicial |
| N+4 | SALDO info | Cantidad de cuotas y monto por cuota |
| N+5 | VENTA TOTAL | Precio total de la operacion |
| N+6+ | Garante (opcional) | Nombre y telefono del garante |

### Datos clave descubiertos

- **Headers 100% consistentes** en los 55 archivos: `VTO, DOC, MONTO, FECHA, FORMA`
- **54 de 55 archivos** tienen numero de chassis
- **53 de 55 archivos** tienen codigo CM (los 2 sin CM son ventas antiguas: Sportage y Tucson 2006)
- **Nombre del archivo** contiene: `{NumVenta}-{Vehiculo} {Anio} {Cliente}.ods`
- **Valores de FORMA**: EF (Efectivo), TB (Transferencia Bancaria), CJ (Caja), A/C (A Cuenta), TB SILV (Transferencia Silvio), VENCIDO (cuota impaga)
- **Formatos de MONTO**: Mixtos - algunos como `2.000.000.-` y otros como `2400000` (numerico puro)
- **Rango de cuotas**: 4 a 40 cuotas por venta

### Campos de vinculacion disponibles (ordenados por confiabilidad)

| Campo | Fuente ODS | Campo en BD | Confiabilidad |
|-------|-----------|-------------|---------------|
| Codigo CM | Seccion resumen (`CM86/24`) | `Sale.sale_number` | ALTA - identificador unico |
| Chassis | Fila 2 (`CHAS: 046161`) | `Vehicle.vin` | ALTA - unico por vehiculo |
| Nro. de venta del filename | Filename (`132-VITZ...`) | `Sale.sale_number` | MEDIA - puede no coincidir |
| Nombre del cliente | Fila 0 | `Customer.first_name + last_name` | BAJA - variaciones |
| Vehiculo + Anio | Fila 2 + filename | `Vehicle.model + year` | MEDIA - complementario |

---

## 1. Estrategia de Vinculacion (Matching)

### Algoritmo de Matching en 3 Niveles

```
NIVEL 1 - Match Exacto (automatico, sin intervencion):
  1. Buscar por codigo CM → Sale.sale_number
  2. Si no hay CM, buscar por chassis → Vehicle.vin → Sale.vehicle
  
  Si match unico → VINCULAR AUTOMATICAMENTE

NIVEL 2 - Match Heuristico (scoring):
  Si Nivel 1 no encuentra match unico:
  - Fuzzy match sobre nombre del cliente (peso: 40%)
  - Match vehiculo+anio (peso: 30%)
  - Proximidad de fecha de primera cuota vs fecha de venta (peso: 20%)
  - Match de monto total (peso: 10%)
  
  Score >= 85% → SUGERIR como match probable
  Score 60-84% → MOSTRAR como candidato, requiere confirmacion
  Score < 60% → MARCAR como "sin match" → crear venta nueva

NIVEL 3 - Modo Asistido (intervencion del desarrollador):
  - Mostrar los candidatos con su score
  - Permitir seleccion manual
  - Opcion de "Crear Venta Nueva" si ninguno corresponde
```

### Implementacion del Fuzzy Matching

```python
from difflib import SequenceMatcher
import re

def normalize_name(name: str) -> str:
    """Normaliza nombre para comparacion."""
    name = name.upper().strip()
    # Quitar tildes
    replacements = {'A': 'A', 'E': 'E', 'I': 'I', 'O': 'O', 'U': 'U',
                    'N': 'N'}  # Ñ se maneja aparte
    name = re.sub(r'\s+', ' ', name)
    # Quitar prefijos comunes
    for prefix in ['DE ', 'DEL ', 'LA ', 'LOS ', 'LAS ', 'Ma. ']:
        name = name.replace(prefix, '')
    return name

def match_score(ods_data: dict, sale) -> float:
    """Calcula score de coincidencia entre datos ODS y una venta."""
    score = 0.0
    
    # 1. Nombre del cliente (40%)
    if sale.customer:
        db_name = normalize_name(sale.customer.full_name)
        ods_name = normalize_name(ods_data['client_name'])
        name_ratio = SequenceMatcher(None, db_name, ods_name).ratio()
        score += name_ratio * 40
    
    # 2. Vehiculo + Anio (30%)
    if sale.vehicle:
        # Comparar modelo
        ods_vehicle = normalize_name(ods_data['vehicle_desc'])
        db_vehicle = normalize_name(f"{sale.vehicle.brand} {sale.vehicle.model}")
        vehicle_ratio = SequenceMatcher(None, db_vehicle, ods_vehicle).ratio()
        
        # Comparar anio
        year_match = 1.0 if str(sale.vehicle.year) in ods_data['vehicle_desc'] else 0.0
        
        score += (vehicle_ratio * 0.6 + year_match * 0.4) * 30
    
    # 3. Proximidad de fecha (20%)
    if ods_data.get('first_due_date') and sale.sale_date:
        days_diff = abs((ods_data['first_due_date'] - sale.sale_date.date()).days)
        if days_diff <= 30:
            score += 20
        elif days_diff <= 90:
            score += 15
        elif days_diff <= 180:
            score += 10
    
    # 4. Monto total (10%)
    if ods_data.get('venta_total') and sale.total_price:
        diff = abs(float(ods_data['venta_total']) - float(sale.total_price))
        tolerance = float(sale.total_price) * 0.05  # 5% tolerancia
        if diff <= tolerance:
            score += 10
    
    return score
```

---

## 2. Diseno del Flujo de Importacion

### Diagrama de Flujo

```
[1. CARGA]           [2. PARSING]          [3. MATCHING]
Seleccionar      →   Extraer datos     →   Buscar venta
archivos ODS          del ODS               en BD
                      Validar formato       Calcular scores

[4. PREVIEW]          [5. CONFIRMACION]     [6. EJECUCION]
Mostrar tabla     →   Desarrollador     →   Insertar cuotas
con matches           confirma/corrige      en BD
Color-coded           o crea ventas         Log de auditoria

[7. VERIFICACION]
Reporte final
de consistencia
```

### Vista de Preview para el Desarrollador

La pantalla de importacion debe mostrar:

```
+------------------------------------------------------------------+
| IMPORTACION DE CUOTAS                          [Procesar Lote]   |
+------------------------------------------------------------------+
| Archivo: 132-VITZ 2007 SOFIA FRANCO RAMIREZ.ods                 |
| Cliente: SOFIA FRANCO RAMIREZ                                    |
| Vehiculo: VITZ 1.3CC 2007 | Chassis: 046161                    |
| CM: CM86/24 | Cuotas: 20 x 1.400.000 | Total: 48.000.000       |
|                                                                  |
| MATCH ENCONTRADO:                                                |
|   [*] Venta #CM86/24 - Sofia Franco - Vitz 2007   Score: 98%    |
|   [ ] Venta #132 - S. Franco Ramirez - Vitz 2007  Score: 72%    |
|   [ ] Crear Venta Nueva                                          |
|                                                                  |
| CUOTAS A IMPORTAR:                                               |
| # | VTO        | MONTO     | PAGADA     | FORMA | ESTADO        |
| 1 | 2024-07-02 | 1.400.000 | 2024-07-05 | EF    | Cobrada       |
| 2 | 2024-08-02 | 1.400.000 | 2024-08-03 | TB    | Cobrada       |
| ...                                                              |
| 20| 2026-02-02 | 1.400.000 | -          | -     | Pendiente     |
|                                                                  |
| [Confirmar Match] [Saltar Archivo] [Editar Datos]               |
+------------------------------------------------------------------+
```

### Color Coding

- **Verde**: Match automatico (score >= 85%), listo para importar
- **Amarillo**: Match ambiguo (60-84%), requiere revision
- **Rojo**: Sin match (< 60%), se creara venta nueva
- **Gris**: Ya importado (cuotas duplicadas detectadas)

---

## 3. Logica de Backend

### Estructura de Servicios

```
core/
  services/
    __init__.py
    migration/
      __init__.py
      ods_parser.py          # Parser de archivos ODS
      matching_engine.py     # Motor de matching
      quota_importer.py      # Importador de cuotas
      sale_creator.py        # Creador de ventas nuevas
      migration_logger.py    # Logger de migracion
      validators.py          # Validaciones
  management/
    commands/
      import_quotas.py       # Comando Django para ejecutar
      preview_quotas.py      # Comando para preview
```

### Parser de ODS

```python
# core/services/migration/ods_parser.py

import pandas as pd
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pathlib import Path


@dataclass
class QuotaRow:
    """Representa una cuota parseada del ODS."""
    quota_number: int
    total_plan: int
    due_date: date
    amount: Decimal
    payment_date: Optional[date]
    payment_method: str  # EF, TB, CJ, A/C, VENCIDO
    status: str  # paid, pending, overdue


@dataclass
class ODSData:
    """Datos extraidos de un archivo ODS."""
    filename: str
    # Encabezado
    client_name: str
    phone: str
    vehicle_desc: str
    chassis: Optional[str]
    # Referencia
    cm_code: Optional[str]
    sale_number_from_filename: Optional[str]
    # Resumen financiero
    deuda_total: Optional[Decimal]
    entrega_inicial: Optional[Decimal]
    venta_total: Optional[Decimal]
    # Cuotas
    quotas: list = field(default_factory=list)
    # Garante
    guarantor_name: Optional[str] = None
    guarantor_phone: Optional[str] = None
    # Metadatos de parsing
    parse_warnings: list = field(default_factory=list)


def parse_money(value) -> Optional[Decimal]:
    """Convierte montos en formato paraguayo a Decimal.
    Maneja: '2.000.000.-', '2400000', '2.000.000', etc.
    """
    if pd.isna(value):
        return None
    s = str(value).strip().rstrip('.-').rstrip('-').strip()
    s = s.replace('GS', '').replace('Gs', '').replace('gs', '').strip()
    
    # Si tiene puntos como separadores de miles (formato paraguayo)
    # Patron: digitos.3digitos.3digitos...
    if re.match(r'^\d{1,3}(\.\d{3})+$', s):
        s = s.replace('.', '')
    
    try:
        return Decimal(s)
    except Exception:
        return None


def parse_date(value) -> Optional[date]:
    """Convierte valores de fecha del ODS."""
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # Intentar formato string
    s = str(value).strip()
    for fmt in ['%Y-%m-%d', '%d/%m/%y', '%d/%m/%Y']:
        try:
            return datetime.strptime(s.split()[0], fmt).date()
        except ValueError:
            continue
    return None


def extract_chassis(vehicle_line: str) -> Optional[str]:
    """Extrae numero de chassis de la linea de vehiculo."""
    patterns = [
        r'CHAS[IS]*[:\s]+([A-Z0-9-]+)',
        r'CHASIS[:\s]+([A-Z0-9-]+)',
    ]
    for p in patterns:
        m = re.search(p, vehicle_line.upper())
        if m:
            return m.group(1).strip(' .-')
    return None


def extract_sale_number_from_filename(filename: str) -> Optional[str]:
    """Extrae el numero de venta del nombre del archivo."""
    m = re.match(r'^(\d+)', filename)
    return m.group(1) if m else None


def parse_ods_file(filepath: str) -> ODSData:
    """Parsea un archivo ODS y retorna datos estructurados."""
    path = Path(filepath)
    df = pd.read_excel(filepath, engine='odf', header=None)
    
    warnings = []
    
    # --- Encabezado (filas 0-2) ---
    client_name = str(df.iloc[0, 0]).strip() if pd.notna(df.iloc[0, 0]) else ''
    phone = str(df.iloc[1, 0]).strip() if pd.notna(df.iloc[1, 0]) else ''
    vehicle_desc = str(df.iloc[2, 0]).strip() if pd.notna(df.iloc[2, 0]) else ''
    
    chassis = extract_chassis(vehicle_desc)
    if not chassis:
        warnings.append(f"CHASSIS no encontrado en: {vehicle_desc}")
    
    # Limpiar telefono
    phone = re.sub(r'[CEL.\s-]+', '', phone.replace('CEL', '').replace('cel', ''))
    
    # --- Cuotas (fila 4 en adelante hasta DEUDA) ---
    quotas = []
    summary_start = None
    
    for i in range(4, len(df)):
        val0 = str(df.iloc[i, 0]) if pd.notna(df.iloc[i, 0]) else ''
        
        # Detectar inicio de seccion resumen
        if 'DEUDA' in val0.upper():
            summary_start = i
            break
        
        # Saltar filas vacias
        if not val0 or val0 == 'nan':
            continue
        
        # Parsear cuota
        due_date = parse_date(df.iloc[i, 0])
        doc_str = str(df.iloc[i, 1]) if pd.notna(df.iloc[i, 1]) else ''
        amount = parse_money(df.iloc[i, 2])
        payment_date = parse_date(df.iloc[i, 3])
        forma = str(df.iloc[i, 4]).strip() if pd.notna(df.iloc[i, 4]) else ''
        
        if not due_date or not amount:
            warnings.append(f"Fila {i}: no se pudo parsear fecha o monto")
            continue
        
        # Parsear DOC (ej: "5/24" -> cuota 5 de 24)
        quota_num, total_plan = 0, 0
        doc_match = re.match(r'(\d+)/(\d+)', doc_str)
        if doc_match:
            quota_num = int(doc_match.group(1))
            total_plan = int(doc_match.group(2))
        
        # Determinar estado
        if forma == 'VENCIDO':
            status = 'overdue'
        elif payment_date:
            status = 'paid'
        else:
            status = 'pending'
        
        quotas.append(QuotaRow(
            quota_number=quota_num,
            total_plan=total_plan,
            due_date=due_date,
            amount=amount,
            payment_date=payment_date,
            payment_method=forma if forma != 'VENCIDO' else '',
            status=status,
        ))
    
    # --- Seccion Resumen ---
    cm_code = None
    deuda_total = None
    entrega_inicial = None
    venta_total = None
    guarantor_name = None
    guarantor_phone = None
    
    if summary_start:
        # DEUDA TOTAL
        deuda_total = parse_money(df.iloc[summary_start, 2])
        
        for i in range(summary_start + 1, len(df)):
            val = str(df.iloc[i, 0]) if pd.notna(df.iloc[i, 0]) else ''
            val_upper = val.upper()
            
            # Codigo CM
            cm_match = re.match(r'(CM\d+/\d+)', val)
            if cm_match:
                cm_code = cm_match.group(1)
            
            # Entrega inicial
            if 'ENTREGA' in val_upper:
                entrega_match = re.search(r'[\d.]+', val.replace('.', '', val.count('.')-1) 
                                          if val.count('.') > 1 else val)
                entrega_inicial = parse_money(
                    re.sub(r'[^\d.]', '', val.replace('.', '', val.count('.')-1))
                    if val.count('.') > 1 
                    else re.sub(r'[^\d.]', '', val)
                )
            
            # Venta total
            if 'VENTA TOTAL' in val_upper:
                venta_total = parse_money(
                    re.sub(r'[^\d.]', '', val.replace('.', '', val.count('.')-1))
                    if val.count('.') > 1 
                    else re.sub(r'[^\d.]', '', val)
                )
            
            # Garante (lineas despues del resumen que tienen nombre + telefono)
            if i > summary_start + 4 and val and 'CUOTA' not in val_upper and 'SALDO' not in val_upper:
                if not guarantor_name and re.match(r'^[A-Z\s]+$', val.strip()):
                    guarantor_name = val.strip()
                elif 'GARANTE' in val_upper or re.search(r'\d{4}[-.]?\d{3}', val):
                    if not guarantor_phone:
                        guarantor_phone = val.strip()
    
    sale_num = extract_sale_number_from_filename(path.stem)
    
    return ODSData(
        filename=path.name,
        client_name=client_name,
        phone=phone,
        vehicle_desc=vehicle_desc,
        chassis=chassis,
        cm_code=cm_code,
        sale_number_from_filename=sale_num,
        deuda_total=deuda_total,
        entrega_inicial=entrega_inicial,
        venta_total=venta_total,
        quotas=quotas,
        guarantor_name=guarantor_name,
        guarantor_phone=guarantor_phone,
        parse_warnings=warnings,
    )
```

### Motor de Matching

```python
# core/services/migration/matching_engine.py

from dataclasses import dataclass
from enum import Enum
from difflib import SequenceMatcher
from core.models import Sale, Vehicle, Customer


class MatchLevel(Enum):
    EXACT = "exact"           # Match por CM o chassis - automatico
    PROBABLE = "probable"     # Score >= 85%
    AMBIGUOUS = "ambiguous"   # Score 60-84%
    NO_MATCH = "no_match"     # Score < 60%
    ALREADY_IMPORTED = "already_imported"  # Cuotas ya existen


@dataclass
class MatchResult:
    sale: Sale = None
    score: float = 0.0
    level: MatchLevel = MatchLevel.NO_MATCH
    match_details: dict = None  # Detalle de por que se eligio


def find_matches(ods_data, enterprise) -> list[MatchResult]:
    """Busca ventas candidatas para vincular las cuotas."""
    results = []
    
    # ---- NIVEL 1: Match exacto por CM code ----
    if ods_data.cm_code:
        try:
            sale = Sale.objects.get(
                enterprise=enterprise,
                sale_number=ods_data.cm_code
            )
            # Verificar si ya tiene cuotas importadas
            if sale.quotas.exists():
                return [MatchResult(
                    sale=sale, score=100.0,
                    level=MatchLevel.ALREADY_IMPORTED,
                    match_details={'method': 'CM code', 'existing_quotas': sale.quotas.count()}
                )]
            return [MatchResult(
                sale=sale, score=100.0,
                level=MatchLevel.EXACT,
                match_details={'method': 'CM code match'}
            )]
        except Sale.DoesNotExist:
            pass
        except Sale.MultipleObjectsReturned:
            # Caso raro pero posible
            sales = Sale.objects.filter(enterprise=enterprise, sale_number=ods_data.cm_code)
            for s in sales:
                results.append(MatchResult(
                    sale=s, score=95.0,
                    level=MatchLevel.AMBIGUOUS,
                    match_details={'method': 'CM code - multiple matches'}
                ))
            return results
    
    # ---- NIVEL 1: Match exacto por chassis ----
    if ods_data.chassis:
        vehicles = Vehicle.objects.filter(
            enterprise=enterprise,
            vin__icontains=ods_data.chassis
        )
        for v in vehicles:
            sales = Sale.objects.filter(enterprise=enterprise, vehicle=v)
            for s in sales:
                if s.quotas.exists():
                    results.append(MatchResult(
                        sale=s, score=95.0,
                        level=MatchLevel.ALREADY_IMPORTED,
                        match_details={'method': 'chassis', 'vin': v.vin}
                    ))
                else:
                    results.append(MatchResult(
                        sale=s, score=95.0,
                        level=MatchLevel.EXACT,
                        match_details={'method': 'chassis match', 'vin': v.vin}
                    ))
        if results:
            return sorted(results, key=lambda r: r.score, reverse=True)
    
    # ---- NIVEL 2: Match heuristico ----
    # Buscar en todas las ventas de la empresa que NO tengan cuotas
    candidate_sales = Sale.objects.filter(
        enterprise=enterprise
    ).select_related('customer', 'vehicle')
    
    for sale in candidate_sales:
        score = match_score(ods_data, sale)
        if score >= 60:
            level = MatchLevel.PROBABLE if score >= 85 else MatchLevel.AMBIGUOUS
            results.append(MatchResult(
                sale=sale, score=score, level=level,
                match_details={'method': 'heuristic', 'score_breakdown': 'name+vehicle+date+amount'}
            ))
    
    # Ordenar por score descendente
    results.sort(key=lambda r: r.score, reverse=True)
    
    # Si no hay resultados, retornar NO_MATCH
    if not results:
        results.append(MatchResult(level=MatchLevel.NO_MATCH))
    
    return results[:5]  # Top 5 candidatos
```

### Importador de Cuotas

```python
# core/services/migration/quota_importer.py

import logging
from django.db import transaction
from core.models import Sale, Quotum, Customer, Vehicle, PaymentForm

logger = logging.getLogger('migration')

# Mapeo de codigos FORMA del ODS a PaymentForm del sistema
FORMA_MAP = {
    'EF': 'Efectivo',
    'TB': 'Transferencia Bancaria',
    'TB SILV': 'Transferencia Bancaria',
    'CJ': 'Caja',
    'A/C': 'A Cuenta',
}

STATUS_MAP = {
    'paid': 'paid',
    'pending': 'pending',
    'overdue': 'overdue',
}


@transaction.atomic
def import_quotas_for_sale(ods_data, sale, enterprise, dry_run=False):
    """Importa las cuotas de un ODS a una venta existente.
    
    Args:
        ods_data: Datos parseados del ODS
        sale: Instancia de Sale a la cual vincular
        enterprise: Enterprise activa
        dry_run: Si True, solo valida sin insertar
    
    Returns:
        dict con resultado de la importacion
    """
    result = {
        'success': False,
        'quotas_created': 0,
        'quotas_skipped': 0,
        'warnings': [],
        'errors': [],
    }
    
    # Verificacion de duplicados
    existing_quotas = Quotum.objects.filter(sale=sale)
    if existing_quotas.exists():
        result['errors'].append(
            f"La venta {sale.sale_number} ya tiene {existing_quotas.count()} cuotas. "
            f"Saltando para evitar duplicacion."
        )
        return result
    
    # Validar coherencia de montos
    if ods_data.venta_total and sale.total_price:
        diff = abs(float(ods_data.venta_total) - float(sale.total_price))
        if diff > float(sale.total_price) * 0.1:  # > 10% diferencia
            result['warnings'].append(
                f"Diferencia significativa en monto total: "
                f"ODS={ods_data.venta_total} vs BD={sale.total_price}"
            )
    
    quotas_to_create = []
    
    for q in ods_data.quotas:
        quota = Quotum(
            enterprise=enterprise,
            sale=sale,
            customer=sale.customer,
            quota_number=q.quota_number,
            total_plan=q.total_plan or len(ods_data.quotas),
            amount=q.amount,
            due_date=q.due_date,
            payment_date=q.payment_date,
            status=STATUS_MAP.get(q.status, 'pending'),
            notes=f"Migrado desde {ods_data.filename}. Forma: {q.payment_method}",
        )
        quotas_to_create.append(quota)
    
    if dry_run:
        result['success'] = True
        result['quotas_created'] = len(quotas_to_create)
        return result
    
    # Insercion masiva
    try:
        Quotum.objects.bulk_create(quotas_to_create)
        result['success'] = True
        result['quotas_created'] = len(quotas_to_create)
        
        logger.info(
            f"Importadas {len(quotas_to_create)} cuotas para venta "
            f"{sale.sale_number} desde {ods_data.filename}"
        )
    except Exception as e:
        result['errors'].append(f"Error al insertar cuotas: {str(e)}")
        logger.error(f"Error importando cuotas: {e}", exc_info=True)
    
    return result
```

### Creador de Ventas Nuevas

```python
# core/services/migration/sale_creator.py

import re
from django.db import transaction
from core.models import Sale, Customer, Vehicle, Branch


def split_name(full_name: str) -> tuple[str, str]:
    """Divide nombre completo en first_name y last_name.
    Heuristica: los primeros N-1 tokens son nombre, el ultimo es apellido.
    Excepcion: si tiene 4+ tokens, los ultimos 2 son apellidos.
    """
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ''
    elif len(parts) == 2:
        return parts[0], parts[1]
    elif len(parts) == 3:
        return parts[0], f"{parts[1]} {parts[2]}"
    else:
        # 4+ palabras: primeros N-2 nombre, ultimos 2 apellidos
        mid = len(parts) - 2
        return ' '.join(parts[:mid]), ' '.join(parts[mid:])


@transaction.atomic
def create_sale_from_ods(ods_data, enterprise, branch, dry_run=False):
    """Crea una venta nueva a partir de datos del ODS.
    
    Solo se usa cuando no se encontro match con venta existente.
    """
    result = {
        'sale': None,
        'customer': None,
        'customer_created': False,
        'warnings': [],
    }
    
    # 1. Buscar o crear cliente
    first_name, last_name = split_name(ods_data.client_name)
    
    # Intentar encontrar por nombre similar
    customer = None
    candidates = Customer.objects.filter(
        enterprise=enterprise,
        first_name__icontains=first_name.split()[0] if first_name else '',
    )
    
    for c in candidates:
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(
            None,
            f"{c.first_name} {c.last_name}".upper(),
            ods_data.client_name.upper()
        ).ratio()
        if ratio >= 0.85:
            customer = c
            break
    
    if not customer:
        # Crear nuevo con documento placeholder
        doc_number = f"MIG-{ods_data.cm_code or ods_data.sale_number_from_filename or 'UNKNOWN'}"
        customer = Customer(
            enterprise=enterprise,
            first_name=first_name,
            last_name=last_name,
            document_type='ci',
            document_number=doc_number,
            phone=ods_data.phone or '',
            notes=f"Cliente creado por migracion desde {ods_data.filename}",
        )
        if not dry_run:
            customer.save()
        result['customer_created'] = True
        result['warnings'].append(
            f"Cliente creado con documento placeholder: {doc_number}. "
            f"REQUIERE actualizacion manual del numero de documento."
        )
    
    result['customer'] = customer
    
    # 2. Buscar vehiculo por chassis
    vehicle = None
    if ods_data.chassis:
        vehicle = Vehicle.objects.filter(
            enterprise=enterprise,
            vin__icontains=ods_data.chassis
        ).first()
    
    if not vehicle:
        result['warnings'].append(
            f"Vehiculo no encontrado (chassis: {ods_data.chassis}). "
            f"La venta se creara sin vehiculo vinculado."
        )
    
    # 3. Crear la venta
    sale_number = ods_data.cm_code or f"MIG-{ods_data.sale_number_from_filename}"
    
    # Calcular total
    total = ods_data.venta_total or sum(q.amount for q in ods_data.quotas)
    entrega = ods_data.entrega_inicial or 0
    
    sale = Sale(
        enterprise=enterprise,
        branch=branch,
        sale_number=sale_number,
        customer=customer,
        vehicle=vehicle,
        unit_price=total,
        discount=0,
        total_price=total,
        status='completed' if all(q.status == 'paid' for q in ods_data.quotas) else 'pending',
        notes=(
            f"Venta creada por migracion desde {ods_data.filename}.\n"
            f"Entrega inicial: {entrega}\n"
            f"Deuda total: {ods_data.deuda_total or 'N/A'}\n"
            f"Garante: {ods_data.guarantor_name or 'N/A'}"
        ),
    )
    
    if not dry_run:
        sale.save()
    
    result['sale'] = sale
    return result
```

### Comando Django Principal

```python
# core/management/commands/import_quotas.py

import os
import json
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from core.models import Enterprise, Branch
from core.services.migration.ods_parser import parse_ods_file
from core.services.migration.matching_engine import find_matches, MatchLevel
from core.services.migration.quota_importer import import_quotas_for_sale
from core.services.migration.sale_creator import create_sale_from_ods


class Command(BaseCommand):
    help = 'Importar cuotas desde archivos ODS'

    def add_arguments(self, parser):
        parser.add_argument('folder', type=str, help='Carpeta con archivos ODS')
        parser.add_argument('--enterprise-id', type=int, required=True)
        parser.add_argument('--branch-id', type=int, required=True)
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo simular, no insertar datos')
        parser.add_argument('--auto-confirm', action='store_true',
                            help='Confirmar automaticamente matches exactos')
        parser.add_argument('--file', type=str,
                            help='Procesar solo un archivo especifico')

    def handle(self, *args, **options):
        enterprise = Enterprise.objects.get(id=options['enterprise_id'])
        branch = Branch.objects.get(id=options['branch_id'])
        folder = Path(options['folder'])
        dry_run = options['dry_run']
        
        # Recopilar archivos
        if options.get('file'):
            files = [folder / options['file']]
        else:
            files = sorted(folder.glob('*.ods'))
        
        self.stdout.write(f"\nProcesando {len(files)} archivos...")
        self.stdout.write(f"Modo: {'DRY RUN' if dry_run else 'PRODUCCION'}\n")
        
        # Reporte
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_files': len(files),
            'processed': 0,
            'auto_matched': 0,
            'manual_matched': 0,
            'sales_created': 0,
            'quotas_imported': 0,
            'skipped': 0,
            'errors': [],
            'details': [],
        }
        
        for filepath in files:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Archivo: {filepath.name}")
            
            # 1. PARSEAR
            try:
                ods_data = parse_ods_file(str(filepath))
            except Exception as e:
                report['errors'].append({'file': filepath.name, 'error': str(e)})
                self.stderr.write(f"  ERROR parseando: {e}")
                continue
            
            if ods_data.parse_warnings:
                for w in ods_data.parse_warnings:
                    self.stdout.write(f"  WARN: {w}")
            
            self.stdout.write(f"  Cliente: {ods_data.client_name}")
            self.stdout.write(f"  CM: {ods_data.cm_code}")
            self.stdout.write(f"  Chassis: {ods_data.chassis}")
            self.stdout.write(f"  Cuotas: {len(ods_data.quotas)}")
            
            # 2. MATCHING
            matches = find_matches(ods_data, enterprise)
            best = matches[0] if matches else None
            
            if best and best.level == MatchLevel.ALREADY_IMPORTED:
                self.stdout.write(f"  SALTADO: Ya tiene cuotas importadas")
                report['skipped'] += 1
                continue
            
            sale = None
            
            if best and best.level == MatchLevel.EXACT:
                if options['auto_confirm']:
                    sale = best.sale
                    self.stdout.write(
                        f"  AUTO-MATCH: Venta #{sale.sale_number} "
                        f"(score: {best.score}%)"
                    )
                    report['auto_matched'] += 1
                else:
                    # Modo asistido
                    self.stdout.write(f"\n  Matches encontrados:")
                    for i, m in enumerate(matches):
                        if m.sale:
                            self.stdout.write(
                                f"    [{i+1}] Venta #{m.sale.sale_number} - "
                                f"{m.sale.customer.full_name if m.sale.customer else 'N/A'} "
                                f"- Score: {m.score:.1f}%"
                            )
                    self.stdout.write(f"    [N] Crear venta nueva")
                    self.stdout.write(f"    [S] Saltar archivo")
                    
                    choice = input("  Seleccione opcion: ").strip().upper()
                    
                    if choice == 'S':
                        report['skipped'] += 1
                        continue
                    elif choice == 'N':
                        sale = None  # Se creara abajo
                    elif choice.isdigit() and 1 <= int(choice) <= len(matches):
                        sale = matches[int(choice)-1].sale
                        report['manual_matched'] += 1
            
            elif best and best.level in (MatchLevel.PROBABLE, MatchLevel.AMBIGUOUS):
                # Siempre requiere confirmacion
                self.stdout.write(f"\n  Matches posibles:")
                for i, m in enumerate(matches):
                    if m.sale:
                        self.stdout.write(
                            f"    [{i+1}] Venta #{m.sale.sale_number} - "
                            f"{m.sale.customer.full_name if m.sale.customer else 'N/A'} "
                            f"- Score: {m.score:.1f}%"
                        )
                self.stdout.write(f"    [N] Crear venta nueva")
                self.stdout.write(f"    [S] Saltar")
                
                choice = input("  Seleccione: ").strip().upper()
                if choice == 'S':
                    report['skipped'] += 1
                    continue
                elif choice == 'N':
                    sale = None
                elif choice.isdigit() and 1 <= int(choice) <= len(matches):
                    sale = matches[int(choice)-1].sale
                    report['manual_matched'] += 1
            
            # 3. CREAR VENTA SI NO HAY MATCH
            if sale is None:
                self.stdout.write(f"  Creando venta nueva...")
                create_result = create_sale_from_ods(
                    ods_data, enterprise, branch, dry_run
                )
                sale = create_result['sale']
                for w in create_result['warnings']:
                    self.stdout.write(f"  WARN: {w}")
                report['sales_created'] += 1
            
            # 4. IMPORTAR CUOTAS
            import_result = import_quotas_for_sale(
                ods_data, sale, enterprise, dry_run
            )
            
            if import_result['success']:
                report['quotas_imported'] += import_result['quotas_created']
                self.stdout.write(
                    f"  OK: {import_result['quotas_created']} cuotas importadas"
                )
            else:
                for e in import_result['errors']:
                    self.stderr.write(f"  ERROR: {e}")
                    report['errors'].append({'file': filepath.name, 'error': e})
            
            report['processed'] += 1
            report['details'].append({
                'file': filepath.name,
                'cm_code': ods_data.cm_code,
                'sale_number': sale.sale_number if sale else None,
                'quotas_count': import_result.get('quotas_created', 0),
                'match_level': best.level.value if best else 'no_match',
                'score': best.score if best else 0,
            })
        
        # REPORTE FINAL
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"REPORTE FINAL")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Archivos procesados: {report['processed']}/{report['total_files']}")
        self.stdout.write(f"Match automatico: {report['auto_matched']}")
        self.stdout.write(f"Match manual: {report['manual_matched']}")
        self.stdout.write(f"Ventas creadas: {report['sales_created']}")
        self.stdout.write(f"Cuotas importadas: {report['quotas_imported']}")
        self.stdout.write(f"Saltados: {report['skipped']}")
        self.stdout.write(f"Errores: {len(report['errors'])}")
        
        # Guardar reporte
        report_path = folder / f"migration_report_{datetime.now():%Y%m%d_%H%M%S}.json"
        if not dry_run:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self.stdout.write(f"\nReporte guardado en: {report_path}")
```

---

## 4. Estructura de Datos - Mapeo ODS a BD

### Mapeo de Columnas

| ODS | Campo | Modelo Django | Notas |
|-----|-------|---------------|-------|
| Fila 0 | Nombre cliente | `Customer.first_name + last_name` | Requiere split inteligente |
| Fila 1 | Telefono | `Customer.phone` | Limpiar formato |
| Fila 2 | Descripcion vehiculo | `Vehicle.brand + model + year` | Extraer chassis |
| Col VTO | Fecha vencimiento | `Quotum.due_date` | date |
| Col DOC | Numero cuota/total | `Quotum.quota_number + total_plan` | Parsear "5/24" |
| Col MONTO | Monto de cuota | `Quotum.amount` | Normalizar formato |
| Col FECHA | Fecha de pago | `Quotum.payment_date` | null si no pagada |
| Col FORMA | Forma de pago | Nota en `Quotum.notes` | EF/TB/CJ/A-C |
| CM code | Referencia venta | `Sale.sale_number` | Clave de matching |
| ENTREGA | Entrega inicial | `Sale.notes` | Informativo |
| VENTA TOTAL | Total operacion | `Sale.total_price` | Validacion cruzada |

### Mapeo de Estados

| FORMA en ODS | Status en Quotum | Logica |
|-------------|-----------------|--------|
| EF, TB, CJ, A/C | `paid` | Tiene fecha de pago |
| VENCIDO | `overdue` | Sin fecha de pago + marca explicita |
| (vacio) | `pending` | Sin fecha de pago, sin marca VENCIDO |

---

## 5. Validaciones

### Pre-importacion (por archivo)

```python
def validate_ods_data(ods_data) -> list[str]:
    """Validaciones antes de importar."""
    errors = []
    
    # 1. Tiene cuotas
    if not ods_data.quotas:
        errors.append("No se encontraron cuotas en el archivo")
    
    # 2. Numeros de cuota consecutivos
    nums = [q.quota_number for q in ods_data.quotas]
    expected = list(range(1, len(nums) + 1))
    if nums != expected:
        errors.append(f"Numeracion no consecutiva: {nums}")
    
    # 3. Total plan consistente
    plans = set(q.total_plan for q in ods_data.quotas)
    if len(plans) > 1:
        errors.append(f"Total de plan inconsistente: {plans}")
    
    # 4. Montos positivos
    for q in ods_data.quotas:
        if q.amount <= 0:
            errors.append(f"Cuota {q.quota_number}: monto no positivo ({q.amount})")
    
    # 5. Fechas ordenadas
    dates = [q.due_date for q in ods_data.quotas]
    if dates != sorted(dates):
        errors.append("Fechas de vencimiento no estan en orden")
    
    # 6. Coherencia suma vs total
    if ods_data.venta_total and ods_data.entrega_inicial:
        suma_cuotas = sum(q.amount for q in ods_data.quotas)
        expected_debt = ods_data.venta_total - ods_data.entrega_inicial
        diff = abs(suma_cuotas - expected_debt)
        tolerance = expected_debt * Decimal('0.05')
        if diff > tolerance:
            errors.append(
                f"Suma de cuotas ({suma_cuotas}) no coincide con "
                f"saldo esperado ({expected_debt} = {ods_data.venta_total} - {ods_data.entrega_inicial})"
            )
    
    return errors
```

### Post-importacion (integridad global)

```python
def verify_migration_integrity(enterprise):
    """Verificacion final despues de toda la migracion."""
    issues = []
    
    # 1. Ventas con cuotas duplicadas
    from django.db.models import Count
    dupes = Quotum.objects.filter(enterprise=enterprise) \
        .values('sale', 'quota_number') \
        .annotate(count=Count('id')) \
        .filter(count__gt=1)
    if dupes:
        issues.append(f"Cuotas duplicadas encontradas: {list(dupes)}")
    
    # 2. Clientes con documento placeholder
    placeholders = Customer.objects.filter(
        enterprise=enterprise,
        document_number__startswith='MIG-'
    ).count()
    if placeholders:
        issues.append(f"{placeholders} clientes con documento placeholder (requieren actualizacion)")
    
    # 3. Ventas sin cuotas (que deberian tenerlas)
    sales_no_quotas = Sale.objects.filter(
        enterprise=enterprise,
        sale_number__startswith='CM'
    ).annotate(q_count=Count('quotas')).filter(q_count=0)
    if sales_no_quotas.exists():
        issues.append(f"{sales_no_quotas.count()} ventas con codigo CM sin cuotas asociadas")
    
    return issues
```

---

## 6. Estrategia Incremental

### Principios

1. **Idempotencia**: Cada archivo se puede reprocesar sin duplicar datos
   - Se verifica si la venta ya tiene cuotas antes de insertar
   - Se registra hash del archivo procesado

2. **Procesamiento por lotes**: Se puede ejecutar de a 10-15 archivos
   ```bash
   # Primero dry run completo
   python manage.py import_quotas cuotas/ --enterprise-id=1 --branch-id=1 --dry-run
   
   # Luego por archivo individual para los complicados
   python manage.py import_quotas cuotas/ --enterprise-id=1 --branch-id=1 --file="132-VITZ 2007 SOFIA FRANCO RAMIREZ.ods"
   
   # Finalmente, batch con auto-confirm para los que son match exacto
   python manage.py import_quotas cuotas/ --enterprise-id=1 --branch-id=1 --auto-confirm
   ```

3. **Tabla de control de migracion**

```python
# core/models/migration.py (modelo temporal para tracking)

class MigrationLog(models.Model):
    enterprise = models.ForeignKey('core.Enterprise', on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64)  # SHA256
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pendiente'),
        ('processed', 'Procesado'),
        ('error', 'Error'),
        ('skipped', 'Saltado'),
    ])
    sale_number = models.CharField(max_length=50, blank=True)
    quotas_created = models.IntegerField(default=0)
    match_method = models.CharField(max_length=50, blank=True)
    match_score = models.FloatField(default=0)
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('enterprise', 'file_hash')
```

### Orden de Ejecucion Recomendado

```
FASE 1 - Preparacion (sin tocar BD)
  1. Ejecutar dry-run completo
  2. Revisar reporte: cuantos match exacto, cuantos ambiguos, cuantos sin match
  3. Corregir datos en la BD existente si es necesario (ej: VINs incompletos)

FASE 2 - Match Exactos (bajo riesgo)
  4. Importar con --auto-confirm los que tienen CM code + match exacto
  5. Verificar integridad parcial

FASE 3 - Match Manuales (riesgo medio)
  6. Procesar uno por uno los archivos con match ambiguo
  7. El desarrollador confirma cada vinculacion

FASE 4 - Ventas Nuevas (riesgo alto)
  8. Procesar archivos sin match, creando ventas nuevas
  9. Marcar clientes con documento placeholder para revision posterior

FASE 5 - Verificacion Final
  10. Ejecutar verify_migration_integrity()
  11. Comparar totales: sum(cuotas) por venta vs total_price
  12. Actualizar documentos de clientes placeholder
```

---

## 7. Ejecucion

### Comandos en orden

```bash
# 1. BACKUP primero (siempre)
pg_dump -U postgres playa_db > backup_pre_migration_$(date +%Y%m%d).sql

# 2. Crear migracion Django para MigrationLog
python manage.py makemigrations core
python manage.py migrate

# 3. Dry run completo - revisar output
python manage.py import_quotas "C:\Users\prueb\CascadeProjects\playa\cuotas" \
    --enterprise-id=1 --branch-id=1 --dry-run > dry_run_report.txt 2>&1

# 4. Importar matches exactos con auto-confirm
python manage.py import_quotas "C:\Users\prueb\CascadeProjects\playa\cuotas" \
    --enterprise-id=1 --branch-id=1 --auto-confirm

# 5. Procesar restantes uno por uno (modo interactivo)
python manage.py import_quotas "C:\Users\prueb\CascadeProjects\playa\cuotas" \
    --enterprise-id=1 --branch-id=1

# 6. Verificacion final
python manage.py shell -c "
from core.services.migration.validators import verify_migration_integrity
from core.models import Enterprise
e = Enterprise.objects.get(id=1)
issues = verify_migration_integrity(e)
for i in issues: print(i)
"
```

---

## 8. Consideraciones Especiales para tus Datos

### Los 2 archivos sin codigo CM
- `08-SPORTAGE 2006 - NICOLAS ACOSTA.ods`
- `16-TUCSON 2006 - SILVIA RAMONA CARDOZO.ods`

Estos se matchearan por chassis o nombre. Si no hay match, se crearan como ventas nuevas.

### Typo detectado en cuota 4/34 (archivo Luis Perez)
El archivo `173-VITZ 2005 LUIS PEREZ SERVIAN.ods` tiene la cuota 4 con DOC `4/34` en lugar de `4/24`. El parser debe normalizar el `total_plan` al valor mas frecuente en el archivo.

### Formatos mixtos de MONTO
Algunos archivos usan `2.000.000.-` (formato paraguayo con puntos) y otros usan `1500000` (numerico puro). El parser `parse_money()` maneja ambos.

### Garantes
La informacion de garantes aparece al final de los archivos. Se almacena en `Sale.notes` ya que el modelo actual no tiene campo de garante. Si se necesita en el futuro, se puede crear un modelo `Guarantor`.
