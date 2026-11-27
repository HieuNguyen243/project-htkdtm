CREATE OR REPLACE VIEW analytics.vw_import_batch_quality AS

WITH issue_summary AS (

    SELECT
        batch_id,

        COUNT(*) AS total_issues,

        COUNT(*) FILTER (
            WHERE severity = 'error'
        ) AS error_count,

        COUNT(*) FILTER (
            WHERE severity = 'warning'
        ) AS warning_count

    FROM audit.import_issue

    GROUP BY batch_id
)

SELECT
    b.batch_id,
    b.schema_version,
    b.dataset_version,
    b.data_origin,
    b.export_mode,
    b.import_status,
    b.imported_at,
    b.total_rows,
    b.accepted_rows,
    b.rejected_rows,

    ROUND(
        100.0 * b.accepted_rows
        / NULLIF(b.total_rows, 0),
        2
    ) AS acceptance_rate,

    COALESCE(i.total_issues, 0)
        AS total_issues,

    COALESCE(i.error_count, 0)
        AS error_count,

    COALESCE(i.warning_count, 0)
        AS warning_count

FROM audit.ingest_batch b

LEFT JOIN issue_summary i
    ON b.batch_id = i.batch_id;


COMMENT ON VIEW analytics.vw_import_batch_quality IS
'Thong ke chat luong nhap du lieu theo batch';

GRANT SELECT ON analytics.vw_import_batch_quality
TO bi_reader;