"""Main entry point for the TV4 Streamlit rental analysis & decision-support application."""

from __future__ import annotations

import streamlit as st

from config import PROVIDER_MODE_MOCK, PROVIDER_MODE_REAL, SUPPORTED_UI_VERSION
from providers import DataProvider, MockDataProvider, ProviderError, RealDataProvider
from state import DEFAULT_PREFERENCES, init_session_state, record_search_result
from ui.bi_view import render_bi_view
from ui.compare_view import render_compare_view
from ui.map_view import render_map_view
from ui.results_view import render_detail_view, render_results_view
from ui.search_form import render_search_form


st.set_page_config(
    page_title="Hệ thống phân tích thị trường phòng trọ sinh viên",
    page_icon="🏠",
    layout="wide",
)


def _build_provider(mode: str) -> DataProvider:
    if mode == PROVIDER_MODE_REAL:
        return RealDataProvider()
    return MockDataProvider()


def main() -> None:
    init_session_state(st.session_state)

    st.title("🏠 Hệ thống phân tích thị trường phòng trọ hỗ trợ sinh viên")
    st.caption(
        f"Phân hệ Giao diện & Trải nghiệm (TV4 • Phiên bản `{SUPPORTED_UI_VERSION}`) — "
        "Hỗ trợ ra quyết định, không thay thế khảo sát thực địa hoặc giao dịch đặt cọc."
    )

    with st.sidebar:
        st.header("Cấu hình dữ liệu & Chế độ")
        mode = st.radio(
            "Nguồn dữ liệu & Gợi ý:",
            options=[PROVIDER_MODE_MOCK, PROVIDER_MODE_REAL],
            format_func=lambda m: (
                "Chế độ mẫu (dữ liệu/kết quả giả lập)"
                if m == PROVIDER_MODE_MOCK
                else "Chế độ thực (TV1 listings + TV3 mô-đun)"
            ),
            key="provider_mode_radio",
        )
        st.session_state["provider_mode"] = mode

    try:
        provider = _build_provider(mode)
        info = provider.get_dataset_info()
    except ProviderError as exc:
        st.error(f"Không thể khởi tạo nguồn dữ liệu ({mode}): {exc}")
        st.info("Hãy kiểm tra lại tệp dữ liệu mẫu trong `fixtures/` hoặc đường dẫn `data/listings.csv`.")
        return

    if info.get("is_mock"):
        st.info(
            f"📌 **{info['mode_label']}** | Phạm vi: {info['scope']} | "
            f"Số tin mẫu: {info['listing_count']} | Phiên bản: `{info['dataset_version']}`"
        )
    else:
        st.success(
            f"📌 **{info['mode_label']}** | Khu vực: {info['scope']} | "
            f"Số tin: {info['listing_count']} | Phiên bản: `{info['dataset_version']}`"
        )

    preferences, profile_id, submit_clicked, reset_clicked = render_search_form(provider)

    if reset_clicked:
        st.session_state["draft_preferences"] = dict(DEFAULT_PREFERENCES)
        st.session_state["submitted_preferences"] = None
        st.session_state["last_response"] = None
        st.session_state["results_stale"] = False
        st.session_state["active_view"] = "results"
        st.rerun()

    if submit_clicked:
        response = provider.recommend(preferences=preferences, profile_id=profile_id)
        removed_ids = record_search_result(st.session_state, preferences, response)
        if removed_ids:
            st.toast(
                "Đã loại bỏ khỏi danh sách so sánh các tin không còn ở phiên bản dữ liệu mới: "
                + ", ".join(removed_ids)
            )
        st.session_state["active_view"] = "results"

    last_response = st.session_state.get("last_response")
    compare_count = len(st.session_state.get("compare_ids", []))

    tab_results, tab_detail, tab_compare, tab_map, tab_bi = st.tabs(
        [
            "📋 Kết quả gợi ý",
            "📄 Chi tiết phòng",
            f"⚖️ So sánh ({compare_count}/4)",
            "🗺️ Bản đồ vị trí",
            "📊 Dashboard BI (Superset)",
        ]
    )

    with tab_results:
        render_results_view(last_response)

    with tab_detail:
        render_detail_view(provider, last_response)

    with tab_compare:
        render_compare_view(provider, last_response)

    with tab_map:
        render_map_view(last_response)

    with tab_bi:
        render_bi_view(provider)


if __name__ == "__main__":
    main()
