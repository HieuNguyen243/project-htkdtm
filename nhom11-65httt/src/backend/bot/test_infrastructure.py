"""Unit and integration tests covering TV1-07/TV1-08 requirements and Playwright infra."""

from __future__ import annotations

import asyncio
import csv
import http.server
import json
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path

from base_scraper import BaseScraper, RobotsPolicy, RoomListing
from config import VN_TZ, has_conflicting_district, is_non_room_listing, parse_monthly_rent, redact_pii
from deduplicator import Deduplicator
from evaluate import evaluate_duplicate_pairs, evaluate_extraction
from extractor import enrich_row, extract_amenities, extract_deposit, extract_fees, infer_price_basis
from pipeline import run_pipeline, validate_release
from playwright_scraper import PlaywrightScraper
from scheduler import next_run_time, parse_schedule_times
from template_playwright_bot import PlaywrightSourceBot


class _LocalTestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/robots.txt":
            body = b"User-agent: *\nAllow: /allowed/\nDisallow: /blocked/\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/forbidden"):
            self.send_response(403)
            self.end_headers()
        elif self.path.startswith("/allowed/dong-da"):
            html = """
            <html><body>
              <article class="listing-card">
                <a href="https://example.local/allowed/room-101">
                  <h3>Phòng trọ khép kín Xã Đàn</h3>
                </a>
                <span class="price">3.5 triệu/tháng</span>
                <span class="area">22</span>
                <p class="address">Ngõ 10 Xã Đàn, Đống Đa</p>
              </article>
              <article class="listing-card">
                <a href="https://example.local/allowed/room-102">
                  <h3>Bán nhà nguyên căn Xã Đàn</h3>
                </a>
                <span class="price">5 triệu/tháng</span>
                <span class="area">40</span>
                <p class="address">Xã Đàn, Đống Đa</p>
              </article>
            </body></html>
            """.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


class _DummyScraper(BaseScraper):
    def district_url(self, slug: str, page: int = 1) -> str:
        return f"{self.base_url}/allowed/{slug}?page={page}"

    def scrape_district(self, slug: str, district: str) -> tuple[list[RoomListing], list[dict[str, str]]]:
        if slug != "dong-da":
            return [], []
        valid = RoomListing(
            listing_id="dummy:1",
            source_name="dummy",
            source_record_key="1",
            source_url=f"{self.base_url}/room-1",
            district=district,
            title="Phòng trọ khép kín gọi 0912345678",
            rent_vnd_month=3_500_000,
            area_m2="25",
            address_clean="Ngõ 10 Chùa Bộc, Đống Đa",
            description_clean="Liên hệ test@example.com",
        )
        bad_district = RoomListing(
            listing_id="dummy:2",
            source_name="dummy",
            source_record_key="2",
            source_url=f"{self.base_url}/room-2",
            district=district,
            title="Phòng trọ Hà Đông giá rẻ",
            rent_vnd_month=2_000_000,
            address_clean="Hà Đông, Hà Nội",
        )
        return [valid, bad_district], []


