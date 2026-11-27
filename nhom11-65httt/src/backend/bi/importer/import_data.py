import argparse

from psycopg import sql
from psycopg.types.json import Jsonb

from .connection import get_connection
from .validator import load_batch, validate_row


IDENTITY_FIELDS = {
    "listing_id",
    "source_name",
    "source_record_key",
}

JSON_FIELDS = {
    "fees_json",
    "amenities_json",
    "quality_flags_json",
}


def save_issue(cur, batch_id, row_number,
               listing_id, message):

    cur.execute("""
        INSERT INTO audit.import_issue (
            batch_id,
            row_number,
            listing_id,
            error_code,
            error_message,
            severity
        )
        VALUES (%s, %s, %s, %s, %s, 'error')
    """, (
        batch_id,
        row_number,
        listing_id,
        "INVALID_ROW",
        message,
    ))


def save_listing(cur, batch_id, data):

    cur.execute("""
        INSERT INTO core.listing (
            listing_id,
            source_name,
            source_record_key,
            first_seen_at
        )
        VALUES (%s, %s, %s, %s)

        ON CONFLICT (listing_id)
        DO UPDATE SET
            first_seen_at = LEAST(
                core.listing.first_seen_at,
                EXCLUDED.first_seen_at
            )
    """, (
        data["listing_id"],
        data["source_name"],
        data["source_record_key"],
        data["collected_at"],
    ))

    snapshot = {
        "listing_id": data["listing_id"],
        "batch_id": batch_id,
    }

    for field, value in data.items():

        if field in IDENTITY_FIELDS:
            continue

        if field in JSON_FIELDS:
            value = Jsonb(value)

        snapshot[field] = value

    columns = list(snapshot.keys())

    query = sql.SQL("""
        INSERT INTO core.listing_snapshot ({})
        VALUES ({})
    """).format(
        sql.SQL(", ").join(
            sql.Identifier(c) for c in columns
        ),
        sql.SQL(", ").join(
            sql.Placeholder() for _ in columns
        ),
    )

    cur.execute(
        query,
        list(snapshot.values())
    )


def import_batch(csv_path, manifest_path, batch_id):

    manifest, rows, checksum = load_batch(
        csv_path, manifest_path
    )

    if manifest.get("batch_id") != batch_id:
        raise ValueError("BATCH_ID_MISMATCH")

    with get_connection() as conn:

        # 1. Khoi tao batch
        with conn.transaction():
            with conn.cursor() as cur:

                cur.execute("""
                    INSERT INTO audit.ingest_batch (
                        batch_id,
                        schema_version,
                        dataset_version,
                        export_mode,
                        data_origin,
                        checksum,
                        import_status,
                        total_rows
                    )
                    VALUES (
                        %s, %s, %s, %s,
                        %s, %s, 'processing', %s
                    )
                    ON CONFLICT (batch_id)
                    DO NOTHING
                    RETURNING batch_id
                """, (
                    batch_id,
                    manifest["schema_version"],
                    manifest["dataset_version"],
                    manifest["export_mode"],
                    manifest["data_origin"],
                    checksum,
                    len(rows),
                ))

                created = cur.fetchone()

                if created is None:

                    cur.execute("""
                        SELECT checksum, import_status
                        FROM audit.ingest_batch
                        WHERE batch_id = %s
                    """, (batch_id,))

                    old_checksum, status = cur.fetchone()

                    if old_checksum != checksum:
                        raise ValueError("BATCH_CONFLICT")

                    if status == "succeeded":
                        print("BATCH_ALREADY_IMPORTED")
                        return

                    raise ValueError(
                        f"BATCH_NOT_RETRYABLE: {status}"
                    )

        accepted = 0
        rejected = 0
        seen = set()
        valid_rows = []

        try:

            # 2. Luu staging va kiem tra du lieu
            with conn.transaction():
                with conn.cursor() as cur:

                    for number, row in enumerate(rows, 1):

                        cur.execute("""
                            INSERT INTO raw.staging_listing (
                                batch_id,
                                row_number,
                                raw_data,
                                validation_status
                            )
                            VALUES (%s, %s, %s, 'pending')
                        """, (
                            batch_id,
                            number,
                            Jsonb(row),
                        ))

                        try:

                            data = validate_row(row)

                            listing_id = data["listing_id"]

                            if listing_id in seen:
                                raise ValueError(
                                    "DUPLICATE_LISTING_ID"
                                )

                            seen.add(listing_id)
                            valid_rows.append(data)

                            status = "valid"
                            accepted += 1

                        except Exception as exc:

                            status = "invalid"
                            rejected += 1

                            save_issue(
                                cur,
                                batch_id,
                                number,
                                row.get("listing_id"),
                                str(exc),
                            )

                        cur.execute("""
                            UPDATE raw.staging_listing
                            SET validation_status = %s
                            WHERE batch_id = %s
                            AND row_number = %s
                        """, (
                            status,
                            batch_id,
                            number,
                        ))

                    cur.execute("""
                        UPDATE audit.ingest_batch
                        SET rejected_rows = %s
                        WHERE batch_id = %s
                    """, (rejected, batch_id))

            # 3. Khong cong bo batch co du lieu loi
            if rejected > 0:
                raise ValueError("BATCH_VALIDATION_FAILED")

            # 4. Nhap du lieu vao bang nghiep vu
            with conn.transaction():
                with conn.cursor() as cur:

                    for data in valid_rows:
                        save_listing(
                            cur, batch_id, data
                        )

                    cur.execute("""
                        UPDATE audit.ingest_batch
                        SET
                            import_status = 'succeeded',
                            imported_at = NOW(),
                            accepted_rows = %s,
                            rejected_rows = %s
                        WHERE batch_id = %s
                    """, (
                        accepted,
                        rejected,
                        batch_id,
                    ))

        except Exception as exc:

            # 5. Ghi nhan batch that bai
            with conn.transaction():
                with conn.cursor() as cur:

                    save_issue(
                        cur,
                        batch_id,
                        None,
                        None,
                        str(exc),
                    )

                    cur.execute("""
                        UPDATE audit.ingest_batch
                        SET
                            import_status = 'failed',
                            accepted_rows = 0,
                            imported_at = NOW()
                        WHERE batch_id = %s
                    """, (batch_id,))

            raise

        # 6. Hien thi ket qua
        print("=" * 40)
        print("IMPORT SUCCESS")
        print(f"Batch: {batch_id}")
        print(f"Total rows: {len(rows)}")
        print(f"Accepted: {accepted}")
        print(f"Rejected: {rejected}")
        print("=" * 40)


def main():

    parser = argparse.ArgumentParser(
        description="Phong Tro BI Importer"
    )

    parser.add_argument("--file", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--batch", required=True)

    args = parser.parse_args()

    import_batch(
        args.file,
        args.manifest,
        args.batch,
    )


if __name__ == "__main__":
    main()
