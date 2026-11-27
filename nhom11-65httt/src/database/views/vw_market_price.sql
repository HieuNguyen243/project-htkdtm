CREATE OR REPLACE VIEW analytics.vw_market_price AS

SELECT
    listing_id,
    batch_id,
    dataset_version,
    data_origin,
    source_name,
    district,
    ward,
    room_type,
    title,
    source_url,
    collected_at,
    listing_status,
    price_basis,
    rent_vnd_month,
    area_m2,

    CASE
        WHEN rent_vnd_month > 0
        AND price_basis IN ('room', 'person')
        THEN 1
        ELSE 0
    END AS valid_price,

    CASE
        WHEN price_basis = 'room'
        AND rent_vnd_month > 0
        AND area_m2 > 0

        THEN ROUND(
            rent_vnd_month::NUMERIC / area_m2,
            2
        )

        ELSE NULL
    END AS rent_per_m2,

    CASE
        WHEN rent_vnd_month IS NULL
            THEN 'missing'

        WHEN rent_vnd_month < 2000000
            THEN 'under_2m'

        WHEN rent_vnd_month < 3000000
            THEN '2m_to_under_3m'

        WHEN rent_vnd_month < 4000000
            THEN '3m_to_under_4m'

        WHEN rent_vnd_month < 5000000
            THEN '4m_to_under_5m'

        ELSE '5m_and_above'

    END AS price_range

FROM analytics.vw_listing_current;


COMMENT ON VIEW analytics.vw_market_price IS
'Du lieu phan tich gia thue va gia thue tren met vuong';

GRANT SELECT ON analytics.vw_market_price
TO bi_reader;