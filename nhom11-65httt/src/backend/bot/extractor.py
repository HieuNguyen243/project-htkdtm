"""Rule-based Vietnamese extraction aligned with data/reference catalogs."""

from __future__ import annotations

import hashlib
import json
import re

from config import clean_text, fold_text

AMENITY_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("air_conditioner", ("điều hòa", "điều hoà", "máy lạnh"), ("không điều hòa", "không có điều hòa", "chưa điều hòa", "không máy lạnh")),
    ("parking", ("chỗ để xe", "để xe", "hầm để xe", "bãi xe"), ("không chỗ để xe", "không có chỗ để xe")),
    ("private_bathroom", ("khép kín", "wc riêng", "vệ sinh riêng", "vskk"), ("vệ sinh chung", "wc chung")),
    ("wifi", ("wifi", "wi-fi", "internet", "mạng"), ("không có mạng", "không wifi")),
    ("washer", ("máy giặt",), ("không máy giặt", "không có máy giặt")),
    ("balcony", ("ban công",), ("không ban công", "không có ban công")),
    ("water_heater", ("nóng lạnh", "bình nóng lạnh", "bình nước nóng"), ("không nóng lạnh", "không có nóng lạnh")),
    ("kitchen", ("kệ bếp", "tủ bếp", "bếp riêng", "bàn bếp", "khu nấu ăn"), ("không có bếp", "không nấu ăn", "cấm nấu ăn")),
)

ROOM_TYPE_ALIASES: dict[str, str] = {
    "phòng trọ": "room",
    "phòng đơn": "room",
    "room": "room",
    "phòng khép kín": "self_contained",
    "self_contained": "self_contained",
    "studio": "studio_mini",
    "studio mini": "studio_mini",
    "studio_mini": "studio_mini",
    "gác xép": "loft_room",
    "duplex": "loft_room",
    "loft_room": "loft_room",
    "ở ghép": "shared_place",
    "shared_place": "shared_place",
    "ccmn": "self_contained",
}

WARD_PATTERN = re.compile(r"(?:phường|p\.?)\s+([^,;•\n]+)", re.I)
PER_PERSON_PATTERN = re.compile(r"/\s*(?:người|ng\b|khách|giường|slot)|\b(?:ở ghép|tìm bạn ở ghép|ký túc xá|ktx)\b", re.I)
RENT_PER_PERSON_DESC = re.compile(
    r"(?:giá\s*thuê|tiền\s*phòng|giá\s*phòng|thuê\s*phòng|\d+(?:[.,]\d+)?\s*(?:triệu|tr))\s*(?:/|một\s*)?(?:người|khách|giường)",
    re.I,
)
DEPOSIT_VND_PATTERN = re.compile(r"(?:tiền\s+)?cọc\s*:?\s*(\d+(?:[.,]\d+)?)\s*(triệu|tr|nghìn|ngàn|k|đ|vnđ)?", re.I)
DEPOSIT_MONTHS_PATTERN = re.compile(r"(?:tiền\s+)?cọc\s*:?\s*(\d+|một|hai|ba)\s*tháng", re.I)
NUMBER_WORDS = {"một": 1, "hai": 2, "ba": 3}

ELEC_FEE_RE = re.compile(r"điện\s*:?\s*(\d+(?:[.,]\d+)?)\s*(k|nghìn|ngàn|đ|vnđ)?\s*(?:/\s*(số|kwh|kw|tháng|người|phòng))?", re.I)
WATER_FEE_RE = re.compile(r"nước\s*:?\s*(\d+(?:[.,]\d+)?)\s*(k|nghìn|ngàn|đ|vnđ)?\s*(?:/\s*(khối|m3|người|ng|phòng|tháng))?", re.I)
NET_FEE_RE = re.compile(r"(?:mạng|internet|wifi)\s*:?\s*(\d+(?:[.,]\d+)?)\s*(k|nghìn|ngàn|đ|vnđ)?\s*(?:/\s*(phòng|người|tháng))?", re.I)
PARKING_FEE_RE = re.compile(r"(?:gửi\s*xe|để\s*xe)\s*:?\s*(\d+(?:[.,]\d+)?)\s*(k|nghìn|ngàn|đ|vnđ)?\s*(?:/\s*(xe|chiếc|phòng|tháng))?", re.I)
SERVICE_FEE_RE = re.compile(r"(?:dịch vụ|dv|vệ sinh)\s*(?:chung)?\s*:?\s*(\d+(?:[.,]\d+)?)\s*(k|nghìn|ngàn|đ|vnđ)?\s*(?:/\s*(người|phòng|tháng))?", re.I)