class ConfigAndExtractorTests(unittest.TestCase):
    def test_helpers(self) -> None:
        self.assertEqual(parse_monthly_rent("3,5 triệu/tháng"), 3_500_000)
        self.assertEqual(parse_monthly_rent("900 nghìn/tháng"), 900_000)
        self.assertIsNone(parse_monthly_rent("Thỏa thuận"))
        self.assertTrue(is_non_room_listing("Cho thuê căn hộ 1N1K"))
        self.assertFalse(is_non_room_listing("Cho thuê phòng trọ trong chung cư mini"))
        self.assertTrue(has_conflicting_district("Phòng trọ Hà Đông", "Thanh Xuân"))
        self.assertFalse(has_conflicting_district("Phòng trọ Khương Trung, Thanh Xuân", "Thanh Xuân"))
        self.assertEqual(
            redact_pii("Gọi 0987.654.321 hoặc a@b.vn"),
            "Gọi [số điện thoại] hoặc [email]",
        )
        self.assertEqual(
            redact_pii("LH 091261735 / 090 525 414 ngày 09/11/2026"),
            "LH [số điện thoại] / [số điện thoại] ngày 09/11/2026",
        )

    def test_extractor_matches_reference_catalog_codes_and_negation(self) -> None:
        text = "Phòng không có điều hòa, có bình nóng lạnh, gửi xe miễn phí. Điện 4k/số, nước 100k/người, cọc 1 tháng."
        amenities = extract_amenities("", text)
        self.assertEqual(set(amenities), {"air_conditioner", "parking", "private_bathroom", "wifi", "washer", "balcony", "water_heater", "kitchen"})
        self.assertFalse(amenities["air_conditioner"])
        self.assertTrue(amenities["water_heater"])
        self.assertIsNone(amenities["washer"])

        fees = extract_fees(text)
        self.assertEqual(set(fees), {"electricity", "water", "internet", "parking", "service"})
        self.assertEqual(fees["electricity"]["amount"], 4000)
        self.assertEqual(fees["electricity"]["unit"], "vnd_per_kwh")
        self.assertEqual(fees["water"]["amount"], 100000)
        self.assertEqual(fees["water"]["unit"], "vnd_per_person_month")
        self.assertEqual(fees["parking"]["status"], "free")
        self.assertEqual(fees["internet"]["status"], "unknown")

        dep_vnd, dep_months = extract_deposit(text, rent_vnd_month=3_500_000, price_basis="room")
        self.assertEqual(dep_vnd, "3500000")
        self.assertEqual(dep_months, "1")
        self.assertEqual(infer_price_basis("1.4 triệu/tháng", "Phòng trọ ở ghép 2 người", "", "shared_place"), "person")
        self.assertEqual(infer_price_basis("3.5 triệu/tháng", "Phòng trọ khép kín", "", "self_contained"), "room")

        enriched = enrich_row(
            {
                "title": "Studio Láng Thượng",
                "rent_vnd_month": "4500000",
                "area_m2": "25",
                "address_clean": "Ngõ 44 Pháo Đài Láng, Phường Láng Thượng, Đống Đa Xem bản đồ",
                "description_clean": text,
                "price_basis": "unknown",
                "posted_at": "",
                "posted_date": "",
                "geo_confidence": "",
            },
            price_raw="4.5 triệu/tháng",
        )
        self.assertEqual(enriched["room_type"], "studio_mini")
        self.assertEqual(enriched["ward"], "Láng Thượng")
        self.assertNotIn("Xem bản đồ", enriched["address_clean"])
        self.assertEqual(enriched["price_basis"], "room")
        flags = json.loads(enriched["quality_flags_json"])
        self.assertIn("MISSING_POSTED_AT", flags)
        self.assertIn("GEO_AREA_ONLY", flags)


class BaseAndPlaywrightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _LocalTestHandler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def test_base_scraper_run_writes_clean_and_rejected(self) -> None:
        scraper = _DummyScraper(name="dummy", base_url=self.base_url, delay=1.0)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dummy_rooms.csv"
            exit_code = scraper.run(output)
            self.assertEqual(exit_code, 0)
            with output.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertIn("[số điện thoại]", rows[0]["title"])
            self.assertIn("[email]", rows[0]["description_clean"])
            rejected_path = output.with_name("dummy_rooms_rejected.csv")
            with rejected_path.open(encoding="utf-8-sig", newline="") as stream:
                rejected_rows = list(csv.DictReader(stream))
            self.assertEqual(len(rejected_rows), 1)
            self.assertIn("conflicting", rejected_rows[0]["reason"])

    def test_playwright_scraper_respects_robots_and_403(self) -> None:
        policy = RobotsPolicy(self.base_url)
        self.assertTrue(policy.load())

        async def run_checks() -> None:
            async with PlaywrightScraper(headless=True, delay=1.0, robots_policy=policy) as browser:
                with self.assertRaisesRegex(PermissionError, "robots.txt"):
                    await browser.navigate(f"{self.base_url}/blocked/secret")
                with self.assertRaisesRegex(PermissionError, "HTTP 403"):
                    await browser.navigate(f"{self.base_url}/forbidden")
                rendered = await browser.navigate(
                    f"{self.base_url}/allowed/dong-da",
                    wait_selector=".listing-card",
                )
                self.assertIn("Phòng trọ khép kín Xã Đàn", rendered)

        asyncio.run(run_checks())

    def test_template_playwright_bot_parses_and_filters(self) -> None:
        bot = PlaywrightSourceBot(
            name="localtest",
            base_url=self.base_url,
            url_patterns={
                "dong-da": f"{self.base_url}/allowed/dong-da?page={{page}}",
                "thanh-xuan": f"{self.base_url}/allowed/dong-da?page={{page}}",
                "cau-giay": f"{self.base_url}/allowed/dong-da?page={{page}}",
            },
            wait_selector=".listing-card",
            max_pages=1,
            delay=1.0,
        )
        self.assertTrue(bot.check_robots_txt())
        items, rejected = bot.scrape_district("dong-da", "Đống Đa")
        self.assertEqual(len(items), 2)
        self.assertEqual(rejected, [])
        valid, _ = bot.validate_listing(items[0])
        invalid, reason = bot.validate_listing(items[1])
        self.assertTrue(valid)
        self.assertFalse(invalid)
        self.assertIn("non-room", reason)


