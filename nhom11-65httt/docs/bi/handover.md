# TÀI LIỆU BÀN GIAO PHÂN HỆ CSDL VÀ BI – TV2

## 1. Sản phẩm bàn giao

- PostgreSQL Database.
- Schema, bảng, ràng buộc, index và phân quyền.
- Python Importer.
- Bộ dữ liệu giả lập B001 và B002.
- 5 Analytics Views.
- 30 biểu đồ Superset.
- 3 Dashboard BI.
- Docker Compose và script triển khai.
- Tài liệu thiết kế, KPI và kiểm thử.

## 2. Vị trí mã nguồn

| Thành phần | Đường dẫn |
|---|---|
| Database | src/database/ |
| Backend BI | src/backend/bi/ |
| Importer | src/backend/bi/importer/ |
| Superset | src/backend/bi/superset/ |
| Test fixtures | src/backend/bi/tests/fixtures/ |
| Tài liệu | docs/bi/ |

## 3. Thông tin kết nối PostgreSQL

| Thuộc tính | Giá trị |
|---|---|
| Host từ máy cục bộ | 127.0.0.1 |
| Port | 5433 |
| Database | phongtro_bi_demo |
| User đọc dữ liệu BI | bi_reader |
| Password | BI_READER_PASSWORD trong .env |
| Schema | analytics |

Nếu ứng dụng chạy trong Docker và được kết nối vào cùng network BI, sử dụng hostname phongtro_bi_db và cổng nội bộ 5432.

Không sử dụng tài khoản quản trị cơ sở dữ liệu trong frontend.

## 4. Danh sách Analytics Views

| View | Mục đích |
|---|---|
| vw_listing_current | Danh sách tin hiện tại |
| vw_market_price | Phân tích giá thuê |
| vw_affordability | Phân tích khả năng chi trả |
| vw_listing_quality | Phân tích chất lượng tin |
| vw_import_batch_quality | Theo dõi chất lượng nhập dữ liệu |

TV3 có thể sử dụng vw_listing_current làm nguồn dữ liệu đầu vào cho thuật toán, sau khi thống nhất các trường cần thiết và tiêu chí xử lý dữ liệu thiếu.

## 5. Bàn giao cho TV4

Superset Base URL:

http://localhost:8089

Dashboard:

- /superset/dashboard/phongtro-market/
- /superset/dashboard/phongtro-affordability/
- /superset/dashboard/phongtro-quality/

TV4 phụ trách tích hợp các đường dẫn Dashboard vào giao diện Streamlit.

Có thể sử dụng liên kết mở Dashboard sau khi đăng nhập Superset. Nếu cần nhúng trực tiếp, phải thống nhất cấu hình xác thực và quyền truy cập phù hợp.

Không đưa tài khoản Admin hoặc mật khẩu Superset vào mã nguồn frontend.

## 6. Phối hợp với TV1

TV1 bàn giao listings.csv và manifest.json tương ứng với phiên bản dữ liệu đã chuẩn hóa và được phép sử dụng.

TV2 phụ trách kiểm tra checksum, schema, import dữ liệu và xác nhận kết quả KPI.

## 7. Trạng thái bàn giao

Phiên bản phát triển đã triển khai thành công với dữ liệu giả lập.

Dữ liệu thực tế và kiểm thử tích hợp toàn hệ thống sẽ được bổ sung sau khi các thành viên thống nhất giao diện kết nối và hoàn thành bàn giao dữ liệu.