"""Shared configuration, schema definition, and text normalization helpers."""

from __future__ import annotations

import re
import unicodedata
from datetime import timedelta, timezone
from pathlib import Path

DISTRICTS: dict[str, str] = {
    "thanh-xuan": "Thanh Xuân",
    "dong-da": "Đống Đa",
    "cau-giay": "Cầu Giấy",
}

OTHER_HANOI_DISTRICTS: tuple[str, ...] = (
    "Ba Đình",
    "Bắc Từ Liêm",
    "Hà Đông",
    "Hai Bà Trưng",
    "Hoài Đức",
    "Hoàng Mai",
    "Hoàn Kiếm",
    "Long Biên",
    "Nam Từ Liêm",
    "Tây Hồ",
    "Thanh Trì",
)

USER_AGENT = "TLU-RentalResearchBot/1.0 (student research; contact: 2351160519@e.tlu.edu.vn)"
VN_TZ = timezone(timedelta(hours=7))
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
REF_DIR = DATA_DIR / "reference"
SCHEMA_VERSION = "1.0.0-draft.1"

STANDARD_FIELDS: tuple[str, ...] = (
    "listing_id",
    "source_name",
    "source_record_key",
    "public_code",
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
    "available_rooms",
    "duplicate_group_id",
    "duplicate_status",
    "is_representative",
    "listing_status",
    "record_status",
    "quality_flags_json",
)

REJECTION_FIELDS: tuple[str, ...] = ("source_url", "district", "reason")

PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?84(?:[.\s-]*\d){9,10}|0[35789](?:[.\s-]*\d){7,9}|0(?:[.\s-]*\d){9,10})(?!\d)"
)
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
NON_ROOM_PATTERN = re.compile(
    r"\b(?:bán\s+(?:nhà|đất|căn\s*hộ|chung\s*cư)|nhà\s+nguyên\s+căn|"
    r"mặt\s+bằng|văn\s+phòng|sang\s+nhượng|căn\s+hộ|"
    r"[1-9]\s*n\s*1\s*k|[1-9]\s*ngủ\s*1\s*khách|"
    r"cần\s+thuê|tìm\s+(?:thuê\s+)?phòng|cần\s+tìm\s+phòng)\b",
    re.I,
)
MONTHLY_RENT_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(triệu|tr|nghìn|ngàn|k)\s*/\s*tháng",
    re.I,
)


def clean_text(value: str) -> str:
    """Collapse redundant whitespace into single spaces."""
    return " ".join(value.split())


def fold_text(value: str) -> str:
    """Normalize Vietnamese text to lowercase ASCII for accent-insensitive comparison."""
    normalized = unicodedata.normalize("NFD", value.casefold()).replace("đ", "d")
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def redact_pii(value: str) -> str:
    """Redact phone numbers and email addresses before storing text."""
    return clean_text(EMAIL_PATTERN.sub("[email]", PHONE_PATTERN.sub("[số điện thoại]", value)))


def is_non_room_listing(text: str) -> bool:
    """Return True if text indicates a non-room property, sale ad, or seeking ad."""
    return bool(NON_ROOM_PATTERN.search(text))


def has_conflicting_district(text: str, expected_district: str) -> bool:
    """Return True if text mentions a Hanoi district other than expected_district."""
    folded = fold_text(text)
    all_districts = (*DISTRICTS.values(), *OTHER_HANOI_DISTRICTS)
    return any(fold_text(name) in folded for name in all_districts if name != expected_district)


def parse_monthly_rent(value: str) -> int | None:
    """Parse a Vietnamese monthly rent string into VND/month, or None if invalid."""
    match = MONTHLY_RENT_PATTERN.search(value)
    if not match:
        return None
    amount = float(match.group(1).replace(",", "."))
    unit = match.group(2).lower()
    multiplier = 1_000_000 if unit in ("triệu", "tr") else 1_000
    rent = round(amount * multiplier)
    return rent if rent > 0 else None
