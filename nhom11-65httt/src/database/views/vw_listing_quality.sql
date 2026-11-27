CREATE OR REPLACE VIEW analytics.vw_listing_quality AS

SELECT
    listing_id,
    batch_id,
    dataset_version,
    data_origin,
    source_name,
    district,
    ward,
    room_type,
    price_basis,
    collected_at,
    rent_vnd_month,
    area_m2,
    geo_confidence,
    duplicate_status,
    quality_flags_json,

    CASE
        WHEN rent_vnd_month IS NULL
        THEN 1 ELSE 0
    END AS missing_price,

    CASE
        WHEN area_m2 IS NULL
        THEN 1 ELSE 0
    END AS missing_area,

    CASE
        WHEN district IS NULL
        OR TRIM(district) = ''
        THEN 1 ELSE 0
    END AS missing_district,

    CASE
        WHEN address_clean IS NULL
        OR TRIM(address_clean) = ''
        THEN 1 ELSE 0
    END AS missing_address,

    CASE
        WHEN latitude IS NOT NULL
        AND longitude IS NOT NULL
        THEN 1 ELSE 0
    END AS has_coordinates,

    CASE
        WHEN fees_json = '{}'::JSONB
        OR EXISTS (
            SELECT 1
            FROM jsonb_each(fees_json) AS fee
            WHERE COALESCE(
                fee.value ->> 'status',
                'unknown'
            ) = 'unknown'
        )
        THEN 1 ELSE 0
    END AS missing_fee_info,

    CASE
        WHEN duplicate_status = 'suspected'
        THEN 1 ELSE 0
    END AS suspected_duplicate,

    JSONB_ARRAY_LENGTH(
        quality_flags_json
    ) AS quality_flag_count,

    ROUND(
        EXTRACT(
            EPOCH FROM (NOW() - collected_at)
        ) / 3600,
        2
    ) AS freshness_hours

FROM analytics.vw_listing_current;


COMMENT ON VIEW analytics.vw_listing_quality IS
'Phan tich du lieu thieu, trung lap va do moi du lieu';

GRANT SELECT ON analytics.vw_listing_quality
TO bi_reader;