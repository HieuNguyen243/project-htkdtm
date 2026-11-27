import csv
import json
import hashlib

from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

from .config import SCHEMA_VERSION


FIELDS = """
listing_id source_name source_record_key source_url
raw_ref run_id content_hash collected_at posted_at
posted_date expires_on title description_clean
room_type area_m2 rent_vnd_month price_basis
deposit_vnd deposit_months fees_json amenities_json
district ward address_clean latitude longitude
geo_confidence max_occupants duplicate_group_id
duplicate_status is_representative listing_status
record_status quality_flags_json
""".split()


def load_batch(csv_path, manifest_path):
    csv_path = Path(csv_path)
    manifest_path = Path(manifest_path)

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8-sig")
    )

    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ValueError("INVALID_SCHEMA")

    # Giai doan hien tai chi nhap du lieu gia lap
    if manifest["data_origin"] != "synthetic":
        raise ValueError("ONLY_SYNTHETIC_DATA_ALLOWED")

    if manifest["export_mode"] != "full":
        raise ValueError("UNSUPPORTED_EXPORT_MODE")

    checksum = hashlib.sha256(
        csv_path.read_bytes()
    ).hexdigest()

    file_info = manifest["files"]["listings.csv"]

    if checksum != file_info["sha256"]:
        raise ValueError("CHECKSUM_MISMATCH")

    with csv_path.open(
        encoding="utf-8-sig", newline=""
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames != FIELDS:
            raise ValueError("INVALID_CSV_COLUMNS")

        rows = list(reader)

    if len(rows) != file_info["row_count"]:
        raise ValueError("ROW_COUNT_MISMATCH")

    return manifest, rows, checksum


def validate_row(row):
    if None in row or any(v is None for v in row.values()):
        raise ValueError("INVALID_CSV_ROW")

    data = {
        key: value.strip() if value.strip() else None
        for key, value in row.items()
    }

    required = [
        "listing_id",
        "source_name",
        "source_record_key",
        "raw_ref",
        "run_id",
        "content_hash",
        "collected_at",
        "price_basis",
        "is_representative",
        "record_status",
    ]

    for field in required:
        if data[field] is None:
            raise ValueError(
                f"MISSING_REQUIRED_FIELD: {field}"
            )

    expected_id = (
        data["source_name"] + ":" +
        data["source_record_key"]
    )

    if data["listing_id"] != expected_id:
        raise ValueError("INVALID_LISTING_ID")

    integer_fields = [
        "rent_vnd_month",
        "deposit_vnd",
        "max_occupants",
    ]

    for field in integer_fields:
        if data[field] is not None:
            data[field] = int(data[field])

    decimal_fields = [
        "area_m2",
        "deposit_months",
        "latitude",
        "longitude",
    ]

    for field in decimal_fields:
        if data[field] is not None:
            value = Decimal(data[field])

            if not value.is_finite():
                raise ValueError(
                    f"INVALID_NUMBER: {field}"
                )

            data[field] = value

    for field in [
        "rent_vnd_month",
        "area_m2",
        "max_occupants",
    ]:
        value = data[field]

        if value is not None and value <= 0:
            raise ValueError(
                f"INVALID_POSITIVE_VALUE: {field}"
            )

    for field in ["deposit_vnd", "deposit_months"]:
        value = data[field]

        if value is not None and value < 0:
            raise ValueError(
                f"INVALID_DEPOSIT: {field}"
            )

    allowed_values = {
        "price_basis": [
            "room", "person", "unknown"
        ],
        "geo_confidence": [
            "confirmed", "approximate",
            "area_only", "unknown"
        ],
        "duplicate_status": [
            "unique", "suspected",
            "confirmed", "unknown"
        ],
        "listing_status": [
            "expired", "unverified_available",
            "unknown"
        ],
        "record_status": [
            "accepted", "needs_review", "rejected"
        ],
    }

    for field, allowed in allowed_values.items():
        if data[field] not in allowed:
            raise ValueError(
                f"INVALID_ENUM: {field}"
            )

    if data["record_status"] != "accepted":
        raise ValueError("RECORD_NOT_ACCEPTED")

    for field in ["collected_at", "posted_at"]:
        if data[field]:
            value = datetime.fromisoformat(
                data[field].replace("Z", "+00:00")
            )

            if value.tzinfo is None:
                raise ValueError(
                    f"TIMEZONE_REQUIRED: {field}"
                )

            data[field] = value

    for field in ["posted_date", "expires_on"]:
        if data[field]:
            data[field] = date.fromisoformat(
                data[field]
            )

    json_fields = {
        "fees_json": dict,
        "amenities_json": dict,
        "quality_flags_json": list,
    }

    for field, expected_type in json_fields.items():
        value = json.loads(data[field])

        if not isinstance(value, expected_type):
            raise ValueError(
                f"INVALID_JSON: {field}"
            )

        data[field] = value

    representative = data["is_representative"].lower()

    if representative not in ["true", "false"]:
        raise ValueError("INVALID_BOOLEAN")

    data["is_representative"] = (
        representative == "true"
    )

    if not data["is_representative"]:
        raise ValueError("NOT_REPRESENTATIVE")

    return data