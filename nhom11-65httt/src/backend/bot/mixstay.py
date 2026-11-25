"""Read MixStay's public HTML room cards and JSON-LD in three Hanoi districts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from lxml import html

from base_scraper import PoliteHttpFetcher, atomic_write_csv
from config import (
    DATA_DIR,
    DISTRICTS,
    OTHER_HANOI_DISTRICTS as OTHER_DISTRICTS,
    REJECTION_FIELDS,
    USER_AGENT,
    clean_text as clean,
    fold_text as fold,
    redact_pii as redact,
)


BASE_URL = "https://mixstay.vn"
ALLOWED_TYPES = {"studio", "gác xép", "phòng đơn", "duplex"}
FIELDS = (
    "listing_id", "source_name", "source_record_key", "public_code", "source_url",
    "district", "title", "room_type", "price_raw", "rent_vnd_month", "price_basis",
    "area_m2", "address", "available_rooms", "deposit_vnd", "amenities",
    "description_clean", "posted_at", "collected_at",
)
ROOM_URL = re.compile(r"^/tin/([a-zA-Z0-9]+)$")
NON_ROOM = re.compile(
    r"bán\s+(?:nhà|đất|căn\s+hộ)|nhà\s+nguyên\s+căn|căn\s+hộ|"
    r"mặt\s+bằng|văn\s+phòng|sang\s+nhượng|"
    r"\b[12]\s*n\s*1\s*k\b|[12]\s*ngủ\s*1\s*khách",
    re.I,
)


@dataclass(frozen=True)
class Candidate:
    url: str
    key: str
    district: str
    title: str
    room_type: str
    address: str
    available_rooms: int


def canonical_room_url(value: str) -> tuple[str, str]:
    parts = urllib.parse.urlsplit(urllib.parse.urljoin(BASE_URL, value))
    match = ROOM_URL.fullmatch(parts.path.rstrip("/"))
    if parts.scheme != "https" or parts.netloc != "mixstay.vn" or not match:
        raise ValueError("invalid room URL")
    return f"{BASE_URL}{parts.path.rstrip('/')}", match.group(1)


def has_conflicting_district(value: str, district: str) -> bool:
    folded = fold(value)
    return any(fold(name) in folded for name in (*DISTRICTS.values(), *OTHER_DISTRICTS) if name != district)


def parse_listing_page(page: bytes, district: str) -> tuple[list[Candidate], list[dict[str, str]]]:
    """Read only the cards rendered in a district page's initial HTML."""
    tree = html.fromstring(page.decode("utf-8", "replace"))
    candidates = []
    rejected = []
    seen = set()
    allowed = {fold(value) for value in ALLOWED_TYPES}
    for anchor in tree.xpath('//a[starts-with(@href, "/tin/") and .//h3]'):
        try:
            url, key = canonical_room_url(anchor.get("href"))
        except ValueError:
            continue
        if key in seen:
            continue
        seen.add(key)
        title = clean(" ".join(anchor.xpath(".//h3[1]//text()")))
        labels = [clean(node.text_content()) for node in anchor.xpath(".//span")]
        room_type = next((label for label in labels if fold(label) in allowed), "")
        address_nodes = anchor.xpath(".//h3[1]/following-sibling::p[1]")
        address = clean(address_nodes[0].text_content()) if address_nodes else ""
        status = re.search(r"Còn\s+(\d+)\s+phòng", clean(anchor.text_content()), re.I)
        if NON_ROOM.search(title):
            reason = "non-room property in title"
        elif not room_type:
            reason = "unsupported room type"
        elif not address or fold(district) not in fold(address) or has_conflicting_district(title + " " + address, district):
            reason = "district not confirmed or conflicting"
        elif not status or int(status.group(1)) < 1:
            reason = "room not confirmed available"
        else:
            reason = ""
        if reason:
            rejected.append({"source_url": url, "district": district, "reason": reason})
            continue
        candidates.append(Candidate(url, key, district, title, room_type, address, int(status.group(1))))
    return candidates, rejected


def product_data(page: bytes) -> dict:
    tree = html.fromstring(page.decode("utf-8", "replace"))
    for script in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            value = json.loads(script)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        values = [value] + (value.get("@graph", []) if isinstance(value.get("@graph"), list) else [])
        for item in values:
            if isinstance(item, dict) and item.get("@type") == "Product":
                return item
    return {}


