CREATE OR REPLACE VIEW analytics.vw_affordability AS

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
    rent_vnd_month,
    area_m2,
    deposit_vnd,
    deposit_months,
    fees_json,
    collected_at,

    CASE
        WHEN rent_vnd_month > 0
        AND price_basis IN ('room', 'person')
        THEN 1
        ELSE 0
    END AS valid_price,

    CASE
        WHEN rent_vnd_month IS NULL
        OR price_basis = 'unknown'
        THEN NULL
        WHEN rent_vnd_month <= 2000000
        THEN 1
        ELSE 0
    END AS affordable_2m,

    CASE
        WHEN rent_vnd_month IS NULL
        OR price_basis = 'unknown'
        THEN NULL
        WHEN rent_vnd_month <= 3000000
        THEN 1
        ELSE 0
    END AS affordable_3m,

    CASE
        WHEN rent_vnd_month IS NULL
        OR price_basis = 'unknown'
        THEN NULL
        WHEN rent_vnd_month <= 4000000
        THEN 1
        ELSE 0
    END AS affordable_4m,

    CASE
        WHEN rent_vnd_month IS NULL
        OR price_basis = 'unknown'
        THEN NULL
        WHEN rent_vnd_month <= 5000000
        THEN 1
        ELSE 0
    END AS affordable_5m,

    'rent_only'::TEXT AS cost_scope

FROM analytics.vw_listing_current;


COMMENT ON VIEW analytics.vw_affordability IS
'Phan tich kha nang chi tra theo gia thue va nguong ngan sach';

GRANT SELECT ON analytics.vw_affordability
TO bi_reader;