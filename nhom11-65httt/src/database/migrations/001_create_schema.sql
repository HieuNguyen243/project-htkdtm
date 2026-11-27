-- ==================================================
-- Project: Phong Tro BI
-- Group: nhom11-65httt
-- Author: Tran Thi Minh Thu
-- Migration: 001_create_schema.sql
-- Description: Khoi tao cac schema co so du lieu
-- ==================================================

BEGIN;

-- Schema luu du lieu dau vao
CREATE SCHEMA IF NOT EXISTS raw
    AUTHORIZATION bi_admin;

-- Schema luu du lieu nghiep vu
CREATE SCHEMA IF NOT EXISTS core
    AUTHORIZATION bi_admin;

-- Schema quan ly batch va loi
CREATE SCHEMA IF NOT EXISTS audit
    AUTHORIZATION bi_admin;

-- Schema phuc vu phan tich BI
CREATE SCHEMA IF NOT EXISTS analytics
    AUTHORIZATION bi_admin;

-- Mo ta chuc nang cua tung schema
COMMENT ON SCHEMA raw IS
    'Luu tru du lieu dau vao truoc khi xu ly';

COMMENT ON SCHEMA core IS
    'Luu tru du lieu nghiep vu phong tro';

COMMENT ON SCHEMA audit IS
    'Quan ly batch va loi nhap du lieu';

COMMENT ON SCHEMA analytics IS
    'Cung cap du lieu phan tich cho BI';

-- Han che quyen tao doi tuong trong public
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

COMMIT;

-- Kiem tra cac schema da tao
SELECT
    schema_name,
    schema_owner
FROM information_schema.schemata
WHERE schema_name IN (
    'raw',
    'core',
    'audit',
    'analytics'
)
ORDER BY schema_name;