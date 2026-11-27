"""Real data provider adapter for connecting TV1 listings.csv and TV3 module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from config import DEFAULT_REAL_LISTINGS_PATH, DEFAULT_REAL_MANIFEST_PATH

from .base import (
    DataProvider,
    ProviderError,
    RecommendationResponse,
    join_results_with_listings,
    load_listings_csv,
    validate_preferences,
)

REAL_MODE_LABEL = "Chế độ thực — dữ liệu TV1 & mô-đun gợi ý TV3"


class RealDataProvider(DataProvider):
    """Connects to real TV1 dataset and an injected TV3 recommender callable."""

    def __init__(
        self,
        listings_path: Path = DEFAULT_REAL_LISTINGS_PATH,
        manifest_path: Path = DEFAULT_REAL_MANIFEST_PATH,
        recommender_fn: Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]] | None = None,
    ) -> None:
        self.listings_path = Path(listings_path)
        self.manifest_path = Path(manifest_path)
        self.recommender_fn = recommender_fn
        self._listings = load_listings_csv(self.listings_path)
        self._manifest = self._load_manifest(self.manifest_path)

    @staticmethod
    def _load_manifest(manifest_path: Path) -> dict[str, Any]:
        if not manifest_path.exists():
            return {}
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def get_dataset_info(self) -> dict[str, Any]:
        districts = self._manifest.get("scope", {}).get("districts", [])
        return {
            "mode_label": REAL_MODE_LABEL,
            "is_mock": False,
            "dataset_version": self._manifest.get("dataset_version", "unknown"),
            "algorithm_version": "tv3-pending" if self.recommender_fn is None else "tv3-connected",
            "listing_count": len(self._listings),
            "released_at": self._manifest.get("released_at", ""),
            "scope": ", ".join(districts) if districts else "Dữ liệu thực TV1",
        }

    def get_profiles(self) -> list[dict[str, Any]]:
        return []

    def get_listing_by_id(self, listing_id: str) -> dict[str, Any] | None:
        return self._listings.get(listing_id)

    def recommend(
        self,
        preferences: dict[str, Any],
        profile_id: str | None = None,
    ) -> RecommendationResponse:
        del profile_id
        dataset_version = self._manifest.get("dataset_version", "unknown")

        validation_errors = validate_preferences(preferences)
        if validation_errors:
            return RecommendationResponse(
                status="invalid_request",
                mode_label=REAL_MODE_LABEL,
                is_mock=False,
                dataset_version=dataset_version,
                algorithm_version="unknown",
                errors=validation_errors,
                applied_preferences=dict(preferences),
            )

        if self.recommender_fn is None:
            return RecommendationResponse(
                status="module_error",
                mode_label=REAL_MODE_LABEL,
                is_mock=False,
                dataset_version=dataset_version,
                algorithm_version="unavailable",
                errors=[
                    "Mô-đun gợi ý TV3 chưa được tích hợp hoặc chưa cấu hình trong môi trường thực.",
                    "Giao diện không tự động chuyển sang điểm giả lập. Vui lòng chuyển sang 'Chế độ mẫu' để kiểm thử luồng UI.",
                ],
                applied_preferences=dict(preferences),
            )

        try:
            raw_result = self.recommender_fn(preferences, list(self._listings.values()))
        except Exception as exc:  # noqa: BLE001 - boundary guard for external TV3 module
            return RecommendationResponse(
                status="module_error",
                mode_label=REAL_MODE_LABEL,
                is_mock=False,
                dataset_version=dataset_version,
                algorithm_version="error",
                errors=[f"Lỗi khi gọi mô-đun gợi ý TV3: {type(exc).__name__}"],
                applied_preferences=dict(preferences),
            )

        if not isinstance(raw_result, dict) or "status" not in raw_result:
            return RecommendationResponse(
                status="module_error",
                mode_label=REAL_MODE_LABEL,
                is_mock=False,
                dataset_version=dataset_version,
                algorithm_version="invalid_schema",
                errors=["Phản hồi từ mô-đun TV3 không đúng schema (thiếu trường 'status')."],
                applied_preferences=dict(preferences),
            )

        raw_items = list(raw_result.get("items") or [])
        joined_items, join_errors = join_results_with_listings(raw_items, self._listings)
        if join_errors:
            return RecommendationResponse(
                status="module_error",
                mode_label=REAL_MODE_LABEL,
                is_mock=False,
                dataset_version=dataset_version,
                algorithm_version=str(raw_result.get("version", "unknown")),
                errors=join_errors,
                applied_preferences=dict(preferences),
            )

        return RecommendationResponse(
            status=str(raw_result.get("status")),
            mode_label=REAL_MODE_LABEL,
            is_mock=False,
            dataset_version=dataset_version,
            algorithm_version=str(raw_result.get("version", "unknown")),
            candidate_count=int(raw_result.get("candidate_count", len(joined_items))),
            items=joined_items,
            warnings=list(raw_result.get("warnings") or []),
            applied_preferences=dict(preferences),
        )
