-- =====================================================
--  BookDrop — Database Verification Script (v1.1)
--  Ensures schema consistency and reports key metadata
-- =====================================================

\echo '=== 1. Verify schema structure ==='
\dt public.*

\echo '--- ENUM types ---'
\dT+

\echo '--- Foreign keys and relationships ---'
SELECT conname AS constraint_name,
       conrelid::regclass AS table_name,
       confrelid::regclass AS referenced_table,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE contype = 'f'
ORDER BY conrelid::regclass::text;

-- =====================================================
\echo '=== 2. Verify indexes ==='
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- =====================================================
\echo '=== 3. Verify triggers ==='
SELECT event_object_table AS table_name,
       trigger_name,
       action_timing,
       event_manipulation,
       action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table, trigger_name;

-- =====================================================
\echo '=== 4. Quick sanity checks (row counts) ==='
SELECT 'user' AS table, COUNT(*) AS rows FROM "user"
UNION ALL
SELECT 'book', COUNT(*) FROM book
UNION ALL
SELECT 'book_item', COUNT(*) FROM book_item
UNION ALL
SELECT 'cart', COUNT(*) FROM cart
UNION ALL
SELECT 'cart_item', COUNT(*) FROM cart_item
UNION ALL
SELECT 'order', COUNT(*) FROM "order"
UNION ALL
SELECT 'order_item', COUNT(*) FROM order_item
UNION ALL
SELECT 'locker', COUNT(*) FROM locker
UNION ALL
SELECT 'locker_box', COUNT(*) FROM locker_box
UNION ALL
SELECT 'locker_shipment', COUNT(*) FROM locker_shipment;

-- =====================================================
\echo '=== 5. ENUM integrity check ==='
SELECT t.typname AS enum_type,
       e.enumlabel AS value
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname IN (
    'user_role', 'order_status', 'shipment_mode',
    'shipment_status', 'cart_status', 'book_location'
)
ORDER BY t.typname, e.enumsortorder;

-- =====================================================
\echo '=== 6. Geometry (PostGIS) sanity check ==='
SELECT f_table_name AS table_name,
       f_geometry_column AS geom_column,
       type,
       srid
FROM geometry_columns
WHERE f_table_name IN ('locker');

-- =====================================================
\echo '=== 7. Check timestamp columns and timezone compliance ==='
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE data_type ILIKE '%timestamp%'
ORDER BY table_name, column_name;

-- =====================================================
\echo '=== 8. Validate constraints and uniqueness ==='
SELECT conrelid::regclass AS table_name,
       conname AS constraint_name,
       contype,
       pg_get_constraintdef(pg_constraint.oid) AS definition
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
ORDER BY conrelid::regclass::text, contype DESC;

-- =====================================================
\echo '=== 9. Additional sanity checks ==='

-- Verify email lowercase constraint trigger
\echo '--- Checking user email normalization trigger ---'
SELECT tgname AS trigger_name, tgrelid::regclass AS table_name
FROM pg_trigger
WHERE tgname = 'trg_user_lower_email';

-- Verify pickup_code generator trigger
\echo '--- Checking locker_shipment pickup_code trigger ---'
SELECT tgname AS trigger_name, tgrelid::regclass AS table_name
FROM pg_trigger
WHERE tgname = 'trg_locker_shipment_pickup_code';

-- Verify book_item sync trigger
\echo '--- Checking book availability sync trigger ---'
SELECT tgname AS trigger_name, tgrelid::regclass AS table_name
FROM pg_trigger
WHERE tgname = 'trg_order_item_sync';

-- =====================================================
\echo '=== 10. Suggested data health checks ==='
\echo '--- Users with multiple active carts (should be 0) ---'
SELECT u.id, u.email, COUNT(c.id) AS carts
FROM "user" u
LEFT JOIN cart c ON c.user_id = u.id AND c.status = 'active'
GROUP BY u.id
HAVING COUNT(c.id) > 1;

\echo '--- Books in inconsistent availability state ---'
SELECT bi.id, bi.isbn, bi.is_available, bi.current_location
FROM book_item bi
WHERE (is_available AND current_location = 'borrowed')
   OR (NOT is_available AND current_location = 'library');

-- =====================================================
\echo 'Verification complete. Schema and metadata listed above.'