"""Checks for the fields present in MixStay's public HTML and JSON-LD."""

import json
import unittest

from mixstay import Candidate, parse_detail, parse_listing_page


URL = "https://mixstay.vn/tin/cmtb8o98g0003fywz2anl2hk0"


def room_card(title="Phòng studio Xã Đàn", district="Đống Đa", kind="Studio", available=1):
    return f"""<a href="/tin/cmtb8o98g0003fywz2anl2hk0">
        <span>{kind}</span><span>Còn {available} phòng</span>
        <div><h3>{title}</h3><p>{district} • Xã Đàn</p></div>
    </a>"""


def detail_page(name="Phòng studio Xã Đàn", district="Đống Đa", availability="https://schema.org/InStock"):
    product = {
        "@type": "Product", "name": name, "url": URL,
        "description": "Phòng có điều hòa. Gọi 0912345678.",
        "offers": {
            "price": 5300000, "priceCurrency": "VND",
            "priceSpecification": {"unitText": "tháng"}, "availability": availability,
        },
        "additionalProperty": [
            {"name": "Diện tích", "value": "30 m²"},
            {"name": "Khu vực", "value": district},
        ],
    }
    return f'<html><head><script type="application/ld+json">{json.dumps(product, ensure_ascii=False)}</script></head></html>'.encode()


class MixstayParserTests(unittest.TestCase):
    def test_public_html_and_jsonld_make_one_room_record(self):
        candidates, rejected = parse_listing_page(room_card().encode(), "Đống Đa")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(rejected, [])
        record = parse_detail(detail_page(), candidates[0], "2026-11-25T00:00:00+00:00")
        self.assertEqual(record["listing_id"], "mixstay:cmtb8o98g0003fywz2anl2hk0")
        self.assertEqual(record["rent_vnd_month"], "5300000")
        self.assertEqual(record["area_m2"], "30")
        self.assertEqual(record["available_rooms"], "1")
        self.assertIn("[số điện thoại]", record["description_clean"])
        self.assertEqual(record["public_code"], "")

    def test_list_rejects_sale_apartment_wrong_district_and_unavailable_room(self):
        bad_cards = (
            room_card(title="Bán nhà Xã Đàn"),
            room_card(kind="1 ngủ 1 khách"),
            room_card(title="Studio Hà Đông"),
            room_card(available=0),
        )
        for card in bad_cards:
            with self.subTest(card=card[:80]):
                candidates, rejected = parse_listing_page(card.encode(), "Đống Đa")
                self.assertEqual(candidates, [])
                self.assertEqual(len(rejected), 1)

    def test_detail_rejects_wrong_district_sale_and_unavailable_offer(self):
        candidate = Candidate(URL, "cmtb8o98g0003fywz2anl2hk0", "Đống Đa", "Phòng studio", "Studio", "Đống Đa • Xã Đàn", 1)
        bad_pages = (
            detail_page(district="Hà Đông"),
            detail_page(name="Bán nhà Xã Đàn"),
            detail_page(availability="https://schema.org/OutOfStock"),
        )
        for page in bad_pages:
            with self.subTest(page=page[:100]), self.assertRaises(ValueError):
                parse_detail(page, candidate, "now")


if __name__ == "__main__":
    unittest.main()
