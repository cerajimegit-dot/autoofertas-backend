# FIX: FieldError en Dashboard

## Problema
Error al acceder a /dashboard/:
```
FieldError at /dashboard/
Cannot resolve keyword 'customuser' into field.
```

## Causa
El código en `ui/views.py` estaba usando un nombre de campo incorrecto. El filtro intentaba usar:
```python
Enterprise.objects.filter(customuser=request.user)
```

Pero el campo correcto es `users` (relación reverse del ForeignKey de CustomUser a Enterprise).

## Solución
Se reemplazaron todas las instancias de `customuser=request.user` por `users=request.user` en 6 funciones:

1. **dashboard()** - Línea 51
2. **vehicles()** - Línea 69  
3. **sales()** - Línea 87
4. **quotas()** - Línea 105
5. **customers()** - Línea 123
6. **api_dashboard_stats()** - Línea 142

## Cambio Realizado

**Antes:**
```python
enterprise = Enterprise.objects.filter(customuser=request.user).first()
```

**Después:**
```python
enterprise = Enterprise.objects.filter(users=request.user).first()
```

## Verificación
- ✓ Cambios aplicados a ui/views.py
- ✓ Servidor Django reboot automático (StatReloader detectó cambios)
- ✓ Dashboard debería funcionar ahora sin FieldError

## Próxima Prueba
1. Accede a http://127.0.0.1:8001/dashboard/
2. Debería cargar correctamente sin errores de FieldError
3. Se mostrarán las estadísticas de la empresa

## Archivos Modificados
- `ui/views.py` - 6 líneas corregidas
