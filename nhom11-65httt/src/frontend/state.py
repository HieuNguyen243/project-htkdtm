"""Session state management for search criteria, stale results, and 2-4 room comparison."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from config import MAX_COMPARE_ITEMS, PROVIDER_MODE_MOCK


DEFAULT_PREFERENCES: dict[str, Any] = {
    "budget_vnd": 4000000,
    "price_basis": "room",
    "cost_mode": "rent_only",
    "campus_id": "tlu_hanoi",
    "district": "Đống Đa",
    "room_type": "all",
    "occupants": 1,
    "must_have_amenities": [],
    "nice_to_have_amenities": [],
    "weights": {"budget": 40, "location": 35, "amenities": 25},
    "top_k": 10,
}


def init_session_state(session: MutableMapping[str, Any]) -> None:
    """Initialize all required keys in a per-user session mapping."""
    defaults: dict[str, Any] = {
        "provider_mode": PROVIDER_MODE_MOCK,
        "selected_profile_id": "tlu_under_4m",
        "draft_preferences": dict(DEFAULT_PREFERENCES),
        "submitted_preferences": None,
        "last_response": None,
        "dataset_version": None,
        "selected_listing_id": None,
        "compare_ids": [],
        "active_view": "results",
        "results_stale": False,
    }
    for key, value in defaults.items():
        if key not in session:
            session[key] = value


def mark_stale_if_modified(session: MutableMapping[str, Any], current_draft: dict[str, Any]) -> bool:
    """Flag results as stale if user edited criteria without re-submitting."""
    submitted = session.get("submitted_preferences")
    if submitted is None:
        session["results_stale"] = False
        return False
    is_stale = current_draft != submitted
    session["results_stale"] = is_stale
    return is_stale


def record_search_result(
    session: MutableMapping[str, Any],
    preferences: dict[str, Any],
    response: Any,
) -> list[str]:
    """Store new search response and reconcile compare_ids against dataset_version."""
    old_version = session.get("dataset_version")
    new_version = getattr(response, "dataset_version", None)
    removed_compare_ids: list[str] = []

    if old_version and new_version and old_version != new_version:
        # Remove compare IDs that no longer exist in the new response items when dataset changes
        valid_ids = {
            item["listing"]["listing_id"]
            for item in getattr(response, "items", [])
            if isinstance(item, dict) and "listing" in item
        }
        kept: list[str] = []
        for cid in session.get("compare_ids", []):
            if cid in valid_ids:
                kept.append(cid)
            else:
                removed_compare_ids.append(cid)
        session["compare_ids"] = kept

    session["submitted_preferences"] = dict(preferences)
    session["last_response"] = response
    session["dataset_version"] = new_version
    session["results_stale"] = False
    return removed_compare_ids


def add_to_compare(session: MutableMapping[str, Any], listing_id: str) -> tuple[bool, str]:
    """Add a listing_id to the comparison list (deduplicated, max 4)."""
    compare_ids: list[str] = list(session.get("compare_ids", []))
    if listing_id in compare_ids:
        return False, f"Phòng {listing_id} đã có trong danh sách so sánh."
    if len(compare_ids) >= MAX_COMPARE_ITEMS:
        return False, f"Danh sách so sánh đã đạt tối đa {MAX_COMPARE_ITEMS} phòng. Vui lòng bỏ bớt trước khi thêm."
    compare_ids.append(listing_id)
    session["compare_ids"] = compare_ids
    return True, f"Đã thêm phòng {listing_id} vào danh sách so sánh ({len(compare_ids)}/{MAX_COMPARE_ITEMS})."


def remove_from_compare(session: MutableMapping[str, Any], listing_id: str) -> None:
    """Remove a single listing_id from the comparison list."""
    compare_ids: list[str] = list(session.get("compare_ids", []))
    session["compare_ids"] = [cid for cid in compare_ids if cid != listing_id]


def clear_compare(session: MutableMapping[str, Any]) -> None:
    """Clear all listings from the comparison list."""
    session["compare_ids"] = []
