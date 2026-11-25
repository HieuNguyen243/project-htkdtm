# Hướng dẫn chạy và kiểm tra phần TV1

**Môi trường đã kiểm chứng:** Windows, Python 3.12, Playwright Chromium `156.0.8078.4` (ngày 25/11/2026). Chạy toàn bộ lệnh từ thư mục gốc `project-htkdtm`.

## 1. Cài đặt phụ thuộc & chạy kiểm thử

```powershell
python -m pip install -r nhom11-65httt/src/backend/bot/requirements.txt
python -m unittest discover -s nhom11-65httt/src/backend/bot -p "test_*.py" -v
```

Kết quả kiểm chứng ngày 25/11/2026: **19/19 kiểm thử đạt** (`test_infrastructure.py`, `test_mixstay.py`, `test_muaban.py`, `test_thuephongtro.py`).

## 2. Chạy pipeline ETL đầu–cuối & đối soát phát hành

```powershell
# Chạy ETL trên dữ liệu CSV đã thu thập và đóng gói snapshot releases/<version>/ (không gọi mạng)
python nhom11-65httt/src/backend/bot/pipeline.py --skip-scrape --snapshot

# Kiểm tra tính toàn vẹn schema, danh mục tham chiếu và SHA-256 checksum trong manifest.json
python nhom11-65httt/src/backend/bot/pipeline.py --validate
python nhom11-65httt/src/backend/bot/pipeline.py --validate --data-dir nhom11-65httt/data/releases/v20261125_2139

# Chạy đánh giá trích xuất & khử trùng trên tập đối chứng thực (holdout) và tập giả lập
python nhom11-65httt/src/backend/bot/evaluate.py --fixture nhom11-65httt/src/backend/bot/fixtures/real_eval_sample.json --split holdout
python nhom11-65httt/src/backend/bot/evaluate.py
```

Đầu ra của `pipeline.py` nằm tại `nhom11-65httt/data/`:
- `listings.csv`: Tập công bố (`record_status=accepted` và `is_representative=true`).
- `listings_all.csv`: Toàn bộ bản ghi đã xử lý (bao gồm cả bản phụ `confirmed` và bản ghi `rejected`/`needs_review`).
- `records_to_review.csv`: Các bản ghi `needs_review` cần kiểm tra thủ công.
- `manifest.json`: Phiên bản schema, `dataset_version`, `input_run_ids`, thống kê số lượng và SHA-256 checksum.

## 3. Chạy lẻ từng bot thu thập (khi cần)

| Nguồn | Lệnh mẫu | Kết quả |
|---|---|---|
| Phongtro123 | `python nhom11-65httt/src/backend/bot/phongtro123.py --pages 10 --delay 1.2 --skip-existing` | `data/phongtro123_rooms.csv` (thêm `--fresh` nếu muốn cào mới hoàn toàn) |
| Mua Bán | `python nhom11-65httt/src/backend/bot/muaban.py --pages 5 --delay 1.2 --skip-existing` | `data/muaban_rooms.csv`, `muaban_rooms_rejected.csv` |
| MixStay | `python nhom11-65httt/src/backend/bot/mixstay.py --limit-per-district 24 --delay 1.2` | `data/mixstay_rooms.csv`, `mixstay_rooms_rejected.csv` |
| Thuephongtro (lịch sử) | `python nhom11-65httt/src/backend/bot/thuephongtro.py --pages 1 --limit-per-district 3 --delay 2 --include-expired --output nhom11-65httt/data/thuephongtro_rooms_historical.csv` | Tệp tin quá hạn riêng (`expired`) |
| Nhà Tốt | **Không chạy** | HTTP 403 và thiếu chấp thuận văn bản |

## 4. Lập lịch chạy định kỳ

```powershell
# Chạy một chu kỳ ngay lập tức để kiểm tra
python nhom11-65httt/src/backend/bot/scheduler.py --once --skip-scrape

# Chạy nền định kỳ 06:00 và 18:00 giờ Việt Nam
python nhom11-65httt/src/backend/bot/scheduler.py --times 06:00,18:00
```
