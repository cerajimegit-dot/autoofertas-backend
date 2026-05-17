-- =============================================================
--  Consulta / edición de cuotas por código interno de venta
--
--  Uso en DB Browser for SQLite:
--    1. Abrí db.sqlite3
--    2. Pestaña "Execute SQL"
--    3. Cambiá el código al principio
--    4. Ejecutá con F5
--
--  IMPORTANTE:
--    Las consultas #2 y #3 NO usan JOINs → los resultados son
--    editables directamente en la grilla (doble-click sobre una
--    celda). Al terminar presioná "Write Changes" (💾).
-- =============================================================


-- ═══════════════════════════════════════════════════════════════
-- 1) Buscar el SALE_ID a partir del código (CM130/25, MIG000023…)
-- ═══════════════════════════════════════════════════════════════
-- 🔧 EDITAR ACÁ EL CÓDIGO:
SELECT
    id               AS sale_id,
    sale_number      AS codigo,
    DATE(sale_date)  AS fecha_venta,
    total_price,
    down_payment,
    customer_id,
    vehicle_id,
    payment_form_id,
    status
FROM core_sale
WHERE sale_number = 'CM130/25';          -- ← EDITAR AQUÍ


-- ═══════════════════════════════════════════════════════════════
-- 2) DETALLE DE CUOTAS — EDITABLE (doble-click sobre la celda)
-- ═══════════════════════════════════════════════════════════════
-- 🔧 Copiá el sale_id de la consulta #1 y pegalo acá:
SELECT
    id,
    quota_number,
    due_date,
    payment_date,
    cancelled_date,
    amount,
    interest,
    status,
    plan_name,
    total_plan,
    notes,
    customer_id
FROM core_quotum
WHERE sale_id = 319                       -- ← EDITAR AQUÍ (sale_id)
ORDER BY quota_number;


-- ═══════════════════════════════════════════════════════════════
-- 3) VENTA — EDITABLE (si querés cambiar entrega, cliente, etc.)
-- ═══════════════════════════════════════════════════════════════
SELECT
    id,
    sale_number,
    sale_date,
    total_price,
    down_payment,
    customer_id,
    vehicle_id,
    payment_form_id,
    status,
    notes
FROM core_sale
WHERE id = 319;                           -- ← EDITAR AQUÍ (sale_id)


-- ═══════════════════════════════════════════════════════════════
-- REFERENCIAS RÁPIDAS (no se ejecutan como edición — solo info)
-- ═══════════════════════════════════════════════════════════════

-- Estados de cuota disponibles:
--   'pending'   = Pendiente
--   'paid'      = Cobrada (setear payment_date)
--   'overdue'   = Vencida
--   'cancelled' = Cancelada (setear cancelled_date)

-- Formas de pago (payment_form_id):
--   1 = CONTADO
--   2 = CRÉDITO (con tilde)
--   3 = CREDITO (sin tilde — la más usada)
--   4 = MIXTO


-- ═══════════════════════════════════════════════════════════════
-- BÚSQUEDA DE CLIENTES (para conocer customer_id) — EDITABLE
-- ═══════════════════════════════════════════════════════════════
SELECT
    id,
    first_name,
    last_name,
    document_type,
    document_number,
    phone,
    email,
    city
FROM core_customer
WHERE first_name LIKE '%MIRIAM%'          -- ← EDITAR (nombre parcial)
   OR last_name  LIKE '%MIRIAM%';


-- ═══════════════════════════════════════════════════════════════
-- BÚSQUEDA DE VEHÍCULOS POR CHASIS — EDITABLE
-- ═══════════════════════════════════════════════════════════════
SELECT
    id,
    vin,
    year,
    color,
    price,
    currency,
    state,
    brand_id,
    model_id
FROM core_vehicle
WHERE vin LIKE '%KSP90-2010957%';         -- ← EDITAR (chasis parcial)
