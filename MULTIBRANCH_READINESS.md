# 🏢 ANÁLISIS: PREPARACIÓN PARA MÚLTIPLES SUCURSALES

## 📋 RESUMEN EJECUTIVO

**Estado General**: ⚠️ **PARCIALMENTE PREPARADO**

El sistema **SÍ tiene** la estructura de datos para múltiples sucursales, pero le falta funcionalidad en el frontend para:
- ✅ Créar y gestionar sucursales
- ✅ Asignar usuarios a sucursales  
- ❌ Filtrar datos por sucursal en el UI
- ❌ Selector de sucursal en las vistas

---

## ✅ LO QUE YA ESTÁ IMPLEMENTADO

### 1. Modelos (Backend) ✅
```
Enterprise (Empresa)
  └─ Relación 1:N con Branch
  
Branch (Sucursal)
  ├─ ForeignKey a Enterprise
  ├─ Nombre, Código, Dirección, Ciudad
  ├─ ForeignKey a CustomUser (manager/encargado)
  └─ Campo is_active para activar/desactivar
  
CustomUser (Usuario)
  ├─ ForeignKey a Enterprise
  ├─ related_name='branches_managed' (un usuario puede administrar varias sucursales)
  └─ Roles: admin, manager, vendor
  
Sale (Venta)
  ├─ ForeignKey a Branch (sucursal)
  ├─ ForeignKey a Enterprise
  ├─ ForeignKey a CustomUser (vendedor)
  └─ Las ventas se asignan automáticamente a una sucursal
```

### 2. Base de Datos ✅
```
Estado actual en AUTO OFERTAS:
├─ Sucursales: 1 creada ("CASA CENTRAL")
├─ Ventas con sucursal: 21/161 (13%)
├─ Ventas sin sucursal: 140/161 (87%)
└─ Usuarios: 3 (ninguno asignado a sucursales)
```

### 3. APIs REST ✅
```
GET /api/branches/               - Listar sucursales
GET /api/sales/?branch=2         - Filtrar ventas por sucursal
GET /api/customers/              - Listar clientes
GET /api/quotas/                 - Listar cuotas
```

Las APIs soportan parámetro `?branch=id` para filtrar.

### 4. Filtros Backend ✅
```python
# En core/views/sales.py:
branch_id = self.request.query_params.get('branch')
if branch_id:
    queryset = queryset.filter(branch_id=branch_id)
```

---

## ❌ LO QUE FALTA

### 1. Frontend - Selector de Sucursal ❌
**Dónde**: `ui/templates/ui/*.html`

**Lo que falta**:
- Dropdown para seleccionar sucursal (en Dashboard, Ventas, Cuotas)
- Persistencia de la sucursal seleccionada (localStorage)
- Filtrado automático de datos según sucursal

**Ejemplo deseado**:
```html
<select id="branch" class="form-select">
  <option value="">Todas las sucursales</option>
  <option value="1">CASA CENTRAL</option>
  <option value="2">Sucursal 2</option>
</select>
```

### 2. Frontend - Llamadas AJAX con Filtro ❌
**Dónde**: `ui/templates/ui/dashboard.html` (JavaScript)

**Lo que falta**:
```javascript
// Falta pasar branch_id en las llamadas AJAX
fetch('/api/sales/?branch=2')  // ← No está implementado
fetch('/api/quotas/?branch=2') // ← No está implementado
```

### 3. Asignación de Vendedores a Sucursales ❌
**Problema**: Los usuarios (vendor, manager) no tienen sucursales asignadas

**Lo que falta**:
- Relación ManyToMany entre CustomUser y Branch
- Panel para asignar usuarios a sucursales
- Filtrar datos según sucursal del usuario

### 4. Asignación de Ventas a Sucursales ❌
**Problema**: 140 de 161 ventas (87%) no están vinculadas a sucursal

**Lo que falta**:
- Script para asignar ventas a sucursal por defecto
- Validación al crear venta (debe tener sucursal)

### 5. Dashboard por Sucursal ❌
**Lo que falta**:
- KPIs filtrados por sucursal
- Gráficos por sucursal
- Comparativas entre sucursales

---

## 🔍 ANÁLISIS DETALLADO

### Estado de la Base de Datos

```
Empresa: AUTO OFERTAS
├─ Total de sucursales: 1
│  └─ CASA CENTRAL (código: )
│     ├─ Ciudad: [vacío]
│     ├─ Encargado: None
│     └─ Activa: Yes
├─ Ventas por sucursal:
│  ├─ Con sucursal: 21 (13%)
│  ├─ Sin sucursal: 140 (87%)
│  └─ Total: 161
└─ Usuarios asignados a sucursales: 0
   ├─ admin: No
   ├─ manager: No
   └─ vendor: No
```

