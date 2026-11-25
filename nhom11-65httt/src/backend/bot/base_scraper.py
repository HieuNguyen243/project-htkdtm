"""Shared base classes, HTTP fetcher, robots.txt policy, and CSV writers."""

from __future__ import annotations

import csv
import logging
import time
import urllib.error
import urllib.request
import urllib.robotparser
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from config import (
    DISTRICTS,
    REJECTION_FIELDS,
    STANDARD_FIELDS,
    USER_AGENT,
    clean_text,
    has_conflicting_district,
    is_non_room_listing,
    redact_pii,
)


def atomic_write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Mapping[str, str]],
) -> None:
    """Atomically write UTF-8 BOM CSV using temporary file replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(path)


@dataclass
class RoomListing:
    """Normalized room-rental listing record matching TV1 data specification."""

    listing_id: str
    source_name: str
    source_record_key: str
    source_url: str
    district: str
    title: str
    rent_vnd_month: int
    raw_ref: str = ""
    run_id: str = ""
    content_hash: str = ""
    public_code: str = ""
    room_type: str = "room"
    price_basis: str = "unknown"
    area_m2: str = ""
    deposit_vnd: str = ""
    deposit_months: str = ""
    fees_json: str = "{}"
    amenities_json: str = "{}"
    ward: str = ""
    address_clean: str = ""
    latitude: str = ""
    longitude: str = ""
    geo_confidence: str = "area_only"
    max_occupants: str = ""
    available_rooms: str = ""
    description_clean: str = ""
    posted_at: str = ""
    posted_date: str = ""
    expires_on: str = ""
    duplicate_group_id: str = ""
    duplicate_status: str = "unique"
    is_representative: str = "true"
    listing_status: str = "unverified_available"
    record_status: str = "accepted"
    quality_flags_json: str = "[]"
    collected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, str]:
        """Convert listing into a CSV-ready dictionary matching STANDARD_FIELDS."""
        raw = asdict(self)
        raw["rent_vnd_month"] = str(self.rent_vnd_month)
        return {field_name: str(raw.get(field_name, "")) for field_name in STANDARD_FIELDS}


class RobotsPolicy:
    """Fetch and enforce a site's robots.txt rules for the research bot."""

    def __init__(self, base_url: str, user_agent: str = USER_AGENT, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self.robots_url = f"{self.base_url}/robots.txt"
        self.parser = urllib.robotparser.RobotFileParser()
        self.parser.set_url(self.robots_url)
        self._loaded = False

    def load(self) -> bool:
        """Download and parse robots.txt. Returns False if unavailable or denied."""
        request = urllib.request.Request(self.robots_url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    return False
                content = response.read().decode("utf-8-sig", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError):
            return False
        self.parser.parse(content.splitlines())
        self._loaded = True
        return True

    def load_from_text(self, content: str) -> None:
        """Load robots.txt rules directly from text (useful for testing)."""
        self.parser.parse(content.splitlines())
        self._loaded = True

    def can_fetch(self, url: str) -> bool:
        """Check whether the bot User-Agent is allowed to access url."""
        if not self._loaded:
            raise RuntimeError("robots.txt has not been loaded yet")
        return self.parser.can_fetch(self.user_agent, url)


class PoliteHttpFetcher:
    """Shared HTTP fetcher obeying robots.txt, rate limits, and 401/403/429 stops."""

    def __init__(
        self,
        base_url: str,
        delay: float = 2.0,
        user_agent: str = USER_AGENT,
        timeout: int = 25,
        require_html: bool = True,
        disallow_redirects: bool = False,
    ) -> None:
        if delay < 1.0:
            raise ValueError("delay must be at least 1.0 second")
        self.base_url = base_url.rstrip("/")
        self.delay = delay
        self.user_agent = user_agent
        self.timeout = timeout
        self.require_html = require_html
        self.disallow_redirects = disallow_redirects
        self.last_request = 0.0
        self.robots = RobotsPolicy(self.base_url, user_agent=user_agent, timeout=timeout)
        if not self.robots.load():
            raise RuntimeError(f"Cannot load {self.robots.robots_url}")
        self.last_request = time.monotonic()

    def get(self, url: str, max_bytes: int | None = None) -> bytes:
        """Fetch url after robots.txt check and delay, stopping immediately on 401/403/429."""
        if not self.robots.can_fetch(url):
            raise RuntimeError(f"Disallowed by robots.txt: {url}")
        elapsed = time.monotonic() - self.last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    if self.disallow_redirects and response.geturl() != url:
                        raise RuntimeError("redirected outside requested URL")
                    content_type = response.headers.get("Content-Type", "")
                    if self.require_html and "text/html" not in content_type:
                        raise ValueError("Unexpected content type")
                    return response.read() if max_bytes is None else response.read(max_bytes)
            except urllib.error.HTTPError as error:
                if error.code in (401, 403, 429):
                    raise
                if error.code not in (500, 502, 503, 504) or attempt == 2:
                    raise
            except (TimeoutError, urllib.error.URLError):
                if attempt == 2:
                    raise
            finally:
                self.last_request = time.monotonic()
            time.sleep(self.delay * (attempt + 1))
        raise RuntimeError("Request failed")


class BaseScraper(ABC):
    """Abstract base class enforcing ethical scraping, validation, and CSV output."""

    MAX_PLAUSIBLE_RENT_VND = 50_000_000

    def __init__(
        self,
        name: str,
        base_url: str,
        delay: float = 2.0,
        user_agent: str = USER_AGENT,
    ) -> None:
        if delay < 1.0:
            raise ValueError("delay must be at least 1.0 second")
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.delay = delay
        self.user_agent = user_agent
        self.robots = RobotsPolicy(self.base_url, user_agent=user_agent)
        self.logger = logging.getLogger(name)

    def check_robots_txt(self) -> bool:
        """Verify robots.txt is readable and permits district listing URLs."""
        if not self.robots.load():
            self.logger.error("Failed to load %s", self.robots.robots_url)
            return False
        for slug in DISTRICTS:
            url = self.district_url(slug)
            if not self.robots.can_fetch(url):
                self.logger.error("Disallowed by robots.txt: %s", url)
                return False
        return True

    @abstractmethod
    def district_url(self, slug: str, page: int = 1) -> str:
        """Build the listing page URL for a district slug."""

    @abstractmethod
    def scrape_district(self, slug: str, district: str) -> tuple[list[RoomListing], list[dict[str, str]]]:
        """Collect valid and rejected listings for a single district."""

    def validate_listing(self, listing: RoomListing) -> tuple[bool, str]:
        """Validate scope (3 districts, room rental only, plausible monthly rent)."""
        if listing.district not in DISTRICTS.values():
            return False, "district outside scope"
        if is_non_room_listing(listing.title):
            return False, "non-room property or seeking ad in title"
        if listing.address_clean and has_conflicting_district(
            f"{listing.title} {listing.address_clean}", listing.district
        ):
            return False, "conflicting Hanoi district in title/address"
        if listing.rent_vnd_month <= 0 or listing.rent_vnd_month > self.MAX_PLAUSIBLE_RENT_VND:
            return False, "implausible monthly rent"
        return True, ""

    def sanitize_listing(self, listing: RoomListing) -> RoomListing:
        """Redact phone numbers and emails and normalize whitespace."""
        listing.title = redact_pii(listing.title)
        listing.address_clean = redact_pii(listing.address_clean)
        listing.description_clean = redact_pii(listing.description_clean)
        return listing

    @staticmethod
    def write_csv(path: Path, listings: Sequence[RoomListing]) -> None:
        """Atomically write normalized listings to UTF-8 BOM CSV."""
        sorted_items = sorted(listings, key=lambda item: item.listing_id)
        atomic_write_csv(path, STANDARD_FIELDS, [item.to_dict() for item in sorted_items])

    @staticmethod
    def write_rejected_csv(path: Path, rejected: Sequence[dict[str, str]]) -> None:
        """Atomically write rejected URLs and reasons to UTF-8 BOM CSV."""
        atomic_write_csv(path, REJECTION_FIELDS, rejected)

    def run(self, output: Path) -> int:
        """Execute full collection across all three target districts."""
        if not self.check_robots_txt():
            return 1

        accepted: dict[str, RoomListing] = {}
        rejected: list[dict[str, str]] = []
        for slug, district in DISTRICTS.items():
            try:
                items, discarded = self.scrape_district(slug, district)
            except Exception as error:
                self.logger.error("Error scraping %s: %s", district, error)
                return 1

            rejected.extend(discarded)
            for item in items:
                valid, reason = self.validate_listing(item)
                if not valid:
                    rejected.append(
                        {"source_url": item.source_url, "district": district, "reason": reason}
                    )
                    continue
                accepted[item.listing_id] = self.sanitize_listing(item)
            self.logger.info("%s: %d accepted, %d rejected", district, len(items), len(discarded))

        self.write_csv(output, list(accepted.values()))
        rejected_path = output.with_name(f"{output.stem}_rejected.csv")
        self.write_rejected_csv(rejected_path, rejected)
        return 0 if accepted else 1
