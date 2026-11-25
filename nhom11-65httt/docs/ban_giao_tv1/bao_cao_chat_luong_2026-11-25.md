# Báo cáo chất lượng dữ liệu TV1 — 25/11/2026

**Phạm vi đo:** Tập tin nguồn (`phongtro123_rooms.csv`, `mixstay_rooms.csv`, `muaban_rooms.csv`) và đầu ra ETL (`listings.csv`, `listings_all.csv`, `records_to_review.csv`, `manifest.json` phiên bản `v20261125_2139`, đồng thời đóng gói tại `data/releases/v20261125_2139/`), đối soát trực tiếp bằng `pipeline.py --validate`.

## 1. Dòng chảy dữ liệu thực tế (`run_20261125T143944Z`)

| Bước / Nguồn | Tổng bản ghi | Đống Đa | Thanh Xuân | Cầu Giấy | Ghi chú |
|---|---:|---:|---:|---:|---|
| `phongtro123_rooms.csv` (10 trang/quận) | 558 | — | — | — | Đã lọc bỏ 36 tin sai loại hình/thiếu giá ngay lúc cào |
| `muaban_rooms.csv` (5 trang/quận) | 75 | — | — | — | Đã loại 110 tin (94 hết hạn/quá hạn, 13 sai loại hình, 2 sai quận, 1 thiếu giá) |
| `mixstay_rooms.csv` (trang đầu, tối đa 24 thẻ/quận) | 56 | — | — | — | Đã loại 16 thẻ không phù hợp |
| `thuephongtro_rooms_historical.csv` | 9 | 3 | 3 | 3 | Dữ liệu lịch sử (`expired`), tách riêng khỏi tập hiện hành |
| Nhà Tốt (`nhatot.com`) | 0 | 0 | 0 | 0 | Không cào do HTTP 403 và chưa có chấp thuận văn bản |
| **Tổng đầu vào ETL (`raw_input`)** | **689** | — | — | — | Tổng từ 3 nguồn hiện hành (`558 + 75 + 56`) |
| Bị loại ở bước ETL (`rejected`) | 5 | — | — | — | Lọc lại theo quy tắc chuẩn hóa & phạm vi |
| Cần rà soát (`needs_review`) | 0 | — | — | — | Ghi ra `records_to_review.csv` |
| Gộp trùng chắc chắn (`confirmed` phụ) | 12 | — | — | — | Giữ ở `listings_all.csv` (`is_representative=false`), loại khỏi `listings.csv` |
| **Tập công bố (`listings.csv`)** | **672** | **229** | **210** | **233** | Đạt mục tiêu ≥ 250 tin hợp lệ tuần 4 (`phongtro123`: 542, `muaban`: 74, `mixstay`: 56) |

## 2. Phân bố và độ phủ thuộc tính trên `listings.csv` (n = 672)

| Chỉ tiêu | Kết quả thực đo | Tỷ lệ / ghi chú |
|---|---|---|
| Cơ sở giá (`price_basis`) | `room`: **650**, `person`: **22**, `unknown`: **0** | Đã tách rõ giá theo phòng và giá theo người/ở ghép |
| Loại phòng (`room_type`) | `room`: **291**, `self_contained`: **188**, `studio_mini`: **104**, `loft_room`: **69**, `shared_place`: **20** | Chuẩn 100% theo `data/reference/room_types.csv` |
| Diện tích (`area_m2`) | Thiếu: **0 / 672** | Đầy đủ 100% |
| Thời điểm đăng (`posted_at`) | Thiếu: **56 / 672** | Toàn bộ 56 tin thiếu là từ MixStay (JSON-LD công khai không có ngày đăng) |
| Phường (`ward`) | Trích được: **592 / 672** (thiếu 80) | Trích từ địa chỉ/breadcrumb |
| Tiện ích (`amenities_json`) | Có ≥ 1 tiện ích `true`/`false`: **640 / 672** | Chuẩn 8 mã trong `amenity_catalog.csv`, bảo toàn phủ định |
| Chi phí (`fees_json`) | Có ≥ 1 loại phí `known`/`free`/`included`: **332 / 672** | Chuẩn 5 mã trong `fee_catalog.csv`; không mặc định thiếu = 0 |
| Tiền cọc (`deposit_vnd` / `deposit_months`) | Có thông tin cọc: **35 / 672** | Chỉ trích khi văn bản nêu rõ |
| Trạng thái trùng (`duplicate_status`) | `unique`: **594**, `suspected`: **66**, `confirmed` (đại diện): **12** | Tin `suspected` được giữ riêng và gắn cờ `POSSIBLE_DUPLICATE`; không gộp tin thiếu số nhà hoặc khác số phòng |
| Che PII (`title`, `description_clean`, `address_clean`) | SĐT còn sót: **0 / 672**, Email còn sót: **0 / 672** | Đã che cả SĐT 9–11 chữ số (`PHONE_PATTERN`) |
| Độ chính xác vị trí (`geo_confidence`) | `area_only`: **672 / 672** | Tọa độ để trống, không tạo tọa độ giả |

