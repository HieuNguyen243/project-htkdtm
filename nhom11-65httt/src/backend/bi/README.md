# PHÂN HỆ CƠ SỞ DỮ LIỆU VÀ BUSINESS INTELLIGENCE

## 1. Thông tin dự án

- Đề tài: Hệ thống phân tích thị trường phòng trọ hỗ trợ sinh viên lựa chọn nơi ở.
- Học phần: Hệ thống Kinh doanh thông minh.
- Nhóm: 11 - 65HTTT.
- Thành viên thực hiện: Trần Thị Minh Thư.
- Vai trò: Thành viên 2 - Cơ sở dữ liệu và BI.

## 2. Mục tiêu

Xây dựng phân hệ cơ sở dữ liệu PostgreSQL và Apache Superset
có khả năng hoạt động độc lập, tiếp nhận dữ liệu phòng trọ
đã được chuẩn hóa, quản lý lịch sử dữ liệu và cung cấp
các dashboard hỗ trợ phân tích thị trường phòng trọ.

## 3. Phạm vi nhiệm vụ

| Mã nhiệm vụ | Nội dung | Trạng thái |
|---|---|---|
| TV2-01 | Hợp đồng dữ liệu và bộ mẫu kiểm thử | Chưa hoàn thành |
| TV2-02 | Thiết kế cơ sở dữ liệu | Chưa hoàn thành |
| TV2-03 | Xây dựng công cụ nhập dữ liệu | Chưa hoàn thành |
| TV2-04 | Analytics Views và định nghĩa KPI | Chưa hoàn thành |
| TV2-05A | Dashboard giá chào thuê | Chưa hoàn thành |
| TV2-05B | Dashboard khả năng chi trả | Chưa hoàn thành |
| TV2-05C | Dashboard chất lượng dữ liệu | Chưa hoàn thành |
| TV2-06 | Kiểm thử và đối soát SQL | Chưa hoàn thành |
| TV2-07 | Môi trường, phân quyền và khôi phục | Chưa hoàn thành |
| TV2-08 | Báo cáo và bàn giao sản phẩm | Chưa hoàn thành |

## 4. Kiến trúc hệ thống

Dữ liệu chuẩn từ thành viên 1
-> Python Importer
-> PostgreSQL
-> Analytics Views
-> Apache Superset
-> Dashboard BI

## 5. Công nghệ dự kiến

- PostgreSQL 16: Lưu trữ và truy vấn dữ liệu.
- Python: Kiểm tra và nhập dữ liệu CSV.
- SQL: Xây dựng các view và tính toán KPI.
- Apache Superset: Trực quan hóa dữ liệu.
- Docker Compose: Triển khai môi trường.
- Git/GitHub: Quản lý mã nguồn và tiến độ.

## 6. Cấu trúc thư mục

- importer/: Công cụ nhập và kiểm tra dữ liệu.
- superset/: Cấu hình và bản xuất dashboard.
- tests/: Mã nguồn kiểm thử.
- tests/fixtures/: Dữ liệu giả lập phục vụ kiểm thử.
- ../../database/: Script cơ sở dữ liệu và SQL.
- ../../../docs/bi/: Tài liệu, báo cáo và minh chứng.

## 7. Dashboard dự kiến

### Dashboard 1 - Giá chào thuê

- Tổng số tin đăng hiện tại.
- Số tin có giá hợp lệ.
- Trung vị giá thuê.
- Phân vị P25 và P75.
- Giá thuê theo khu vực.
- Phân bố giá thuê.
- Giá thuê trên mét vuông.

### Dashboard 2 - Khả năng chi trả

- Số tin có giá hợp lệ.
- Số tin trong ngân sách.
- Tỷ lệ tin trong ngân sách.
- Độ phủ thông tin giá.
- So sánh các mức ngân sách.
- So sánh khả năng chi trả theo khu vực.

### Dashboard 3 - Chất lượng dữ liệu

- Tỷ lệ thiếu giá, diện tích, phí và vị trí.
- Độ phủ dữ liệu theo nguồn và khu vực.
- Độ mới của dữ liệu.
- Chất lượng thông tin vị trí.
- Thống kê tin trùng theo nhãn của TV1.
- Thống kê kết quả nhập dữ liệu và lỗi.

## 8. Nguyên tắc xử lý dữ liệu

- Không trộn dữ liệu thực với dữ liệu giả lập.
- Không thay giá trị chưa biết bằng 0.
- Không trộn giá/phòng và giá/người.
- Không tự thực hiện lại quy trình làm sạch của TV1.
- Không suy diễn tin biến mất là đã cho thuê.
- Nhập lại cùng đợt không làm nhân đôi dữ liệu.
- Cập nhật dữ liệu phải giữ được lịch sử.
- Dashboard chỉ đọc dữ liệu đã công bố thành công.
- Các KPI phải được kiểm chứng bằng SQL.

## 9. Hướng dẫn cài đặt

Sẽ được bổ sung sau khi hoàn thiện môi trường
PostgreSQL, Python Importer và Apache Superset.

## 10. Trạng thái dự án

Đang triển khai phân hệ Cơ sở dữ liệu và BI.