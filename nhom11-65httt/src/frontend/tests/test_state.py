"""Unit tests for session state management, stale detection, and 2-4 room compare list."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

FRONTEND_DIR = Path(__file__).resolve().parents[1]
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from state import (  # noqa: E402
    add_to_compare,
    clear_compare,
    init_session_state,
    mark_stale_if_modified,
    record_search_result,
    remove_from_compare,
)


class StateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session: dict = {}
        init_session_state(self.session)

    def test_compare_deduplicates_and_enforces_max_4(self) -> None:
        for i in range(1, 5):
            ok, _ = add_to_compare(self.session, f"MOCK-00{i}")
            self.assertTrue(ok)

        dup_ok, _ = add_to_compare(self.session, "MOCK-001")
        self.assertFalse(dup_ok)

        over_ok, _ = add_to_compare(self.session, "MOCK-005")
        self.assertFalse(over_ok)
        self.assertEqual(len(self.session["compare_ids"]), 4)

        remove_from_compare(self.session, "MOCK-002")
        self.assertEqual(self.session["compare_ids"], ["MOCK-001", "MOCK-003", "MOCK-004"])

        clear_compare(self.session)
        self.assertEqual(self.session["compare_ids"], [])

    def test_stale_result_flagged_when_criteria_change(self) -> None:
        prefs = {"budget_vnd": 4_000_000, "district": "Đống Đa"}
        fake_resp = SimpleNamespace(dataset_version="v1", items=[])
        record_search_result(self.session, prefs, fake_resp)
        self.assertFalse(self.session["results_stale"])

        is_stale = mark_stale_if_modified(self.session, {"budget_vnd": 3_000_000, "district": "Đống Đa"})
        self.assertTrue(is_stale)
        self.assertTrue(self.session["results_stale"])

    def test_dataset_version_change_reconciles_compare_ids(self) -> None:
        add_to_compare(self.session, "MOCK-001")
        add_to_compare(self.session, "OLD-999")
        resp_v1 = SimpleNamespace(dataset_version="v1", items=[{"listing": {"listing_id": "MOCK-001"}}])
        record_search_result(self.session, {"budget_vnd": 4_000_000}, resp_v1)

        resp_v2 = SimpleNamespace(dataset_version="v2", items=[{"listing": {"listing_id": "MOCK-001"}}])
        removed = record_search_result(self.session, {"budget_vnd": 4_000_000}, resp_v2)
        self.assertEqual(removed, ["OLD-999"])
        self.assertEqual(self.session["compare_ids"], ["MOCK-001"])


if __name__ == "__main__":
    unittest.main()
