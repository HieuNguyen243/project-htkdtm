"""End-to-end flow tests covering TV4-08 user journeys and edge cases."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parents[1]
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from providers import MockDataProvider, RealDataProvider  # noqa: E402
from state import (  # noqa: E402
    add_to_compare,
    init_session_state,
    mark_stale_if_modified,
    record_search_result,
)
from ui.components import (  # noqa: E402
    count_missing_fields,
    format_quality_flags,
    has_usable_coordinates,
)


class EndToEndFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = MockDataProvider()
        self.session: dict = {}
        init_session_state(self.session)

    def test_full_journey_search_detail_compare_and_modify(self) -> None:
        prefs = {
            "budget_vnd": 4_000_000,
            "price_basis": "room",
            "occupants": 1,
            "top_k": 10,
        }
        resp = self.provider.recommend(prefs, profile_id="tlu_under_4m")
        self.assertEqual(resp.status, "ok")
        self.assertEqual(len(resp.items), 4)

        record_search_result(self.session, prefs, resp)
        self.assertFalse(self.session["results_stale"])

        # Open detail for MOCK-006 (missing deposit, missing area, missing fees, suspected_duplicate)
        detail = self.provider.get_listing_by_id("MOCK-006")
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertGreaterEqual(count_missing_fields(detail), 3)
        flags = format_quality_flags(detail["quality_flags"])
        self.assertTrue(any("trùng lặp" in f for f in flags))

        # Add 2 rooms to compare
        ok1, _ = add_to_compare(self.session, "MOCK-001")
        ok2, _ = add_to_compare(self.session, "MOCK-006")
        self.assertTrue(ok1 and ok2)

        # Modify criteria without re-searching -> results must be flagged stale
        modified_prefs = dict(prefs, budget_vnd=2_500_000)
        self.assertTrue(mark_stale_if_modified(self.session, modified_prefs))

    def test_utc_profile_handles_missing_coordinates_and_mixed_basis(self) -> None:
        prefs = {
            "budget_vnd": 4_500_000,
            "price_basis": "room",
            "occupants": 2,
            "top_k": 10,
        }
        resp = self.provider.recommend(prefs, profile_id="utc_studio_or_shared")
        self.assertEqual(resp.status, "ok")
        self.assertEqual(len(resp.items), 3)

        # MOCK-003 has missing coordinates -> must not be plotted on map
        mock_003 = self.provider.get_listing_by_id("MOCK-003")
        assert mock_003 is not None
        self.assertFalse(has_usable_coordinates(mock_003))

        # MOCK-007 has exact coordinates -> usable for map
        mock_007 = self.provider.get_listing_by_id("MOCK-007")
        assert mock_007 is not None
        self.assertTrue(has_usable_coordinates(mock_007))

    def test_real_provider_with_connected_tv3_callable(self) -> None:
        sample_csv = FRONTEND_DIR / "fixtures" / "sample_listings.csv"

        def fake_tv3(preferences: dict, listings: list[dict]) -> dict:
            del preferences
            return {
                "status": "ok",
                "version": "tv3-real-1.0",
                "candidate_count": len(listings),
                "items": [{"listing_id": listings[0]["listing_id"], "rank": 1, "score": 0.95}],
            }

        real = RealDataProvider(listings_path=sample_csv, recommender_fn=fake_tv3)
        resp = real.recommend({"budget_vnd": 4_000_000, "price_basis": "room", "occupants": 1, "top_k": 5})
        self.assertEqual(resp.status, "ok")
        self.assertFalse(resp.is_mock)
        self.assertEqual(resp.items[0]["listing"]["listing_id"], "MOCK-001")


if __name__ == "__main__":
    unittest.main()
