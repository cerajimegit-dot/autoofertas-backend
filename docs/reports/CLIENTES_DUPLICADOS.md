# Clientes duplicados — análisis y plan de depuración

> Análisis del **18/05/2026** contra la copia local de Supabase (298 clientes).
> Trigger: Marcelo detectó que **CARLOS ALBERTO RAMOS JIMENEZ** está duplicado, junto con sus ventas.
> Script: `scripts/find_duplicate_customers.py`. CSV: `docs/reports/duplicados.csv` (54 filas).

## 📊 Resumen

| Métrica | Valor |
|---|---|
| Grupos de duplicados | **26** |
| Fichas duplicadas (total) | 54 |
| Si se mergea uno por grupo | 28 fichas eliminadas |
| Clientes únicos finales | 270 (de 298 = -9%) |

---

## 🔍 5 patrones detectados

### Patrón A — Split del nombre diferente + doc autogenerado (8 casos)

La ficha "real" tiene doc real + ventas reales. La ficha "fantasma" tiene doc `DRV026-XXXX` o `MIG-CMxxx` y una venta con monto 0 o duplicada.

| Ficha real (mantener) | Ficha fantasma (mergear/borrar) |
|---|---|
| CARLOS ALBERTO RAMOS JIMENEZ, doc 48679178 (MIG000137 Gs.115M) | CARLOS ALBERTO RAMOS JIMENEZ, doc DRV026-0008 (CM105/24 Gs.0) |
| ANA PAULA RAMOS JIMENEZ, doc 34312788 | doc DRV026-0004 + venta CM66/23 Gs.0 |
| DERLIS MANUEL ACOSTA GARCIA, doc 0101 | doc DRV026-0007 + venta CM70/24 Gs.0 |
| KATHYANA YSABEL BENITEZ, doc 117 | doc DRV026-0006 + venta CM14/24 Gs.0 |
| NATALIA ACOSTA JIMENEZ, doc 82318880 | doc DRV026-0003 + venta CM78/22 Gs.0 |
| LUCAS LEANDRO MOLINAS ROLON, doc 28224677 | doc MIG-CM19/26 + venta CM19/26 Gs.63M ⚠ |
| MARIANA CECILIA CABRAL, doc 8521811 | doc MIG-CM108/25 + venta CM108/25 Gs.58M ⚠ |

> ⚠ **Lucas Leandro y Mariana Cecilia son distintos**: la ficha "fantasma" tiene una venta CM con monto real. Probablemente alguien creó un cliente nuevo en lugar de usar el existente. Hay que reasignar la venta al cliente original y borrar el fantasma.

### Patrón B — Espacios extras "invisibles" (12 casos)

Misma persona, dos fichas, diferencia: una tiene espacio al final de `first_name` o `last_name`. Casi siempre la duplicada NO tiene ventas asociadas (alguien la pre-cargó y nunca se usó).

| Cliente | Ficha real | Duplicada (sin ventas, borrable) |
|---|---|---|
| ANDREA GISEL GARCIA BRITOS | doc 22 (1 venta MIG) | doc 5589244, sin ventas |
| ANDRES ALBERTO PATIÑO ESQUIVEL | doc 10 (2 ventas MIG) | doc 4401955, sin ventas |
| BETINA BENITEZ LOPEZ | doc 112 (2 ventas) | doc 3180785, sin ventas |
| CARLOS NICOLAS BRITEZ ROJAS | doc 105 (2 ventas) | doc 6301446, sin ventas |
| CAROLINA ISABEL BRITOS DUARTE | doc 107 (2 ventas) | doc 4787597, sin ventas |
| CATALINO VELAZQUEZ | doc 119 (2 ventas) | doc 1684094, sin ventas |
| DAMARIS MARLENE OJEDA CACERES | doc 110 (2 ventas) | doc 6902889, sin ventas |
| ERIKA BEATRIZ BENITEZ VERA | doc 85769292 (2 ventas) | doc 5297781, sin ventas |
| GRISELDA NOEMI DIAZ ALVAREZ | doc 001 (2 ventas) | doc 6288326, sin ventas |
| ISAIAS RAFAEL ASCURRA PEREIRA | doc 111 (2 ventas) | doc 5713230, sin ventas |
| LILIAN CAROLINA PERALTA | doc 115 (2 ventas) | doc 3473003, sin ventas |
| MARIA CRISTINA GODOY DURE | doc 102 (2 ventas) | doc 1534638, sin ventas |
| MARINA LEGUIZAMON DOMINGUEZ | doc 101 (1 venta) | doc 2209850, sin ventas |
| VICTOR MANUEL AYALA OLMEDO | doc 114 (2 ventas) | doc 5415737, sin ventas |

> Estas son **borrado trivial**: la ficha duplicada no tiene ventas → eliminarla no rompe nada. Sería bueno verificar primero si la duplicada tiene la cédula real (los docs como 22, 10, 112, 001 parecen IDs internos cortos).

### Patrón C — Venta duplicada en pares MIG (5 casos)

Una persona aparece dos veces; cada ficha tiene UNA venta MIG diferente, pero con la **misma fecha y mismo monto**. Esto sugiere que la migración generó dos veces la misma venta (no que el cliente compró dos autos).

