"""ETL pipeline: normalize, enrich, deduplicate, validate against reference catalogs, and release."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from base_scraper import atomic_write_csv
from config import (
    DATA_DIR,
    DISTRICTS,
    REF_DIR,
    SCHEMA_VERSION,
    STANDARD_FIELDS,
    VN_TZ,
    clean_text,
    has_conflicting_district,
    is_non_room_listing,
    redact_pii,
)
from deduplicator import Deduplicator
from extractor import build_quality_flags, enrich_row

BOT_DIR = Path(__file__).resolve().parent
DEFAULT_BOTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("phongtro123.py", ("--pages", "10", "--delay", "1.2", "--skip-existing")),
    ("mixstay.py", ("--limit-per-district", "24", "--delay", "1.2")),
    ("muaban.py", ("--pages", "5", "--delay", "1.2", "--skip-existing")),
)
REVIEW_FIELDS: tuple[str, ...] = (
    "listing_id",
    "source_name",
    "source_url",
    "district",
    "record_status",
    "reason",
    "quality_flags_json",
)


@dataclass(frozen=True)
class PipelineSummary:
    """Counts and artifact paths produced by a single ETL pipeline run."""

    run_id: str
    raw_count: int
    rejected_count: int
    needs_review_count: int
    confirmed_duplicate_count: int
    suspected_duplicate_count: int
    clean_count: int
    listings_path: Path
    listings_all_path: Path
    review_path: Path
    manifest_path: Path
    by_district: dict[str, int]
    by_source: dict[str, int]
    by_price_basis: dict[str, int]


def _parse_posted_fields(posted_raw: str) -> tuple[str, str]:
    """Separate full ISO-8601 UTC timestamp from date-only YYYY-MM-DD."""
    if not posted_raw:
        return "", ""
    if len(posted_raw) == 10 and posted_raw[4] == "-" and posted_raw[7] == "-":
        return "", posted_raw
    try:
        dt = datetime.fromisoformat(posted_raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        utc_dt = dt.astimezone(timezone.utc)
        return utc_dt.isoformat(), utc_dt.date().isoformat()
    except ValueError:
        return "", ""


def _parse_collected_utc(collected_raw: str) -> str:
    """Normalize collected_at to UTC ISO-8601 without refreshing an existing timestamp."""
    if not collected_raw:
        return ""
    try:
        dt = datetime.fromisoformat(collected_raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return collected_raw


def normalize_row(row: dict[str, str], raw_ref: str, run_id: str) -> dict[str, str]:
    """Normalize a source CSV row into STANDARD_FIELDS, preserve collected_at, and enrich."""
    normalized = {field: "" for field in STANDARD_FIELDS}
    for field in STANDARD_FIELDS:
        if field in row and row[field] is not None:
            normalized[field] = clean_text(str(row[field]))

    normalized["raw_ref"] = raw_ref
    normalized["run_id"] = run_id
    normalized["title"] = redact_pii(normalized["title"])
    normalized["description_clean"] = redact_pii(normalized["description_clean"])

    raw_addr = row.get("address_clean") or row.get("address") or ""
    normalized["address_clean"] = redact_pii(raw_addr)
    normalized["collected_at"] = _parse_collected_utc(normalized["collected_at"])

    posted_at, posted_date = _parse_posted_fields(row.get("posted_at") or "")
    normalized["posted_at"] = posted_at
    normalized["posted_date"] = row.get("posted_date") or posted_date
    normalized["expires_on"] = (row.get("expires_on") or row.get("expires_at") or "")[:10]

    if not normalized["price_basis"]:
        normalized["price_basis"] = "unknown"
    if not normalized["listing_status"]:
        normalized["listing_status"] = "unverified_available"
    if not normalized["record_status"]:
        normalized["record_status"] = "accepted"

    return enrich_row(
        normalized,
        explicit_amenities=clean_text(str(row.get("amenities") or "")),
        price_raw=clean_text(str(row.get("price_raw") or "")),
    )


def classify_row(row: dict[str, str]) -> tuple[str, str]:
    """Classify row record_status as 'accepted', 'needs_review', or 'rejected'."""
    if row.get("district") not in DISTRICTS.values():
        return "rejected", "district outside scope"
    if row.get("listing_status") == "expired":
        return "rejected", "expired listing"
    title = row.get("title", "")
    if not title or is_non_room_listing(title):
        return "rejected", "non-room property or missing title"
    address = row.get("address_clean", "")
    if address and has_conflicting_district(f"{title} {address}", row["district"]):
        return "rejected", "conflicting district in title/address"
    if not row.get("rent_vnd_month"):
        return "needs_review", "missing monthly rent"
    try:
        rent = int(float(row["rent_vnd_month"]))
    except ValueError:
        return "rejected", "invalid rent_vnd_month format"
    if rent <= 0 or rent > 50_000_000:
        return "needs_review", "implausible rent_vnd_month"
    return "accepted", ""


def find_source_csvs(data_dir: Path) -> list[Path]:
    """Discover per-source *_rooms.csv files while skipping derived/historical/rejected outputs."""
    candidates = sorted(data_dir.glob("*_rooms.csv"))
    return [
        path
        for path in candidates
        if not path.name.startswith("all_rooms_clean")
        and not path.name.endswith("_historical.csv")
        and not path.name.endswith("_rejected.csv")
        and not path.name.endswith("_so_bo.csv")
    ]


def sha256_file(path: Path) -> str:
    """Return hex SHA-256 checksum of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_scrapers(bots: Sequence[tuple[str, Sequence[str]]], logger: logging.Logger) -> None:
    """Execute each configured scraper script as an isolated subprocess."""
    for script_name, extra_args in bots:
        script_path = BOT_DIR / script_name
        if not script_path.exists():
            logger.warning("Scraper not found, skipping: %s", script_path)
            continue
        command = [sys.executable, str(script_path), *extra_args]
        logger.info("Running scraper: %s", " ".join(command))
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("%s exited with %d: %s", script_name, result.returncode, result.stderr.strip())


