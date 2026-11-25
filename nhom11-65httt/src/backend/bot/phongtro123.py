"""Collect public room listings from three Hanoi districts on Phongtro123."""

from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from lxml import html

from base_scraper import PoliteHttpFetcher, atomic_write_csv
from config import DATA_DIR, DISTRICTS, USER_AGENT, clean_text, redact_pii


BASE_URL = "https://phongtro123.com"
FIELDS = [
    "listing_id", "source_name", "source_record_key", "source_url",
    "district", "title", "price_raw", "rent_vnd_month", "price_basis",
    "area_m2", "address", "amenities", "description_clean", "posted_at", "collected_at",
]
LISTING_ID = re.compile(r"-pr(\d+)\.html(?:\?.*)?$", re.I)
NON_ROOM_TITLE = re.compile(
    r"\b(?:bán nhà|bán đất|bán căn hộ|nhà nguyên căn|mặt bằng|văn phòng|"
    r"căn hộ|1n1k|2n1k|1 ngủ 1 khách|2 ngủ 1 khách)\b",
    re.I,
)


def monthly_rent(value: str) -> str:
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(triệu|tr|nghìn|ngàn|k)\s*/\s*tháng", value, re.I)
    if not match:
        return ""
    amount = float(match.group(1).replace(",", "."))
    multiplier = 1_000_000 if match.group(2).lower() in ("triệu", "tr") else 1_000
    return str(round(amount * multiplier))


def parse_posted_at(value: str) -> str:
    match = re.search(r"(\d{1,2}:\d{2})\s+(\d{2}/\d{2}/\d{4})", value)
    if not match:
        return ""
    from datetime import timedelta

    vietnam_time = datetime.strptime(f"{match.group(2)} {match.group(1)}", "%d/%m/%Y %H:%M")
    return vietnam_time.replace(tzinfo=timezone(timedelta(hours=7))).astimezone(timezone.utc).isoformat()


def listing_links(page: bytes) -> list[str]:
    tree = html.fromstring(page)
    links = []
    seen = set()
    for anchor in tree.xpath('//ul[contains(concat(" ", normalize-space(@class), " "), " post__listing ")]//a[@href]'):
        url = urllib.parse.urljoin(BASE_URL, anchor.get("href"))
        url = urllib.parse.urlsplit(url)._replace(query="", fragment="").geturl()
        if LISTING_ID.search(url) and url not in seen:
            seen.add(url)
            links.append(url)
    return links


