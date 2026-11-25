"""Periodic scheduler for running the rental ETL pipeline in Vietnam time."""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, timedelta

from config import VN_TZ
from pipeline import run_pipeline


def parse_schedule_times(raw: str) -> list[tuple[int, int]]:
    """Parse comma-separated HH:MM strings into sorted (hour, minute) tuples."""
    parsed: list[tuple[int, int]] = []
    for token in raw.split(","):
        item = token.strip()
        if not item:
            continue
        hour_str, minute_str = item.split(":", 1)
        hour, minute = int(hour_str), int(minute_str)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"Invalid schedule time: {item}")
        parsed.append((hour, minute))
    if not parsed:
        raise ValueError("At least one HH:MM schedule time is required")
    return sorted(set(parsed))


def next_run_time(now: datetime, times: list[tuple[int, int]]) -> datetime:
    """Compute the next scheduled datetime >= now for the given daily HH:MM slots."""
    local_now = now.astimezone(VN_TZ)
    candidates = [
        local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        for hour, minute in times
    ]
    upcoming = [dt for dt in candidates if dt > local_now]
    if upcoming:
        return upcoming[0]
    first_hour, first_minute = times[0]
    return (local_now + timedelta(days=1)).replace(
        hour=first_hour, minute=first_minute, second=0, microsecond=0
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    logger = logging.getLogger("scheduler")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--times", default="06:00,18:00", help="Daily HH:MM times (Asia/Ho_Chi_Minh)")
    parser.add_argument("--run-now", action="store_true", help="Run the pipeline immediately on startup")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--skip-scrape", action="store_true", help="Pass --skip-scrape to pipeline")
    args = parser.parse_args()

    times = parse_schedule_times(args.times)
    if args.run_now or args.once:
        run_pipeline(skip_scrape=args.skip_scrape, save_snapshot=True)
        if args.once:
            return 0

    while True:
        now = datetime.now(VN_TZ)
        target = next_run_time(now, times)
        wait_seconds = max(1.0, (target - now).total_seconds())
        logger.info("Next scheduled run at %s (sleeping %.0fs)", target.isoformat(), wait_seconds)
        time.sleep(wait_seconds)
        run_pipeline(skip_scrape=args.skip_scrape, save_snapshot=True)


if __name__ == "__main__":
    raise SystemExit(main())