def parse_detail(page: bytes, candidate: Candidate, collected_at: str) -> dict[str, str]:
    """Use only Product JSON-LD embedded in the public /tin/ HTML."""
    product = product_data(page)
    if not product:
        raise ValueError("missing Product JSON-LD")
    if canonical_room_url(product.get("url", ""))[0] != candidate.url:
        raise ValueError("structured data URL mismatch")
    if NON_ROOM.search(str(product.get("name", ""))):
        raise ValueError("non-room property in structured data")
    properties = product.get("additionalProperty", [])
    properties = properties if isinstance(properties, list) else []
    values = {item.get("name"): str(item.get("value", "")) for item in properties if isinstance(item, dict)}
    if fold(values.get("Khu vực", "")) != fold(candidate.district):
        raise ValueError("structured district mismatch")
    area_match = re.search(r"(\d+(?:[.,]\d+)?)\s*m\s*[²2]", values.get("Diện tích", ""), re.I)
    offer = product.get("offers", {})
    offer = offer if isinstance(offer, dict) else {}
    specification = offer.get("priceSpecification", {})
    specification = specification if isinstance(specification, dict) else {}
    if offer.get("priceCurrency") != "VND" or fold(str(specification.get("unitText", ""))) != "thang":
        raise ValueError("missing VND monthly rent")
    if offer.get("availability") != "https://schema.org/InStock":
        raise ValueError("offer not in stock")
    try:
        rent = int(offer["price"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("invalid monthly rent") from None
    if rent <= 0:
        raise ValueError("nonpositive monthly rent")
    return {
        "listing_id": f"mixstay:{candidate.key}",
        "source_name": "mixstay",
        "source_record_key": candidate.key,
        "public_code": "",
        "source_url": candidate.url,
        "district": candidate.district,
        "title": redact(candidate.title),
        "room_type": candidate.room_type,
        "price_raw": f"{rent:,} ₫/tháng".replace(",", "."),
        "rent_vnd_month": str(rent),
        "price_basis": "unknown",
        "area_m2": area_match.group(1).replace(",", ".") if area_match else "",
        "address": redact(candidate.address),
        "available_rooms": str(candidate.available_rooms),
        "deposit_vnd": "",
        "amenities": "",
        "description_clean": redact(str(product.get("description", ""))),
        "posted_at": "",
        "collected_at": collected_at,
    }


def run(maximum: int, delay: float, output: Path) -> int:
    try:
        fetcher = PoliteHttpFetcher(BASE_URL, delay=delay, user_agent=USER_AGENT)
    except Exception as error:
        print(f"Cannot check MixStay robots.txt: {error}", file=sys.stderr)
        return 1
    rows: dict[str, dict[str, str]] = {}
    rejected: list[dict[str, str]] = []
    failures = 0
    collected_at = datetime.now(timezone.utc).isoformat()
    for slug, district in DISTRICTS.items():
        list_url = f"{BASE_URL}/thue-phong-tro/{slug}"
        try:
            candidates, discarded = parse_listing_page(fetcher.get(list_url), district)
        except Exception as error:
            print(f"ERROR list {list_url}: {error}", file=sys.stderr)
            failures += 1
            continue
        rejected.extend(discarded)
        candidates = candidates[:maximum] if maximum else candidates
        print(f"{district}: {len(candidates)} candidate rooms from public HTML", flush=True)
        for candidate in candidates:
            try:
                record = parse_detail(fetcher.get(candidate.url), candidate, collected_at)
                rows[record["listing_id"]] = record
            except ValueError as error:
                rejected.append({"source_url": candidate.url, "district": district, "reason": str(error)})
            except Exception as error:
                print(f"ERROR detail {candidate.url}: {error}", file=sys.stderr)
                failures += 1
    atomic_write_csv(output, FIELDS, [rows[key] for key in sorted(rows)])
    rejected_path = output.with_name(output.stem + "_rejected.csv")
    atomic_write_csv(rejected_path, REJECTION_FIELDS, rejected)
    print(f"Saved {len(rows)} rooms to {output}; {len(rejected)} rejected; {failures} errors")
    return 0 if rows and failures == 0 else 1


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit-per-district", type=int, default=24, help="Maximum matching cards per district from the first public HTML page; 0 means all cards on that page")
    parser.add_argument("--delay", type=float, default=2.0, help="Minimum seconds between HTTP requests")
    parser.add_argument("--output", type=Path, default=DATA_DIR / "mixstay_rooms.csv")
    args = parser.parse_args()
    if args.limit_per_district < 0 or args.delay < 1:
        parser.error("limit must be nonnegative and delay must be at least one second")
    return run(args.limit_per_district, args.delay, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
