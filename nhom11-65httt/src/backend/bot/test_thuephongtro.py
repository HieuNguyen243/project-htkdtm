"""Checks the filters that keep property sales and expired listings out of CSV."""

import unittest
from datetime import datetime

from thuephongtro import VN_TZ, parse_detail, parse_list, parse_price, room_title


class RentalFilterTests(unittest.TestCase):
    def test_title_and_price_scope(self):
        self.assertTrue(room_title("Cho thuê phòng trọ khép kín có ban công"))
        for title in ("Bán căn hộ chung cư", "Cho thuê căn hộ 1N1K", "Cho thuê nhà nguyên căn",
                      "Cho thuê văn phòng", "Cần thuê phòng trọ", "Phòng khách 1 ngủ"):
            self.assertFalse(room_title(title), title)
        self.assertEqual(parse_price("3,5 Triệu/tháng"), 3_500_000)
        for value in ("4.2 Nghìn/tháng", "450000 Triệu/tháng", "3 Triệu/ngày"):
            with self.assertRaises(ValueError):
                parse_price(value)

    def test_list_requires_district_rental_filter(self):
        page = b'<h1>Cho thue nha o Dong Da</h1>'
        with self.assertRaises(ValueError):
            parse_list(page, "Đống Đa")

    def test_expired_detail_rejected(self):
        page = """<meta charset="utf-8"><div id="breadcrumb"><a href="https://thuephongtro.com/cho-thue-phong-tro">Phòng</a>
        <a href="https://thuephongtro.com/cho-thue-phong-tro-dong-da">Đống Đa</a></div>
        <h1>Cho thuê phòng trọ khép kín</h1><div class="section-content">Phòng trọ khép kín còn cho thuê</div>
        <div class="post-features"><p class="post-address">Địa chỉ: Đống Đa, Hà Nội</p>
        <span class="post-price">3 Triệu/tháng</span><span class="post-acreage">20 m²</span></div>
        <div class="section-detail-row"><strong>Mã tin</strong><span>123</span></div>
        <div class="section-detail-row"><strong>Ngày hết hạn</strong><span>01/11/2026</span></div>""".encode()
        candidate = {"key": "123", "district": "Đống Đa", "title": "Cho thuê phòng trọ khép kín",
                     "price_raw": "3 Triệu/tháng", "source_url": "https://thuephongtro.com/phong-123.html"}
        with self.assertRaisesRegex(ValueError, "expired"):
            parse_detail(page, candidate, datetime(2026, 11, 25, tzinfo=VN_TZ))
        record = parse_detail(page, candidate, datetime(2026, 11, 25, tzinfo=VN_TZ), include_expired=True)
        self.assertEqual(record["listing_status"], "expired")
        self.assertEqual(record["rent_vnd_month"], "3000000")


if __name__ == "__main__":
    unittest.main()