def load_reference_codes(ref_dir: Path = REF_DIR) -> dict[str, set[str]]:
    """Load valid primary keys from the six reference catalogs."""
    specs = {
        "areas": ("areas.csv", "area_name"),
        "room_types": ("room_types.csv", "room_type_code"),
        "amenities": ("amenity_catalog.csv", "amenity_code"),
        "fees": ("fee_catalog.csv", "fee_code"),
        "flags": ("quality_flag_catalog.csv", "flag_code"),
        "campuses": ("campuses.csv", "campus_id"),
    }
    catalogs: dict[str, set[str]] = {}
    for key, (filename, column) in specs.items():
        path = ref_dir / filename
        with path.open(encoding="utf-8-sig", newline="") as stream:
            values = [row[column] for row in csv.DictReader(stream)]
        if len(values) != len(set(values)) or any(not v for v in values):
            raise ValueError(f"Invalid or duplicate keys in reference catalog {path}")
        catalogs[key] = set(values)
    return catalogs


def validate_release(data_dir: Path = DATA_DIR, ref_dir: Path = REF_DIR) -> list[str]:
    """Validate listings.csv, listings_all.csv, manifest.json, and reference catalog integrity."""
    errors: list[str] = []
    catalogs = load_reference_codes(ref_dir)

    manifest_path = data_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"Missing manifest: {manifest_path}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for filename, meta in manifest.get("files", {}).items():
        target = data_dir / filename
        if not target.exists():
            errors.append(f"Manifest file missing: {filename}")
            continue
        actual_hash = sha256_file(target)
        if actual_hash != meta.get("sha256"):
            errors.append(f"Checksum mismatch for {filename}")
        with target.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
            if stream.closed:
                pass
        if len(rows) != meta.get("row_count"):
            errors.append(f"Row count mismatch for {filename}: {len(rows)} != {meta.get('row_count')}")

    listings_path = data_dir / "listings.csv"
    with listings_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != STANDARD_FIELDS:
            errors.append("listings.csv columns do not match STANDARD_FIELDS")
        seen_ids: set[str] = set()
        for idx, row in enumerate(reader, start=1):
            lid = row.get("listing_id", "")
            if not lid or lid in seen_ids:
                errors.append(f"Row {idx}: missing or duplicate listing_id '{lid}'")
            seen_ids.add(lid)
            if row.get("district") not in catalogs["areas"]:
                errors.append(f"Row {idx} ({lid}): unknown district '{row.get('district')}'")
            if row.get("room_type") not in catalogs["room_types"]:
                errors.append(f"Row {idx} ({lid}): unknown room_type '{row.get('room_type')}'")
            if row.get("record_status") != "accepted" or row.get("is_representative") != "true":
                errors.append(f"Row {idx} ({lid}): non-accepted or non-representative row in listings.csv")
            try:
                amenities = json.loads(row.get("amenities_json", "{}"))
                fees = json.loads(row.get("fees_json", "{}"))
                flags = json.loads(row.get("quality_flags_json", "[]"))
            except json.JSONDecodeError as exc:
                errors.append(f"Row {idx} ({lid}): invalid JSON ({exc})")
                continue
            if not set(amenities).issubset(catalogs["amenities"]):
                errors.append(f"Row {idx} ({lid}): unknown amenity keys")
            if not set(fees).issubset(catalogs["fees"]):
                errors.append(f"Row {idx} ({lid}): unknown fee keys")
            if not set(flags).issubset(catalogs["flags"]):
                errors.append(f"Row {idx} ({lid}): unknown quality flags")
    return errors


