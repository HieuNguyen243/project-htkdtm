"""Cross-source deduplication and duplicate-cluster annotation per TV1-05 specs."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from config import fold_text

ADDRESS_PREFIXES = (
    "tp ha noi",
    "ha noi",
    "quan ",
    "phuong ",
    "duong ",
    "pho ",
    "ngach ",
    "ngo ",
    "hem ",
    "so nha ",
    "so ",
)


class Deduplicator:
    """Detect confirmed and suspected duplicates across room-rental listings."""

    def __init__(
        self,
        suspected_threshold: float = 0.85,
        confirmed_threshold: float = 0.96,
        max_price_diff_ratio: float = 0.10,
        max_area_diff_m2: float = 2.0,
    ) -> None:
        self.suspected_threshold = suspected_threshold
        self.confirmed_threshold = confirmed_threshold
        self.max_price_diff_ratio = max_price_diff_ratio
        self.max_area_diff_m2 = max_area_diff_m2

    @staticmethod
    def normalize_address(address: str) -> str:
        """Normalize address text for cross-source similarity comparison."""
        normalized = fold_text(address)
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        for prefix in ADDRESS_PREFIXES:
            normalized = normalized.replace(prefix, " ")
        return re.sub(r"\s+", " ", normalized).strip()

    @staticmethod
    def _parse_int(value: str) -> int | None:
        try:
            parsed = int(float(value))
            return parsed if parsed > 0 else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_float(value: str) -> float | None:
        try:
            parsed = float(value)
            return parsed if parsed > 0 else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _representative_key(record: dict[str, str]) -> tuple[str, int, str]:
        """Rank candidate representatives: latest collected_at, highest completeness, ascending ID."""
        filled = sum(1 for value in record.values() if str(value).strip())
        return (str(record.get("collected_at", "")), filled, str(record.get("listing_id", "")))

    def classify_pair(self, first: dict[str, str], second: dict[str, str]) -> str:
        """Return 'confirmed', 'suspected', or 'none' for two listing records."""
        if first.get("listing_id") and first.get("listing_id") == second.get("listing_id"):
            return "confirmed"

        if fold_text(first.get("district", "")) != fold_text(second.get("district", "")):
            return "none"

        price_a = self._parse_int(first.get("rent_vnd_month", ""))
        price_b = self._parse_int(second.get("rent_vnd_month", ""))
        if price_a is None or price_b is None:
            return "none"
        price_diff = abs(price_a - price_b) / max(price_a, price_b)
        if price_diff > self.max_price_diff_ratio:
            return "none"

        area_a = self._parse_float(first.get("area_m2", ""))
        area_b = self._parse_float(second.get("area_m2", ""))
        area_diff = abs(area_a - area_b) if (area_a is not None and area_b is not None) else None
        if area_diff is not None and area_diff > self.max_area_diff_m2:
            return "none"

        addr_a = self.normalize_address(first.get("address_clean") or first.get("address", ""))
        addr_b = self.normalize_address(second.get("address_clean") or second.get("address", ""))
        if not addr_a or not addr_b:
            return "none"

        nums_a = re.findall(r"\b\d+[a-z]?\b", addr_a)
        nums_b = re.findall(r"\b\d+[a-z]?\b", addr_b)
        if nums_a and nums_b and nums_a != nums_b:
            return "none"

        title_a = fold_text(first.get("title", ""))
        title_b = fold_text(second.get("title", ""))
        loc_re = re.compile(r"\b(?:so nha|so|ngo|ngach|hem)\s+(\d+[a-z]?(?:/\d+[a-z]?)*)\b")
        t_locs_a = loc_re.findall(title_a)
        t_locs_b = loc_re.findall(title_b)
        if (not nums_a or not nums_b) and t_locs_a and t_locs_b and t_locs_a != t_locs_b:
            return "none"

        room_re = re.compile(r"\b(?:phong|p)\s*([1-9]\d{2,3}[a-z]?)\b")
        rooms_a = room_re.findall(title_a)
        rooms_b = room_re.findall(title_b)
        if rooms_a and rooms_b and rooms_a != rooms_b:
            return "none"

        has_specific_address_num = bool(nums_a and nums_b)
        rt_a = first.get("room_type", "")
        rt_b = second.get("room_type", "")
        shared_mismatch = bool(rt_a and rt_b and ("shared_place" in (rt_a, rt_b)) and rt_a != rt_b)

        similarity = SequenceMatcher(None, addr_a, addr_b).ratio()
        if (
            has_specific_address_num
            and not shared_mismatch
            and similarity >= self.confirmed_threshold
            and price_diff <= 0.05
            and (area_diff is None or area_diff <= 1.0)
        ):
            return "confirmed"
        if similarity >= self.suspected_threshold:
            return "suspected"
        return "none"

    def is_duplicate(self, first: dict[str, str], second: dict[str, str]) -> bool:
        """Backward-compatible boolean check for confirmed or suspected matches."""
        return self.classify_pair(first, second) != "none"

    def annotate_clusters(self, listings: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, int]]:
        """Annotate all rows with duplicate_group_id, duplicate_status, and is_representative.

        Per TV1-05:
        - confirmed groups keep one representative (is_representative='true') and mark others 'false'
        - suspected matches remain separate in published listings with duplicate_status='suspected'
        """
        rows = [dict(item) for item in listings]
        n = len(rows)
        assigned = [False] * n
        group_counter = 0
        confirmed_clusters = 0
        confirmed_secondary = 0
        suspected_count = 0

        for i in range(n):
            if assigned[i]:
                continue
            confirmed_members = [i]
            suspected_with = []
            for j in range(i + 1, n):
                if assigned[j]:
                    continue
                relation = self.classify_pair(rows[i], rows[j])
                if relation == "confirmed":
                    confirmed_members.append(j)
                elif relation == "suspected":
                    suspected_with.append(j)

            if len(confirmed_members) > 1:
                group_counter += 1
                confirmed_clusters += 1
                group_id = f"DG-{group_counter:04d}"
                rep_idx = max(
                    confirmed_members,
                    key=lambda idx: (
                        str(rows[idx].get("collected_at", "")),
                        sum(1 for v in rows[idx].values() if str(v).strip()),
                    ),
                )
                for idx in confirmed_members:
                    assigned[idx] = True
                    rows[idx]["duplicate_group_id"] = group_id
                    rows[idx]["duplicate_status"] = "confirmed"
                    is_rep = idx == rep_idx
                    rows[idx]["is_representative"] = "true" if is_rep else "false"
                    if not is_rep:
                        confirmed_secondary += 1
            elif suspected_with:
                group_counter += 1
                group_id = f"DG-{group_counter:04d}"
                assigned[i] = True
                rows[i]["duplicate_group_id"] = group_id
                rows[i]["duplicate_status"] = "suspected"
                rows[i]["is_representative"] = "true"
                suspected_count += 1
                for idx in suspected_with:
                    assigned[idx] = True
                    rows[idx]["duplicate_group_id"] = group_id
                    rows[idx]["duplicate_status"] = "suspected"
                    rows[idx]["is_representative"] = "true"
                    suspected_count += 1
            else:
                assigned[i] = True
                rows[i]["duplicate_group_id"] = ""
                rows[i]["duplicate_status"] = "unique"
                rows[i]["is_representative"] = "true"

        stats = {
            "confirmed_clusters": confirmed_clusters,
            "confirmed_secondary": confirmed_secondary,
            "suspected_records": suspected_count,
        }
        return rows, stats

    def deduplicate(
        self, listings: list[dict[str, str]]
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """Return representative rows and non-representative confirmed duplicate rows."""
        annotated, _ = self.annotate_clusters(listings)
        published = [row for row in annotated if row.get("is_representative") == "true"]
        removed = [row for row in annotated if row.get("is_representative") != "true"]
        return published, removed
