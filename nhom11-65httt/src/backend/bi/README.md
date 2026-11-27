# PHONG TRO BI – Hệ thống phân tích thị trường phòng trọ

## 1. Giới thiệu

Phân hệ CSDL và BI thuộc dự án Hệ thống phân tích thị trường phòng trọ hỗ trợ sinh viên lựa chọn nơi ở của nhóm 11 – 65HTTT.

Hệ thống sử dụng PostgreSQL để lưu trữ dữ liệu, Python để kiểm tra và nhập liệu, Apache Superset để trực quan hóa và phân tích dữ liệu.

## 2. Công nghệ sử dụng

- PostgreSQL 16
- Apache Superset 6.1.0
- Python 3.12
- Docker và Docker Compose
- SQL, Bash và CSS

## 3. Yêu cầu môi trường

- Git
- Docker Desktop đang hoạt động
- Python 3.12
- Git Bash đối với Windows

## 4. Hướng dẫn cài đặt

### Bước 1. Clone repository

```bash
git clone -b nhom11-65httt https://github.com/HieuNguyen243/project-htkdtm.git
cd project-htkdtm/nhom11-65httt/src/backend/bi
```

### Bước 2. Cấu hình môi trường

```bash
cp .env.example .env
```

Mở file `.env` và thiết lập các mật khẩu:

- POSTGRES_PASSWORD: Mật khẩu quản trị PostgreSQL.
- DB_PASSWORD: Mật khẩu tài khoản bi_importer.
- BI_READER_PASSWORD: Mật khẩu tài khoản bi_reader.
- SUPERSET_DB_PASSWORD: Mật khẩu database metadata.
- SUPERSET_PASSWORD: Mật khẩu đăng nhập Superset.
- SUPERSET_SECRET_KEY: Khóa bảo mật ngẫu nhiên.

Tạo Secret Key bằng lệnh:

```bash
py -3.12 -c "import secrets; print(secrets.token_hex(48))"
```

Không đưa file `.env` lên GitHub.

### Bước 3. Triển khai hệ thống

```bash
bash setup_bi.sh
```

Trong lần cài đặt đầu tiên, chọn `y` khi được hỏi có tạo tài khoản admin hay không.

Tạo tài khoản admin với mật khẩu đã cấu hình. Khi chạy lại trên môi trường đã có tài khoản, chọn `n`.

Nhập mật khẩu Superset và BI Reader nếu chương trình yêu cầu.

### Bước 4. Truy cập hệ thống

- Superset: http://localhost:8089
- PostgreSQL: localhost:5433
- Database: phongtro_bi_demo

## 5. Danh sách Dashboard

| Dashboard | Đường dẫn |
|---|---|
| Phân tích giá thuê | http://localhost:8089/superset/dashboard/phongtro-market/ |
| Khả năng chi trả | http://localhost:8089/superset/dashboard/phongtro-affordability/ |
| Chất lượng dữ liệu | http://localhost:8089/superset/dashboard/phongtro-quality/ |

Hệ thống gồm 5 Dataset, 30 Chart và 3 Dashboard.

## 6. Dữ liệu kiểm thử

Hai bộ dữ liệu B001 và B002 là dữ liệu giả lập phục vụ kiểm thử chức năng.

Dữ liệu giả lập không đại diện cho thị trường phòng trọ thực tế.

## 7. Cập nhật Dashboard

```bash
python superset/build_dashboards.py --url http://localhost:8089 --user admin --bootstrap
```

## 8. Dừng hệ thống

```bash
docker compose --env-file .env -f docker-compose.yml -f docker-compose.superset.yml stop
```

Lệnh này dừng container nhưng giữ nguyên dữ liệu trong volume.

## 9. Bảo mật

- Không commit mật khẩu, Secret Key và file .env.
- Không commit bản export Superset chưa được kiểm tra.
- Tài khoản bi_reader chỉ được đọc dữ liệu phân tích.
- Tài khoản bi_importer phục vụ nhập liệu.
- Dashboard yêu cầu xác thực và phân quyền phù hợp.

## 10. Trạng thái kiểm thử

Script triển khai đã chạy thành công trên môi trường phát triển Windows.

Cần tiếp tục kiểm thử cài đặt từ bản clone mới và tích hợp dữ liệu thực tế trước khi bàn giao chính thức.
## Tài liệu phân hệ BI

- [Hướng dẫn cài đặt](../../../docs/bi/installation.md)
- [Báo cáo kiểm thử](../../../docs/bi/test_report.md)
- [Tài liệu bàn giao](../../../docs/bi/handover.md)
- [Hợp đồng dữ liệu](../../../docs/bi/data_contract.md)
- [Danh mục KPI](../../../docs/bi/kpi_catalog.md)

Phiên bản hiện tại sử dụng dữ liệu SYNTHETIC DEMO.
Người dùng nhập mật khẩu Superset khi script yêu cầu.