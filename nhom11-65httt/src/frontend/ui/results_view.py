"""Results list and room detail view (TV4-04) joined strictly by listing_id."""

from __future__ import annotations

from typing import Any

import streamlit as st

from providers import DataProvider, RecommendationResponse
from state import add_to_compare, remove_from_compare
from ui.components import (
    GEO_CONFIDENCE_LABELS,
    build_amenity_rows,
    count_missing_fields,
    format_deposit,
    format_fees_breakdown,
    format_price_basis_label,
    format_price_with_basis,
    format_quality_flags,
    format_room_type,
    is_safe_http_url,
)


def render_results_view(response: RecommendationResponse | None) -> None:
    """Render status banner, warnings, and ranked list from TV3/mock response."""
    st.subheader("2. Kết quả gợi ý phòng trọ")

    if response is None:
        st.info("Hãy chọn hồ sơ hoặc nhập nhu cầu ở trên rồi nhấn **Tìm phòng gợi ý**.")
        return

    if st.session_state.get("results_stale"):
        st.warning("⚠️ Bạn đã thay đổi tiêu chí tìm kiếm nhưng chưa nhấn **Tìm phòng gợi ý**. Danh sách dưới đây thuộc lần tìm trước.")

    st.caption(
        f"Chế độ: **{response.mode_label}** | Phiên bản dữ liệu: `{response.dataset_version}` | "
        f"Phiên bản thuật toán: `{response.algorithm_version}`"
    )

    if response.errors:
        for err in response.errors:
            st.error(err)
        return

    for warn in response.warnings:
        st.warning(warn)

    if response.status == "no_match":
        st.info("Không tìm thấy phòng phù hợp với toàn bộ điều kiện đã chọn. Bạn có thể tăng ngân sách hoặc nới bớt điều kiện bắt buộc rồi tìm lại.")
        return

    if response.status == "unsimulated_mock":
        st.info("Yêu cầu tự nhập này chưa có hồ sơ mô phỏng sẵn trong chế độ mẫu. Hãy chọn một hồ sơ mẫu ở mục trên để xem kết quả giả lập.")
        return

    if not response.items:
        st.info("Danh sách kết quả trống.")
        return

    st.success(f"Tìm thấy **{len(response.items)}** phòng phù hợp (ứng viên xét duyệt: {response.candidate_count}).")
    compare_ids: list[str] = list(st.session_state.get("compare_ids", []))

    for item in response.items:
        listing = item["listing"]
        lid = listing["listing_id"]
        with st.container(border=True):
            top_l, top_r = st.columns([3, 1])
            with top_l:
                st.markdown(f"**#{item.get('rank', '-')} — {listing['title']}**")
                st.caption(
                    f"Mã tin: `{lid}` | Loại: {format_room_type(listing['room_type'])} | "
                    f"Khu vực: {listing['ward']}, {listing['district']} | Nguồn: {listing['source_name']} ({listing['posted_date']})"
                )
            with top_r:
                score = item.get("score")
                st.metric("Điểm phù hợp", f"{score:.2f}" if isinstance(score, (int, float)) else "N/A")

            m1, m2, m3 = st.columns(3)
            m1.write(f"**Giá thuê:** {format_price_with_basis(listing['rent_vnd_month'], listing['price_basis'])}")
            area = listing.get("area_m2")
            m2.write(f"**Diện tích:** {f'{area:g} m²' if area is not None else 'Chưa có dữ liệu'}")
            m3.write(f"**Độ chính xác vị trí:** {GEO_CONFIDENCE_LABELS.get(listing.get('geo_confidence', 'unknown'), 'Chưa rõ')}")

            if item.get("reasons"):
                st.markdown("**Lý do gợi ý:** " + " • ".join(item["reasons"]))
            for w in item.get("warnings", []):
                st.caption(f"⚠️ {w}")

            b1, b2 = st.columns([1, 1])
            if b1.button("📄 Xem chi tiết", key=f"detail_{lid}"):
                st.session_state["selected_listing_id"] = lid
                st.session_state["active_view"] = "detail"
                st.rerun()

            if lid in compare_ids:
                if b2.button("➖ Bỏ khỏi so sánh", key=f"rm_cmp_{lid}"):
                    remove_from_compare(st.session_state, lid)
                    st.rerun()
            else:
                if b2.button("➕ Thêm vào so sánh", key=f"add_cmp_{lid}"):
                    ok, msg = add_to_compare(st.session_state, lid)
                    if ok:
                        st.toast(msg)
                    else:
                        st.warning(msg)
                    st.rerun()


