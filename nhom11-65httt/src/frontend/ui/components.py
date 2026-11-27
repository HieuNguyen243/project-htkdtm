"""Safe formatting helpers for prices, fees, 3-state amenities, coordinates, and URLs."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from config import AMENITIES, PRICE_BASIS_LABELS, ROOM_TYPES


FEE_LABELS: dict[str, tuple[str, str]] = {
    "electricity_vnd_kwh": ("Tiền điện", "đ/kWh"),
    "water_vnd_m3": ("Tiền nước (theo khối)", "đ/m³"),
    "water_vnd_person": ("Tiền nước (theo người)", "đ/người/tháng"),
    "internet_vnd_month": ("Internet/Wi-Fi", "đ/tháng"),
    "service_vnd_month": ("Phí dịch vụ chung", "đ/tháng"),
    "parking_vnd_month": ("Phí gửi xe", "đ/tháng"),
}

GEO_CONFIDENCE_LABELS: dict[str, str] = {
    "exact": "Tọa độ chính xác theo địa chỉ",
    "ward_centroid": "Điểm đại diện cấp phường (không phải vị trí chính xác phòng)",
    "district_centroid": "Điểm đại diện cấp quận (chỉ mang tính tham khảo khu vực)",
    "unknown": "Chưa có dữ liệu tọa độ",
}


def format_vnd(amount: float | int | None) -> str:
    """Format VND amount or explicitly indicate missing data."""
    if amount is None:
        return "Chưa có dữ liệu"
    return f"{int(round(amount)):,}".replace(",", ".") + " đ"


def format_price_with_basis(rent_vnd: float | None, price_basis: str) -> str:
    """Display rent along with explicit price basis (per room vs per person)."""
    if rent_vnd is None:
        return "Chưa có dữ liệu"
    basis_suffix = "/người/tháng" if price_basis == "person" else "/phòng/tháng"
    return f"{format_vnd(rent_vnd)} {basis_suffix}"


def format_deposit(deposit_vnd: float | None, deposit_months: float | None) -> str:
    """Keep deposit strictly separate from monthly recurring rent/fees."""
    if deposit_vnd is not None:
        if deposit_months is not None:
            return f"{format_vnd(deposit_vnd)} ({deposit_months:g} tháng)"
        return format_vnd(deposit_vnd)
    if deposit_months is not None:
        return f"{deposit_months:g} tháng tiền phòng"
    return "Chưa có dữ liệu"


def format_fees_breakdown(fees: dict[str, Any] | None) -> list[tuple[str, str]]:
    """Return human-readable fee rows without turning missing fees into 0."""
    if not fees:
        return [("Các khoản phí (điện, nước, dịch vụ)", "Chưa có dữ liệu")]

    rows: list[tuple[str, str]] = []
    for key, (label, unit) in FEE_LABELS.items():
        val = fees.get(key)
        if val is None:
            continue
        if isinstance(val, (int, float)):
            rows.append((label, f"{int(round(val)):,}".replace(",", ".") + f" {unit}"))
        else:
            rows.append((label, str(val)))

    if not rows:
        return [("Các khoản phí (điện, nước, dịch vụ)", "Chưa có dữ liệu")]
    return rows


def format_amenity_state(value: Any) -> str:
    """Distinguish True ('Có'), False ('Không có'), and None ('Chưa biết')."""
    if value is True:
        return "Có"
    if value is False:
        return "Không có"
    return "Chưa biết"


def build_amenity_rows(amenities: dict[str, Any] | None) -> list[tuple[str, str]]:
    """Build 3-state amenity table rows using the standard catalog."""
    amenities = amenities or {}
    return [
        (label, format_amenity_state(amenities.get(code)))
        for code, label in AMENITIES.items()
    ]


def is_safe_http_url(url: str | None) -> bool:
    """Accept only http/https URLs; reject javascript:, data:, or malformed links."""
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def has_usable_coordinates(listing: dict[str, Any]) -> bool:
    """Return True only when lat/lon are valid non-(0,0) coordinates and confidence is known."""
    lat = listing.get("latitude")
    lon = listing.get("longitude")
    conf = listing.get("geo_confidence", "unknown")
    if lat is None or lon is None or conf == "unknown":
        return False
    if float(lat) == 0.0 and float(lon) == 0.0:
        return False
    return -90.0 <= float(lat) <= 90.0 and -180.0 <= float(lon) <= 180.0


def format_room_type(room_type_code: str) -> str:
    """Map room_type code to Vietnamese label."""
    return ROOM_TYPES.get(room_type_code, room_type_code or "Chưa rõ")


def format_price_basis_label(price_basis: str) -> str:
    """Map price_basis code to clear Vietnamese label."""
    return PRICE_BASIS_LABELS.get(price_basis, price_basis or "Chưa rõ")
