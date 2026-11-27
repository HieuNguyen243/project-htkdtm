-- Project: Phong Tro BI
-- Group: nhom11-65httt
-- File: check_database.sql
-- Kiem tra cau truc va phan quyen co so du lieu

\echo '===== 1. DATABASE ====='

SELECT current_database(), current_user;

\echo '===== 2. SCHEMAS ====='

SELECT schema_name, schema_owner
FROM information_schema.schemata
WHERE schema_name IN (
    'raw', 'core', 'audit', 'analytics'
)
ORDER BY schema_name;

\echo '===== 3. TABLES ====='

SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN (
    'raw', 'core', 'audit'
)
AND table_type = 'BASE TABLE'
ORDER BY table_schema, table_name;

\echo '===== 4. CONSTRAINTS ====='

SELECT
    table_schema,
    table_name,
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_schema IN (
    'raw', 'core', 'audit'
)
ORDER BY table_schema, table_name, constraint_type;

\echo '===== 5. INDEXES ====='

SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname IN (
    'raw', 'core', 'audit'
)
ORDER BY schemaname, tablename;

\echo '===== 6. ROLES ====='

SELECT
    rolname,
    rolcanlogin,
    rolsuper,
    rolcreatedb
FROM pg_roles
WHERE rolname IN (
    'bi_admin',
    'bi_importer',
    'bi_reader'
)
ORDER BY rolname;

\echo '===== 7. PERMISSION CHECK ====='

SELECT
    has_table_privilege(
        'bi_importer',
        'core.listing',
        'INSERT'
    ) AS importer_can_insert,

    has_table_privilege(
        'bi_importer',
        'core.listing',
        'DELETE'
    ) AS importer_can_delete,

    has_table_privilege(
        'bi_reader',
        'core.listing',
        'SELECT'
    ) AS reader_can_read_core,

    has_table_privilege(
        'bi_reader',
        'core.listing',
        'INSERT'
    ) AS reader_can_insert,

    has_schema_privilege(
        'bi_reader',
        'analytics',
        'USAGE'
    ) AS reader_can_use_analytics;

\echo '===== 8. ROW COUNTS ====='

SELECT 'ingest_batch' AS table_name,
       COUNT(*) AS total_rows
FROM audit.ingest_batch

UNION ALL

SELECT 'staging_listing', COUNT(*)
FROM raw.staging_listing

UNION ALL

SELECT 'listing', COUNT(*)
FROM core.listing

UNION ALL

SELECT 'listing_snapshot', COUNT(*)
FROM core.listing_snapshot

UNION ALL

SELECT 'import_issue', COUNT(*)
FROM audit.import_issue;

\echo '===== DATABASE CHECK COMPLETED ====='