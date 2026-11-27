# HỢP ĐỒNG DỮ LIỆU ĐẦU VÀO - TV2

## 1. Thông tin chung

- Đề tài: Hệ thống phân tích thị trường phòng trọ hỗ trợ sinh viên lựa chọn nơi ở.
- Nhóm: 11 - 65HTTT.
- Người thực hiện: Trần Thị Minh Thư.
- Nhiệm vụ: TV2-01.
- Bên cung cấp dữ liệu: Thành viên 1.
- Bên tiếp nhận dữ liệu: Thành viên 2.
- Schema version: 1.0.0-draft.1.
- Dataset version: v20261125_2139.
- Trạng thái hợp đồng: Dự thảo, chờ xác nhận bàn giao.

## 2. Mục đích

Thống nhất cấu trúc dữ liệu giữa phân hệ thu thập,
chuẩn hóa dữ liệu của TV1 và phân hệ PostgreSQL,
Business Intelligence của TV2.

TV2 không thực hiện lại quá trình thu thập, làm sạch
và loại bỏ trùng lặp thuộc trách nhiệm của TV1.

## 3. Các tệp dữ liệu đầu vào

| Tệp | Mục đích |
|---|---|
| listings.csv | Dữ liệu tin đăng đã được TV1 lựa chọn để công bố |
| manifest.json | Metadata, phiên bản, số dòng và checksum |
| listings_all.csv | Dữ liệu phục vụ đối soát nếu được phép bàn giao |
| reference/*.csv | Danh mục tham chiếu |

Định dạng dữ liệu:

- CSV mã hóa UTF-8, hỗ trợ BOM.
- Dòng đầu tiên chứa tên các cột.
- Giá thuê sử dụng đơn vị VND/tháng.
- Diện tích sử dụng đơn vị m2.
- Thời gian thu thập theo ISO 8601.
- Dữ liệu chưa biết không được tự động thay bằng 0.

## 4. Cấu trúc các trường dữ liệu

| Tên trường | Kiểu dữ liệu dự kiến | Ý nghĩa |
|---|---|---|
| listing_id | TEXT | Định danh ổn định của tin đăng |
| source_name | TEXT | Nguồn thu thập |
| source_record_key | TEXT | Mã tin tại nguồn |
| source_url | TEXT | Đường dẫn tin đăng |
| raw_ref | TEXT | Tham chiếu dữ liệu gốc |
| run_id | TEXT | Mã lần thu thập |
| content_hash | TEXT | Mã SHA-256 nội dung |
| collected_at | TIMESTAMPTZ | Thời gian thu thập |
| posted_at | TIMESTAMPTZ | Thời gian đăng tin |
| posted_date | DATE | Ngày đăng |
| expires_on | DATE | Ngày hết hạn |
| title | TEXT | Tiêu đề tin đăng |
| description_clean | TEXT | Nội dung đã chuẩn hóa |
| room_type | TEXT | Loại phòng |
| area_m2 | NUMERIC | Diện tích phòng |
| rent_vnd_month | BIGINT | Giá thuê theo tháng |
| price_basis | TEXT | Đơn vị tính giá |
| deposit_vnd | BIGINT | Tiền đặt cọc |
| deposit_months | NUMERIC | Số tháng đặt cọc |
| fees_json | JSONB | Thông tin các khoản phí |
| amenities_json | JSONB | Thông tin tiện ích |
| district | TEXT | Quận |
| ward | TEXT | Phường |
| address_clean | TEXT | Địa chỉ đã chuẩn hóa |
| latitude | NUMERIC | Vĩ độ |
| longitude | NUMERIC | Kinh độ |
| geo_confidence | TEXT | Độ tin cậy vị trí |
| max_occupants | INTEGER | Số người ở tối đa |
| duplicate_group_id | TEXT | Mã nhóm tin trùng |
| duplicate_status | TEXT | Trạng thái trùng lặp |
| is_representative | BOOLEAN | Tin đại diện |
| listing_status | TEXT | Trạng thái tin đăng |
| record_status | TEXT | Trạng thái chất lượng bản ghi |
| quality_flags_json | JSONB | Danh sách cờ chất lượng |

Các kiểu dữ liệu PostgreSQL trên là đề xuất thiết kế
của TV2, không thay thế đặc tả dữ liệu gốc của TV1.

## 5. Quy tắc định danh

listing_id được hình thành từ:

source_name:source_record_key

Mỗi listing_id đại diện cho một tin đăng tại nguồn.

Một tin đăng có thể xuất hiện trong nhiều đợt dữ liệu.

Mỗi cặp listing_id và batch_id chỉ có tối đa
một snapshot trong cơ sở dữ liệu.

## 6. Quy tắc kiểm tra dữ liệu

### 6.1. Giá thuê

- Giá thuê hợp lệ phải lớn hơn 0.
- Không tự suy diễn giá khi thiếu thông tin.
- Giá chưa biết được lưu dưới dạng NULL.

price_basis gồm:

- room: Giá thuê theo phòng.
- person: Giá thuê theo người.
- unknown: Chưa xác định đơn vị tính giá.

Không gộp giá theo phòng và giá theo người
để tính trung vị hoặc khả năng chi trả.

### 6.2. Diện tích

- Diện tích hợp lệ phải lớn hơn 0.
- Diện tích chưa biết được lưu dưới dạng NULL.
- Không tính giá trên m2 nếu diện tích không hợp lệ.
- Chỉ tính giá thuê trên m2 đối với giá theo phòng.

### 6.3. Tiền đặt cọc

- deposit_vnd không âm.
- deposit_months không âm.
- NULL biểu thị chưa có thông tin.
- Không tính tiền đặt cọc vào giá thuê hằng tháng.

### 6.4. Chi phí

fees_json lưu các khoản phí theo cấu trúc:

{
  "fee_code": {
    "amount": null,
    "unit": null,
    "status": "unknown"
  }
}

Các trạng thái:

- known: Đã biết.
- included: Đã bao gồm.
- free: Miễn phí.
- unknown: Chưa biết.
- not_applicable: Không áp dụng.

Không coi khoản phí chưa biết là miễn phí.

### 6.5. Vị trí

Phạm vi dữ liệu hiện tại:

- Đống Đa.
- Thanh Xuân.
- Cầu Giấy.

geo_confidence gồm:

- confirmed
- approximate
- area_only
- unknown

Không tự tạo tọa độ nếu nguồn không cung cấp
thông tin vị trí đủ tin cậy.

### 6.6. Chất lượng và trùng lặp

record_status gồm:

- accepted
- needs_review
- rejected

duplicate_status gồm:

- unique
- suspected
- confirmed
- unknown

TV2 sử dụng nhãn chất lượng và trùng lặp do TV1
cung cấp, không tự thực hiện lại thuật toán loại trùng.

Dữ liệu công bố phải tuân thủ quy tắc lựa chọn
tin đại diện của TV1.

### 6.7. Trạng thái tin đăng

listing_status gồm:

- expired
- unverified_available
- unknown

Không suy diễn tin đăng đã được cho thuê chỉ vì
tin không xuất hiện trong đợt dữ liệu tiếp theo.

## 7. Quản lý đợt nhập dữ liệu

Mỗi đợt nhập cần lưu:

- batch_id.
- schema_version.
- dataset_version.
- export_mode.
- data_origin.
- checksum.
- imported_at.
- import_status.
- total_rows.
- accepted_rows.
- rejected_rows.

Nguyên tắc:

1. Kiểm tra schema và checksum trước khi công bố.
2. Nhập lại cùng batch và checksum không tạo dữ liệu trùng.
3. Cùng batch nhưng checksum khác phải báo xung đột.
4. Batch mới phải giữ lại lịch sử dữ liệu trước đó.
5. Ghi nhận các lỗi nhập dữ liệu.
6. Dashboard chỉ sử dụng batch nhập thành công.

## 8. Tách biệt dữ liệu thực và dữ liệu giả lập

Dữ liệu thực sử dụng để phân tích thị trường
khi đã được phép tiếp nhận và sử dụng.

Dữ liệu giả lập sử dụng để kiểm thử:

- Quy trình nhập dữ liệu.
- Tính đúng đắn của KPI.
- Các trường hợp dữ liệu thiếu.
- Nhập lặp và cập nhật lịch sử.
- Hoạt động của dashboard.

Hai loại dữ liệu phải được lưu trữ tách biệt.

Không sử dụng dữ liệu giả lập để đưa ra kết luận
về thị trường phòng trọ thực tế.

## 9. Trạng thái bàn giao từ TV1

Theo manifest phiên bản v20261125_2139:

| Chỉ tiêu | Số lượng |
|---|---:|
| Dữ liệu đầu vào | 689 |
| Bản ghi bị loại | 5 |
| Tin trùng đã loại khỏi tập công bố | 12 |
| Tin nghi ngờ trùng | 66 |
| Tin đăng công bố | 672 |
| Đống Đa | 229 |
| Thanh Xuân | 210 |
| Cầu Giấy | 233 |
| Giá theo phòng | 650 |
| Giá theo người | 22 |

Đây là số liệu metadata do TV1 công bố,
chưa phải kết quả đối soát độc lập của TV2.

Tại thời điểm lập tài liệu, chưa có listings.csv
thực tế trong thư mục dữ liệu đã kiểm tra.

Cần xác nhận quyền sử dụng và tiếp nhận dữ liệu
trước khi nhập dữ liệu thực.

## 10. Tiêu chí nghiệm thu

- Xác định đầy đủ cấu trúc dữ liệu đầu vào.
- Thống nhất kiểu dữ liệu và đơn vị đo.
- Xác định quy tắc xử lý dữ liệu thiếu.
- Xác định quy tắc định danh và quản lý batch.
- Có khả năng kiểm tra dữ liệu bằng chương trình.
- Không trộn dữ liệu thực và dữ liệu giả lập.

## 11. Tài liệu tham chiếu

- ../ban_giao_tv1/dac_ta_du_lieu_v0_1.md
- ../ban_giao_tv1/huong_dan_chay_va_kiem_tra.md
- ../ban_giao_tv1/bao_cao_chat_luong_2026-11-25.md
- ../../data/manifest.json
- Nhiệm vụ chi tiết TV2 - CSDL và BI.