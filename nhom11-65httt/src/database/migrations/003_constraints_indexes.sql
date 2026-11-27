-- Migration: 003_constraints_indexes.sql

BEGIN;

-- =============================================
-- 1. Rang buoc bang ingest_batch
-- =============================================

ALTER TABLE audit.ingest_batch
ADD CONSTRAINT chk_export_mode
CHECK (export_mode IN ('full', 'delta'));

ALTER TABLE audit.ingest_batch
ADD CONSTRAINT chk_data_origin
CHECK (data_origin IN ('real', 'synthetic'));

ALTER TABLE audit.ingest_batch
ADD CONSTRAINT chk_import_status
CHECK (
    import_status IN (
        'pending',
        'processing',
        'succeeded',
        'failed'
    )
);

ALTER TABLE audit.ingest_batch
ADD CONSTRAINT chk_batch_counts
CHECK (
    total_rows >= 0
    AND accepted_rows >= 0
    AND rejected_rows >= 0
    AND accepted_rows + rejected_rows <= total_rows
);

ALTER TABLE audit.ingest_batch
ADD CONSTRAINT chk_batch_checksum
CHECK (checksum ~ '^[0-9a-fA-F]{64}$');

-- =============================================
-- 2. Rang buoc bang staging_listing
-- =============================================

ALTER TABLE raw.staging_listing
ADD CONSTRAINT chk_validation_status
CHECK (
    validation_status IN (
        'pending', 'valid', 'invalid'
    )
);

ALTER TABLE raw.staging_listing
ADD CONSTRAINT chk_staging_row_number
CHECK (row_number > 0);

ALTER TABLE raw.staging_listing
ADD CONSTRAINT chk_raw_data
CHECK (jsonb_typeof(raw_data) = 'object');

-- =============================================
-- 3. Rang buoc bang listing
-- =============================================

ALTER TABLE core.listing
ADD CONSTRAINT chk_listing_id
CHECK (
    listing_id = source_name || ':' || source_record_key
);

-- =============================================
-- 4. Rang buoc bang listing_snapshot
-- =============================================

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_rent_positive
CHECK (rent_vnd_month IS NULL OR rent_vnd_month > 0);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_area_positive
CHECK (area_m2 IS NULL OR area_m2 > 0);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_deposit_vnd
CHECK (deposit_vnd IS NULL OR deposit_vnd >= 0);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_deposit_months
CHECK (deposit_months IS NULL OR deposit_months >= 0);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_price_basis
CHECK (price_basis IN ('room', 'person', 'unknown'));

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_max_occupants
CHECK (max_occupants IS NULL OR max_occupants > 0);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_latitude
CHECK (latitude BETWEEN -90 AND 90);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_longitude
CHECK (longitude BETWEEN -180 AND 180);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_coordinate_pair
CHECK (
    (latitude IS NULL AND longitude IS NULL)
    OR
    (
        latitude IS NOT NULL
        AND longitude IS NOT NULL
        AND NOT (latitude = 0 AND longitude = 0)
    )
);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_geo_confidence
CHECK (
    geo_confidence IN (
        'confirmed',
        'approximate',
        'area_only',
        'unknown'
    )
);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_duplicate_status
CHECK (
    duplicate_status IN (
        'unique',
        'suspected',
        'confirmed',
        'unknown'
    )
);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_listing_status
CHECK (
    listing_status IN (
        'expired',
        'unverified_available',
        'unknown'
    )
);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_record_status
CHECK (
    record_status IN (
        'accepted',
        'needs_review',
        'rejected'
    )
);

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_fees_json
CHECK (jsonb_typeof(fees_json) = 'object');

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_amenities_json
CHECK (jsonb_typeof(amenities_json) = 'object');

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_quality_flags_json
CHECK (jsonb_typeof(quality_flags_json) = 'array');

ALTER TABLE core.listing_snapshot
ADD CONSTRAINT chk_content_hash
CHECK (content_hash ~ '^[0-9a-fA-F]{64}$');

-- =============================================
-- 5. Rang buoc bang import_issue
-- =============================================

ALTER TABLE audit.import_issue
ADD CONSTRAINT chk_issue_severity
CHECK (severity IN ('warning', 'error'));

-- =============================================
-- 6. Index phuc vu truy van
-- =============================================

CREATE INDEX IF NOT EXISTS idx_batch_status
ON audit.ingest_batch(import_status);

CREATE INDEX IF NOT EXISTS idx_batch_origin
ON audit.ingest_batch(data_origin);

CREATE INDEX IF NOT EXISTS idx_snapshot_latest
ON core.listing_snapshot(
    listing_id,
    collected_at DESC,
    snapshot_id DESC
);

CREATE INDEX IF NOT EXISTS idx_snapshot_batch
ON core.listing_snapshot(batch_id);

CREATE INDEX IF NOT EXISTS idx_snapshot_district
ON core.listing_snapshot(district);

CREATE INDEX IF NOT EXISTS idx_snapshot_room_type
ON core.listing_snapshot(room_type);

CREATE INDEX IF NOT EXISTS idx_snapshot_price
ON core.listing_snapshot(price_basis, rent_vnd_month);

CREATE INDEX IF NOT EXISTS idx_snapshot_collected_at
ON core.listing_snapshot(collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_snapshot_record_status
ON core.listing_snapshot(record_status, is_representative);

CREATE INDEX IF NOT EXISTS idx_issue_batch
ON audit.import_issue(batch_id);

CREATE INDEX IF NOT EXISTS idx_issue_error_code
ON audit.import_issue(error_code);

COMMIT;