def render_detail_view(provider: DataProvider, response: RecommendationResponse | None) -> None:
    """Render detailed trade-offs for a listing looked up strictly by listing_id."""
    listing_id = st.session_state.get("selected_listing_id")
    if not listing_id:
        st.info("Chưa chọn phòng để xem chi tiết. Hãy chọn một phòng từ tab **Kết quả**.")
        return

    listing = provider.get_listing_by_id(listing_id)
    if listing is None:
        st.error(f"Lỗi dữ liệu: Không tìm thấy mã tin `{listing_id}` trong tệp danh sách hiện tại.")
        return

    matched_rec: dict[str, Any] | None = None
    if response and response.items:
        for item in response.items:
            if item["listing"]["listing_id"] == listing_id:
                matched_rec = item
                break

    if st.button("⬅ Quay lại danh sách kết quả"):
        st.session_state["active_view"] = "results"
        st.rerun()

    st.subheader(listing["title"])
    st.caption(
        f"Mã tin: `{listing_id}` | Loại phòng: {format_room_type(listing['room_type'])} | "
        f"Thu thập lúc: {listing['collected_at']} | Ngày đăng: {listing['posted_date']}"
    )

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("#### Giá thuê, phí và tiền cọc")
        st.write(f"- **Giá thuê:** {format_price_with_basis(listing['rent_vnd_month'], listing['price_basis'])}")
        st.write(f"- **Cơ sở tính giá:** {format_price_basis_label(listing['price_basis'])}")
        st.write(f"- **Tiền cọc (tách riêng chi phí tháng):** {format_deposit(listing.get('deposit_vnd'), listing.get('deposit_months'))}")
        for fee_name, fee_val in format_fees_breakdown(listing.get("fees")):
            st.write(f"- **{fee_name}:** {fee_val}")

    with col_right:
        st.markdown("#### Tiện ích và thuộc tính (3 trạng thái)")
        area = listing.get("area_m2")
        occ = listing.get("max_occupants")
        st.write(f"- **Diện tích:** {f'{area:g} m²' if area is not None else 'Chưa có dữ liệu'}")
        st.write(f"- **Số người tối đa:** {occ if occ is not None else 'Chưa có dữ liệu'}")
        for label, state_text in build_amenity_rows(listing.get("amenities")):
            st.write(f"- **{label}:** {state_text}")

    st.markdown("#### Giải thích gợi ý & Vị trí")
    if matched_rec:
        st.write(f"- **Thứ hạng:** #{matched_rec.get('rank')} | **Điểm phù hợp:** {matched_rec.get('score')}")
        if matched_rec.get("score_components"):
            st.write("- **Điểm thành phần:** " + ", ".join(f"{k}: {v}" for k, v in matched_rec["score_components"].items()))
        if matched_rec.get("reasons"):
            st.write("- **Lý do chính:** " + "; ".join(matched_rec["reasons"]))
        for w in matched_rec.get("warnings", []):
            st.warning(w)
    else:
        st.info("Phòng này hiện chưa có điểm gợi ý từ lần chạy gần nhất.")

    st.write(f"- **Địa chỉ:** {listing['address_clean']} ({listing['ward']}, {listing['district']})")
    st.write(f"- **Mức độ chính xác vị trí:** {GEO_CONFIDENCE_LABELS.get(listing.get('geo_confidence', 'unknown'), 'Chưa rõ')}")

    q_flags = format_quality_flags(listing.get("quality_flags"))
    missing_count = count_missing_fields(listing)
    if q_flags or missing_count > 0:
        st.markdown("#### Cờ chất lượng & Phần thông tin còn thiếu")
        if missing_count > 0:
            st.info(f"Tin này hiện còn thiếu dữ liệu ở **{missing_count}** nhóm thông tin quan trọng (không tự điền 0 hay 'miễn phí').")
        for flag_msg in q_flags:
            st.warning(f"🚩 {flag_msg}")

    st.markdown("#### Nguồn tin & Giới hạn hỗ trợ quyết định")
    st.write("*(Lưu ý: Hệ thống chỉ hỗ trợ ra quyết định; sinh viên cần xác minh thực tế trước khi đặt cọc hoặc ký hợp đồng.)*")
    st.text(f"Mô tả nguồn (đã làm sạch PII): {listing.get('description_clean', '')}")
    if is_safe_http_url(listing.get("source_url")):
        st.markdown(f"[Mở liên kết nguồn gốc ({listing['source_name']})]({listing['source_url']})")
    else:
        st.caption("Liên kết nguồn không khả dụng hoặc không hợp lệ.")
