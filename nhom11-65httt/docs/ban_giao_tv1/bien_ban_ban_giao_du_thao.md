# Biên bản bàn giao TV1 cho TV2–4 — bản dự thảo đối soát

**Ngày lập:** 25/11/2026  
**Người chuẩn bị:** TV1, Nguyễn Ngọc Hiếu  
**Phiên bản dữ liệu:** `dataset_version = v20261125_2139` (`schema_version = 1.0.0-draft.1`, `run_id = run_20261125T143944Z`)  
**Trạng thái:** đã hoàn thiện gói tệp chuẩn, `manifest.json`, bản snapshot tại `data/releases/v20261125_2139/` và đối soát tự động; **chờ TV2–4 xác nhận đọc/nhập thử và chờ phản hồi quyền chia sẻ nội dung từ các nền tảng nguồn**.

## 1. Danh sách tệp bàn giao trong gói

| Thành phần | Đường dẫn | Số dòng / Phiên bản | SHA-256 (từ `manifest.json`) |
|---|---|---|---|
| Tập công bố chuẩn (BI/AI/UI) | `nhom11-65httt/data/listings.csv` (và bản snapshot `releases/v20261125_2139/listings.csv`) | **672** dòng (`accepted`, đại diện) | `47a81607ebc6c2e4b649bf942b277a101b3a0228827703651fc5ba36bb0fafee` |
| Tập truy vết đầy đủ (nội bộ) | `nhom11-65httt/data/listings_all.csv` | **689** dòng | `629c10ebae388488d3a321c5d0b10f57d222d9302c5e5922e31fea8a9a4d451b` |
| Danh sách chờ rà soát | `nhom11-65httt/data/records_to_review.csv` | **0** dòng | `4c1a9bf20aa1bd0a8f3ce27001ea10bc216098402e67e612d04d2599820001dd` |
| Manifest phát hành | `nhom11-65httt/data/manifest.json` | `v20261125_2139` | — |
| 6 danh mục tham chiếu | `nhom11-65httt/data/reference/*.csv` | `0.1-draft` | Đã đối soát 100% qua `pipeline.py --validate` |
| Tập đánh giá thực tế | `nhom11-65httt/src/backend/bot/fixtures/real_eval_sample.json` | 18 mẫu + 10 cặp | Holdout F1 ≥ 0.91, Dup Precision = 1.0 |
| Bộ tài liệu & báo cáo TV1 | `nhom11-65httt/docs/ban_giao_tv1/*.md` | `25/11/2026` | — |

## 2. Việc cần người nhận thử và phản hồi

| Người nhận | Nội dung kiểm tra | Tiêu chí xác nhận |
|---|---|---|
| TV2 — CSDL/BI | Nạp `listings.csv` UTF-8 BOM, parse JSON (`fees_json`, `amenities_json`, `quality_flags_json`), kiểm tra khóa `listing_id`, tách `price_basis=room/person`. | Xác nhận nạp được vào PostgreSQL/Superset, đối chiếu đúng `672` dòng (`Đống Đa: 229`, `Thanh Xuân: 210`, `Cầu Giấy: 233`). |
| TV3 — Gợi ý/đánh giá | Đọc `rent_vnd_month`, `price_basis`, `room_type`, `amenities_json`, `geo_confidence=area_only`. | Xác nhận chạy được bộ lọc & chấm điểm; không tính khoảng cách điểm–điểm giả khi thiếu tọa độ. |
| TV4 — Giao diện | Nối theo `listing_id`, hiển thị giá kèm `price_basis`, `quality_flags_json` và `listing_status=unverified_available`. | Xác nhận hiển thị đúng nhãn thiếu/nghi trùng, không suy diễn thành “còn phòng”. |

**Mẫu phản hồi:** `TV số — v20261125_2139 — tên tệp/cột hoặc listing_id — vấn đề quan sát — dữ liệu mong đợi — mức ảnh hưởng`.

## 3. Bảng theo dõi nghiệm thu

| Mục xác nhận | Trạng thái hiện tại |
|---|---|
| `schema_version` / `dataset_version` | `1.0.0-draft.1` / `v20261125_2139` |
| Kiểm thử đơn vị & tích hợp (`unittest`) | Đạt (**19/19** test cases) |
| Đối soát danh mục & checksum (`pipeline.py --validate`) | Đạt (**0 lỗi**) |
| TV2 nhận và thử nạp CSDL/Superset | Chưa xác nhận |
| TV3 nhận và thử đọc cho gợi ý | Chưa xác nhận |
| TV4 nhận và thử hiển thị trên UI | Chưa xác nhận |
