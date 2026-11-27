"""Mock data provider for independent TV4 development without TV1/TV2/TV3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import DEFAULT_SAMPLE_LISTINGS_PATH, DEFAULT_SAMPLE_RESULTS_PATH

from .base import (
    DataProvider,
    ProviderError,
    RecommendationResponse,
    join_results_with_listings,
    load_listings_csv,
    validate_preferences,
)

MOCK_MODE_LABEL = "Chế độ mẫu — dữ liệu/kết quả giả lập"


class MockDataProvider(DataProvider):
    """Serves pre-defined simulated results tied strictly to sample profiles."""

    def __init__(
        self,
        listings_path: Path = DEFAULT_SAMPLE_LISTINGS_PATH,
        results_path: Path = DEFAULT_SAMPLE_RESULTS_PATH,
    ) -> None:
        self.listings_path = Path(listings_path)
        self.results_path = Path(results_path)
        self._listings = load_listings_csv(self.listings_path)
        self._payload = self._load_results_json(self.results_path)
        self._profiles_by_id = {
            p["profile_id"]: p for p in self._payload.get("profiles", []) if "profile_id" in p
        }

    @staticmethod
    def _load_results_json(results_path: Path) -> dict[str, Any]:
        if not results_path.exists():
            raise ProviderError(f"Không tìm thấy tệp kết quả mẫu: {results_path.name}")
        try:
            data = json.loads(results_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Tệp kết quả mẫu không đúng định dạng JSON: {exc}") from exc
        if "profiles" not in data or not isinstance(data["profiles"], list):
            raise ProviderError("Tệp kết quả mẫu thiếu danh sách 'profiles'.")
        return data

    def get_dataset_info(self) -> dict[str, Any]:
        return {
            "mode_label": MOCK_MODE_LABEL,
            "is_mock": True,
            "dataset_version": self._payload.get("dataset_version", "mock-v0.1"),
            "algorithm_version": self._payload.get("algorithm_version", "mock-tv3-v0.1"),
            "listing_count": len(self._listings),
            "scope": "Dữ liệu mẫu giả lập (Đống Đa, Thanh Xuân, Cầu Giấy)",
        }

    def get_profiles(self) -> list[dict[str, Any]]:
        return list(self._payload.get("profiles", []))

    def get_listing_by_id(self, listing_id: str) -> dict[str, Any] | None:
        return self._listings.get(listing_id)

    def recommend(
        self,
        preferences: dict[str, Any],
        profile_id: str | None = None,
    ) -> RecommendationResponse:
        dataset_version = self._payload.get("dataset_version", "mock-v0.1")
        algorithm_version = self._payload.get("algorithm_version", "mock-tv3-v0.1")

        validation_errors = validate_preferences(preferences)
        if validation_errors:
            return RecommendationResponse(
                status="invalid_request",
                mode_label=MOCK_MODE_LABEL,
                is_mock=True,
                dataset_version=dataset_version,
                algorithm_version=algorithm_version,
                errors=validation_errors,
                applied_preferences=dict(preferences),
            )

        if not profile_id or profile_id not in self._profiles_by_id:
            return RecommendationResponse(
                status="unsimulated_mock",
                mode_label=MOCK_MODE_LABEL,
                is_mock=True,
                dataset_version=dataset_version,
                algorithm_version=algorithm_version,
                warnings=[
                    "Yêu cầu hiện tại chưa có hồ sơ mô phỏng sẵn trong chế độ mẫu.",
                    "Vui lòng chọn một hồ sơ mẫu có sẵn; giao diện không tự tính lại điểm thay TV3.",
                ],
                applied_preferences=dict(preferences),
            )

        profile = self._profiles_by_id[profile_id]
        raw_result = profile.get("result") or {}
        status = raw_result.get("status", "module_error")
        raw_items = list(raw_result.get("items") or [])
        joined_items, join_errors = join_results_with_listings(raw_items, self._listings)

        if join_errors:
            return RecommendationResponse(
                status="module_error",
                mode_label=MOCK_MODE_LABEL,
                is_mock=True,
                dataset_version=raw_result.get("dataset_version", dataset_version),
                algorithm_version=raw_result.get("version", algorithm_version),
                errors=join_errors,
                applied_preferences=dict(preferences),
            )

        return RecommendationResponse(
            status=status,
            mode_label=MOCK_MODE_LABEL,
            is_mock=True,
            dataset_version=raw_result.get("dataset_version", dataset_version),
            algorithm_version=raw_result.get("version", algorithm_version),
            candidate_count=int(raw_result.get("candidate_count", len(joined_items))),
            items=joined_items,
            warnings=list(raw_result.get("warnings") or []),
            applied_preferences=dict(preferences),
        )
