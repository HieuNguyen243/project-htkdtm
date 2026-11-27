import csv
import json
import hashlib
from pathlib import Path

# Thu muc chua du lieu kiem thu
BASE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = BASE_DIR / "fixtures"

SCHEMA_VERSION = "1.0.0-draft.1"

# Cac cot theo dac ta du lieu TV1
FIELDS = [
    "listing_id",
    "source_name",
    "source_record_key",
    "source_url",
    "raw_ref",
    "run_id",
    "content_hash",
    "collected_at",
    "posted_at",
    "posted_date",
    "expires_on",
    "title",
    "description_clean",
    "room_type",
    "area_m2",
    "rent_vnd_month",
    "price_basis",
    "deposit_vnd",
    "deposit_months",
    "fees_json",
    "amenities_json",
    "district",
    "ward",
    "address_clean",
    "latitude",
    "longitude",
    "geo_confidence",
    "max_occupants",
    "duplicate_group_id",
    "duplicate_status",
    "is_representative",
    "listing_status",
    "record_status",
    "quality_flags_json",
]


def make_listing(
    number,
    district,
    rent,
    area,
    batch_id,
    collected_at,
    price_basis="room",
):
    key = f"{number:03d}"

    fees = {
        "electricity": {
            "amount": None,
            "unit": None,
            "status": "unknown",
        },
        "water": {
            "amount": None,
            "unit": None,
            "status": "unknown",
        },
    }

    amenities = {
        "wifi": True,
        "air_conditioner": None,
    }

    title = f"[SYNTHETIC] Phong tro {key} - {district}"

    row = {
        "listing_id": f"demo:{key}",
        "source_name": "demo",
        "source_record_key": key,
        "source_url": "",
        "raw_ref": f"synthetic/{batch_id}/{key}",
        "run_id": f"demo_{batch_id}",
        "content_hash": "",
        "collected_at": collected_at,
        "posted_at": "",
        "posted_date": "",
        "expires_on": "",
        "title": title,
        "description_clean": (
            "Du lieu gia lap chi dung de kiem thu BI."
        ),
        "room_type": "phong_tro",
        "area_m2": area,
        "rent_vnd_month": rent,
        "price_basis": price_basis,
        "deposit_vnd": None,
        "deposit_months": None,
        "fees_json": json.dumps(
            fees, ensure_ascii=False
        ),
        "amenities_json": json.dumps(
            amenities, ensure_ascii=False
        ),
        "district": district,
        "ward": "",
        "address_clean": "",
        "latitude": None,
        "longitude": None,
        "geo_confidence": "area_only",
        "max_occupants": None,
        "duplicate_group_id": "",
        "duplicate_status": "unique",
        "is_representative": "true",
        "listing_status": "unverified_available",
        "record_status": "accepted",
        "quality_flags_json": "[]",
    }

    # Hash noi dung gia lap, khong bao gom metadata
    # cua lan thu thap.
    excluded = {
        "content_hash",
        "run_id",
        "collected_at",
        "raw_ref",
    }

    content = {
        k: v
        for k, v in row.items()
        if k not in excluded
    }

    payload = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
    )

    row["content_hash"] = hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()

    return row


def build_batch_001():
    batch_id = "B001"
    observed_at = "2026-11-25T10:00:00Z"

    samples = [
        (1, "Đống Đa", 2000000, 20, "room"),
        (2, "Thanh Xuân", 3000000, 30, "room"),
        (3, "Cầu Giấy", 4000000, 20, "room"),
        (4, "Cầu Giấy", 5000000, 25, "room"),
        (5, "Thanh Xuân", None, None, "room"),
        (6, "Đống Đa", None, 18, "room"),
        (7, "Đống Đa", 1200000, None, "person"),
    ]

    return [
        make_listing(
            number,
            district,
            rent,
            area,
            batch_id,
            observed_at,
            basis,
        )
        for number, district, rent, area, basis
        in samples
    ]


def build_batch_002():
    batch_id = "B002"
    observed_at = "2026-11-27T03:00:00Z"

    samples = [
        (1, "Đống Đa", 2500000, 20, "room"),
        (2, "Thanh Xuân", 3000000, 30, "room"),
        (3, "Cầu Giấy", 4000000, 20, "room"),
        (4, "Cầu Giấy", 4500000, 25, "room"),
        (5, "Thanh Xuân", 2800000, None, "room"),
        (6, "Đống Đa", None, 18, "room"),
        (7, "Đống Đa", 1200000, None, "person"),
        (8, "Cầu Giấy", 3200000, 22, "room"),
    ]

    return [
        make_listing(
            number,
            district,
            rent,
            area,
            batch_id,
            observed_at,
            basis,
        )
        for number, district, rent, area, basis
        in samples
    ]


def write_batch(batch_id, rows):
    batch_dir = FIXTURE_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    csv_path = batch_dir / "listings.csv"

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDS,
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"Created: {csv_path}")
    print(f"Batch: {batch_id}")
    print(f"Rows: {len(rows)}")


def main():
    print("GENERATE SYNTHETIC TEST DATA")
    print("-" * 40)

    write_batch("B001", build_batch_001())
    write_batch("B002", build_batch_002())

    print("-" * 40)
    print("Completed successfully.")
    print("WARNING: SYNTHETIC DATA ONLY")


if __name__ == "__main__":
    main()