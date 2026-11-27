-- Project: Phong Tro BI
-- Group: nhom11-65httt
-- Migration: 002_create_tables.sql

BEGIN;

-- 1. Quan ly cac dot nhap du lieu
CREATE TABLE IF NOT EXISTS audit.ingest_batch (
    batch_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    export_mode TEXT NOT NULL,
    data_origin TEXT NOT NULL,
    checksum TEXT NOT NULL,
    import_status TEXT NOT NULL DEFAULT 'pending',
    imported_at TIMESTAMPTZ,
    total_rows INTEGER NOT NULL DEFAULT 0,
    accepted_rows INTEGER NOT NULL DEFAULT 0,
    rejected_rows INTEGER NOT NULL DEFAULT 0
);

-- 2. Luu du lieu CSV truoc khi xu ly
CREATE TABLE IF NOT EXISTS raw.staging_listing (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    batch_id TEXT NOT NULL
        REFERENCES audit.ingest_batch(batch_id),
    row_number INTEGER NOT NULL,
    raw_data JSONB NOT NULL,
    validation_status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (batch_id, row_number)
);

-- 3. Quan ly dinh danh tin dang
CREATE TABLE IF NOT EXISTS core.listing (
    listing_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_record_key TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (source_name, source_record_key)
);

-- 4. Luu lich su thay doi cua tin dang
CREATE TABLE IF NOT EXISTS core.listing_snapshot (
    snapshot_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    listing_id TEXT NOT NULL
        REFERENCES core.listing(listing_id),

    batch_id TEXT NOT NULL
        REFERENCES audit.ingest_batch(batch_id),

    source_url TEXT,
    raw_ref TEXT NOT NULL,
    run_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,

    collected_at TIMESTAMPTZ NOT NULL,
    posted_at TIMESTAMPTZ,
    posted_date DATE,
    expires_on DATE,

    title TEXT,
    description_clean TEXT,
    room_type TEXT,

    area_m2 NUMERIC,
    rent_vnd_month BIGINT,
    price_basis TEXT NOT NULL,

    deposit_vnd BIGINT,
    deposit_months NUMERIC,

    fees_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    amenities_json JSONB NOT NULL DEFAULT '{}'::JSONB,

    district TEXT,
    ward TEXT,
    address_clean TEXT,

    latitude NUMERIC,
    longitude NUMERIC,
    geo_confidence TEXT,

    max_occupants INTEGER,

    duplicate_group_id TEXT,
    duplicate_status TEXT,

    is_representative BOOLEAN NOT NULL,

    listing_status TEXT,
    record_status TEXT,

    quality_flags_json JSONB NOT NULL DEFAULT '[]'::JSONB,

    UNIQUE (listing_id, batch_id)
);

-- 5. Ghi nhan loi trong qua trinh nhap
CREATE TABLE IF NOT EXISTS audit.import_issue (
    issue_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    batch_id TEXT NOT NULL
        REFERENCES audit.ingest_batch(batch_id),

    row_number INTEGER,
    listing_id TEXT,
    field_name TEXT,

    error_code TEXT NOT NULL,
    error_message TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'error',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE audit.ingest_batch IS
    'Quan ly cac dot nhap du lieu';

COMMENT ON TABLE raw.staging_listing IS
    'Luu du lieu dau vao truoc khi xu ly';

COMMENT ON TABLE core.listing IS
    'Quan ly dinh danh duy nhat cua tin dang';

COMMENT ON TABLE core.listing_snapshot IS
    'Luu lich su tin dang theo tung batch';

COMMENT ON TABLE audit.import_issue IS
    'Luu loi va canh bao khi nhap du lieu';

COMMIT;