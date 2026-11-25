"""Collect current room-rental metadata from Thuephongtro's district filters."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path

from lxml import html

from base_scraper import PoliteHttpFetcher, atomic_write_csv
from config import (
    DATA_DIR,
    DISTRICTS,
    REJECTION_FIELDS as REJECT_FIELDS,
    USER_AGENT,
    VN_TZ,
    clean_text as clean,
    fold_text as fold,
    redact_pii as redact,
)


BASE = "https://thuephongtro.com"
FIELDS = ("listing_id", "source_name", "source_record_key", "source_url", "district", "title",
          "room_type", "price_raw", "rent_vnd_month", "price_basis", "area_m2", "address",
          "posted_at", "expires_at", "listing_status", "collected_at")
DETAIL_PATH = re.compile(r"^/[^/]+-(\d+)\.html$")
NON_ROOM = re.compile(
    r"bán\s+(?:nhà|đất|căn\s*hộ|chung\s*cư)|nhà\s+nguyên\s+căn|căn\s+hộ|"
    r"chung\s+cư|mặt\s+bằng|văn\s+phòng|sang\s+nhượng|"
    r"\b[1-9]\s*n\s*1\s*k\b|\b[1-9]\s*ngủ\b|\b[1-9]\s*khách\s*[1-9]\s*ngủ\b",
    re.I,
)
ROOM = re.compile(r"phòng\s*(?:trọ|ở|khép\s*kín|cho\s*thuê)?|studio|gác\s*xép", re.I)
SEEKING = re.compile(r"\b(?:cần\s+thuê|tìm\s+(?:thuê\s+)?phòng|cần\s+tìm\s+phòng)\b", re.I)


def district_url(slug: str, page: int = 1) -> str:
    if slug not in DISTRICTS or page < 1:
        raise ValueError("district/page outside scope")
    url = f"{BASE}/cho-thue-phong-tro-{slug}"
    return url if page == 1 else f"{url}?page={page}"


def detail_url(href: str) -> tuple[str, str]:
    parts = urllib.parse.urlsplit(urllib.parse.urljoin(BASE, href))
    match = DETAIL_PATH.fullmatch(parts.path)
    if parts.scheme != "https" or parts.netloc != "thuephongtro.com" or not match or parts.query:
        raise ValueError("detail URL outside source")
    return BASE + parts.path, match.group(1)


def text_at(tree: html.HtmlElement, xpath: str) -> str:
    nodes = tree.xpath(xpath)
    return clean(nodes[0].text_content()) if nodes else ""


def parse_price(value: str) -> int:
    match = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*triệu\s*/\s*tháng\s*", value, re.I)
    if not match:
        raise ValueError("price is not unambiguous VND/month")
    number = float(match.group(1).replace(",", "."))
    if not 0 < number <= 30:
        raise ValueError("implausible monthly price")
    return round(number * 1_000_000)


def date_at(value: str) -> datetime:
    return datetime.strptime(value, "%d/%m/%Y").replace(tzinfo=VN_TZ)


def room_title(title: str) -> bool:
    return bool(ROOM.search(title) and not NON_ROOM.search(title) and not SEEKING.search(title))


def parse_list(page: bytes, district: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    tree = html.fromstring(page.decode("utf-8", "replace"))
    if clean(tree.xpath("string(//h1)")) != f"Cho thuê phòng trọ {district} đẹp giá tốt":
        raise ValueError("district rental filter not confirmed")
    candidates, rejected = [], []
    for card in tree.xpath('//article[contains(concat(" ",normalize-space(@class)," ")," post-item ")]'):
        href = card.xpath("string(./a/@href)")
        try:
            url, key = detail_url(href)
        except ValueError:
            continue
        title = text_at(card, './/h3[contains(@class,"title")]')
        address = text_at(card, './/div[contains(@class,"post-address")]')
        price_raw = text_at(card, './/span[contains(@class,"price")]')
        if not room_title(title):
            reason = "not explicitly a room rental or non-room property"
        elif fold(district) not in fold(address) or "ha noi" not in fold(address):
            reason = "district/address mismatch"
        else:
            try:
                parse_price(price_raw)
                reason = ""
            except ValueError as exc:
                reason = str(exc)
        if reason:
            rejected.append({"source_url": url, "district": district, "reason": reason})
        else:
            candidates.append({"source_url": url, "key": key, "district": district,
                               "title": title, "price_raw": price_raw})
    return candidates, rejected


def parse_detail(page: bytes, candidate: dict[str, str], now: datetime,
                 include_expired: bool = False) -> dict[str, str]:
    tree = html.fromstring(page.decode("utf-8", "replace"))
    breadcrumb = tree.xpath('//div[@id="breadcrumb"]//a[@href]/@href')
    slug = next(k for k, v in DISTRICTS.items() if v == candidate["district"])
    required = {f"{BASE}/cho-thue-phong-tro", district_url(slug)}
    if not required.issubset(set(breadcrumb)):
        raise ValueError("detail rental category/district mismatch")
    title = clean(tree.xpath("string(//h1)"))
    if not room_title(title) or fold(title) != fold(candidate["title"]):
        raise ValueError("detail title is not matching room rental")
    description = clean(tree.xpath('string(//div[contains(@class,"section-content")])'))
    if not description:
        raise ValueError("missing rental description")
    if NON_ROOM.search(description) or SEEKING.search(description):
        raise ValueError("detail description indicates non-room property or seeking ad")
    address = text_at(tree, '//div[contains(@class,"post-features")]//p[contains(@class,"post-address")]')
    if fold(candidate["district"]) not in fold(address) or "ha noi" not in fold(address):
        raise ValueError("detail address outside district")
    price_raw = text_at(tree, '//div[contains(@class,"post-features")]//span[contains(@class,"post-price")]')
    rent = parse_price(price_raw)
    if rent != parse_price(candidate["price_raw"]):
        raise ValueError("list/detail price mismatch")
    rows = {clean(row.xpath("string(./strong)")): clean(row.xpath("string(./span)"))
            for row in tree.xpath('//div[contains(@class,"section-detail-row")]')}
    if rows.get("Mã tin") != candidate["key"]:
        raise ValueError("detail listing id mismatch")
    if not rows.get("Ngày hết hạn"):
        raise ValueError("missing expiry date")
    expiry = date_at(rows["Ngày hết hạn"])
    expired = expiry.date() < now.astimezone(VN_TZ).date()
    if expired and not include_expired:
        raise ValueError("listing expired")
    area = text_at(tree, '//div[contains(@class,"post-features")]//span[contains(@class,"post-acreage")]')
    area_match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*m\s*[²2]", area, re.I)
    if not area_match:
        raise ValueError("missing room area")
    return {"listing_id": f"thuephongtro:{candidate['key']}", "source_name": "thuephongtro",
            "source_record_key": candidate["key"], "source_url": candidate["source_url"],
            "district": candidate["district"], "title": redact(title), "room_type": "phòng trọ",
            "price_raw": price_raw, "rent_vnd_month": str(rent), "price_basis": "unknown",
            "area_m2": area_match.group(1).replace(",", "."), "address": redact(address.removeprefix("Địa chỉ: ")),
            "posted_at": date_at(rows["Ngày cập nhật"]).date().isoformat() if rows.get("Ngày cập nhật") else "",
            "expires_at": expiry.date().isoformat(),
            "listing_status": "expired" if expired else "unverified_available",
            "collected_at": now.isoformat()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=1, help="pages per district")
    parser.add_argument("--limit-per-district", type=int, default=10, help="detail requests per district; 0 means all")
    parser.add_argument("--include-expired", action="store_true", help="include expired room ads, marked expired, for historical analysis")
    parser.add_argument("--delay", type=float, default=2.0, help="minimum seconds between HTTP requests")
    parser.add_argument("--output", type=Path, default=DATA_DIR / "thuephongtro_rooms.csv")
    args = parser.parse_args()
    if args.pages < 1 or args.limit_per_district < 0 or args.delay < 1:
        parser.error("pages must be >=1, limit >=0, delay >=1")
    try:
        fetch = PoliteHttpFetcher(BASE, delay=args.delay, user_agent=USER_AGENT, require_html=False, disallow_redirects=True)
        now = datetime.now(VN_TZ)
        accepted, rejected, seen = [], [], set()
        for slug, district in DISTRICTS.items():
            checked = 0
            for page in range(1, args.pages + 1):
                candidates, list_rejected = parse_list(fetch.get(district_url(slug, page), max_bytes=2_000_000), district)
                rejected.extend(list_rejected)
                for candidate in candidates:
                    if candidate["key"] in seen:
                        continue
                    seen.add(candidate["key"])
                    if args.limit_per_district and checked >= args.limit_per_district:
                        continue
                    checked += 1
                    try:
                        accepted.append(parse_detail(fetch.get(candidate["source_url"], max_bytes=2_000_000), candidate, now,
                                                     include_expired=args.include_expired))
                    except ValueError as exc:
                        rejected.append({"source_url": candidate["source_url"], "district": district, "reason": str(exc)})
        atomic_write_csv(args.output, FIELDS, accepted)
        atomic_write_csv(args.output.with_name(args.output.stem + "_rejected.csv"), REJECT_FIELDS, rejected)
        print(f"Accepted {len(accepted)} room-rental ads; rejected {len(rejected)} listings. Output: {args.output}")
        return 0
    except (ValueError, urllib.error.URLError, RuntimeError) as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
