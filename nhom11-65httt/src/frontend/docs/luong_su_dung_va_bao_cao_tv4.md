# Tài Liệu Thiết Kế Luồng Sử Dụng, Kiểm Thử & Demo (TV4)

**Phân hệ:** Giao diện và trải nghiệm (Streamlit)  
**Thành viên phụ trách:** Trịnh Khắc Hưng (2351160526 — TV4)  
**Nhánh phát triển:** `feature/hungw-frontend-streamlit`

---

## 1. Sơ Đồ Luồng Sử Dụng Trọn Vẹn (TV4-02)

```text
[Giới thiệu & Chế độ Mẫu/Thực]
        │
        ▼
[Nhập nhu cầu] ──(Đặt lại)──► [Xóa điều kiện & kết quả cũ]
        │
  (Tìm phòng gợi ý)
        │
        ├──(Lỗi nhập)──────────────► [Thông báo lỗi gần trường nhập]
        ├──(Chế độ mẫu chưa có)────► [Báo rõ chưa mô phỏng, không tự tính điểm]
        ├──(no_match)──────────────► [Gợi ý nới điều kiện, chỉ chạy lại khi xác nhận]
        │
        ▼ (ok)
[Danh sách kết quả] ──(Đổi tiêu chí chưa tìm lại)──► [Đánh dấu kết quả cũ (stale)]
        │
        ├──► [Chi tiết phòng] (Nối theo listing_id, tách tiền thuê/phí/cọc, tiện ích 3 trạng thái)
        ├──► [So sánh 2–4 phòng] (Cảnh báo khác cơ sở giá, thấy phần thiếu dữ liệu)
        └──► [Bản đồ vị trí] (Phân biệt exact / centroid / missing; không vẽ tại 0,0)
```

---

## 2. Bảng Kiểm Tra Trạng Thái Giao Diện

| Trạng thái | Hành vi đã cài đặt |
| :--- | :--- |
| `invalid_request` | Báo lỗi rõ ràng, giữ nguyên giá trị người dùng đã nhập |
| `ok` | Giữ đúng thứ hạng từ TV3/mẫu, hiển thị lý do, cảnh báo và điểm thành phần |
| `no_match` | Báo không có phòng phù hợp, gợi ý nới điều kiện, không tự động đổi tiêu chí |
| `unsimulated_mock` | Báo rõ yêu cầu chưa có hồ sơ giả lập, không tự viết thuật toán thay TV3 |
| `module_error` | Báo lỗi mô-đun/schema ở chế độ thực, không âm thầm chuyển sang điểm giả lập |
| `results_stale` | Đánh dấu cảnh báo khi người dùng sửa form mà chưa nhấn Tìm lại |

---

## 3. Kịch Bản Demo & Kiểm Thử Trước Bàn Giao (TV4-10)

1. Chạy kiểm tra tự động:
   ```bash
   cd nhom11-65httt/src/frontend
   python scripts/run_checks.py
   ```
2. Khởi chạy ứng dụng chế độ mẫu:
   ```bash
   streamlit run app.py
   ```
3. Thực hiện luồng trình bày:
   - Chọn hồ sơ **Sinh viên ĐH Thủy lợi - Ngân sách <= 4.000.000 đ/tháng** $\rightarrow$ nhấn **Tìm phòng gợi ý**.
   - Mở chi tiết **MOCK-006** để minh họa trường hợp **thiếu tiền cọc, thiếu diện tích, thiếu phí và cờ nghi ngờ trùng lặp**.
   - Thêm **MOCK-001** và **MOCK-006** vào tab **So sánh** để xem bảng đối chiếu đánh đổi.
   - Chuyển sang hồ sơ **Khu vực Cầu Giấy / Đống Đa** $\rightarrow$ mở tab **Bản đồ vị trí** để xem phân biệt tọa độ chính xác (**MOCK-007**) và tin thiếu tọa độ (**MOCK-003** không vẽ điểm giả).
   - Chọn hồ sơ **Kịch bản không có kết quả** để minh họa trạng thái `no_match`.
