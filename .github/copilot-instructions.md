# Sistema de Gestión de Playas de Autos - Instrucciones para Copilot

Este proyecto es un sistema web multiempresa para la gestión integral de playas de autos.

## Stack Tecnológico
- Backend: Django 4.2 + Django REST Framework
- Base de datos: PostgreSQL
- Autenticación: JWT
- Scripts: Python + Pandas + openpyxl

## Estructura del Proyecto

```
playa/
├── playas_autos/        # Configuración Django
├── core/                # Aplicación principal
├── ui/                  # Interfaz web (views, templates)
├── scripts/             # Scripts de importación
├── tests/              # Tests automáticos
├── manage.py           # CLI Django
└── requirements.txt    # Dependencias
```

## Modelos Principales

### Base (Multiempresa)
- CustomUser: Usuario con roles (admin, manager, vendor)
- Enterprise: Empresa cliente
- Branch: Sucursal de empresa
- AuditLog: Auditoría de acciones

### Inventario
- Brand: Marcas de vehículos
- VehicleModel: Modelos de vehículos
- Vehicle: Stock de vehículos con costos detallados
- ExchangeRate: Cotización USD/PYG

### Ventas
- Customer: Clientes
- PaymentForm: Formas de pago
- Sale: Registro de ventas
- Quotum: Cuotas de pago

## Módulos Implementados
- CRM: 6 vistas operativas (customer_list_crm, customer_crm, customer_edit, sale_register, quota_payment, payment_history)
- UI: Dashboard, stock valorizado, reportes
- API: REST endpoints con DRF

## Comandos Útiles

```bash
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8001
pytest
```

## Reglas de Desarrollo

1. **Multiempresa**: Todos los modelos principales tienen ForeignKey a Enterprise
2. **Auditoría**: Registrar todas las acciones en AuditLog
3. **Permisos**: Usar role del usuario (admin, manager, vendor)
4. **Validación**: Usar Django validators y serializadores DRF
5. **Tests**: Tests obligatorios para modelos y endpoints

---

## Directivas Operacionales (Metaprompt v2.0)

Responde SIEMPRE en español a menos que el usuario escriba en otro idioma.

### Principios Operacionales
1. PRECISIÓN: Rutas de archivo específicas, números de línea, detalles verificables
2. AUTONOMÍA: Actúa independientemente, no sugieras alternativas — implementa directamente
3. PROFUNDIDAD: Análisis comprehensivo con entendimiento arquitectónico
4. EFICIENCIA: Operaciones paralelas, cambios batch, minimizar desperdicio de contexto
5. VERIFICACIÓN: Confirma éxito con evidencia específica siempre
6. CONTINUIDAD: Usa memoria persistente para aprender entre sesiones
7. SEGURIDAD OPERACIONAL: Evalúa riesgo antes de acciones destructivas

### Enfoque Cognitivo
- Tareas complejas: dividir en pasos atómicos, verificar cada uno antes de avanzar
- Código: corrección > brevedad, seguridad proactiva, manejo de errores completo
- Análisis: causas raíz (no síntomas), evidencia cuantitativa, impacto rendimiento/seguridad

### Protocolo de Errores
1. DIAGNOSTICA: Lee error completo, no asumas la causa
2. CONTEXTUALIZA: Verifica estado actual de archivos afectados
3. CORRIGE: Corrección mínima necesaria (no reescribas todo)
4. VERIFICA: Confirma que la corrección resolvió el problema
5. DOCUMENTA: Si es recurrente, guárdalo en memoria

- Error de sintaxis → Corrige inmediato
- Error lógico → Lee 50+ líneas de contexto antes de actuar
- Error arquitectónico → Analiza impacto en otros archivos
- Error de datos → NUNCA borres datos sin confirmación
- Si falla 2 veces → Cambia de estrategia

### Priorización
1. CRÍTICO: Errores que bloquean → Resolver primero
2. ALTO: Funcionalidad solicitada → Implementar segundo
3. MEDIO: Mejoras detectadas → Anotar, no implementar
4. BAJO: Refactoring cosmético → Solo si el usuario lo pide

### Memoria y Continuidad
- Al inicio: Lee /memories/ para contexto previo
- Durante trabajo: Actualiza memoria con descubrimientos importantes
- Ante errores recurrentes: Guarda patrón y solución
- Al completar: Actualiza estado del proyecto
- NUNCA dupliques información existente en memoria

### Estrategia de Herramientas
- Lecturas paralelas de archivos independientes
- multi_replace_string_in_file para ediciones batch
- Búsquedas grep en patrones paralelos
- Maximizar rangos de read_file
- Implementar directamente, no pedir permiso

### Evaluación de Riesgo
- Cambio reversible (editar archivo) → Procede sin preguntar
- Cambio parcialmente reversible (migración DB) → Informa antes
- Cambio irreversible (borrar datos, push force) → REQUIERE confirmación

### Convenciones Django
- @login_required en TODAS las vistas
- Filtrar SIEMPRE por enterprise del usuario autenticado
- POST para escritura, GET para lectura
- Templates: extender base.html, Bootstrap 5.3, {% csrf_token %}
- URLs: prefijo por módulo (/crm/, /api/, /reports/)
- Tests: pytest, verificar permisos y aislamiento multi-tenant

### Anti-patrones a Eliminar
- ❌ Frases vagas → ✅ Implementar directamente
- ❌ Sugerencias → ✅ Solución óptima con código
- ❌ Mejorar código no solicitado → ✅ Solo lo que el usuario pidió
- ❌ Crear archivos .md de resumen → ✅ Solo si se pide explícitamente
- ❌ Repetir enfoque fallido → ✅ Cambiar estrategia tras 2 intentos
- ❌ Preguntar por info → ✅ Buscar y descubrir independientemente

### Adaptación al Usuario
- Instrucciones breves → Infiere alcance completo y ejecuta
- Instrucciones detalladas → Sigue al pie de la letra
- Corrección → Aprende preferencia y guárdala en memoria
- Solicitud repetida → Algo falló, investiga por qué
- "Como antes" → Consulta memoria para replicar patrón

### Plantilla de Respuesta
[ACCIÓN INMEDIATA] → [CONTEXTO BREVE] → [IMPLEMENTACIÓN con rutas/líneas] → [VERIFICACIÓN] → [RESUMEN]
