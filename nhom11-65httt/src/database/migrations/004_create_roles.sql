-- Migration: 004_create_roles.sql

BEGIN;

-- Tao role neu chua ton tai
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname = 'bi_importer'
    ) THEN
        CREATE ROLE bi_importer LOGIN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname = 'bi_reader'
    ) THEN
        CREATE ROLE bi_reader LOGIN;
    END IF;
END
$$;

-- Han che quyen mac dinh
REVOKE ALL ON DATABASE phongtro_bi_demo FROM PUBLIC;

REVOKE ALL ON SCHEMA raw, core, audit, analytics
FROM PUBLIC;

-- =============================================
-- 1. Quyen cua Importer
-- =============================================

GRANT CONNECT ON DATABASE phongtro_bi_demo
TO bi_importer;

GRANT USAGE ON SCHEMA raw, core, audit
TO bi_importer;

GRANT SELECT, INSERT, UPDATE
ON ALL TABLES IN SCHEMA raw, core, audit
TO bi_importer;

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA raw, core, audit
TO bi_importer;

ALTER DEFAULT PRIVILEGES FOR ROLE bi_admin
IN SCHEMA raw, core, audit
GRANT SELECT, INSERT, UPDATE ON TABLES
TO bi_importer;

ALTER DEFAULT PRIVILEGES FOR ROLE bi_admin
IN SCHEMA raw, core, audit
GRANT USAGE, SELECT ON SEQUENCES
TO bi_importer;

-- =============================================
-- 2. Quyen cua BI Reader
-- =============================================

GRANT CONNECT ON DATABASE phongtro_bi_demo
TO bi_reader;

GRANT USAGE ON SCHEMA analytics
TO bi_reader;

GRANT SELECT ON ALL TABLES IN SCHEMA analytics
TO bi_reader;

ALTER DEFAULT PRIVILEGES FOR ROLE bi_admin
IN SCHEMA analytics
GRANT SELECT ON TABLES TO bi_reader;

ALTER ROLE bi_reader
SET default_transaction_read_only = on;

COMMIT;