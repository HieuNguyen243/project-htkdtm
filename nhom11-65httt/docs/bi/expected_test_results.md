# KẾT QUẢ KIỂM THỬ KỲ VỌNG

## 1. Thông tin chung

- Đề tài: Hệ thống phân tích thị trường phòng trọ hỗ trợ sinh viên lựa chọn nơi ở.
- Nhóm: 11 - 65HTTT.
- Người thực hiện: Trần Thị Minh Thư.
- Nhiệm vụ: TV2-01, TV2-06.
- Nguồn dữ liệu: Synthetic.
- Trạng thái: Kết quả kỳ vọng, chưa kiểm thử trên PostgreSQL.

## 2. Mục tiêu kiểm thử

- Kiểm tra tính chính xác của KPI.
- Kiểm tra xử lý dữ liệu thiếu.
- Phân biệt giá theo phòng và theo người.
- Kiểm tra cơ chế nhập lặp.
- Kiểm tra lưu lịch sử thay đổi.
- Kiểm tra dữ liệu hiện tại.
- Kiểm tra tính toàn vẹn dữ liệu.
- Kiểm tra phân quyền người dùng.

## 3. Kiểm tra manifest

| Chỉ tiêu | B001 | B002 |
|---|---:|---:|
| Tổng số bản ghi | 7 | 8 |
| Tin theo phòng | 6 | 7 |
| Tin theo người | 1 | 1 |
| Tin thiếu giá | 2 | 1 |
| Tin thiếu diện tích | 2 | 2 |
| Đống Đa | 3 | 3 |
| Thanh Xuân | 2 | 2 |
| Cầu Giấy | 2 | 3 |

Kết quả tạo CSV và manifest đã được kiểm tra
thông qua terminal.

Checksum B001:

16a252fea0acb70e6ad6bb8e8e12b49d7af1c56b8aef8da575c764992e09b4de

Checksum B002:

f4e7b57bd78cab9f7bc657344d99fddd4332510b6b0254f116bcd4d9355328b4

Các checksum cần được kiểm tra lại khi nhập dữ liệu.

## 4. Kết quả KPI kỳ vọng của B001

### 4.1. Dashboard giá chào thuê

Phạm vi: Giá theo phòng.

| KPI | Kết quả kỳ vọng |
|---|---:|
| Tổng số tin | 6 |
| Tin có giá hợp lệ | 4 |
| Tin thiếu giá | 2 |
| Giá thấp nhất | 2000000 |
| Giá cao nhất | 5000000 |
| Trung vị giá | 3500000 |
| P25 | 2750000 |
| P75 | 4250000 |
| Trung vị giá trên m2 | 150000 |
| Số mẫu tính giá trên m2 | 4 |

### 4.2. Dashboard khả năng chi trả

| Ngân sách | Số tin phù hợp | Tỷ lệ |
|---|---:|---:|
| 2000000 | 1 | 25% |
| 3000000 | 2 | 50% |
| 4000000 | 3 | 75% |
| 5000000 | 4 | 100% |

Độ phủ giá: 4 / 6 = 66.67%.

### 4.3. Dashboard chất lượng dữ liệu

Phạm vi: Giá theo phòng.

| KPI | Kết quả kỳ vọng |
|---|---:|
| Tỷ lệ thiếu giá | 33.33% |
| Tỷ lệ thiếu diện tích | 16.67% |
| Độ phủ thông tin quận | 100% |
| Độ phủ tọa độ | 0% |

## 5. Kết quả KPI kỳ vọng của B002

| KPI | Kết quả kỳ vọng |
|---|---:|
| Tổng số tin hiện tại | 8 |
| Tin theo phòng | 7 |
| Tin theo người | 1 |
| Tin theo phòng có giá hợp lệ | 6 |
| Tin theo phòng thiếu giá | 1 |
| Trung vị giá theo phòng | 3100000 |
| Tin trong ngân sách 3 triệu | 3 |
| Tỷ lệ phù hợp ngân sách 3 triệu | 50% |
| Độ phủ giá theo phòng | 85.71% |

## 6. Kiểm thử lịch sử dữ liệu

Sau khi nhập thành công B001 và B002:

| Chỉ tiêu | Kết quả kỳ vọng |
|---|---:|
| Số batch thành công | 2 |
| Số listing duy nhất | 8 |
| Tổng số snapshot | 15 |
| Số tin hiện tại | 8 |
| Snapshot của demo:001 | 2 |
| Giá cũ demo:001 | 2000000 |
| Giá hiện tại demo:001 | 2500000 |

## 7. Kiểm thử nhập lặp

Mã kiểm thử: TC-01.

Thực hiện nhập lại B001 với cùng checksum.

Kết quả kỳ vọng:

- Không tạo thêm listing.
- Không tạo thêm snapshot.
- Không thay đổi dữ liệu đã công bố.
- Thông báo batch đã được nhập.

## 8. Kiểm thử xung đột batch

Mã kiểm thử: TC-02.

Sử dụng cùng batch_id nhưng checksum khác.

Kết quả kỳ vọng:

- Từ chối dữ liệu mới.
- Không ghi đè batch đã thành công.
- Ghi nhận lỗi BATCH_CONFLICT.

## 9. Kiểm thử dữ liệu không hợp lệ

| Mã kiểm thử | Trường hợp |
|---|---|
| TC-03 | Thiếu cột bắt buộc |
| TC-04 | Sai kiểu dữ liệu |
| TC-05 | Giá thuê âm |
| TC-06 | Diện tích âm |
| TC-07 | JSON không hợp lệ |
| TC-08 | Listing ID trùng trong batch |
| TC-09 | Checksum không khớp |
| TC-10 | Schema version không được hỗ trợ |

Kết quả kỳ vọng:

- Phát hiện và ghi nhận lỗi.
- Không công bố batch thất bại.
- Không làm hỏng dữ liệu trước đó.

## 10. Kiểm thử phân quyền

Mã kiểm thử: TC-11.

Tài khoản BI Reader:

- Được SELECT analytics view đã cấp quyền.
- Không được INSERT.
- Không được UPDATE.
- Không được DELETE.
- Không được sửa cấu trúc bảng.

## 11. Kiểm thử Dashboard

| Mã kiểm thử | Nội dung |
|---|---|
| TC-12 | KPI khớp kết quả SQL |
| TC-13 | Bộ lọc theo quận |
| TC-14 | Bộ lọc theo nguồn |
| TC-15 | Bộ lọc theo loại phòng |
| TC-16 | Bộ lọc theo price_basis |
| TC-17 | Bộ lọc ngân sách |
| TC-18 | Bộ lọc không có dữ liệu |
| TC-19 | Không nhân đôi tin khi JOIN |

## 12. Nguyên tắc sử dụng dữ liệu

- Dữ liệu giả lập chỉ phục vụ kiểm thử.
- Các dòng thiếu giá là trường hợp kiểm thử có chủ đích.
- Không nới lỏng quy tắc nhập dữ liệu thực.
- Không trộn dữ liệu thực và dữ liệu giả lập.
- Không sử dụng dữ liệu giả lập để kết luận về thị trường thực tế.

## 13. Trạng thái nghiệm thu

Đã tạo hai file CSV và hai file manifest.

Các KPI và trường hợp kiểm thử PostgreSQL,
Importer và Superset hiện là kết quả kỳ vọng.

Kết quả chạy thực tế sẽ được cập nhật
trong báo cáo test_report.md.