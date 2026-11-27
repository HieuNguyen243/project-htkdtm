# TỪ ĐIỂN DỮ LIỆU - DATA DICTIONARY

## 1. Thông tin chung

- Nhóm: 11 - 65HTTT.
- Người thực hiện: Trần Thị Minh Thư.
- Nhiệm vụ: TV2-02.
- Hệ quản trị: PostgreSQL 16.
- Phiên bản: 1.0.
- Trạng thái: Thiết kế dự thảo.

## 2. Quy ước

- PK: Primary Key.
- FK: Foreign Key.
- UQ: Unique.
- NN: Not Null.
- NULL: Giá trị chưa biết hoặc chưa có thông tin.
- TIMESTAMPTZ: Thời gian có múi giờ.
- JSONB: Dữ liệu JSON trong PostgreSQL.

## 3. Bảng ingest_batch

| Trường | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| batch_id | TEXT | PK | Mã đợt nhập |
| schema_version | TEXT | NN | Phiên bản cấu trúc dữ liệu |
| dataset_version | TEXT | NN | Phiên bản bộ dữ liệu |
| export_mode | TEXT | NN | full hoặc delta |
| data_origin | TEXT | NN | real hoặc synthetic |
| checksum | TEXT | NN | SHA-256 của CSV |
| import_status | TEXT | NN | Trạng thái nhập |
| imported_at | TIMESTAMPTZ | NULL | Thời điểm hoàn tất nhập |
| total_rows | INTEGER | NN | Tổng số dòng |
| accepted_rows | INTEGER | NN | Số dòng được chấp nhận |
| rejected_rows | INTEGER | NN | Số dòng bị từ chối |

## 4. Bảng staging_listing

| Trường | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| staging_id | BIGINT | PK | Mã dòng staging |
| batch_id | TEXT | FK, NN | Mã đợt nhập |
| row_number | INTEGER | NN | Số thứ tự dòng dữ liệu |
| raw_data | JSONB | NN | Dữ liệu đầu vào |
| validation_status | TEXT | NN | Trạng thái kiểm tra |
| created_at | TIMESTAMPTZ | NN | Thời điểm tạo |

Ràng buộc UQ: batch_id, row_number.

## 5. Bảng listing

| Trường | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| listing_id | TEXT | PK | Định danh tin đăng |
| source_name | TEXT | NN | Nguồn tin |
| source_record_key | TEXT | NN | Mã tin tại nguồn |
| first_seen_at | TIMESTAMPTZ | NN | Thời điểm quan sát sớm nhất |
| created_at | TIMESTAMPTZ | NN | Thời điểm tạo trong CSDL |

Ràng buộc UQ: source_name, source_record_key.

## 6. Bảng listing_snapshot

### 6.1. Nhóm định danh và nguồn

| Trường | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| snapshot_id | BIGINT | PK | Mã snapshot |
| listing_id | TEXT | FK, NN | Mã tin đăng |
| batch_id | TEXT | FK, NN | Mã đợt nhập |
| source_url | TEXT | Có điều kiện | URL tin đăng |
| raw_ref | TEXT | NN | Tham chiếu dữ liệu gốc |
| run_id | TEXT | NN | Mã lần thu thập |
| content_hash | TEXT | NN | SHA-256 nội dung |

### 6.2. Nhóm thời gian

| Trường | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| collected_at | TIMESTAMPTZ | NN | Thời gian thu thập |
| posted_at | TIMESTAMPTZ | NULL | Thời gian đăng |
| posted_date | DATE | NULL | Ngày đăng |
| expires_on | DATE | NULL | Ngày hết hạn |

### 6.3. Nhóm thông tin phòng

| Trường | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| title | TEXT | Theo contract | Tiêu đề |
| description_clean | TEXT | Theo contract | Mô tả chuẩn hóa |
| room_type | TEXT | Theo contract | Loại phòng |
| area_m2 | NUMERIC | Dương hoặc NULL | Diện tích m2 |
| max_occupants | INTEGER | Dương hoặc NULL | Số người tối đa |

