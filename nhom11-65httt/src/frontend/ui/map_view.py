"""Grounded map view (TV4-06) distinguishing exact vs centroid vs missing coordinates."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from providers import RecommendationResponse
from ui.components import GEO_CONFIDENCE_LABELS, format_price_with_basis, has_usable_coordinates


def render_map_view(response: RecommendationResponse | None) -> None:
    """Render map only for listings with valid coordinates; never plot (0,0) or fake points."""
    st.subheader("4. Bản đồ vị trí có căn cứ")
    st.caption(
        "Lưu ý: Chỉ hiển thị các tin có tọa độ hợp lệ. Các điểm đại diện phường/quận được gắn nhãn rõ ràng "
        "và không dùng để khẳng định khoảng cách đi lại thực tế. Nền bản đồ có thể cần kết nối Internet."
    )

    if response is None or not response.items:
        st.info("Chưa có danh sách kết quả để hiển thị trên bản đồ. Chức năng tìm và so sánh vẫn hoạt động bình thường không phụ thuộc bản đồ.")
        return

    if response.is_mock:
        st.info("Bản đồ chế độ mẫu — vị trí chỉ mang tính giả lập, không thể hiện phòng thực đang còn trống.")

    usable_rows: list[dict[str, object]] = []
    missing_geo_items: list[dict[str, object]] = []

    for item in response.items:
        listing = item["listing"]
        if has_usable_coordinates(listing):
            usable_rows.append(
                {
                    "listing_id": listing["listing_id"],
                    "title": listing["title"],
                    "price": format_price_with_basis(listing.get("rent_vnd_month"), listing.get("price_basis", "")),
                    "geo_confidence": GEO_CONFIDENCE_LABELS.get(listing.get("geo_confidence", "unknown"), "Chưa rõ"),
                    "lat": float(listing["latitude"]),
                    "lon": float(listing["longitude"]),
                }
            )
        else:
            missing_geo_items.append(listing)

    if usable_rows:
        map_df = pd.DataFrame(usable_rows)
        try:
            st.map(map_df[["lat", "lon"]])
        except Exception:  # noqa: BLE001 - fallback when offline or map tiles fail
            st.warning("Không thể tải nền bản đồ trực tuyến lúc này. Bảng tọa độ tham khảo vẫn hiển thị bên dưới.")

        st.markdown("**Danh sách điểm có dữ liệu tọa độ:**")
        st.dataframe(
            map_df[["listing_id", "title", "price", "geo_confidence"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Không có tin nào trong kết quả hiện tại có đủ dữ liệu tọa độ hợp lệ để hiển thị trên bản đồ.")

    if missing_geo_items:
        st.warning(
            f"Có {len(missing_geo_items)} tin bị thiếu tọa độ (vẫn giữ nguyên trong danh sách & so sánh, không vẽ vị trí giả): "
            + ", ".join(item["listing_id"] for item in missing_geo_items)
        )
