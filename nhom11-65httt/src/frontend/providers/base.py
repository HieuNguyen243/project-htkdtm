"""Base provider interface, schema validation, and safe listing join logic."""

from __future__ import annotations

import csv
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import REQUIRED_LISTING_COLUMNS


class ProviderError(Exception):
    """Raised when input files or TV3 responses violate the expected contract."""


@dataclass
class RecommendationResponse:
    """Normalized response contract returned to the Streamlit UI."""

    status: str  # ok | no_match | invalid_request | module_error | unsimulated_mock
    mode_label: str
    is_mock: bool
    dataset_version: str
    algorithm_version: str
    candidate_count: int = 0
    items: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    applied_preferences: dict[str, Any] = field(default_factory=dict)


def validate_preferences(preferences: dict[str, Any]) -> list[str]:
    """Validate user preference form fields before calling any provider."""
    errors: list[str] = []
    budget = preferences.get("budget_vnd")
    if budget is None or not isinstance(budget, (int, float)) or budget <= 0:
        errors.append("Ngân sách phải là số dương (VNĐ/tháng).")

    occupants = preferences.get("occupants")
    if occupants is None or not isinstance(occupants, int) or occupants < 1:
        errors.append("Số người ở phải là số nguyên >= 1.")

    top_k = preferences.get("top_k", 10)
    if not isinstance(top_k, int) or top_k < 1 or top_k > 50:
        errors.append("Số lượng gợi ý (top_k) phải nằm trong khoảng 1–50.")

    if not preferences.get("price_basis"):
        errors.append("Vui lòng chọn cơ sở giá (theo phòng hoặc theo người).")

    return errors


def _parse_json_field(raw_value: str, fallback: Any) -> Any:
    if not raw_value or not raw_value.strip():
        return fallback
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback


def _parse_optional_float(raw_value: str) -> float | None:
    if raw_value is None or str(raw_value).strip() == "":
        return None
    try:
        return float(raw_value)
    except ValueError:
        return None


def _parse_optional_int(raw_value: str) -> int | None:
    if raw_value is None or str(raw_value).strip() == "":
        return None
    try:
        return int(float(raw_value))
    except ValueError:
        return None


def load_listings_csv(csv_path: Path) -> dict[str, dict[str, Any]]:
    """Load listings CSV into a dict keyed strictly by listing_id."""
    if not csv_path.exists():
        raise ProviderError(f"Không tìm thấy tệp dữ liệu danh sách phòng: {csv_path.name}")

    listings_by_id: dict[str, dict[str, Any]] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ProviderError("Tệp CSV danh sách phòng rỗng hoặc thiếu dòng tiêu đề.")

        missing_cols = [col for col in REQUIRED_LISTING_COLUMNS if col not in reader.fieldnames]
        if missing_cols:
            raise ProviderError(f"Tệp CSV thiếu cột bắt buộc theo schema: {', '.join(missing_cols)}")

        for row in reader:
            listing_id = (row.get("listing_id") or "").strip()
            if not listing_id:
                continue
            listings_by_id[listing_id] = {
                "listing_id": listing_id,
                "source_name": (row.get("source_name") or "").strip(),
                "source_url": (row.get("source_url") or "").strip(),
                "collected_at": (row.get("collected_at") or "").strip(),
                "posted_date": (row.get("posted_date") or "").strip(),
                "title": (row.get("title") or "").strip(),
                "description_clean": (row.get("description_clean") or "").strip(),
                "room_type": (row.get("room_type") or "").strip(),
                "area_m2": _parse_optional_float(row.get("area_m2", "")),
                "rent_vnd_month": _parse_optional_float(row.get("rent_vnd_month", "")),
                "price_basis": (row.get("price_basis") or "").strip(),
                "deposit_vnd": _parse_optional_float(row.get("deposit_vnd", "")),
                "deposit_months": _parse_optional_float(row.get("deposit_months", "")),
                "fees": _parse_json_field(row.get("fees_json", ""), {}),
                "amenities": _parse_json_field(row.get("amenities_json", ""), {}),
                "district": (row.get("district") or "").strip(),
                "ward": (row.get("ward") or "").strip(),
                "address_clean": (row.get("address_clean") or "").strip(),
                "latitude": _parse_optional_float(row.get("latitude", "")),
                "longitude": _parse_optional_float(row.get("longitude", "")),
                "geo_confidence": (row.get("geo_confidence") or "unknown").strip(),
                "max_occupants": _parse_optional_int(row.get("max_occupants", "")),
                "quality_flags": _parse_json_field(row.get("quality_flags_json", ""), []),
            }
    return listings_by_id


def join_results_with_listings(
    raw_items: list[dict[str, Any]],
    listings_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Join recommendation items with listing records strictly by listing_id."""
    joined: list[dict[str, Any]] = []
    missing_ids: list[str] = []

    for item in raw_items:
        listing_id = str(item.get("listing_id") or "").strip()
        if not listing_id or listing_id not in listings_by_id:
            missing_ids.append(listing_id or "<rỗng>")
            continue
        joined.append(
            {
                "listing": listings_by_id[listing_id],
                "rank": item.get("rank"),
                "score": item.get("score"),
                "score_components": item.get("score_components") or {},
                "reasons": list(item.get("reasons") or []),
                "warnings": list(item.get("warnings") or []),
            }
        )

    errors: list[str] = []
    if missing_ids:
        errors.append(
            "Không tìm thấy mã tin trong tệp danh sách hiện tại (không thay thế bằng dòng khác): "
            + ", ".join(missing_ids)
        )
    return joined, errors


class DataProvider(ABC):
    """Abstract adapter separating UI from data loading and TV3 scoring."""

    @abstractmethod
    def get_dataset_info(self) -> dict[str, Any]:
        """Return metadata about dataset version, count, and mode."""

    @abstractmethod
    def get_profiles(self) -> list[dict[str, Any]]:
        """Return available sample profiles (empty in real mode if unused)."""

    @abstractmethod
    def get_listing_by_id(self, listing_id: str) -> dict[str, Any] | None:
        """Fetch a single listing record by listing_id."""

    @abstractmethod
    def recommend(
        self,
        preferences: dict[str, Any],
        profile_id: str | None = None,
    ) -> RecommendationResponse:
        """Execute or retrieve recommendations for the given preferences."""