class TV1ChecklistAndPipelineTests(unittest.TestCase):
    def test_reingest_preserves_collected_at_and_tracks_content_hash_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            src = data_dir / "phongtro123_rooms.csv"
            with src.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["listing_id", "source_name", "source_record_key", "district", "title", "price_raw", "rent_vnd_month", "area_m2", "address", "collected_at"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "listing_id": "phongtro123:99",
                        "source_name": "phongtro123",
                        "source_record_key": "99",
                        "district": "Đống Đa",
                        "title": "Phòng trọ khép kín Xã Đàn",
                        "price_raw": "3.5 triệu/tháng",
                        "rent_vnd_month": "3500000",
                        "area_m2": "25",
                        "address": "Ngõ 10 Xã Đàn, Đống Đa",
                        "collected_at": "2026-11-25T08:00:00+00:00",
                    }
                )
            summary1 = run_pipeline(data_dir=data_dir, skip_scrape=True)
            with summary1.listings_path.open(encoding="utf-8-sig", newline="") as f:
                row1 = next(csv.DictReader(f))
            self.assertEqual(row1["collected_at"], "2026-11-25T08:00:00+00:00")

            # Price changes while listing_id and collected_at stay unchanged
            with src.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["listing_id", "source_name", "source_record_key", "district", "title", "price_raw", "rent_vnd_month", "area_m2", "address", "collected_at"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "listing_id": "phongtro123:99",
                        "source_name": "phongtro123",
                        "source_record_key": "99",
                        "district": "Đống Đa",
                        "title": "Phòng trọ khép kín Xã Đàn",
                        "price_raw": "3.8 triệu/tháng",
                        "rent_vnd_month": "3800000",
                        "area_m2": "25",
                        "address": "Ngõ 10 Xã Đàn, Đống Đa",
                        "collected_at": "2026-11-25T08:00:00+00:00",
                    }
                )
            summary2 = run_pipeline(data_dir=data_dir, skip_scrape=True)
            with summary2.listings_path.open(encoding="utf-8-sig", newline="") as f:
                row2 = next(csv.DictReader(f))
            self.assertEqual(row2["listing_id"], "phongtro123:99")
            self.assertEqual(row2["collected_at"], "2026-11-25T08:00:00+00:00")
            self.assertNotEqual(row1["content_hash"], row2["content_hash"])

    def test_pipeline_separates_accepted_needs_review_confirmed_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            src_a = data_dir / "phongtro123_rooms.csv"
            src_b = data_dir / "mixstay_rooms.csv"
            with src_a.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["listing_id", "source_name", "source_record_key", "district", "title", "price_raw", "rent_vnd_month", "area_m2", "address", "collected_at"],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "listing_id": "phongtro123:1",
                            "source_name": "phongtro123",
                            "source_record_key": "1",
                            "district": "Thanh Xuân",
                            "title": "Phòng trọ ngõ 10 Nguyễn Trãi gọi 0912345678",
                            "price_raw": "3.2 triệu/tháng",
                            "rent_vnd_month": "3200000",
                            "area_m2": "20",
                            "address": "Ngõ 10 Nguyễn Trãi, Thanh Xuân",
                            "collected_at": "2026-11-25T09:00:00+00:00",
                        },
                        {
                            "listing_id": "phongtro123:2",
                            "source_name": "phongtro123",
                            "source_record_key": "2",
                            "district": "Thanh Xuân",
                            "title": "Cho thuê căn hộ 1N1K Nguyễn Xiển",
                            "price_raw": "5.5 triệu/tháng",
                            "rent_vnd_month": "5500000",
                            "area_m2": "30",
                            "address": "Nguyễn Xiển, Thanh Xuân",
                            "collected_at": "2026-11-25T09:00:00+00:00",
                        },
                        {
                            "listing_id": "phongtro123:3",
                            "source_name": "phongtro123",
                            "source_record_key": "3",
                            "district": "Thanh Xuân",
                            "title": "Phòng trọ giá thỏa thuận",
                            "price_raw": "Thỏa thuận",
                            "rent_vnd_month": "",
                            "area_m2": "20",
                            "address": "Thanh Xuân",
                            "collected_at": "2026-11-25T09:00:00+00:00",
                        },
                    ]
                )
            with src_b.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["listing_id", "source_name", "source_record_key", "district", "title", "price_raw", "rent_vnd_month", "area_m2", "address", "amenities", "collected_at"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "listing_id": "mixstay:9",
                        "source_name": "mixstay",
                        "source_record_key": "9",
                        "district": "Thanh Xuân",
                        "title": "Phòng trọ Nguyễn Trãi",
                        "price_raw": "3.2 triệu/tháng",
                        "rent_vnd_month": "3200000",
                        "area_m2": "20",
                        "address": "10 Đường Nguyễn Trãi, Quận Thanh Xuân",
                        "amenities": "Điều hòa",
                        "collected_at": "2026-11-25T10:00:00+00:00",
                    }
                )

            summary = run_pipeline(data_dir=data_dir, skip_scrape=True)
            self.assertEqual(summary.raw_count, 4)
            self.assertEqual(summary.rejected_count, 1)
            self.assertEqual(summary.needs_review_count, 1)
            self.assertEqual(summary.confirmed_duplicate_count, 1)
            self.assertEqual(summary.clean_count, 1)
            self.assertEqual(validate_release(data_dir=data_dir), [])

    def test_synthetic_evaluation_metrics(self) -> None:
        fixture = Path(__file__).resolve().parent / "fixtures" / "synthetic_eval.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        metrics = evaluate_extraction(data["extraction_samples"])
        by_field = {item.field: item for item in metrics}
        self.assertEqual(by_field["rent_vnd_month"].f1, 1.0)
        self.assertEqual(by_field["price_basis"].f1, 1.0)
        self.assertEqual(by_field["room_type"].f1, 1.0)
        dup_metrics = evaluate_duplicate_pairs(data["duplicate_pairs"])
        self.assertEqual(dup_metrics["precision"], 1.0)

    def test_deduplicator_guards_against_street_only_and_diff_rooms(self) -> None:
        dedup = Deduplicator()
        base = {
            "listing_id": "m:1",
            "district": "Cầu Giấy",
            "rent_vnd_month": "4800000",
            "area_m2": "25",
            "address_clean": "Cầu Giấy • Nguyễn Khánh Toàn",
            "title": "Studio full đồ Ngõ 58 Nguyễn Khánh Toàn",
            "room_type": "studio_mini",
        }
        diff_alley = {
            "listing_id": "m:2",
            "district": "Cầu Giấy",
            "rent_vnd_month": "4800000",
            "area_m2": "25",
            "address_clean": "Cầu Giấy • Nguyễn Khánh Toàn",
            "title": "Phòng 1 ngủ + gác xép ngõ 92 Nguyễn Khánh Toàn",
            "room_type": "loft_room",
        }
        self.assertEqual(dedup.classify_pair(base, diff_alley), "none")

        diff_room = {
            "listing_id": "p:1",
            "district": "Cầu Giấy",
            "rent_vnd_month": "3300000",
            "area_m2": "25",
            "address_clean": "27 ngõ 255 Đường Cầu Giấy, Phường Cầu Giấy, Hà Nội",
            "title": "Nhà 27 ngõ 255 Cầu Giấy trống phòng 202",
        }
        diff_room_2 = {
            "listing_id": "p:2",
            "district": "Cầu Giấy",
            "rent_vnd_month": "3200000",
            "area_m2": "25",
            "address_clean": "27 ngõ 255 Đường Cầu Giấy, Phường Cầu Giấy, Hà Nội",
            "title": "NHÀ 27 NGÕ 255 CẦU GIẤY TRỐNG: phòng 302",
        }
        self.assertEqual(dedup.classify_pair(diff_room, diff_room_2), "none")

    def test_scheduler_time_calculation(self) -> None:
        slots = parse_schedule_times("18:00,06:00")
        self.assertEqual(slots, [(6, 0), (18, 0)])
        morning = datetime(2026, 11, 25, 7, 30, tzinfo=VN_TZ)
        self.assertEqual(next_run_time(morning, slots), datetime(2026, 11, 25, 18, 0, tzinfo=VN_TZ))
        night = datetime(2026, 11, 25, 20, 0, tzinfo=VN_TZ)
        self.assertEqual(next_run_time(night, slots), datetime(2026, 11, 26, 6, 0, tzinfo=VN_TZ))


if __name__ == "__main__":
    unittest.main()
