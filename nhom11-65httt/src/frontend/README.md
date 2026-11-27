# Phân Hệ Giao Diện & Trải Nghiệm (TV4 — Streamlit)

**Đề tài:** Hệ thống phân tích thị trường phòng trọ hỗ trợ sinh viên lựa chọn nơi ở  
**Thành viên phụ trách:** Trịnh Khắc Hưng (2351160526 — TV4)  
**Nhánh làm việc:** `feature/hungw-frontend-streamlit`

---

## 1. Cấu Trúc Thư Mục `src/frontend/`

```text
src/frontend/
├── app.py                   # Điểm chạy chính của ứng dụng Streamlit
├── config.py                # Cấu hình chế độ mẫu/thực, danh mục trường, loại phòng, tiện ích
├── state.py                 # Quản lý session_state (tiêu chí, kết quả cũ, so sánh 2–4 phòng)
├── requirements.txt         # Thư viện phụ thuộc (streamlit, pandas, pytest)
├── fixtures/
│   ├── sample_listings.csv  # Bộ tin mẫu chuẩn schema 36 cột (đủ tọa độ, thiếu phí, thiếu tọa độ, giá/người)
│   └── sample_results.json  # Kết quả giả lập từ TV3 gắn theo từng hồ sơ mẫu
├── providers/
│   ├── base.py              # Hợp đồng DataProvider, kiểm tra schema & nối theo listing_id
│   ├── mock_provider.py     # Chế độ mẫu (có nhãn giả lập, không tự viết thuật toán thay TV3)
│   └── real_provider.py     # Lớp kết nối dữ liệu TV1 và mô-đun TV3 thật
├── ui/
│   ├── components.py        # Hàm định dạng an toàn: giá/phí/cọc, tiện ích 3 trạng thái, URL HTTP/HTTPS, tọa độ
│   ├── search_form.py       # Biểu mẫu nhập nhu cầu (bắt buộc/mong muốn, ưu tiên, cảnh báo đổi điều kiện)
│   ├── results_view.py      # Danh sách kết quả & trang chi tiết phòng
│   ├── compare_view.py      # So sánh 2–4 phòng & cảnh báo khác cơ sở giá
│   ├── map_view.py          # Bản đồ vị trí có căn cứ (không vẽ điểm giả tại 0,0)
│   └── bi_view.py           # Tích hợp 3 Dashboard Apache Superset BI (TV2) & nhúng Iframe
└── tests/
    ├── test_providers.py    # Kiểm thử provider mẫu/thực & nối dữ liệu theo listing_id
    ├── test_state.py        # Kiểm thử session_state & giới hạn 2–4 phòng
    └── test_ui_helpers.py   # Kiểm thử định dạng an toàn (phí thiếu, 3 trạng thái, URL, tọa độ, Superset config)
```

---

## 2. Hướng Dẫn Cài Đặt & Khởi Chạy Độc Lập

Yêu cầu **Python >= 3.10**. Tại thư mục `nhom11-65httt/src/frontend`:

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Chuyển đổi Chế độ Mẫu / Chế độ Thực
- **Chế độ mẫu (mặc định):** Dùng `fixtures/sample_listings.csv` và `fixtures/sample_results.json`. Không cần CSDL PostgreSQL hay mô-đun TV3 để khởi động.
- **Chế độ thực:** Chọn **Chế độ thực** ở thanh bên (Sidebar) để đọc `nhom11-65httt/data/listings.csv` từ TV1 và kết nối hàm gợi ý TV3 khi sẵn sàng. Nếu mô-đun TV3 chưa sẵn sàng, ứng dụng hiển thị trạng thái lỗi rõ ràng mà không âm thầm dùng điểm giả lập.
- Lưu ý: Nền bản đồ `st.map` cần kết nối Internet; nếu mất mạng, danh sách kết quả, chi tiết và so sánh vẫn hoạt động bình thường.

---

## 3. Tích Hợp Apache Superset BI (TV2)

Giao diện cung cấp tab **"📊 Dashboard BI (Superset)"** kết nối tới cụm Docker Superset của TV2 tại `http://localhost:8089`:
- **Dashboard 1 (phongtro-market):** Phân tích thị trường giá thuê (P25/P50/P75, giá/m² theo quận).
- **Dashboard 2 (phongtro-affordability):** Phân tích khả năng chi trả sinh viên (ngưỡng 2M-3M-4M-5M).
- **Dashboard 3 (phongtro-quality):** Phân tích chất lượng dữ liệu (tỷ lệ thiếu giá, thiếu phí, cờ nghi trùng).
- **Chế độ nhúng:** Hỗ trợ nhúng trực tiếp qua Iframe (`?standalone=true`) hoặc mở tab mới độc lập.
- **Dự phòng ngoại tuyến:** Nếu Superset chưa khởi động, giao diện tự động hiển thị biểu đồ thống kê nội bộ từ dữ liệu phòng trọ hiện tại.

---

## 4. Chạy Bộ Kiểm Thử Đơn Vị

Không cần cài đặt Streamlit hay CSDL để chạy kiểm thử logic giao diện, state, provider và cấu hình Superset:

```bash
cd nhom11-65httt/src/frontend
python scripts/run_checks.py
```
