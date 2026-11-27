\echo ===== 1. ANALYTICS VIEWS =====

SELECT table_schema, table_name
FROM information_schema.views
WHERE table_schema = 'analytics'
ORDER BY table_name;


\echo ===== 2. CURRENT LISTINGS =====

SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT listing_id) AS unique_listings
FROM analytics.vw_listing_current;


\echo ===== 3. PRICE KPI =====

SELECT
    price_basis,
    COUNT(*) AS total_listings,
    SUM(valid_price) AS valid_prices,
    MIN(rent_vnd_month) AS min_price,
    MAX(rent_vnd_month) AS max_price,

    PERCENTILE_CONT(0.25)
        WITHIN GROUP (
            ORDER BY rent_vnd_month
        ) AS p25_price,

    PERCENTILE_CONT(0.5)
        WITHIN GROUP (
            ORDER BY rent_vnd_month
        ) AS median_price,

    PERCENTILE_CONT(0.75)
        WITHIN GROUP (
            ORDER BY rent_vnd_month
        ) AS p75_price

FROM analytics.vw_market_price
WHERE price_basis IN ('room', 'person')
GROUP BY price_basis;


\echo ===== 4. PRICE BY DISTRICT =====

SELECT
    district,
    COUNT(*) AS total_listings,
    SUM(valid_price) AS valid_prices,

    PERCENTILE_CONT(0.5)
        WITHIN GROUP (
            ORDER BY rent_vnd_month
        ) AS median_price

FROM analytics.vw_market_price

WHERE price_basis = 'room'

GROUP BY district
ORDER BY district;


\echo ===== 5. AFFORDABILITY KPI =====

SELECT
    COUNT(*) AS total_listings,
    SUM(valid_price) AS valid_prices,

    SUM(affordable_2m) AS affordable_2m,
    SUM(affordable_3m) AS affordable_3m,
    SUM(affordable_4m) AS affordable_4m,
    SUM(affordable_5m) AS affordable_5m,

    ROUND(
        100.0 * SUM(affordable_3m)
        / NULLIF(SUM(valid_price), 0),
        2
    ) AS affordability_rate_3m,

    ROUND(
        100.0 * SUM(valid_price)
        / NULLIF(COUNT(*), 0),
        2
    ) AS price_coverage

FROM analytics.vw_affordability
WHERE price_basis = 'room';


\echo ===== 6. DATA QUALITY =====

SELECT
    COUNT(*) AS total_listings,
    SUM(missing_price) AS missing_prices,
    SUM(missing_area) AS missing_areas,
    SUM(missing_district) AS missing_districts,
    SUM(missing_address) AS missing_addresses,
    SUM(missing_fee_info) AS missing_fee_info,
    SUM(has_coordinates) AS coordinate_count,
    SUM(suspected_duplicate) AS suspected_duplicates

FROM analytics.vw_listing_quality;


\echo ===== 7. IMPORT BATCH QUALITY =====

SELECT
    batch_id,
    import_status,
    total_rows,
    accepted_rows,
    rejected_rows,

    ROUND(
        100.0 * accepted_rows
        / NULLIF(total_rows, 0),
        2
    ) AS acceptance_rate

FROM audit.ingest_batch
ORDER BY batch_id;


\echo ===== 8. BI READER PERMISSIONS =====

SELECT
    table_name,

    HAS_TABLE_PRIVILEGE(
        'bi_reader',
        'analytics.' || table_name,
        'SELECT'
    ) AS can_select,

    HAS_TABLE_PRIVILEGE(
        'bi_reader',
        'analytics.' || table_name,
        'INSERT'
    ) AS can_insert

FROM information_schema.views

WHERE table_schema = 'analytics'

ORDER BY table_name;


\echo ===== ANALYTICS CHECK COMPLETED =====