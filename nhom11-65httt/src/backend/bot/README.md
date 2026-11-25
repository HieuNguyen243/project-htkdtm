# Bot thu thập phòng trọ

Ba bot đọc tin cho thuê phòng tại **Thanh Xuân, Đống Đa, Cầu Giấy**. Tin bán nhà, đất, nhà nguyên căn, căn hộ 1N1K/2N1K, mặt bằng và văn phòng không thuộc tập tin phòng trọ. Không dùng bộ lọc gần một trường đại học. Bộ tài liệu bàn giao, đặc tả và báo cáo hiện trạng ở [`docs/ban_giao_tv1/`](../../../docs/ban_giao_tv1/).

## MixStay

Bot `mixstay.py` chỉ tải HTML công khai của ba trang `/thue-phong-tro/<quận>` và dữ liệu Product JSON-LD nhúng trong HTML trang `/tin/<mã>`. Bot không mở giao diện JavaScript `/phong` vì giao diện này tự gọi `/api/rooms/public`, trong khi `robots.txt` của MixStay chặn `/api/`. Mỗi lần chạy tạo CSV mới tại `nhom11-65httt/data/mixstay_rooms.csv` và tệp `_rejected.csv` ghi URL cùng lý do loại. Bot kiểm tra `robots.txt` lúc chạy và dừng nếu không truy cập được.

Từ thư mục gốc của kho lưu trữ:

```powershell
python -m pip install -r nhom11-65httt/src/backend/bot/requirements.txt
python nhom11-65httt/src/backend/bot/mixstay.py --limit-per-district 24 --delay 2
```

Mỗi trang quận chỉ đưa tối đa 24 tin vào HTML ban đầu. `--limit-per-district` giới hạn số thẻ phòng phù hợp được mở chi tiết từ trang HTML đó; giá trị `0` lấy mọi thẻ phù hợp **trên trang đầu**, không phải toàn bộ tin của website. `--output` đổi đường dẫn CSV. Bot chỉ xuất tin có loại phòng được nhận, địa chỉ tóm tắt và khu vực khớp quận, ít nhất một phòng trống và giá thuê VND/tháng. `address` là nhãn vị trí ngắn trên thẻ; `description_clean` lấy từ JSON-LD nên có thể bị rút gọn. `public_code`, `deposit_vnd`, `amenities` và `posted_at` để trống vì HTML công khai khảo sát không cung cấp đủ các trường này. `price_basis` là `unknown` khi chưa xác minh giá theo phòng hay người. Số điện thoại và email trong văn bản được che trước khi lưu. Tệp CSV được ghi UTF-8 có BOM.

Môi trường thực thi cần truy cập `mixstay.vn`. Không dùng kết quả cũ như tình trạng phòng hiện tại. Trước khi chia sẻ hoặc công bố nội dung, xác nhận phạm vi sử dụng dữ liệu với MixStay.

## Phongtro123

Bot đọc danh sách phòng trọ của Thanh Xuân, Đống Đa và Cầu Giấy rồi ghi CSV tại `nhom11-65httt/data/phongtro123_rooms.csv`. Mỗi dòng tương ứng một mã tin Phongtro123. Chạy lại bot cập nhật tin cùng mã trong tệp và giữ các tin đã thu từ những lần trước.

## Chạy

Từ thư mục gốc của kho lưu trữ, cài gói trong `nhom11-65httt/src/backend/bot/requirements.txt`, rồi chạy:

```powershell
python nhom11-65httt/src/backend/bot/phongtro123.py --pages 3 --delay 2
```

`--pages` giới hạn số trang danh sách cho **mỗi quận**. Mặc định là 3. `--delay` là số giây tối thiểu giữa hai yêu cầu HTTP, mặc định là 2 và không được dưới 1. `--output` đổi đường dẫn CSV. Bot đọc `robots.txt` trước khi chạy và dừng nếu URL không được cho phép. Trang bị lỗi được ghi ra stderr. Khi lỗi tải hoặc đọc chi tiết, mã thoát là 1 và các trang đã xử lý vẫn được lưu.

CSV dùng UTF-8 có BOM để mở trong Excel. Tin không có giá theo tháng bị loại. `price_basis` hiện là `unknown` vì nhãn giá trên trang chưa luôn cho biết rõ giá/phòng hay giá/người. `posted_at` và `collected_at` dùng ISO 8601 UTC. Mô tả loại số điện thoại và email trước khi lưu.

