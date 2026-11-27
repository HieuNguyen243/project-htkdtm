# ROOM RENTAL DATABASE

## Giới thiệu

Cơ sở dữ liệu thuộc hệ thống phân tích thị trường
phòng trọ hỗ trợ sinh viên lựa chọn nơi ở.

## Công nghệ

PostgreSQL 16.

## Cấu trúc thư mục

- migrations/: Script tạo schema, bảng và phân quyền.
- views/: Các view phục vụ phân tích BI.
- seed/: Script khởi tạo dữ liệu kiểm thử.
- validation/: SQL kiểm tra và đối soát KPI.

## Các bảng dự kiến

- ingest_batch
- staging_listing
- listing
- listing_snapshot
- import_issue

## Các Analytics Views dự kiến

- vw_listing_current
- vw_market_price
- vw_affordability
- vw_listing_quality

## Nguyên tắc thiết kế

- Mỗi tin đăng có một định danh ổn định.
- Lưu lịch sử dữ liệu theo từng đợt.
- Nhập lặp không làm nhân đôi dữ liệu.
- Không thay NULL bằng 0.
- Tách biệt dữ liệu thực và giả lập.
- Tài khoản BI chỉ có quyền đọc.

## Trạng thái

Đang triển khai.