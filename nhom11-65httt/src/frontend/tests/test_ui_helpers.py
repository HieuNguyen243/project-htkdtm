"""Unit tests for UI formatting helpers: fees, 3-state amenities, URL safety, and coordinates."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parents[1]
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from ui.components import (  # noqa: E402
    format_amenity_state,
    format_deposit,
    format_fees_breakdown,
    format_price_with_basis,
    has_usable_coordinates,
    is_safe_http_url,
)


class UiHelperTests(unittest.TestCase):
    def test_missing_fees_never_become_zero(self) -> None:
        rows = format_fees_breakdown({})
        self.assertEqual(rows[0][1], "Chưa có dữ liệu")

    def test_deposit_kept_separate_and_formatted(self) -> None:
        self.assertEqual(format_deposit(None, None), "Chưa có dữ liệu")
        self.assertIn("3.200.000 đ", format_deposit(3_200_000, 1.0))

    def test_price_basis_distinguishes_room_vs_person(self) -> None:
        self.assertIn("/phòng/tháng", format_price_with_basis(3_200_000, "room"))
        self.assertIn("/người/tháng", format_price_with_basis(1_500_000, "person"))

    def test_amenities_three_states(self) -> None:
        self.assertEqual(format_amenity_state(True), "Có")
        self.assertEqual(format_amenity_state(False), "Không có")
        self.assertEqual(format_amenity_state(None), "Chưa biết")

    def test_safe_http_url_rejects_javascript(self) -> None:
        self.assertTrue(is_safe_http_url("https://phongtro123.com/sample"))
        self.assertFalse(is_safe_http_url("javascript:alert(1)"))
        self.assertFalse(is_safe_http_url(""))

    def test_coordinates_reject_zero_zero_and_unknown(self) -> None:
        self.assertFalse(has_usable_coordinates({"latitude": 0.0, "longitude": 0.0, "geo_confidence": "exact"}))
        self.assertFalse(has_usable_coordinates({"latitude": 21.0, "longitude": 105.8, "geo_confidence": "unknown"}))
        self.assertTrue(has_usable_coordinates({"latitude": 21.0, "longitude": 105.8, "geo_confidence": "district_centroid"}))


if __name__ == "__main__":
    unittest.main()