def extract_room_type_code(title: str, description: str, current: str = "") -> str:
    """Map listing text or source label to canonical room_types.csv room_type_code."""
    normalized_current = current.strip().lower()
    if normalized_current in ROOM_TYPE_ALIASES and normalized_current not in ("phòng trọ", "room"):
        return ROOM_TYPE_ALIASES[normalized_current]
    combined = f"{title} {description}"
    if re.search(r"\b(?:ở ghép|tìm bạn ở ghép|ký túc xá|ktx|sleepbox)\b", combined, re.I):
        return "shared_place"
    if re.search(r"\bstudio\b", combined, re.I):
        return "studio_mini"
    if re.search(r"\bgác xép\b|\bcó gác\b|\bduplex\b", combined, re.I):
        return "loft_room"
    if re.search(r"khép kín|wc riêng|vệ sinh riêng|\bccmn\b|chung cư mini", combined, re.I):
        return "self_contained"
    return "room"


def infer_price_basis(price_raw: str, title: str, description: str, room_type: str) -> str:
    """Infer whether monthly rent is per-room, per-person, or unknown."""
    head = f"{price_raw} {title}"
    if PER_PERSON_PATTERN.search(head) or room_type == "shared_place" or RENT_PER_PERSON_DESC.search(description):
        return "person"
    if re.search(r"/\s*tháng", price_raw, re.I):
        return "room"
    return "unknown"


def extract_ward(address: str) -> str:
    """Extract ward name from address when explicitly present."""
    match = WARD_PATTERN.search(address)
    if not match:
        return ""
    ward = clean_text(match.group(1))
    return re.sub(r"\b(?:quận|tp\.?|hà nội).*$", "", ward, flags=re.I).strip(" ,.-")


def clean_address(address: str) -> str:
    """Remove UI artifacts like 'Xem bản đồ' while keeping the source address intact."""
    cleaned = re.sub(r"\b(?:xem bản đồ|bản đồ)\b", "", address, flags=re.I)
    return clean_text(cleaned).strip(" ,.-")


def extract_deposit(text: str, rent_vnd_month: int | None = None, price_basis: str = "unknown") -> tuple[str, str]:
    """Extract deposit_vnd and deposit_months without guessing unstated values."""
    months_match = DEPOSIT_MONTHS_PATTERN.search(text)
    if months_match:
        raw_months = months_match.group(1).lower()
        months = NUMBER_WORDS.get(raw_months) or int(raw_months)
        if 1 <= months <= 6:
            deposit_vnd = str(rent_vnd_month * months) if (rent_vnd_month and price_basis == "room") else ""
            return deposit_vnd, str(months)

    vnd_match = DEPOSIT_VND_PATTERN.search(text)
    if vnd_match:
        amount = float(vnd_match.group(1).replace(",", "."))
        unit = (vnd_match.group(2) or "").lower()
        if unit in ("triệu", "tr"):
            return str(round(amount * 1_000_000)), ""
        if unit in ("nghìn", "ngàn", "k"):
            return str(round(amount * 1_000)), ""
        if amount >= 100_000:
            return str(round(amount)), ""
    return "", ""


def extract_amenities(explicit_amenities: str, text: str) -> dict[str, bool | None]:
    """Extract three-state (true/false/null) amenities matching amenity_catalog.csv."""
    combined = f"{explicit_amenities} {text}".lower()
    result: dict[str, bool | None] = {}
    for code, pos_terms, neg_terms in AMENITY_RULES:
        best_pos = max((len(term) for term in pos_terms if term in combined), default=0)
        best_neg = max((len(term) for term in neg_terms if term in combined), default=0)
        if best_neg == 0 and best_pos == 0:
            result[code] = None
        elif best_neg >= best_pos:
            result[code] = False
        else:
            result[code] = True
    return result


def _parse_single_fee(
    text: str,
    label_pattern: str,
    pattern: re.Pattern[str],
    default_unit: str,
) -> dict[str, object]:
    if re.search(rf"{label_pattern}\s*:?\s*(?:miễn phí|free)\b", text, re.I) or re.search(rf"\b(?:miễn phí|free|bao)\s+{label_pattern}\b", text, re.I):
        return {"amount": None, "unit": None, "status": "free"}
    match = pattern.search(text)
    if not match:
        return {"amount": None, "unit": None, "status": "unknown"}
    raw_num = match.group(1).replace(",", ".")
    unit_token = (match.group(2) or "").lower()
    val = float(raw_num)
    if unit_token in ("k", "nghìn", "ngàn") and val < 1000:
        amount = round(val * 1_000)
    elif unit_token in ("tr", "triệu"):
        amount = round(val * 1_000_000)
    else:
        amount = round(val * 1_000) if val < 100 else round(val)
    unit_ctx = (match.group(3) or "").lower()
    unit = default_unit
    if "người" in unit_ctx or unit_ctx == "ng":
        unit = "vnd_per_person_month"
    elif "phòng" in unit_ctx:
        unit = "vnd_per_room_month"
    elif "xe" in unit_ctx or "chiếc" in unit_ctx:
        unit = "vnd_per_vehicle_month"
    elif "khối" in unit_ctx or "m3" in unit_ctx:
        unit = "vnd_per_m3"
    elif "số" in unit_ctx or "kwh" in unit_ctx:
        unit = "vnd_per_kwh"
    return {"amount": amount, "unit": unit, "status": "known"}