## 3. Kết quả đánh giá trích xuất & khử trùng (`evaluate.py`)

### 3.1. Trên mẫu đối chứng thực tế (`fixtures/real_eval_sample.json`, `origin=real`)

Mẫu gồm **18 tin thật** (6 Phongtro123, 6 Mua Bán, 6 MixStay; chia 6 `development` / 12 `holdout`) và **10 cặp đối chứng** (5 cặp trùng thật + 5 cặp khó không trùng, trong đó 8 cặp ở tập `holdout`).

| Trường / Bài toán | Tập `holdout` (n = 12, cặp = 8) | Toàn mẫu (n = 18, cặp = 10) | Phân tích lỗi thực tế |
|---|---|---|---|
| `rent_vnd_month` | P=1.000, R=1.000, **F1=1.000** | P=1.000, R=1.000, **F1=1.000** | Khớp 100% số VND/tháng. |
| `price_basis` | P=1.000, R=1.000, **F1=1.000** | P=1.000, R=1.000, **F1=1.000** | Phân biệt đúng `room` vs `person`. |
| `area_m2` | P=1.000, R=1.000, **F1=1.000** | P=1.000, R=1.000, **F1=1.000** | Khớp 100% diện tích nêu rõ. |
| `room_type` | P=0.9167, R=0.9167, **F1=0.9167** | P=0.8889, R=0.8889, **F1=0.8889** | Lỗi ở ca từ khóa loại phòng nằm trong danh sách tiện ích (`Có gác`) hoặc mô tả thay vì tiêu đề. |
| `ward` | P=1.000, R=0.8750, **F1=0.9333** | P=1.000, R=0.9167, **F1=0.9565** | Lỗi ở `phongtro123:701085` do địa chỉ dropdown nguồn ghi nhầm `Xã Trung Giã` thay vì `Trung Hòa`. |
| `duplicate_pairs` | **Precision=1.000**, Recall=0.800 | **Precision=1.000**, Recall=0.8333 | Không gộp nhầm cặp khác ngõ/khác số phòng (`FP=0`); 1 cặp chéo nguồn (`phongtro123`–`muaban`) bị xếp `suspected` thay vì `confirmed` do khác tên phường (`Nghĩa Đô` vs `Quan Hoa`). |

> **Giới hạn mẫu đánh giá:** Kích thước mẫu đối chứng thực hiện ở mức khởi đầu (`18` tin trích xuất, `10` cặp trùng), chưa bao phủ toàn bộ biến thể toàn thị trường; chưa chấm riêng từng loại phí `fees_json` trên tập lớn.

### 3.2. Trên mẫu giả lập kiểm thử logic (`fixtures/synthetic_eval.json`, tách biệt hoàn toàn)

- `F1 = 1.0` ở cả 5 trường đo và `duplicate_pairs precision = 1.0` (`n=3`, `n_pairs=2`).

## 4. Kiểm chứng kỹ thuật tổng thể

- **Đối soát danh mục & checksum**: `python nhom11-65httt/src/backend/bot/pipeline.py --validate` đạt 100% (cả `data/` và `data/releases/v20261125_2139/`).
- **Kiểm thử tự động**: **19/19** unit & integration test đạt (`unittest discover`).
- **Giới hạn**: Một tin đăng trong `listings.csv` phản ánh giá chào thuê tại thời điểm thu thập, chưa xác minh phòng thực tế còn trống; dữ liệu chưa có quyền phát hành công khai ngoài nhóm khi chưa nhận phản hồi văn bản từ các nền tảng.
