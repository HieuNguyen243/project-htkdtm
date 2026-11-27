"""Search criteria form (TV4-03) with validation, required/nice-to-have split, and stale state tracking."""

from __future__ import annotations

from typing import Any

import streamlit as st

from config import AMENITIES, CAMPUSES, COST_MODE_LABELS, DISTRICTS, PRICE_BASIS_LABELS, ROOM_TYPES
from providers import DataProvider
from state import DEFAULT_PREFERENCES, mark_stale_if_modified


def render_search_form(provider: DataProvider) -> tuple[dict[str, Any], str | None, bool, bool]:
    """Render sidebar/main demand input form. Returns (preferences, profile_id, submit_clicked, reset_clicked)."""
    st.subheader("1. Nhập nhu cầu tìm phòng")

    profiles = provider.get_profiles()
    profile_id: str | None = st.session_state.get("selected_profile_id")
    if profiles:
        profile_map = {p["profile_id"]: p["label"] for p in profiles}
        profile_options = [*profile_map.keys(), "__custom__"]
        selected = st.selectbox(
            "Hồ sơ mẫu (Chế độ giả lập):",
            options=profile_options,
            format_func=lambda k: profile_map.get(k, "Tự nhập nhu cầu (chưa có kết quả mẫu)"),
            key="ui_profile_selector",
        )
        profile_id = None if selected == "__custom__" else selected
        st.session_state["selected_profile_id"] = profile_id

    draft = dict(st.session_state.get("draft_preferences", DEFAULT_PREFERENCES))

    col1, col2 = st.columns(2)
    with col1:
        budget_vnd = st.number_input(
            "Ngân sách tối đa (VNĐ/tháng):",
            min_value=0,
            max_value=50_000_000,
            value=int(draft.get("budget_vnd", 4_000_000)),
            step=200_000,
        )
        price_basis = st.radio(
            "Cơ sở giá:",
            options=list(PRICE_BASIS_LABELS.keys()),
            format_func=lambda k: PRICE_BASIS_LABELS[k],
            horizontal=True,
        )
        cost_mode = st.radio(
            "Chế độ xét chi phí:",
            options=list(COST_MODE_LABELS.keys()),
            format_func=lambda k: COST_MODE_LABELS[k],
        )

    with col2:
        campus_options = {c["campus_id"]: f"{c['school_name']} ({c['campus_name']})" for c in CAMPUSES}
        campus_id = st.selectbox(
            "Trường / Cơ sở học tập:",
            options=list(campus_options.keys()),
            format_func=lambda k: campus_options[k],
        )
        district = st.selectbox("Quận / Khu vực ưu tiên:", options=["Tất cả", *DISTRICTS], index=1)
        room_type = st.selectbox(
            "Loại phòng:",
            options=["all", *ROOM_TYPES.keys()],
            format_func=lambda k: "Tất cả loại phòng trong phạm vi" if k == "all" else ROOM_TYPES[k],
        )
        occupants = st.number_input("Số người ở thực tế:", min_value=1, max_value=10, value=int(draft.get("occupants", 1)), step=1)

    with st.expander("Tiện ích & Mức độ ưu tiên (tùy chọn)", expanded=False):
        st.caption("Lưu ý: Chọn quá nhiều điều kiện 'bắt buộc có' có thể làm giảm số lượng phòng phù hợp.")
        c_req, c_opt = st.columns(2)
        with c_req:
            must_have = st.multiselect(
                "Tiện ích BẮT BUỘC có:",
                options=list(AMENITIES.keys()),
                format_func=lambda k: AMENITIES[k],
            )
        with c_opt:
            nice_to_have = st.multiselect(
                "Tiện ích MONG MUỐN thêm:",
                options=[k for k in AMENITIES if k not in must_have],
                format_func=lambda k: AMENITIES[k],
            )

        st.markdown("**Trọng số ưu tiên chuyển sang mô-đun gợi ý (TV3):**")
        w1, w2, w3 = st.columns(3)
        w_budget = w1.slider("Ưu tiên Giá (%)", 0, 100, 40, step=5)
        w_location = w2.slider("Ưu tiên Vị trí (%)", 0, 100, 35, step=5)
        w_amenities = w3.slider("Ưu tiên Tiện ích (%)", 0, 100, 25, step=5)
        top_k = st.slider("Số lượng gợi ý tối đa (top_k):", 1, 20, 10)

    current_preferences: dict[str, Any] = {
        "budget_vnd": int(budget_vnd),
        "price_basis": price_basis,
        "cost_mode": cost_mode,
        "campus_id": campus_id,
        "district": district,
        "room_type": room_type,
        "occupants": int(occupants),
        "must_have_amenities": list(must_have),
        "nice_to_have_amenities": list(nice_to_have),
        "weights": {"budget": w_budget, "location": w_location, "amenities": w_amenities},
        "top_k": int(top_k),
    }

    st.session_state["draft_preferences"] = current_preferences
    mark_stale_if_modified(st.session_state, current_preferences)

    btn_col1, btn_col2 = st.columns([1, 1])
    submit_clicked = btn_col1.button("🔍 Tìm phòng gợi ý", type="primary", use_container_width=True)
    reset_clicked = btn_col2.button("↺ Đặt lại điều kiện", use_container_width=True)

    return current_preferences, profile_id, submit_clicked, reset_clicked
