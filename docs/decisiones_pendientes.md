# Decisiones pendientes — bitácora de revisiones

> Cada vez que el Jr (o cualquiera) se topa con un caso que no sabe
> resolver, anota acá. El senior revisa y vuelve con decisión.
>
> Formato: añadir al final, no borrar entries viejas (queda como historial).

## Cómo escribir un entry

```
### YYYY-MM-DD — Tu nombre — Tipo de caso

**Caso**: descripción concreta del caso (sale_number, customer_id, monto, etc).

**Qué chequeé**: pasos que ya diste para investigarlo.

**Mi hipótesis**: qué creés que pasa.

**Pregunta concreta**: qué necesitás que el senior decida.

**Estado**: pendiente | resuelto (con fecha)
```

---

## 2026-06-08 — (ejemplo)

### 2026-06-08 — Jr Ejemplo — Patrón A (cliente duplicado)

**Caso**: Cliente "Juan Pérez" aparece con doc real `12345678` (id=42) y con doc placeholder `DRV026-0042` (id=315). Cada uno tiene 1 venta:
- id=42: sale MIG000050 Gs.45M, 12/24 cuotas paid
- id=315: sale CM05/24 Gs.0 (placeholder), 12/12 cuotas paid (historicas)

**Qué chequeé**: comparé en Django shell ambos customers, las ventas, las cuotas. Ambas series de cuotas paid son del mismo período (enero-diciembre 2025).

**Mi hipótesis**: las 12 cuotas del placeholder son las MISMAS que las 12 paid del real, cargadas dos veces durante la migración. La fica placeholder debería borrarse y sus 12 cuotas también (ya cobradas, no afecta deuda actual).

**Pregunta concreta**: ¿borro las 12 cuotas del placeholder + su sale + el cliente placeholder? ¿O las mantengo como historial?

**Estado**: pendiente

---

(agregar entries acá ↓)