def run_pipeline(
    data_dir: Path = DATA_DIR,
    output_path: Path | None = None,
    skip_scrape: bool = False,
    save_snapshot: bool = False,
    bots: Sequence[tuple[str, Sequence[str]]] = DEFAULT_BOTS,
) -> PipelineSummary:
    """Run scraping (optional), enrichment, deduplication, and release export."""
    logger = logging.getLogger("pipeline")
    now_vn = datetime.now(VN_TZ)
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    if not skip_scrape:
        run_scrapers(bots, logger)

    raw_count = 0
    deduped_inputs: dict[str, dict[str, str]] = {}
    review_rows: list[dict[str, str]] = []

    for csv_path in find_source_csvs(data_dir):
        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            for raw in csv.DictReader(stream):
                raw_count += 1
                lid = clean_text(str(raw.get("listing_id") or ""))
                raw_ref = f"data/{csv_path.name}#{lid}"
                normalized = normalize_row(raw, raw_ref=raw_ref, run_id=run_id)
                status, reason = classify_row(normalized)
                normalized["record_status"] = status
                if status == "needs_review":
                    review_rows.append(
                        {
                            "listing_id": normalized["listing_id"],
                            "source_name": normalized["source_name"],
                            "source_url": normalized["source_url"],
                            "district": normalized["district"],
                            "record_status": status,
                            "reason": reason,
                            "quality_flags_json": normalized["quality_flags_json"],
                        }
                    )
                if lid:
                    deduped_inputs[lid] = normalized

    accepted_candidates = [row for row in deduped_inputs.values() if row["record_status"] == "accepted"]
    non_accepted = [row for row in deduped_inputs.values() if row["record_status"] != "accepted"]
    for row in non_accepted:
        row["duplicate_group_id"] = ""
        row["duplicate_status"] = "unknown"
        row["is_representative"] = "false"
        row["quality_flags_json"] = json.dumps(build_quality_flags(row), ensure_ascii=False)

    annotated_accepted, dup_stats = Deduplicator().annotate_clusters(accepted_candidates)
    for row in annotated_accepted:
        row["quality_flags_json"] = json.dumps(build_quality_flags(row), ensure_ascii=False)

    all_rows = annotated_accepted + non_accepted
    published_rows = [
        row
        for row in annotated_accepted
        if row.get("record_status") == "accepted" and row.get("is_representative") == "true"
    ]
    rejected_count = sum(1 for row in non_accepted if row["record_status"] == "rejected")

    listings_path = output_path or (data_dir / "listings.csv")
    listings_all_path = listings_path.with_name("listings_all.csv")
    review_path = listings_path.with_name("records_to_review.csv")
    manifest_path = listings_path.with_name("manifest.json")

    ordered_published = sorted(published_rows, key=lambda item: item["listing_id"])
    ordered_all = sorted(all_rows, key=lambda item: item["listing_id"])

    atomic_write_csv(listings_path, STANDARD_FIELDS, ordered_published)
    atomic_write_csv(listings_all_path, STANDARD_FIELDS, ordered_all)
    atomic_write_csv(review_path, REVIEW_FIELDS, review_rows)

    dataset_version = f"v{now_vn.strftime('%Y%m%d_%H%M')}"
    district_counts = dict(Counter(row["district"] for row in ordered_published))
    source_counts = dict(Counter(row["source_name"] for row in ordered_published))
    price_basis_counts = dict(Counter(row["price_basis"] for row in ordered_published))

    file_row_counts = {
        listings_path.name: len(ordered_published),
        listings_all_path.name: len(ordered_all),
        review_path.name: len(review_rows),
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_version": dataset_version,
        "released_at": now_vn.isoformat(),
        "export_mode": "full",
        "input_run_ids": [run_id],
        "data_origin": "real",
        "scope": {
            "districts": list(DISTRICTS.values()),
            "property_scope": "room_rental_only",
        },
        "source_rights_status": "internal_technical_sample_pending_written_sharing_approval",
        "representative_rule": "accepted -> latest collected_at -> highest completeness -> ascending listing_id",
        "counts": {
            "raw_input": raw_count,
            "rejected": rejected_count,
            "needs_review": len(review_rows),
            "listings_all": len(ordered_all),
            "confirmed_duplicates_removed": dup_stats["confirmed_secondary"],
            "suspected_duplicates_flagged": dup_stats["suspected_records"],
            "published_listings": len(ordered_published),
            "by_district": district_counts,
            "by_source": source_counts,
            "by_price_basis": price_basis_counts,
        },
        "files": {
            file_path.name: {
                "sha256": sha256_file(file_path),
                "row_count": file_row_counts[file_path.name],
            }
            for file_path in (listings_path, listings_all_path, review_path)
            if file_path.exists()
        },
    }
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2)
    manifest_path.write_text(manifest_text, encoding="utf-8")
    if save_snapshot:
        release_dir = data_dir / "releases" / dataset_version
        atomic_write_csv(release_dir / "listings.csv", STANDARD_FIELDS, ordered_published)
        atomic_write_csv(release_dir / "listings_all.csv", STANDARD_FIELDS, ordered_all)
        atomic_write_csv(release_dir / "records_to_review.csv", REVIEW_FIELDS, review_rows)
        (release_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")

    logger.info(
        "ETL complete (%s): raw=%d rejected=%d review=%d confirmed_dups=%d suspected=%d published=%d",
        run_id,
        raw_count,
        rejected_count,
        len(review_rows),
        dup_stats["confirmed_secondary"],
        dup_stats["suspected_records"],
        len(ordered_published),
    )
    return PipelineSummary(
        run_id=run_id,
        raw_count=raw_count,
        rejected_count=rejected_count,
        needs_review_count=len(review_rows),
        confirmed_duplicate_count=dup_stats["confirmed_secondary"],
        suspected_duplicate_count=dup_stats["suspected_records"],
        clean_count=len(ordered_published),
        listings_path=listings_path,
        listings_all_path=listings_all_path,
        review_path=review_path,
        manifest_path=manifest_path,
        by_district=district_counts,
        by_source=source_counts,
        by_price_basis=price_basis_counts,
    )


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="Directory holding source *_rooms.csv files")
    parser.add_argument("--ref-dir", type=Path, default=REF_DIR, help="Directory holding reference catalog CSVs")
    parser.add_argument("--output", type=Path, default=None, help="Output published listings.csv path")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip running bots and process existing CSV files")
    parser.add_argument("--snapshot", action="store_true", help="Also write an immutable releases/<version> snapshot")
    parser.add_argument("--validate", action="store_true", help="Validate existing outputs and manifest against reference catalogs")
    args = parser.parse_args()

    if args.validate:
        errors = validate_release(data_dir=args.data_dir, ref_dir=args.ref_dir)
        if errors:
            for err in errors:
                print(f"VALIDATION ERROR: {err}", file=sys.stderr)
            return 1
        print(f"Validation passed for {args.data_dir} against {args.ref_dir}")
        return 0

    summary = run_pipeline(
        data_dir=args.data_dir,
        output_path=args.output,
        skip_scrape=args.skip_scrape,
        save_snapshot=args.snapshot,
    )
    print(
        f"Published listings: {summary.clean_count} "
        f"(raw={summary.raw_count}, rejected={summary.rejected_count}, review={summary.needs_review_count}, "
        f"confirmed_dups={summary.confirmed_duplicate_count}, suspected={summary.suspected_duplicate_count})"
    )
    print(f"By district: {summary.by_district}")
    print(f"By source: {summary.by_source}")
    print(f"By price_basis: {summary.by_price_basis}")
    print(f"Output: {summary.listings_path} | Manifest: {summary.manifest_path}")
    return 0 if summary.clean_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
