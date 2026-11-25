# Quy tắc xử lý dữ liệu TV1 — dự thảo 0.1

**Phạm vi:** tin cho thuê phòng trọ/chỗ ở ghép tại Thanh Xuân, Đống Đa, Cầu Giấy. Các quy tắc trong tài liệu này đã được hiện thực hóa thành pipeline Python độc lập tại `src/backend/bot/` (`config.py`, `extractor.py`, `deduplicator.py`, `pipeline.py`, `evaluate.py`) và kiểm chứng tự động qua `unittest` (`19/19`) cùng `pipeline.py --validate`.

## 1. Thu nhận và truy vết

1. Chỉ dùng nguồn có căn cứ sử dụng phù hợp với thu nhận, lưu, chia sẻ nội bộ và demo. Kiểm tra `robots.txt`/hạn mức mỗi lần chạy; không vượt đăng nhập, CAPTCHA, 403 hoặc giới hạn nguồn. Nguồn có điều khoản yêu cầu văn bản phải được chấp thuận trước.
2. Mỗi lần chạy cấp `run_id` riêng, ghi nguồn, thời điểm bắt đầu/kết thúc UTC, phiên bản mã/quy tắc, URL chuyên mục hoặc tệp đầu vào, số yêu cầu, số tin phát hiện, số tin lỗi và lý do. Một `run_id` không tự thành bản phát hành.
3. Nếu được phép giữ bản gốc, lưu bản đọc được/đầu vào bất biến theo `run_id` và `raw_record_id`; không ghi đè khi sửa quy tắc. `raw_ref` dẫn từ dòng chuẩn về bản đó. Bản gốc và log định danh không tự đưa lên Git hoặc gói chia sẻ.
4. `source_record_key` là mã nguồn bền vững. `listing_id = source_name + ":" + source_record_key` sau khi chuẩn hóa mã; quy tắc này giữ nguyên khi tiêu đề, giá, vị trí trong danh sách thay đổi. URL chỉ là khóa khi nguồn không có mã ổn định và phải được chuẩn hóa trước.
5. `content_hash` là SHA-256 của biểu diễn JSON chuẩn từ các trường nguồn đã chọn, tên khóa sắp xếp, UTF-8 và cách chuẩn hóa văn bản cố định. Hash thay đổi khi nội dung đổi nhưng **không** cấp `listing_id` mới. `collected_at` là thời điểm quan sát gốc; chạy lại từ bản lưu giữ nguyên.

## 2. Trích xuất và chuẩn hóa

Thứ tự: **đọc bản gốc → chuẩn hóa khoảng trắng/Unicode → xác nhận giao dịch và loại phòng → trích xuất giá/diện tích/phí/tiện ích → chuẩn hóa đơn vị → đối chiếu khu vực → che liên hệ → kiểm tra kiểu và gắn cờ → khử trùng → xuất**. Mỗi lỗi có `listing_id`/`raw_ref`, bước và mã lý do, tránh ghi cả mô tả/số điện thoại vào log.

| Trường | Quy tắc và ca khó |
|---|---|
| Giao dịch/loại | Trang lọc “Cho thuê phòng trọ” là điều kiện đầu; tiêu đề, breadcrumb/nhãn loại và mô tả chi tiết phải phù hợp. Loại “bán nhà/đất/căn hộ”, nhà nguyên căn, căn hộ 1N1K/2N1K, mặt bằng, văn phòng, sang nhượng và tin người đi tìm thuê. Từ “ban” trong “ban công” không phải “bán”. |
| Giá | “3,5 triệu/tháng” và “3tr5/tháng” chỉ quy ra 3.500.000 khi cú pháp đủ rõ. “1,8 triệu/người/tháng” là 1.800.000, `price_basis=person`. Nhiều mức giá không rõ gắn `AMBIGUOUS_PRICE`, không chọn ngẫu nhiên. “Giá liên hệ” để trống. |
| Diện tích | `25m2`, `25 m²` → `25`; không suy từ ảnh hay phòng khác. Giá trị ≤ 0 không hợp lệ. |
| Cọc | “Cọc một tháng” → `deposit_months=1`; chỉ điền `deposit_vnd` nếu nguồn có tiền cụ thể hoặc việc quy đổi cùng cơ sở giá được kiểm chứng. Không cộng cọc vào tiền thuê. |
| Phí | “Điện 4k/số” → 4.000 `vnd_per_kwh` nếu “số điện” rõ. “Nước 100k/người” chưa nêu kỳ thu thì không mặc định tháng. `unknown` khác `free` và `included`. |
| Tiện ích | Có điều hòa → `true`; “không có điều hòa” → `false`; không nhắc → `null`/không có mã. Giữ phủ định trước khi làm sạch. |
| Thời gian | Nguồn ghi ngày không có giờ thì lưu `posted_date`, để `posted_at` trống. Chuyển thời điểm có múi giờ sang UTC; không dùng ngày chạy ETL thay ngày đăng/quan sát. Ngày hết hạn nguồn ghi vào `expires_on`. |
| Khu vực | So tên quận trên URL lọc, thẻ, breadcrumb và địa chỉ. Mâu thuẫn hoặc chỉ có tên quận trong trang tổng hợp → `DISTRICT_UNCONFIRMED`/`needs_review`. Chưa có bảng ánh xạ phường cũ/mới thì giữ nguyên nhãn nguồn và ghi ghi chú; không tự đổi quận. |
| Vị trí | Chỉ khu vực → `geo_confidence=area_only`, tọa độ trống. Tọa độ phòng chỉ có khi nguồn được phép và có căn cứ tương ứng. Không dùng tọa độ trường/tâm quận làm tọa độ phòng. |

