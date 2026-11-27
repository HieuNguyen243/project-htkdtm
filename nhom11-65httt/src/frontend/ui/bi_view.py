"""Apache Superset BI integration view (TV4) with multi-dashboard embedding and offline fallback."""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config import DEFAULT_SUPERSET_URL, SUPERSET_DASHBOARDS
from providers import DataProvider
from ui.components import check_superset_health, format_room_type, is_safe_http_url


def build_market_overview_df(listings: list[dict[str, Any]]) -> pd.DataFrame:
    """Compute lightweight district-level summary from active listings for standalone BI preview."""
    if not listings:
        return pd.DataFrame()
    df = pd.DataFrame(listings)
    if "district" not in df.columns or "rent_vnd_month" not in df.columns:
        return pd.DataFrame()
    room_only = df[df.get("price_basis", "room") == "room"].copy()
    if room_only.empty:
        return pd.DataFrame()
    summary = (
        room_only.groupby("district", dropna=True)
        .agg(
            so_tin=("listing_id", "count"),
            gia_tb_vnd=("rent_vnd_month", "mean"),
            dien_tich_tb=("area_m2", "mean"),
        )
        .reset_index()
    )
    summary["gia_tb_vnd"] = summary["gia_tb_vnd"].round(0)
    summary["dien_tich_tb"] = summary["dien_tich_tb"].round(1)
    return summary


def render_bi_view(provider: DataProvider, default_url: str = DEFAULT_SUPERSET_URL) -> None:
    """Render Superset BI dashboard embedding, direct links, and standalone analytics preview."""
    st.subheader("5. Phân hệ BI & Trực quan hóa Apache Superset")
    st.caption(
        "Tích hợp kết nối trực tiếp với 3 Dashboard BI do Thành viên 2 (Trần Thị Minh Thư) phát triển. "
        "Nếu cụm Docker Superset chưa khởi động, giao diện hiển thị biểu đồ nội bộ để không làm gián đoạn trải nghiệm."
    )

    # 1. Configuration & Connection bar
    with st.container(border=True):
        c_url, c_status, c_embed = st.columns([2.5, 1.2, 1.3])
        with c_url:
            base_url = st.text_input(
                "Địa chỉ máy chủ Apache Superset (Base URL):",
                value=default_url,
                help="Mặc định là http://localhost:8089 theo cấu hình Docker của TV2.",
                key="bi_superset_base_url",
            ).strip().rstrip("/")
        with c_status:
            st.markdown("**Trạng thái kết nối:**")
            is_online = check_superset_health(base_url)
            if is_online:
                st.success("🟢 Superset Online (8089)")
            else:
                st.warning("🟡 Superset Offline / Chưa bật")
        with c_embed:
            st.markdown("**Chế độ hiển thị:**")
            embed_mode = st.radio(
                "Kiểu xem:",
                options=["iframe", "links_only"],
                format_func=lambda x: "Nhúng trực tiếp (Iframe)" if x == "iframe" else "Chỉ mở liên kết",
                horizontal=True,
                key="bi_embed_mode_radio",
            )

    # 2. Tabs for the 3 TV2 Dashboards + Standalone Fallback
    tab_labels = [f"📊 {d['title']}" for d in SUPERSET_DASHBOARDS]
    tab_labels.append("📈 Thống kê nội bộ (Standalone)")

    tabs = st.tabs(tab_labels)

    for idx, d_info in enumerate(SUPERSET_DASHBOARDS):
        with tabs[idx]:
            slug = d_info["slug"]
            dash_url = f"{base_url}/superset/dashboard/{slug}/?standalone=true"
            full_dash_url = f"{base_url}/superset/dashboard/{slug}/"

            st.markdown(f"### {d_info['title']}")
            st.write(f"- **Mô tả:** {d_info['description']}")
            st.write(f"- **Cấu trúc:** {d_info['kpi_summary']}")
            st.write(f"- **Dashboard Slug:** `{slug}` | **URL:** `{full_dash_url}`")

            # Link button
            b_col1, b_col2 = st.columns([1.5, 3])
            with b_col1:
                st.link_button(
                    f"🔗 Mở `{slug}` trong tab mới",
                    url=full_dash_url,
                    type="primary",
                    use_container_width=True,
                )
            with b_col2:
                if not is_online:
                    st.caption(
                        "💡 Hướng dẫn khởi chạy Superset: Mở Git Bash tại `src/backend/bi`, cấu hình `.env` và chạy `bash setup_bi.sh`."
                    )

            if embed_mode == "iframe":
                if not is_online:
                    st.info(
                        f"Khung nhúng sẵn sàng cho `{slug}`. Khi bạn chạy cụm Docker Superset tại cổng 8089, "
                        "Dashboard sẽ tự động hiển thị trực tiếp bên dưới mà không cần tải lại trang."
                    )
                try:
                    components.iframe(dash_url, height=720, scrolling=True)
                except Exception as exc:
                    st.error(f"Không thể nhúng iframe: {exc}")

    # 3. Standalone Internal Analytics Tab
    with tabs[-1]:
        st.markdown("### Thống kê thị trường nội bộ (Hoạt động không phụ thuộc Superset/Docker)")
        st.caption(
            "Phân hệ này chạy trực tiếp từ dữ liệu ứng dụng hiện tại, đảm bảo luôn có báo cáo BI ngay cả khi môi trường Superset chưa cài đặt."
        )

        listings: list[dict[str, Any]] = []
        if hasattr(provider, "_listings") and isinstance(provider._listings, dict):
            listings = list(provider._listings.values())

        summary_df = build_market_overview_df(listings)
        if summary_df.empty:
            st.info("Chưa đủ dữ liệu giá theo phòng để tổng hợp thống kê khu vực.")
        else:
            col_tbl, col_chart = st.columns([1.3, 1])
            with col_tbl:
                st.dataframe(
                    summary_df.rename(
                        columns={
                            "district": "Quận",
                            "so_tin": "Số tin (theo phòng)",
                            "gia_tb_vnd": "Giá thuê TB (VNĐ)",
                            "dien_tich_tb": "Diện tích TB (m²)",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            with col_chart:
                st.markdown("**Giá thuê trung bình theo quận:**")
                st.bar_chart(summary_df.set_index("district")["gia_tb_vnd"])

            room_type_counts = pd.Series(
                [format_room_type(item.get("room_type", "")) for item in listings]
            ).value_counts()
            st.markdown("**Cơ cấu nguồn cung theo loại phòng:**")
            st.bar_chart(room_type_counts)
