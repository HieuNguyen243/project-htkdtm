# BÁO CÁO KIỂM THỬ PHÂN HỆ CƠ SỞ DỮ LIỆU VÀ BI

## 1. Thông tin chung

- Dự án: Hệ thống phân tích thị trường phòng trọ hỗ trợ sinh viên lựa chọn nơi ở.
- Nhóm: 11 – 65HTTT.
- Phụ trách: TV2 – Trần Thị Minh Thư.
- Ngày kiểm thử: 27/11/2026.
- Công nghệ: PostgreSQL 16, Apache Superset 6.1.0, Python 3.12, Docker Compose.
- Nguồn dữ liệu kiểm thử: SYNTHETIC DEMO, gồm hai batch B001 và B002.

## 2. Mục tiêu kiểm thử

- Kiểm tra khả năng triển khai hệ thống từ repository GitHub.
- Kiểm tra khả năng khởi tạo cơ sở dữ liệu và Superset độc lập.
- Kiểm tra tính toàn vẹn và khả năng lưu lịch sử dữ liệu.
- Kiểm tra khả năng chống nhập trùng batch.
- Đối chiếu kết quả tính toán KPI.
- Kiểm tra phân quyền truy cập dữ liệu BI.
- Kiểm tra khả năng tự động tạo Dataset, Chart và Dashboard.

## 3. Môi trường kiểm thử

| Thành phần | Môi trường chính | Môi trường TEST |
|---|---|---|
| PostgreSQL | 5433 | 5434 |
| Superset | 8089 | 8090 |
| Docker Project | phongtro-bi | phongtro-bi-test |
| Database | phongtro_bi_demo | phongtro_bi_demo |

Hai môi trường sử dụng container, network và volume riêng biệt.

Kết quả kiểm tra: 6 container hoạt động ở trạng thái healthy. Hai Superset Health API đều trả về OK.

## 4. Kết quả kiểm thử dữ liệu

| Chỉ tiêu | Kỳ vọng | Thực tế | Kết quả |
|---|---:|---:|---|
| Số batch | 2 | 2 | PASS |
| Staging rows | 15 | 15 | PASS |
| Listings | 8 | 8 | PASS |
| Snapshots | 15 | 15 | PASS |
| Import issues | 0 | 0 | PASS |
| Current listings | 8 | 8 | PASS |
| Unique current listings | 8 | 8 | PASS |
| Analytics Views | 5 | 5 | PASS |

Sau các lần chạy lại setup, số lượng bản ghi vẫn giữ nguyên. Không phát hiện nhập trùng đối với hai batch kiểm thử.

## 5. Kết quả kiểm thử KPI

| Chỉ số | Kỳ vọng | Thực tế | Kết quả |
|---|---:|---:|---|
| Tổng tin giá theo phòng | 7 | 7 | PASS |
| Tin có giá hợp lệ | 6 | 6 | PASS |
| Giá thấp nhất | 2.500.000 | 2.500.000 | PASS |
| Giá cao nhất | 4.500.000 | 4.500.000 | PASS |
| P25 | 2.850.000 | 2.850.000 | PASS |
| Median | 3.100.000 | 3.100.000 | PASS |
| P75 | 3.800.000 | 3.800.000 | PASS |
| Tin phù hợp 2 triệu | 0 | 0 | PASS |
| Tin phù hợp 3 triệu | 3 | 3 | PASS |
| Tin phù hợp 4 triệu | 5 | 5 | PASS |
| Tin phù hợp 5 triệu | 6 | 6 | PASS |
| Tỷ lệ phù hợp 3 triệu | 50% | 50% | PASS |
| Độ phủ giá | 85,71% | 85,71% | PASS |

## 6. Kiểm thử chất lượng dữ liệu

- Tổng số tin hiện tại: 8.
- Thiếu giá thuê: 1.
- Thiếu diện tích: 2.
- Thiếu quận: 0.
- Thiếu địa chỉ chi tiết: 8.
- Thiếu thông tin phí: 8.
- Có tọa độ: 0.
- Nghi ngờ trùng lặp: 0.

Các giá trị thiếu được giữ nguyên để đánh giá chất lượng dữ liệu, không tự động thay thế bằng giá trị giả định.

## 7. Kiểm thử nhập dữ liệu

| Batch | Tổng số dòng | Hợp lệ | Từ chối | Tỷ lệ thành công |
|---|---:|---:|---:|---:|
| B001 | 7 | 7 | 0 | 100% |
| B002 | 8 | 8 | 0 | 100% |

Cả hai batch có trạng thái succeeded.

## 8. Kiểm thử phân quyền

Tài khoản bi_reader có quyền SELECT trên cả 5 Analytics Views và không có quyền INSERT trên các View này.

Kết quả: PASS.

## 9. Kiểm thử Superset

Script triển khai đã tạo thành công 30 biểu đồ thuộc 3 Dashboard:

- Phân tích thị trường giá thuê.
- Phân tích khả năng chi trả.
- Phân tích chất lượng dữ liệu.

Kết quả tạo Dashboard qua API: PASS.

Việc kiểm tra trực quan toàn bộ biểu đồ, bộ lọc và số lượng Dashboard sau khi chạy lại cần được xác nhận bổ sung.

## 10. Lỗi phát hiện và phương án khắc phục

Trong quá trình triển khai trên Git Bash, thao tác tạo tài khoản Superset Admin tương tác phát sinh lỗi UnicodeEncodeError.

Phương án khắc phục đã kiểm chứng: tạo tài khoản bằng tham số không tương tác.

Hệ thống sau đó triển khai thành công và xuất hiện thông báo BI SETUP COMPLETED.

Bản sửa tự động khởi tạo Admin từ file .env cần được xác nhận bổ sung trên môi trường chưa có tài khoản.

## 11. Kết luận

Phân hệ PostgreSQL và BI đã triển khai thành công trên môi trường Docker độc lập với dữ liệu giả lập. Các kết quả kiểm thử SQL, KPI, số lượng bản ghi và phân quyền BI đều khớp với kỳ vọng.

Hệ thống đủ điều kiện bàn giao phiên bản phát triển để các thành viên khác tiếp tục tích hợp.

Các công việc còn lại gồm kiểm thử dữ liệu thực tế, kiểm thử các trường hợp dữ liệu không hợp lệ, kiểm tra trực quan Dashboard và kiểm thử tích hợp toàn hệ thống.