def extract_fees(text: str) -> dict[str, dict[str, object]]:
    """Extract structured fees matching data/reference/fee_catalog.csv."""
    return {
        "electricity": _parse_single_fee(text, r"điện", ELEC_FEE_RE, "vnd_per_kwh"),
        "water": _parse_single_fee(text, r"nước", WATER_FEE_RE, "vnd_per_person_month"),
        "internet": _parse_single_fee(text, r"(?:mạng|internet|wifi)", NET_FEE_RE, "vnd_per_room_month"),
        "parking": _parse_single_fee(text, r"(?:gửi\s*xe|để\s*xe)", PARKING_FEE_RE, "vnd_per_vehicle_month"),
        "service": _parse_single_fee(text, r"(?:dịch vụ|dv|vệ sinh)", SERVICE_FEE_RE, "vnd_per_person_month"),
    }


def compute_content_hash(row: dict[str, str]) -> str:
    """Compute canonical SHA-256 hash over normalized listing content."""
    canonical = json.dumps(
        {
            "address": fold_text(row.get("address_clean", "")),
            "area_m2": str(row.get("area_m2", "")),
            "description": fold_text(row.get("description_clean", "")),
            "rent_vnd_month": str(row.get("rent_vnd_month", "")),
            "title": fold_text(row.get("title", "")),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_quality_flags(row: dict[str, str]) -> list[str]:
    """Generate standardized flag_code list matching quality_flag_catalog.csv."""
    flags: list[str] = []
    if row.get("record_status") == "rejected":
        flags.append("NON_ROOM")
    if row.get("listing_status") == "expired":
        flags.append("EXPIRED_AD")
    if not row.get("rent_vnd_month"):
        flags.append("MISSING_PRICE")
    if row.get("price_basis") in ("", "unknown"):
        flags.append("UNKNOWN_PRICE_BASIS")
    if not row.get("area_m2"):
        flags.append("MISSING_AREA")
    if not row.get("posted_at") and not row.get("posted_date"):
        flags.append("MISSING_POSTED_AT")
    if row.get("geo_confidence") in ("area_only", "unknown", ""):
        flags.append("GEO_AREA_ONLY")
    if row.get("duplicate_status") == "suspected":
        flags.append("POSSIBLE_DUPLICATE")
    if "[số điện thoại]" in row.get("description_clean", "") or "[email]" in row.get("description_clean", "") or "[số điện thoại]" in row.get("title", ""):
        flags.append("CONTACT_REDACTED")
    return flags


def enrich_row(row: dict[str, str], explicit_amenities: str = "", price_raw: str = "") -> dict[str, str]:
    """Enrich a normalized listing row with extracted attributes, JSON columns, and hash."""
    title = row.get("title", "")
    desc = row.get("description_clean", "")
    full_text = f"{title}. {desc}"
    rent_val = int(float(row["rent_vnd_month"])) if row.get("rent_vnd_month") else None

    room_type = extract_room_type_code(title, desc, row.get("room_type", ""))
    row["room_type"] = room_type
    if row.get("price_basis") in ("", "unknown", None):
        row["price_basis"] = infer_price_basis(price_raw, title, desc, room_type)

    row["address_clean"] = clean_address(row.get("address_clean", ""))
    if not row.get("ward"):
        row["ward"] = extract_ward(row["address_clean"])
    if not row.get("geo_confidence"):
        row["geo_confidence"] = "area_only" if row["address_clean"] else "unknown"

    if not row.get("deposit_vnd") or not row.get("deposit_months"):
        dep_vnd, dep_months = extract_deposit(full_text, rent_val, row.get("price_basis", "unknown"))
        if not row.get("deposit_vnd"):
            row["deposit_vnd"] = dep_vnd
        if not row.get("deposit_months"):
            row["deposit_months"] = dep_months

    amenities = extract_amenities(explicit_amenities, full_text)
    fees = extract_fees(full_text)
    row["amenities_json"] = json.dumps(amenities, ensure_ascii=False, sort_keys=True)
    row["fees_json"] = json.dumps(fees, ensure_ascii=False, sort_keys=True)
    row["content_hash"] = compute_content_hash(row)
    row["quality_flags_json"] = json.dumps(build_quality_flags(row), ensure_ascii=False)
    return row
