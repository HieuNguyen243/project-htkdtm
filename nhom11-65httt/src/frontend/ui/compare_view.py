"""Side-by-side 2-4 room comparison view (TV4-05) highlighting trade-offs and missing data."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from config import AMENITIES, MAX_COMPARE_ITEMS, MIN_COMPARE_ITEMS
from providers import DataProvider, RecommendationResponse
from state import clear_compare, remove_from_compare
from ui.components import (
    GEO_CONFIDENCE_LABELS,
    format_amenity_state,
    format_deposit,
    format_fees_breakdown,
    format_price_with_basis,
    format_room_type,
)


def render_compare_view(provider: DataProvider, response: RecommendationResponse | None) -> None:
    """Render comparison table for 2 to 4 selected listings."""
    st.subheader(f"3. So sánh {MIN_COMPARE_ITEMS}–{MAX_COMPARE_ITEMS} phòng")

    compare_ids: list[str] = list(st.session_state.get("compare_ids", []))
    if not compare_ids:
        st.info("Chưa có phòng nào trong danh sách so sánh. Hãy nhấn **Thêm vào so sánh** ở danh sách kết quả.")
        return

    top_cols = st.columns([3, 1])
    top_cols[0].caption(f"Đang chọn **{len(compare_ids)}/{MAX_COMPARE_ITEMS}** phòng để đối chiếu.")
    if top_cols[1].button("🗑️ Xóa toàn bộ so sánh"):
        clear_compare(st.session_state)
        st.rerun()

    if len(compare_ids) < MIN_COMPARE_ITEMS:
        st.warning(f"Cần chọn tối thiểu {MIN_COMPARE_ITEMS} phòng để so sánh. Hiện mới chọn {len(compare_ids)} phòng.")

    listings: list[dict[str, Any]] = []
    for lid in compare_ids:
        rec = provider.get_listing_by_id(lid)
        if rec is not None:
            listings.append(rec)

    if not listings:
        st.error("Không tìm thấy dữ liệu cho các mã tin đã chọn.")
        return

    # Check mixed price basis (e.g., per room vs per person)
    bases = {item.get("price_basis") for item in listings}
    if len(bases) > 1:
        st.warning("⚠️ Cảnh báo: Danh sách so sánh có lẫn cả giá **theo phòng** và giá **theo người**. Không nên kết luận bên nào rẻ hơn nếu chưa quy đổi cùng cơ sở.")

    if st.session_state.get("results_stale"):
        st.warning("⚠️ Tiêu chí tìm kiếm vừa thay đổi; điểm gợi ý hiển thị thuộc lần chạy trước.")

    # Quick remove buttons
    rm_cols = st.columns(len(listings))
    for idx, item in enumerate(listings):
        lid = item["listing_id"]
        if rm_cols[idx].button(f"✖ Bỏ {lid}", key=f"cmp_rm_{lid}"):
            remove_from_compare(st.session_state, lid)
            st.rerun()

    rec_by_id: dict[str, dict[str, Any]] = {}
    if response and response.items:
        for r in response.items:
            rec_by_id[r["listing"]["listing_id"]] = r

    rows: dict[str, dict[str, str]] = {}
    col_names = [f"{item['listing_id']} ({item['district']})" for item in listings]

    def _add_row(label: str, values: list[str]) -> None:
        rows[label] = dict(zip(col_names, values))

    _add_row("Tiêu đề", [item["title"] for item in listings])
    _add_row("Loại phòng", [format_room_type(item["room_type"]) for item in listings])
    _add_row("Tiền thuê & Cơ sở giá", [format_price_with_basis(item.get("rent_vnd_month"), item.get("price_basis", "")) for item in listings])
    _add_row("Tiền cọc (tách riêng)", [format_deposit(item.get("deposit_vnd"), item.get("deposit_months")) for item in listings])
    _add_row(
        "Các khoản phí đã biết",
        ["; ".join(f"{k}: {v}" for k, v in format_fees_breakdown(item.get("fees"))) for item in listings],
    )
    _add_row("Diện tích", [f"{item['area_m2']:g} m²" if item.get("area_m2") is not None else "Chưa có dữ liệu" for item in listings])
    _add_row("Số người tối đa", [str(item["max_occupants"]) if item.get("max_occupants") is not None else "Chưa có dữ liệu" for item in listings])
    _add_row("Vị trí / Độ chính xác", [f"{item['ward']}, {item['district']} ({GEO_CONFIDENCE_LABELS.get(item.get('geo_confidence', 'unknown'), 'Chưa rõ')})" for item in listings])

    for code, label in AMENITIES.items():
        _add_row(f"Tiện ích: {label}", [format_amenity_state((item.get("amenities") or {}).get(code)) for item in listings])

    _add_row(
        "Điểm & Thứ hạng (cùng lần chạy)",
        [
            f"#{rec_by_id[item['listing_id']].get('rank')} (điểm {rec_by_id[item['listing_id']].get('score')})"
            if item["listing_id"] in rec_by_id
            else "Chưa có trong lần chạy hiện tại"
            for item in listings
        ],
    )
    _add_row("Thời điểm dữ liệu", [item.get("posted_date") or item.get("collected_at", "") for item in listings])

    df = pd.DataFrame.from_dict(rows, orient="index")
    st.table(df)
