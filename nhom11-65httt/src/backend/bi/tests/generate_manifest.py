import csv
import json
import hashlib
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = BASE_DIR / "fixtures"


def generate_manifest(batch_id):
    batch_dir = FIXTURE_DIR / batch_id
    csv_path = batch_dir / "listings.csv"

    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    checksum = hashlib.sha256(
        csv_path.read_bytes()
    ).hexdigest()

    with csv_path.open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    district_counts = Counter(
        row["district"] for row in rows
    )

    source_counts = Counter(
        row["source_name"] for row in rows
    )

    basis_counts = Counter(
        row["price_basis"] for row in rows
    )

    missing_price = sum(
        not row["rent_vnd_month"]
        for row in rows
    )

    missing_area = sum(
        not row["area_m2"]
        for row in rows
    )

    manifest = {
        "batch_id": batch_id,
        "schema_version": "1.0.0-draft.1",
        "dataset_version": f"synthetic_{batch_id}",
        "released_at": max(
            row["collected_at"] for row in rows
        ),
        "export_mode": "full",
        "data_origin": "synthetic",
        "test_profile": "bi_kpi_missing_values",
        "scope": {
            "districts": [
                "Đống Đa",
                "Thanh Xuân",
                "Cầu Giấy",
            ],
            "purpose": "BI testing only",
        },
        "input_run_ids": sorted({
            row["run_id"] for row in rows
        }),
        "source_rights_status": (
            "synthetic_test_data"
        ),
        "counts": {
            "fixture_rows": len(rows),
            "missing_price": missing_price,
            "missing_area": missing_area,
            "by_district": dict(district_counts),
            "by_source": dict(source_counts),
            "by_price_basis": dict(basis_counts),
        },
        "files": {
            "listings.csv": {
                "row_count": len(rows),
                "sha256": checksum,
            }
        },
        "warning": (
            "Synthetic fixture. "
            "Not real market data. "
            "Missing-price rows are intentional."
        ),
    }

    manifest_path = batch_dir / "manifest.json"

    with manifest_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            manifest,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")

    print(f"Created: {manifest_path}")
    print(f"Rows: {len(rows)}")
    print(f"SHA256: {checksum}")


def main():
    generate_manifest("B001")
    generate_manifest("B002")
    print("Manifest generation completed.")


if __name__ == "__main__":
    main()
