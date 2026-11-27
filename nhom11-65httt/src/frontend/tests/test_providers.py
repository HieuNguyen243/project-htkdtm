"""Unit tests for MockDataProvider, RealDataProvider, schema validation, and listing_id join."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parents[1]
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from providers import MockDataProvider, RealDataProvider, validate_preferences  # noqa: E402
from providers.base import join_results_with_listings  # noqa: E402


class ProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock = MockDataProvider()
        self.valid_prefs = {
            "budget_vnd": 4_000_000,
            "price_basis": "room",
            "occupants": 1,
            "top_k": 10,
        }

    def test_validate_preferences_rejects_invalid_budget_and_occupants(self) -> None:
        errors = validate_preferences({"budget_vnd": -100, "price_basis": "room", "occupants": 0})
        self.assertEqual(len(errors), 2)

    def test_mock_provider_returns_ok_and_joins_by_listing_id(self) -> None:
        resp = self.mock.recommend(self.valid_prefs, profile_id="tlu_under_4m")
        self.assertEqual(resp.status, "ok")
        self.assertTrue(resp.is_mock)
        self.assertEqual(len(resp.items), 3)
        self.assertEqual(resp.items[0]["listing"]["listing_id"], "MOCK-001")

    def test_mock_provider_handles_no_match_and_unsimulated_profile(self) -> None:
        no_match = self.mock.recommend(self.valid_prefs, profile_id="no_match_strict")
        self.assertEqual(no_match.status, "no_match")
        self.assertEqual(no_match.items, [])

        unsimulated = self.mock.recommend(self.valid_prefs, profile_id=None)
        self.assertEqual(unsimulated.status, "unsimulated_mock")

    def test_join_reports_missing_listing_id_without_substituting(self) -> None:
        listings = {"MOCK-001": {"listing_id": "MOCK-001", "title": "A"}}
        joined, errors = join_results_with_listings(
            [{"listing_id": "UNKNOWN-999", "rank": 1, "score": 0.9}],
            listings,
        )
        self.assertEqual(joined, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("UNKNOWN-999", errors[0])

    def test_real_provider_without_tv3_module_returns_module_error(self) -> None:
        sample_listings = FRONTEND_DIR / "fixtures" / "sample_listings.csv"
        real = RealDataProvider(listings_path=sample_listings, recommender_fn=None)
        resp = real.recommend(self.valid_prefs)
        self.assertEqual(resp.status, "module_error")
        self.assertFalse(resp.is_mock)


if __name__ == "__main__":
    unittest.main()
