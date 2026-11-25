# Bộ tài liệu bàn giao TV1 — bản v1.0-draft.1

**Ngày cập nhật:** 25/11/2026  
**Phụ trách:** Nguyễn Ngọc Hiếu, Thành viên 1  
**Căn cứ:** `../Nhiem_vu_Thanh_vien_1_Ban_cap_nhat.pdf` (bản 2.0, 14 trang).  
**Trạng thái:** đã hoàn thiện pipeline đầu–cuối, sinh `listings.csv`, `listings_all.csv`, `records_to_review.csv`, `manifest.json` (`dataset_version=v20261125_2139`), bản đóng gói `data/releases/v20261125_2139/` và đối soát tự động với danh mục tham chiếu; **quyền chia sẻ nội dung ngoài phạm vi nội bộ vẫn chờ văn bản chấp thuận từ các nền tảng**.

## Phạm vi đã chốt

Tin **cho thuê phòng trọ/chỗ ở ghép** tại Thanh Xuân, Đống Đa, Cầu Giấy, Hà Nội. Loại tin bán, căn hộ độc lập/1N1K/2N1K, nhà nguyên căn, văn phòng, mặt bằng và tin tìm thuê. Một dòng dữ liệu là **tin đăng được quan sát**, không khẳng định phòng thực tế còn trống.

## Tệp bàn giao trong gói TV1

| Tệp | Mục đích | Trạng thái |
|---|---|---|
| [`../so_nguon_phong_tro_tuan_1.md`](../so_nguon_phong_tro_tuan_1.md) | Sổ nguồn, căn cứ sử dụng, giới hạn kỹ thuật và quyết định nguồn | Đã khảo sát; quyền chia sẻ đang chờ xác nhận |
| [`dac_ta_du_lieu_v0_1.md`](dac_ta_du_lieu_v0_1.md) | Hợp đồng cột CSV, kiểu, đơn vị, giá trị thiếu, JSON và ví dụ | Đã ánh xạ vào `config.py` và `pipeline.py` |
| [`quy_tac_xu_ly_v0_1.md`](quy_tac_xu_ly_v0_1.md) | Mã tin, bản gốc, chuẩn hóa, trùng, vị trí, phát hành | Đã triển khai trong `extractor.py`, `deduplicator.py`, `pipeline.py` |
| [`huong_dan_gan_nhan_danh_gia_v0_1.md`](huong_dan_gan_nhan_danh_gia_v0_1.md) | Nhãn đối chứng, cách chia mẫu và tính P/R/F1 | Đã có `evaluate.py`, fixture giả lập và mẫu đối chứng thực `real_eval_sample.json` |
| [`danh_muc_tham_chieu_v0_1.md`](danh_muc_tham_chieu_v0_1.md) | Ý nghĩa sáu danh mục, nguồn địa chỉ cơ sở trường và giới hạn tọa độ | Đã kiểm chứng tự động qua `pipeline.py --validate` |
| [`huong_dan_chay_va_kiem_tra.md`](huong_dan_chay_va_kiem_tra.md) | Lệnh cài, chạy bot, ETL pipeline, validate, evaluate và unit test | Đã chạy thực tế trên Python 3.12 |
| [`bao_cao_chat_luong_2026-11-25.md`](bao_cao_chat_luong_2026-11-25.md) | Số liệu thực đo sau ETL (`672` tin sạch từ `689` tin nguồn) | Đã cập nhật theo `manifest.json` `v20261125_2139` |
| [`bien_ban_ban_giao_du_thao.md`](bien_ban_ban_giao_du_thao.md) | Tệp nhận, checksum SHA-256, việc TV2–4 cần thử và điều kiện nghiệm thu | Sẵn sàng gửi TV2–4 kiểm tra đầu vào |
| [`../../data/reference/`](../../data/reference/) | Sáu danh mục CSV và workbook tham chiếu | Đã đối soát 100% mã với `listings.csv` |

## Đối chiếu bản phân công 2.0

| Mục PDF | Minh chứng đã triển khai | Lưu ý / việc còn chờ xác nhận ngoài nhóm |
|---|---|---|
| TV1-01 nguồn | Sổ nguồn + dữ liệu thực từ Phongtro123, MixStay, Mua Bán; không cào Nhà Tốt (403) | Chờ văn bản chấp thuận chia sẻ rộng rãi từ nền tảng |
| TV1-02 thu nhận/bản gốc | `listing_id` ổn định (`source:key`), `raw_ref`, `run_id`, `content_hash`, giữ nguyên `collected_at` | Đã kiểm chứng tự động |
| TV1-03 đặc tả | 36 cột chuẩn trong `config.py`, tách `fees_json`, `amenities_json` 3 trạng thái, `quality_flags_json` | Cần TV2–4 xác nhận schema `1.0.0-draft.1` |
| TV1-04 trích xuất | `extractor.py` chuẩn hóa `room_type`, `price_basis`, `ward`, `deposit`, phí, tiện ích | Đã kiểm thử phủ định và đơn vị phí |
| TV1-05 khử trùng | `deduplicator.py` tách `confirmed` (chỉ giữ đại diện) và `suspected` (giữ riêng + cờ) | Không gộp nhầm khác số nhà/ngõ |
| TV1-06 tham chiếu | 6 CSV trong `data/reference/` khớp 1:1 với `listings.csv` | `campuses.csv` giữ `geo_confidence=unknown` |
| TV1-07 đánh giá | `evaluate.py` + `fixtures/real_eval_sample.json` (holdout F1 0.9167–1.0, Dup Precision 1.0) & `synthetic_eval.json` | Có thể mở rộng cỡ mẫu đối chứng khi cần |
| TV1-08 kiểm thử | 19 unit/integration tests trong `test_*.py` đều đạt | Đã kiểm tra nhập lặp, đổi giá, che SĐT 9–11 số, Playwright, manifest |
| TV1-09 phát hành | `listings.csv`, `listings_all.csv`, `records_to_review.csv`, `manifest.json`, `data/releases/v20261125_2139/` | TV2–4 thử đọc cùng `dataset_version` |
| TV1-10 gói chạy | `src/backend/bot/README.md` + `huong_dan_chay_va_kiem_tra.md` | Nhờ 1 thành viên khác chạy lại theo hướng dẫn |
