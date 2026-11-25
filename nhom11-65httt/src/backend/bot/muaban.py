"""Collect public room-rental listings from Mua Ban across three Hanoi districts."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from lxml import html

from base_scraper import PoliteHttpFetcher, atomic_write_csv
from config import DATA_DIR, DISTRICTS, REJECTION_FIELDS, USER_AGENT, clean_text, fold_text, is_non_room_listing, redact_pii

BASE_URL = "https://muaban.net"
DETAIL_URL_RE = re.compile(
    r"^/bat-dong-san/cho-thue-nha-tro-phong-tro-quan-(thanh-xuan|dong-da|cau-giay)-ha-noi/[^/?#]+-id(\d+)$",
    re.I,
)
HOUSE_OR_NON_ROOM_RE = re.compile(
    r"\b(?:cho\s+thuê\s+nhà\s+(?!trọ)|nhà\s+\d+\s*tầng|tầng\s+\d+\s*&\s*\d+|"
    r"nguyên\s+tòa|cả\s+nhà|chung\s+cư(?!\s*mini)|biệt\s+thự|shophouse|ki\s*ốt|kiot)\b",
    re.I,
)
FIELDS = (
    "listing_id",
    "source_name",
    "source_record_key",
    "source_url",
    "district",
    "ward",
    "title",
    "price_raw",
    "rent_vnd_month",
    "price_basis",
    "area_m2",
    "address",
    "amenities",
    "description_clean",
    "posted_at",
    "collected_at",
)


def district_url(slug: str, page: int = 1) -> str:
    if slug not in DISTRICTS or page < 1:
        raise ValueError("district or page outside scope")
    base = f"{BASE_URL}/bat-dong-san/cho-thue-nha-tro-phong-tro-quan-{slug}-ha-noi"
    return base if page == 1 else f"{base}?page={page}"


def parse_listing_links(page: bytes, slug: str) -> list[tuple[str, str]]:
    """Extract unique (detail_url, record_key) pairs for the target district."""
    tree = html.fromstring(page.decode("utf-8", "replace"))
    seen: set[str] = set()
    results: list[tuple[str, str]] = []
    for anchor in tree.xpath("//a[@href]"):
        raw_href = anchor.get("href", "")
        parts = urllib.parse.urlsplit(urllib.parse.urljoin(BASE_URL, raw_href))
        match = DETAIL_URL_RE.fullmatch(parts.path.rstrip("/"))
        if not match or match.group(1).lower() != slug:
            continue
        key = match.group(2)
        if key in seen:
            continue
        seen.add(key)
        results.append((f"{BASE_URL}{parts.path.rstrip('/')}", key))
    return results


def _strip_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<\s*br\s*/?\s*>", " ", raw_html, flags=re.I)
    fragment = html.fromstring(f"<div>{text}</div>")
    return clean_text(fragment.text_content())


def _parse_iso_utc(value: str) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).isoformat()
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return ""


def parse_detail(page: bytes, url: str, key: str, district: str, collected_at: str) -> dict[str, str]:
    """Parse Mua Ban __NEXT_DATA__ classified payload and enforce room-rental scope."""
    tree = html.fromstring(page.decode("utf-8", "replace"))
    scripts = tree.xpath('//script[@id="__NEXT_DATA__"]/text()')
    if not scripts:
        raise ValueError("missing __NEXT_DATA__")
    payload = json.loads(scripts[0])
    classified = payload.get("props", {}).get("pageProps", {}).get("classified")
    if not isinstance(classified, dict):
        raise ValueError("missing classified payload")

    if str(classified.get("id", "")) != key:
        raise ValueError("listing ID mismatch")
    if classified.get("is_expired") or classified.get("is_outdate"):
        raise ValueError("listing expired or outdated")

    breadcrumbs = classified.get("breadcrumbs") or []
    crumb_names = [fold_text(str(item.get("name", ""))) for item in breadcrumbs if isinstance(item, dict)]
    if "cho thue" not in crumb_names:
        raise ValueError("not a rental transaction")
    expected_crumb = fold_text(f"Quận {district}")
    address_raw = clean_text(str(classified.get("address") or classified.get("location") or ""))
    if expected_crumb not in crumb_names or (address_raw and fold_text(district) not in fold_text(address_raw)):
        raise ValueError("district mismatch")

    title = clean_text(str(classified.get("title") or ""))
    body = _strip_html(str(classified.get("body") or ""))
    if not title or is_non_room_listing(title) or HOUSE_OR_NON_ROOM_RE.search(title):
        raise ValueError("non-room property type or sale listing")
    if is_non_room_listing(body[:250]):
        raise ValueError("non-room property in description")

    price = classified.get("price")
    price_display = clean_text(str(classified.get("price_display") or ""))
    if not isinstance(price, (int, float)) or price <= 0 or price > 50_000_000:
        raise ValueError("missing or implausible monthly rent")
    if price_display and not re.search(r"/\s*tháng|triệu|nghìn|đ", price_display, re.I):
        raise ValueError("unrecognized price unit")

    area_m2 = ""
    highlights: list[str] = []
    for param in classified.get("parameters") or []:
        if not isinstance(param, dict):
            continue
        label = fold_text(str(param.get("label", "")))
        val = str(param.get("value", ""))
        if "dien tich" in label:
            match = re.search(r"(\d+(?:[.,]\d+)?)\s*m", val, re.I)
            if match:
                area_m2 = match.group(1).replace(",", ".")
        elif "noi bat" in label or "tien ich" in label:
            cleaned_val = _strip_html(val)
            if cleaned_val:
                highlights.append(cleaned_val)

    if not area_m2:
        for attr in classified.get("attributes") or []:
            if isinstance(attr, dict):
                match = re.search(r"(\d+(?:[.,]\d+)?)\s*m", str(attr.get("value", "")), re.I)
                if match:
                    area_m2 = match.group(1).replace(",", ".")
                    break

    ward = ""
    for crumb in breadcrumbs:
        if isinstance(crumb, dict) and str(crumb.get("name", "")).lower().startswith("phường "):
            ward = clean_text(str(crumb["name"]).removeprefix("Phường ").removeprefix("phường "))
            break

    return {
        "listing_id": f"muaban:{key}",
        "source_name": "muaban",
        "source_record_key": key,
        "source_url": url,
        "district": district,
        "ward": ward,
        "title": redact_pii(title),
        "price_raw": price_display or f"{round(price):,} đ/tháng".replace(",", "."),
        "rent_vnd_month": str(round(price)),
        "price_basis": "unknown",
        "area_m2": area_m2,
        "address": redact_pii(address_raw),
        "amenities": ", ".join(highlights),
        "description_clean": redact_pii(body),
        "posted_at": _parse_iso_utc(str(classified.get("publish_at") or classified.get("created_at") or "")),
        "collected_at": collected_at,
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=4, help="Maximum pages per district")
    parser.add_argument("--delay", type=float, default=1.5, help="Minimum seconds between HTTP requests")
    parser.add_argument("--fresh", action="store_true", help="Ignore existing CSV rows and scrape cleanly")
    parser.add_argument("--skip-existing", action="store_true", help="Skip detail fetch for listing IDs already in CSV")
    parser.add_argument("--output", type=Path, default=DATA_DIR / "muaban_rooms.csv")
    args = parser.parse_args()
    if args.pages < 1 or args.delay < 1:
        parser.error("--pages and --delay must be positive; delay must be at least 1 second")

    fetcher = PoliteHttpFetcher(BASE_URL, delay=args.delay, user_agent=USER_AGENT)
    records: dict[str, dict[str, str]] = {}
    if args.output.exists() and not args.fresh:
        with args.output.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                lid = row.get("listing_id", "")
                if lid and row.get("district") in DISTRICTS.values() and row.get("rent_vnd_month"):
                    records[lid] = {field: row.get(field, "") for field in FIELDS}

    collected_at = datetime.now(timezone.utc).isoformat()
    rejected: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    errors = 0

    for slug, district in DISTRICTS.items():
        for page_num in range(1, args.pages + 1):
            list_url = district_url(slug, page_num)
            try:
                links = parse_listing_links(fetcher.get(list_url), slug)
            except Exception as error:
                print(f"ERROR list {list_url}: {error}", file=sys.stderr)
                errors += 1
                break
            if not links:
                break
            for detail_url, key in links:
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                lid = f"muaban:{key}"
                if args.skip_existing and lid in records:
                    continue
                try:
                    record = parse_detail(fetcher.get(detail_url), detail_url, key, district, collected_at)
                    records[record["listing_id"]] = record
                except ValueError as error:
                    rejected.append({"source_url": detail_url, "district": district, "reason": str(error)})
                except Exception as error:
                    print(f"ERROR detail {detail_url}: {error}", file=sys.stderr)
                    errors += 1
            print(f"{district}, page {page_num}: {len(links)} links, {len(records)} total records", flush=True)
            atomic_write_csv(args.output, FIELDS, [records[k] for k in sorted(records)])

    atomic_write_csv(args.output, FIELDS, [records[k] for k in sorted(records)])
    atomic_write_csv(args.output.with_name(f"{args.output.stem}_rejected.csv"), REJECTION_FIELDS, rejected)
    print(f"Saved {len(records)} records to {args.output}; {len(rejected)} rejected; {errors} errors")
    return 0 if records and errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