Đợt chạy đầu tiên ngày 25/11/2026 lấy ba trang mỗi quận. Đây là một phần tin mà trang khu vực hiển thị, phụ thuộc thứ tự sắp xếp tại thời điểm chạy. Giới hạn trang có thể tăng khi cần thêm tin. Trước khi công bố hoặc chia sẻ dữ liệu ngoài nhóm, xác nhận phạm vi sử dụng nội dung với Phongtro123 theo [quy chế của trang](https://phongtro123.com/quy-che-hoat-dong).

## Thuephongtro.com

Bot `thuephongtro.py` chỉ đi từ bộ lọc **Cho thuê phòng trọ** của Thanh Xuân, Đống Đa và Cầu Giấy trên `thuephongtro.com` (tên miền người dùng cung cấp sau khi sửa `chothuephongtro.com`). Mỗi tin chi tiết phải có đường dẫn danh mục cho thuê phòng trọ, quận khớp địa chỉ, tiêu đề phòng, giá triệu đồng/tháng, diện tích và ngày hết hạn chưa qua. Bot loại nhà nguyên căn, căn hộ, văn phòng, mặt bằng, tin bán, tin tìm thuê, giá sai đơn vị và tin hết hạn. `robots.txt` được đọc trước mỗi lượt chạy; tối thiểu 1 giây giữa hai yêu cầu. Bot không tải ảnh hoặc lưu mô tả, số điện thoại và email được che nếu xuất hiện trong tiêu đề hoặc địa chỉ.

```powershell
python nhom11-65httt/src/backend/bot/thuephongtro.py --pages 1 --limit-per-district 3 --delay 2
```

CSV tại `nhom11-65httt/data/thuephongtro_rooms.csv`; URL và lý do loại tại tệp `_rejected.csv`. `--pages` là số trang danh sách **mỗi quận**; `--limit-per-district` là số yêu cầu trang chi tiết tối đa mỗi quận, `0` nghĩa là tất cả ứng viên trên các trang đã chọn. Chạy thử ngày 25/11/2026 với ba chi tiết mỗi quận cho kết quả **0 tin còn hạn**, 34 tin bị loại (21 sai loại hình/thiếu dấu hiệu phòng thuê, 9 đã hết hạn, 4 giá bất thường hoặc sai đơn vị). Trang danh sách vẫn hiển thị tin đã quá hạn, nên không được dùng số tin do trang công bố làm số tin còn cho thuê.

Để nghiên cứu **tin phòng thuê trong quá khứ** mà không lẫn với phòng đang cho thuê, dùng `--include-expired --output nhom11-65httt/data/thuephongtro_rooms_historical.csv`. Cùng giới hạn ba tin chi tiết mỗi quận, tệp lịch sử có **9 tin**, mỗi quận 3 tin, tất cả ghi `listing_status=expired` và `expires_at`. Giá trị `unverified_available` trên tin chưa hết hạn chỉ nói rằng quảng cáo chưa qua ngày hết hạn; bot không xác minh được phòng thực tế còn trống. Trước khi phát hành lại dữ liệu, kiểm tra [quy chế nguồn](https://thuephongtro.com/quy-che-hoat-dong.html) và ghi rõ nguồn theo yêu cầu của trang.

## Nhà Tốt

Ba trang `thue-phong-tro-quan-{thanh-xuan,dong-da,cau-giay}-ha-noi` hiển thị bộ lọc **Cho thuê → Phòng trọ** trong trình duyệt. Một số tin trong chuyên mục vẫn mô tả nhà nguyên căn hoặc căn hộ, nên bộ lọc của trang chưa đủ để bảo đảm đúng loại tin. Yêu cầu HTTP từ bot nhận `403` trên cả ba trang. [Điều khoản Nhà Tốt](https://trogiup.chotot.com/nguoi-ban/dieu-khoan-su-dung-cua-nhatot-com/) yêu cầu chấp thuận bằng văn bản cho việc tải/sao chép nội dung; nhóm chưa có. Vì vậy **chưa chạy bot, chưa tạo dữ liệu Nhà Tốt**. Mục đích nghiên cứu phi thương mại không tự thay thế điều kiện này. Khi có chấp thuận và đường truy cập chính thức, mới triển khai bộ đọc cho ba chuyên mục trên, kiểm tra riêng giao dịch, loại hình và quận ở từng trang chi tiết.

## Hạ tầng Playwright, Chống trùng & ETL Pipeline

Thư mục bot đã được bổ sung hạ tầng dùng chung cho các nguồn dữ liệu hợp pháp:

- `config.py`: Định nghĩa 3 quận mục tiêu (`Thanh Xuân`, `Đống Đa`, `Cầu Giấy`), `USER_AGENT` nghiên cứu, `STANDARD_FIELDS` (36 cột chuẩn theo `schema_version=1.0.0-draft.1`) và các hàm làm sạch/ẩn PII (`redact_pii`, `is_non_room_listing`, `parse_monthly_rent`).
- `base_scraper.py`: Lớp trừu tượng `BaseScraper`, `PoliteHttpFetcher`, schema `RoomListing`, ghi CSV nguyên tử (`atomic_write_csv`) và `RobotsPolicy` kiểm tra `robots.txt` trước mỗi lượt thu thập.
- `playwright_scraper.py`: Wrapper `PlaywrightScraper` (Chromium headless) hỗ trợ các trang render JavaScript có cấp phép. Tuân thủ `robots.txt`, giữ độ trễ tối thiểu 1 giây (mặc định 2 giây + jitter) và dừng ngay nếu gặp HTTP `401/403/429`.
- `template_playwright_bot.py`: Mẫu `PlaywrightSourceBot` kết hợp `BaseScraper` và `PlaywrightScraper` cho nguồn mới được cấp phép.
- `muaban.py`: Bot đọc dữ liệu SSR (`__NEXT_DATA__`) của `muaban.net` trên chuyên mục phòng trọ/nhà trọ 3 quận, loại tin hết hạn/quá hạn, nhà nguyên căn, căn hộ, ghi `muaban_rooms.csv` và `muaban_rooms_rejected.csv`.
- `extractor.py`: Trích xuất và chuẩn hóa `room_type`, `price_basis`, `ward`, `deposit_vnd`/`deposit_months`, `fees_json`, `amenities_json` (3 trạng thái `true`/`false`/`null`), `content_hash` SHA-256 và `quality_flags_json` khớp 100% với `data/reference/`.
- `deduplicator.py`: Phân cụm trùng lặp chéo nguồn thành `confirmed` (chỉ giữ bản đại diện trong `listings.csv`, yêu cầu khớp số nhà/ngõ và không khác loại phòng ở ghép) và `suspected` (giữ riêng kèm cờ `POSSIBLE_DUPLICATE`).
- `pipeline.py`: Chạy các bot cấu hình (hoặc `--skip-scrape`), chuẩn hóa 36 cột, phân loại `accepted`/`needs_review`/`rejected`, khử trùng, xuất `listings.csv`, `listings_all.csv`, `records_to_review.csv`, `manifest.json`, hỗ trợ `--snapshot` ra `data/releases/<version>/` và `--validate`.
- `evaluate.py`: Đánh giá P/R/F1 theo từng trường và precision/recall cặp trùng trên tập fixture giả lập (`fixtures/synthetic_eval.json`) hoặc mẫu đối chứng thực (`fixtures/real_eval_sample.json`).
- `scheduler.py`: Lập lịch chạy pipeline định kỳ theo giờ Việt Nam (`06:00,18:00` mặc định).

### Chạy ETL Pipeline, Đánh giá và Kiểm thử

```powershell
# Chạy ETL trên dữ liệu CSV hiện có (không gọi mạng) và lưu snapshot release
python nhom11-65httt/src/backend/bot/pipeline.py --skip-scrape --snapshot

# Kiểm tra schema, danh mục tham chiếu và SHA-256 checksum
python nhom11-65httt/src/backend/bot/pipeline.py --validate

# Đánh giá trên tập đối chứng thực (holdout) và tập giả lập
python nhom11-65httt/src/backend/bot/evaluate.py --fixture nhom11-65httt/src/backend/bot/fixtures/real_eval_sample.json --split holdout
python nhom11-65httt/src/backend/bot/evaluate.py

# Chạy toàn bộ unit & integration tests (19/19)
python -m unittest discover -s nhom11-65httt/src/backend/bot -v
```