### 6.4. Nhóm giá và chi phí

| Trường | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| rent_vnd_month | BIGINT | Dương, theo contract | Giá VND/tháng |
| price_basis | TEXT | NN | room/person/unknown |
| deposit_vnd | BIGINT | Không âm hoặc NULL | Tiền đặt cọc |
| deposit_months | NUMERIC | Không âm hoặc NULL | Số tháng đặt cọc |
| fees_json | JSONB | JSON object | Các khoản phí |
| amenities_json | JSONB | JSON object | Tiện ích |

### 6.5. Nhóm vị trí

| Trường | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| district | TEXT | Theo contract | Quận |
| ward | TEXT | NULL | Phường |
| address_clean | TEXT | NULL | Địa chỉ |
| latitude | NUMERIC | NULL hoặc hợp lệ | Vĩ độ |
| longitude | NUMERIC | NULL hoặc hợp lệ | Kinh độ |
| geo_confidence | TEXT | Theo contract | Độ tin cậy vị trí |

### 6.6. Nhóm chất lượng

| Trường | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| duplicate_group_id | TEXT | NULL | Nhóm tin trùng |
| duplicate_status | TEXT | Theo contract | Trạng thái trùng |
| is_representative | BOOLEAN | NN | Tin đại diện |
| listing_status | TEXT | Theo contract | Trạng thái tin |
| record_status | TEXT | Theo contract | Trạng thái bản ghi |
| quality_flags_json | JSONB | JSON array | Cờ chất lượng |

Ràng buộc UQ: listing_id, batch_id.

## 7. Bảng import_issue

| Trường | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| issue_id | BIGINT | PK | Mã lỗi |
| batch_id | TEXT | FK, NN | Đợt nhập |
| row_number | INTEGER | NULL | Dòng phát sinh lỗi |
| listing_id | TEXT | NULL | Định danh tin liên quan |
| field_name | TEXT | NULL | Trường phát sinh lỗi |
| error_code | TEXT | NN | Mã lỗi |
| error_message | TEXT | NN | Nội dung lỗi |
| severity | TEXT | NN | Mức độ lỗi |
| created_at | TIMESTAMPTZ | NN | Thời gian ghi nhận |

## 8. Danh mục giá trị

### price_basis

- room
- person
- unknown

### record_status

- accepted
- needs_review
- rejected

### duplicate_status

- unique
- suspected
- confirmed
- unknown

### geo_confidence

- confirmed
- approximate
- area_only
- unknown

### listing_status

- expired
- unverified_available
- unknown

### import_status

- pending
- processing
- succeeded
- failed

### validation_status

- pending
- valid
- invalid

### severity

- warning
- error

### data_origin

- real
- synthetic

## 9. Quy tắc sử dụng dữ liệu

- Không sử dụng 0 thay cho NULL.
- Không trộn giá theo phòng và giá theo người.
- Không coi phí chưa biết là miễn phí.
- Không sử dụng tiền đặt cọc làm giá thuê tháng.
- Không tính giá trên m2 nếu thiếu diện tích.
- Không sử dụng tọa độ tự suy diễn.
- Không sử dụng batch thất bại trong dashboard.
- Không thay đổi nhãn chất lượng do TV1 cung cấp.

## 10. Tài liệu tham chiếu

- data_contract.md
- erd.md
- ../ban_giao_tv1/dac_ta_du_lieu_v0_1.md

## 11. Ghi chú

Các kiểu dữ liệu và trường quản lý nội bộ
là đề xuất triển khai của TV2.

Các ràng buộc có điều kiện cần được đối chiếu
với hợp đồng dữ liệu TV1 trước khi triển khai.

Từ điển dữ liệu sẽ được cập nhật đồng bộ
với các script migration PostgreSQL.