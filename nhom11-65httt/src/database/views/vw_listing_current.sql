CREATE OR REPLACE VIEW analytics.vw_listing_current AS

WITH ranked_listing AS (

    SELECT
        s.*,
        l.source_name,
        l.source_record_key,
        l.first_seen_at,

        b.data_origin,
        b.dataset_version,
        b.imported_at,

        ROW_NUMBER() OVER (
            PARTITION BY s.listing_id
            ORDER BY
                s.collected_at DESC,
                s.snapshot_id DESC
        ) AS row_rank

    FROM core.listing_snapshot s

    JOIN core.listing l
        ON s.listing_id = l.listing_id

    JOIN audit.ingest_batch b
        ON s.batch_id = b.batch_id

    WHERE b.import_status = 'succeeded'
)

SELECT *

FROM ranked_listing

WHERE row_rank = 1
    AND record_status = 'accepted'
    AND is_representative = TRUE;


COMMENT ON VIEW analytics.vw_listing_current IS
'Du lieu moi nhat cua moi tin dang tu cac batch thanh cong';

GRANT SELECT ON analytics.vw_listing_current
TO bi_reader;