### Relaciones en los Modelos

```
✅ Enterprise → Branch (1:N)
✅ Branch → CustomUser (manager) (N:1)
✅ Sale → Branch (N:1)
✅ CustomUser → Enterprise (N:1)

❌ CustomUser → Branch (N:M) [relación que falta]
✅ Sale → CustomUser (seller) (N:1) [existe pero sin filtrar por branch]
```

---

## 📊 COMPARATIVA: ESTADO ACTUAL vs IDEAL

| Aspecto | Actual | Ideal | Estado |
|--------|--------|-------|--------|
| **Modelos** | Diseñados | Implementados | ✅ |
| **BD - Sucursales** | 1 sucursal | Múltiples | ⚠️ |
| **BD - Ventas vinculadas** | 13% | 100% | ❌ |
| **APIs - Filtro branch** | Implementado | Funcional | ✅ |
| **Frontend - Selector** | No existe | Necesario | ❌ |
| **Frontend - AJAX filter** | No usa branch | Usar branch | ❌ |
| **Usuarios-Sucursales** | Sin asignar | Asignados | ❌ |
| **Dashboard filtrado** | General | Por sucursal | ❌ |

---

## 🚀 PLAN DE IMPLEMENTACIÓN

Para habilitar completamente el soporte para múltiples sucursales:

### Fase 1: Preparación de Datos (1-2 horas)
- [ ] Crear más sucursales en Django Admin
- [ ] Asignar encargados (managers) a cada sucursal
- [ ] Ejecutar script para asignar ventas existentes a sucursal por defecto
- [ ] Asignar usuarios a sucursales

### Fase 2: Backend (2-3 horas)
- [ ] Crear relación ManyToMany: CustomUser ↔ Branch
- [ ] Implementar permission que filtre por sucursal del usuario
- [ ] Actualizar ViewSets para filtrar automáticamente por sucursal del usuario

### Fase 3: Frontend (3-4 horas)
- [ ] Agregar selector de sucursal en base.html
- [ ] Implementar localStorage para persistencia de sucursal
- [ ] Actualizar AJAX calls en dashboard.html para incluir ?branch=id
- [ ] Actualizar llamadas en sales.html, quotas.html, etc.
- [ ] Agregar filtros visuales en cada página

### Fase 4: Testing (1-2 horas)
- [ ] Probar login de usuarios con diferentes sucursales
- [ ] Verificar que cada usuario solo ve datos de sus sucursales
- [ ] Probar cambio de sucursal en el UI
- [ ] Validar permisos por sucursal

---

## 💡 RECOMENDACIONES

### Inmediato (Prioritario)
1. **Crear más sucursales** en Django Admin para preparar el sistema
2. **Asignar usuarios a sucursales** - Relación N:M
3. **Agregar selector de sucursal** en el frontend (UI)

### Corto Plazo
1. **Implementar filtros por sucursal** en todas las vistas
2. **Asegurar que ventas se asignen a sucursal** automáticamente
3. **Agregar permisos** para que usuarios solo vean su sucursal

### Mediano Plazo
1. **Dashboard por sucursal** con KPIs específicos
2. **Reportes comparativos** entre sucursales
3. **Auditoría de acciones** por sucursal

---

## 📌 CONCLUSIÓN

```
┌─────────────────────────────────────────────────────────┐
│ PREPARACIÓN PARA MÚLTIPLES SUCURSALES                 │
├─────────────────────────────────────────────────────────┤
│ Estructura de Datos:     ✅ LISTA                      │
│ Backend (APIs):          ✅ LISTO                      │
│ Frontend (UI/Filtros):   ❌ NECESITA IMPLEMENTACIÓN   │
│ Configuración de Datos:  ⚠️  PARCIAL (1 sucursal)     │
├─────────────────────────────────────────────────────────┤
│ RECOMENDACIÓN: Implementar filtros de sucursal en     │
│ el frontend para completar la funcionalidad            │
└─────────────────────────────────────────────────────────┘
```

**El sistema está diseñado correctamente para múltiples sucursales, pero necesita trabajo en el UI para que sea totalmente funcional.**

---

## 📞 PRÓXIMOS PASOS

1. **¿Necesitas crear más sucursales de prueba?**
   → Usar Django Admin en http://127.0.0.1:8001/admin/

2. **¿Necesitas implementar el filtro de sucursal en frontend?**
   → Requiere cambios en templates y JavaScript

3. **¿Necesitas asignar usuarios a sucursales específicas?**
   → Crear relación ManyToMany y agregar campo en admin

**¿Por dónde deseas continuar?**
