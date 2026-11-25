"""Unit tests for Mua Ban __NEXT_DATA__ scraper and room-rental filters."""

from __future__ import annotations

import json
import unittest

from muaban import parse_detail, parse_listing_links


def make_detail_html(
    classified_id: int = 71312250,
    title: str = "Cho thuê phòng ở Trung Kính",
    price: int = 3_000_000,
    price_display: str = "3 triệu/tháng",
    district_crumb: str = "Quận Cầu Giấy",
    is_expired: bool = False,
) -> bytes:
    payload = {
        "props": {
            "pageProps": {
                "classified": {
                    "id": classified_id,
                    "title": title,
                    "body": "Phòng khép kín sạch sẽ.<br />Điện 4k/số, nước 100k/người. LH 0912345678.",
                    "address": "Phường Yên Hòa, Quận Cầu Giấy, Hà Nội",
                    "price": price,
                    "price_display": price_display,
                    "publish_at": "2026-11-25T00:00:12+07:00",
                    "is_expired": is_expired,
                    "is_outdate": False,
                    "parameters": [
                        {"label": "Diện tích sử dụng", "value": "25 m²"},
                        {"label": "Điểm nổi bật", "value": "<ul><li>Giao nhà ngay</li></ul>"},
                    ],
                    "breadcrumbs": [
                        {"name": "Cho thuê"},
                        {"name": "Hà Nội"},
                        {"name": district_crumb},
                        {"name": "Phường Yên Hòa"},
                    ],
                }
            }
        }
    }
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(payload, ensure_ascii=False)}</script></html>'.encode()


class MuabanParserTests(unittest.TestCase):
    def test_parse_listing_links_filters_district_and_dedups(self) -> None:
        html_bytes = """
        <a href="/bat-dong-san/cho-thue-nha-tro-phong-tro-quan-cau-giay-ha-noi/phong-a-id123">A</a>
        <a href="/bat-dong-san/cho-thue-nha-tro-phong-tro-quan-cau-giay-ha-noi/phong-a-id123">A dup</a>
        <a href="/bat-dong-san/cho-thue-nha-tro-phong-tro-quan-dong-da-ha-noi/phong-b-id456">Other</a>
        """.encode()
        links = parse_listing_links(html_bytes, "cau-giay")
        self.assertEqual(
            links,
            [("https://muaban.net/bat-dong-san/cho-thue-nha-tro-phong-tro-quan-cau-giay-ha-noi/phong-a-id123", "123")],
        )

    def test_parse_detail_valid_record(self) -> None:
        url = "https://muaban.net/bat-dong-san/cho-thue-nha-tro-phong-tro-quan-cau-giay-ha-noi/phong-id71312250"
        record = parse_detail(make_detail_html(), url, "71312250", "Cầu Giấy", "2026-11-25T13:00:00+00:00")
        self.assertEqual(record["listing_id"], "muaban:71312250")
        self.assertEqual(record["rent_vnd_month"], "3000000")
        self.assertEqual(record["area_m2"], "25")
        self.assertEqual(record["ward"], "Yên Hòa")
        self.assertIn("[số điện thoại]", record["description_clean"])
        self.assertEqual(record["amenities"], "Giao nhà ngay")

    def test_parse_detail_rejects_expired_house_and_wrong_district(self) -> None:
        url = "https://muaban.net/bat-dong-san/cho-thue-nha-tro-phong-tro-quan-cau-giay-ha-noi/phong-id71312250"
        for bad_html in (
            make_detail_html(is_expired=True),
            make_detail_html(title="Cho thuê nhà 2 tầng cũ mặt ngõ"),
            make_detail_html(title="Cho thuê căn hộ 1N1K Trung Kính"),
            make_detail_html(district_crumb="Quận Hà Đông"),
        ):
            with self.assertRaises(ValueError):
                parse_detail(bad_html, url, "71312250", "Cầu Giấy", "2026-11-25T13:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