| Cliente | Ficha 1 | Ficha 2 |
|---|---|---|
| JUAN PABLO SANTA CRUZ MENDOZA | doc 113, MIG000019 27/02/2024 Gs.49.750.000 | doc 6508697, MIG000082 27/02/2024 Gs.49.750.000 |
| LUCIA BEATRIZ MANUEL RIQUELME | doc 103, MIG000010 18/07/2024 Gs.45.000.000 | doc 4544208, MIG000093 18/07/2024 Gs.45.000.000 |
| MARIA LUJAN EICHEMBRENNEY GARAY | doc 108, MIG000014 19/02/2024 Gs.48.000.000 | doc 28261845, MIG000080 19/02/2024 Gs.48.000.000 |

> **Acción**: confirmar con rocío si fueron 2 ventas reales o duplicado de la migración. Si es duplicado, borrar UNA de las ventas + mergear las fichas.

### Patrón D — Top morosos también duplicados (4 casos)

Estos clientes ya estaban en el top 30 de cartera vencida del análisis anterior, lo cual significa que la deuda vencida también está duplicada:

| Cliente | Vencidas en ficha real | Vencidas en duplicada |
|---|---|---|
| JOSE RAMON CHIRIFE CORREA | 42 cuotas (Gs. 84M, doc 109) | 0 cuotas (doc 993741, ficha vacía) |
| KATHYANA YSABEL BENITEZ | 48 cuotas (doc 117) | 0 cuotas (doc DRV026-0006, venta Gs.0) |
| ANA PAULA RAMOS JIMENEZ | 28 cuotas (doc 34312788) | 1 cuota (doc DRV026-0004, venta Gs.0) |

> En estos casos la deuda real está en la ficha buena. La ficha fantasma tiene **0 deuda real** porque su venta es de Gs.0. No infla la cartera vencida — sólo confunde la base de clientes.

### Patrón E — Mismo nombre, ambas fichas legacy (1 caso)

```
ROBERTO ROMERO  →  ficha 1: doc CUOTA000170, sin ventas
                   ficha 2: doc CUOTA000175, sin ventas
```

Probable: la planilla vieja tenía dos rangos diferentes de "Roberto Romero". Sin más datos, hay que confirmar si son la misma persona.

---

## 🛠 Plan de depuración propuesto

### Fase 1 — Borrado trivial (Patrón B — 12 casos sin ventas)

Las 12 fichas duplicadas con espacios extras y sin ventas asociadas pueden borrarse directamente — no rompen nada. Bastaría con:

1. Abrir la ficha duplicada (la que NO tiene ventas).
2. Confirmar visualmente que no tiene ventas/cuotas/cobranzas.
3. Eliminar.

**Impacto**: -12 fichas, base de clientes pasa de 298 a 286.

### Fase 2 — Mergeo de fichas fantasma (Patrón A — 5 con DRV026)

Para cada caso DRV026:
1. Abrir la ficha real (la que tiene doc real + ventas reales).
2. Editar la venta de la ficha fantasma (CM... Gs.0) → reasignar al cliente real.
3. Si la venta fantasma es realmente Gs.0 y duplica una real, borrarla.
4. Eliminar la ficha fantasma.

**Impacto**: -5 fichas más + se sanea el set de ventas con doc autogenerado.

### Fase 3 — Casos con ventas reales en ambas fichas (Patrón A.bis + C — 7 casos)

Estos son los más delicados. Para cada uno:
1. **Decidir si las 2 ventas son la misma o son dos compras reales.**
2. Si son la misma:
   - Mantener la venta del cliente real.
   - Borrar la venta duplicada.
   - Borrar la ficha duplicada.
3. Si son dos compras reales:
   - Reasignar AMBAS ventas al cliente real.
   - Borrar la ficha duplicada.

Requiere **revisión humana** (rocío) con el papelerío físico.

### Fase 4 — Roberto Romero (Patrón E)

Confirmar con rocío si CUOTA000170 y CUOTA000175 son el mismo Roberto. Si sí, mergear. Si no, agregar apellido distintivo a uno.

### Workflow futuro para no volver a duplicar

1. **Antes de crear** un cliente, **buscar primero** por nombre o documento.
2. Si aparece uno parecido (la búsqueda fuzzy de B7 cuando deploys ayuda mucho), **NO crear** otro.
3. Si el cliente existente tiene doc autogenerado, editarlo con la cédula real en vez de crear otro.

---

## 🎯 Próximos pasos sugeridos

1. **Revisar este informe con rocío** (15 min). Validar especialmente los Patrón C (Juan Pablo, Lucia Beatriz, etc.) — son los que requieren conocimiento físico de las ventas.
2. **Aprobar Fase 1** (borrado de 12 fichas trivialmente borrables).
3. **Implementar script `cleanup_duplicates_trivial.py`** que:
   - Por cada ficha en Patrón B, verifique que efectivamente no tiene FK referencias.
   - La borre con `--confirm` (dry-run por default igual que `shift_quotas_year.py`).
4. **Para Fase 2 y 3**: hacerlo manualmente desde la UI con la lista del CSV, ya que requiere reasignar ventas (cosa que la UI hace fácil con el filtro `?customer=`).

---

## 📂 Archivos

- **`docs/reports/duplicados.csv`** — CSV detallado con las 54 fichas en 26 grupos. Recomendación de mantener/mergear por fila.
- **`scripts/find_duplicate_customers.py`** — Re-ejecutable: `DB_ENGINE=sqlite python scripts/find_duplicate_customers.py`
- **`scripts/find_duplicate_customers.py --only-with-sales`** — sólo mostrar grupos donde al menos una ficha tiene ventas reales (filtra el ruido).

---

*Reporte generado por `find_duplicate_customers.py` el 18/05/2026.*
