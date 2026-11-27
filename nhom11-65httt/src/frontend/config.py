"""Shared configuration for the TV4 Streamlit rental analysis frontend."""

from __future__ import annotations

from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = FRONTEND_DIR / "fixtures"
PROJECT_DATA_DIR = FRONTEND_DIR.parents[1] / "data"

SUPPORTED_UI_VERSION = "1.0.0-tv4"
DEFAULT_SAMPLE_LISTINGS_PATH = FIXTURES_DIR / "sample_listings.csv"
DEFAULT_SAMPLE_RESULTS_PATH = FIXTURES_DIR / "sample_results.json"
DEFAULT_REAL_LISTINGS_PATH = PROJECT_DATA_DIR / "listings.csv"
DEFAULT_REAL_MANIFEST_PATH = PROJECT_DATA_DIR / "manifest.json"

PROVIDER_MODE_MOCK = "mock"
PROVIDER_MODE_REAL = "real"

DISTRICTS: tuple[str, ...] = ("Thanh Xuân", "Đống Đa", "Cầu Giấy")

CAMPUSES: tuple[dict[str, object], ...] = (
    {
        "campus_id": "tlu_hanoi",
        "school_name": "Trường Đại học Thủy lợi",
        "campus_name": "Cơ sở chính Hà Nội",
        "address_text": "175 Tây Sơn, phường Kim Liên, Hà Nội",
        "district": "Đống Đa",
    },
    {
        "campus_id": "utc_hanoi",
        "school_name": "Trường Đại học Giao thông Vận tải",
        "campus_name": "Cơ sở Hà Nội",
        "address_text": "Số 3 Cầu Giấy, phường Láng, Hà Nội",
        "district": "Cầu Giấy",
    },
)

ROOM_TYPES: dict[str, str] = {
    "room": "Phòng trọ",
    "self_contained": "Phòng khép kín",
    "studio_mini": "Studio mini",
    "loft_room": "Phòng có gác",
    "shared_place": "Chỗ ở ghép",
}

AMENITIES: dict[str, str] = {
    "air_conditioner": "Điều hòa",
    "parking": "Chỗ để xe",
    "private_bathroom": "Vệ sinh riêng",
    "wifi": "Internet/Wi-Fi",
    "washer": "Máy giặt",
    "balcony": "Ban công",
    "water_heater": "Bình nóng lạnh",
    "kitchen": "Khu bếp",
}

PRICE_BASIS_LABELS: dict[str, str] = {
    "room": "Theo phòng (VNĐ/tháng)",
    "person": "Theo người (VNĐ/người/tháng)",
}

COST_MODE_LABELS: dict[str, str] = {
    "rent_only": "Chỉ xét tiền thuê niêm yết",
    "estimated_total": "Tổng chi phí ước tính (nếu đủ dữ liệu phí)",
}

MAX_COMPARE_ITEMS = 4
MIN_COMPARE_ITEMS = 2

REQUIRED_LISTING_COLUMNS: tuple[str, ...] = (
    "listing_id",
    "source_name",
    "source_url",
    "collected_at",
    "posted_date",
    "title",
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
    "quality_flags_json",
)