Ngưỡng giá “bất thường” là tín hiệu cần xem lại, không phải bằng chứng lừa đảo. Bot Thuephongtro hiện loại giá trên 30 triệu/tháng ở bước danh sách; trước schema 1.0 cần thống nhất đây là ngưỡng **rà soát** hay loại, có mẫu kiểm chứng và ghi vào cấu hình. Các bot còn dùng mẫu giá và tên cột khác nhau; không nối trực tiếp CSV nguồn như thể đã chuẩn hóa.

## 3. Trạng thái, trùng và bản đại diện

- **Nhập lặp cùng mã:** khóa `(source_name, source_record_key)`; quan sát mới cập nhật bản mới nhất của cùng `listing_id`, bản cũ vẫn truy vết theo `run_id/raw_ref`. Cùng tin được gặp nhiều lần trong một run chỉ tính một mã tin.
- **Nghi cùng phòng nhưng khác mã:** tạo ứng viên từ địa chỉ, diện tích, giá, loại và văn bản; `duplicate_status=suspected`, vẫn giữ cả hai. Giá/khu vực giống nhau không đủ gộp.
- **Confirmed:** chỉ khi có chứng cứ rõ (ví dụ cùng địa chỉ/phòng, cùng ảnh/mã liên hệ được dùng hợp lệ, hoặc rà soát thủ công có biên bản). Ghi cặp mã, bằng chứng, người duyệt, ngày và phiên bản quy tắc. Không hòa trộn thuộc tính mâu thuẫn của hai tin.
- **Bản đại diện nhóm confirmed:** trong các tin `accepted`, ưu tiên `collected_at` mới nhất, rồi số trường cốt lõi có căn cứ, cuối cùng `listing_id` tăng dần. Quy tắc sắp xếp và ứng viên được lưu để chạy lại ra cùng kết quả. Tin `suspected` không bị loại khỏi bản công bố chỉ vì điểm giống cao.
- **Chọn tệp:** `listings_all.csv` giữ một dòng mới nhất mỗi mã đã xử lý; `listings.csv` chỉ `accepted` và bản đại diện nếu nhóm `confirmed`; `records_to_review.csv` chứa `needs_review` và lý do. Tin thiếu giá nhưng không mâu thuẫn có thể `accepted` với `MISSING_PRICE`; bên nhận quyết định bộ lọc/KPI sử dụng.

`record_status` là quyết định xử lý, tách khỏi `listing_status`: một quảng cáo chưa hết hạn chưa xác nhận phòng còn trống; một tin đã hết hạn có thể dùng cho phân tích lịch sử nếu quyền nguồn cho phép và được gắn nhãn rõ.

## 4. Phát hành và chạy lại

Xử lý vào thư mục tạm, kiểm tra schema/JSON/kiểu/khóa/số dòng/nhóm trùng, đọc lại các tệp, rồi mới tạo manifest và checksum. Chỉ khi đủ quyền và kiểm tra đạt mới công bố thư mục `releases/<dataset_version>/` bất biến. Bản sửa tạo phiên bản mới kèm thay đổi; không ghi đè bản cũ. Cùng bản gốc, cấu hình và phiên bản mã phải tạo cùng giá trị dữ liệu; `released_at` của một bản phát hành mới có thể khác nhưng `collected_at` không đổi.

**Hiện trạng 25/11/2026:** toàn bộ pipeline đầu–cuối đã triển khai đầy đủ `raw_ref`, `run_id`, `content_hash`, che PII (gồm cả SĐT 9–11 chữ số), trích xuất thuộc tính chuẩn danh mục, danh mục cờ `quality_flags_json`, khử trùng theo cụm `confirmed`/`suspected`, phát hành `listings.csv`, `listings_all.csv`, `records_to_review.csv`, `manifest.json` và bản lưu `data/releases/v20261125_2139/`. Không yêu cầu TV2 nạp CSDL trước để TV1 hoàn thành phần này.