def parse_listing(page: bytes, url: str, district: str, collected_at: str) -> dict[str, str]:
    tree = html.fromstring(page)
    headers = tree.xpath("//main//header[h1]")
    if not headers:
        raise ValueError("missing listing header")
    header = headers[0]
    title = clean_text(header.xpath("./h1")[0].text_content())
    details = {}
    for row in header.xpath(".//table//tr"):
        cells = row.xpath("./td")
        if len(cells) == 2:
            details[clean_text(cells[0].text_content()).rstrip(":")] = clean_text(cells[1].text_content())

    match = LISTING_ID.search(url)
    source_key = details.get("Mã tin", "").lstrip("#")
    if not match or source_key != match.group(1):
        raise ValueError("listing ID mismatch")
    if district.casefold() not in details.get("Quận huyện", "").casefold():
        raise ValueError("district mismatch")
    if "cho thuê phòng trọ" not in details.get("Quận huyện", "").casefold():
        raise ValueError("not in room-rental category")
    if NON_ROOM_TITLE.search(title):
        raise ValueError("non-room property type or sale listing")

    price_nodes = header.xpath('.//span[contains(concat(" ", normalize-space(@class), " "), " text-green ")]')
    price_raw = clean_text(price_nodes[0].text_content()) if price_nodes else ""
    rent_vnd_month = monthly_rent(price_raw)
    if not rent_vnd_month:
        raise ValueError("missing monthly rent")
    area_nodes = header.xpath('.//span[contains(translate(., "M", "m"), "m") and not(contains(@class,"text-green"))]')
    area_text = clean_text(area_nodes[0].text_content()) if area_nodes else ""
    area_match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*m\s*2\b", area_text, re.I)
    description_nodes = tree.xpath('//h2[normalize-space()="Thông tin mô tả"]/parent::div')
    description = " ".join(clean_text(p.text_content()) for p in description_nodes[0].xpath("./p") if clean_text(p.text_content())) if description_nodes else ""
    checked_amenities = [
        clean_text(node.text_content())
        for node in tree.xpath('//h2[normalize-space()="Nổi bật"]/parent::div//div[contains(@class,"col")][.//i[contains(@class,"green")]]')
        if clean_text(node.text_content())
    ]

    return {
        "listing_id": f"phongtro123:{source_key}",
        "source_name": "phongtro123",
        "source_record_key": source_key,
        "source_url": url,
        "district": district,
        "title": redact_pii(title),
        "price_raw": price_raw,
        "rent_vnd_month": rent_vnd_month,
        "price_basis": "unknown",
        "area_m2": area_match.group(1).replace(",", ".") if area_match else "",
        "address": redact_pii(details.get("Địa chỉ", "")),
        "amenities": ", ".join(checked_amenities),
        "description_clean": redact_pii(description),
        "posted_at": parse_posted_at(details.get("Ngày đăng", "")),
        "collected_at": collected_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=3, help="Maximum pages per district")
    parser.add_argument("--delay", type=float, default=2.0, help="Minimum seconds between requests")
    parser.add_argument("--fresh", action="store_true", help="Ignore existing CSV rows and scrape cleanly")
    parser.add_argument("--skip-existing", action="store_true", help="Skip detail requests for listing IDs already in CSV")
    parser.add_argument("--output", type=Path, default=DATA_DIR / "phongtro123_rooms.csv")
    args = parser.parse_args()
    if args.pages < 1 or args.delay < 1:
        parser.error("--pages and --delay must be positive; delay must be at least one second")

    fetcher = PoliteHttpFetcher(BASE_URL, delay=args.delay, user_agent=USER_AGENT)
    records = {}
    if args.output.exists() and not args.fresh:
        with args.output.open(encoding="utf-8-sig", newline="") as stream:
            for record in csv.DictReader(stream):
                if (
                    record.get("source_name") == "phongtro123"
                    and record.get("listing_id")
                    and record.get("district") in DISTRICTS.values()
                    and record.get("rent_vnd_month")
                    and not NON_ROOM_TITLE.search(record.get("title", ""))
                ):
                    records[record["listing_id"]] = {field: record.get(field, "") for field in FIELDS}

    collected_at = datetime.now(timezone.utc).isoformat()
    found = set()
    errors = 0
    for slug, district in DISTRICTS.items():
        for page_number in range(1, args.pages + 1):
            url = f"{BASE_URL}/tinh-thanh/ha-noi/quan-{slug}?page={page_number}"
            try:
                urls = listing_links(fetcher.get(url))
            except Exception as error:
                print(f"ERROR list {url}: {error}", file=sys.stderr)
                errors += 1
                break
            if not urls:
                print(f"No listings at {url}")
                break
            for listing_url in urls:
                if listing_url in found:
                    continue
                found.add(listing_url)
                id_match = LISTING_ID.search(listing_url)
                if args.skip_existing and id_match and f"phongtro123:{id_match.group(1)}" in records:
                    continue
                try:
                    record = parse_listing(fetcher.get(listing_url), listing_url, district, collected_at)
                    records[record["listing_id"]] = record
                except Exception as error:
                    print(f"ERROR detail {listing_url}: {error}", file=sys.stderr)
                    errors += 1
            print(f"{district}, page {page_number}: {len(urls)} links, {len(records)} total records", flush=True)
            atomic_write_csv(args.output, FIELDS, [records[k] for k in sorted(records)])
    if records:
        atomic_write_csv(args.output, FIELDS, [records[k] for k in sorted(records)])
    print(f"Saved {len(records)} records to {args.output}; {errors} errors")
    return 0 if records and errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
