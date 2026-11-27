# HƯỚNG DẪN CÀI ĐẶT PHÂN HỆ POSTGRESQL VÀ BI

## 1. Yêu cầu môi trường

- Git.
- Docker Desktop đang hoạt động.
- Docker Compose.
- Python 3.12.
- Git Bash đối với Windows.
- Các cổng 5433 và 8089 chưa bị sử dụng.

## 2. Clone repository

```bash
git clone -b nhom11-65httt https://github.com/HieuNguyen243/project-htkdtm.git
cd project-htkdtm/nhom11-65httt/src/backend/bi
```

Thực hiện sau khi mã nguồn TV2 đã được merge vào nhánh nhóm.

## 3. Cấu hình môi trường

```bash
cp .env.example .env
```

Mở file .env và cấu hình các biến:

- POSTGRES_PASSWORD
- DB_PASSWORD
- BI_READER_PASSWORD
- SUPERSET_DB_PASSWORD
- SUPERSET_SECRET_KEY
- SUPERSET_USER
- SUPERSET_PASSWORD

Giữ nguyên cấu hình host, port và database mặc định nếu không có xung đột.

Tạo Secret Key:

```bash
py -3.12 -c "import secrets; print(secrets.token_hex(48))"
```

Sao chép kết quả vào SUPERSET_SECRET_KEY.

Không đưa file .env hoặc mật khẩu lên GitHub.

## 4. Triển khai hệ thống

```bash
bash setup_bi.sh
```

Script thực hiện:

1. Khởi tạo môi trường Python.
2. Cài đặt thư viện.
3. Khởi động PostgreSQL.
4. Tạo schema, bảng, ràng buộc và phân quyền.
5. Import dữ liệu kiểm thử.
6. Tạo Analytics Views.
7. Khởi tạo Superset.
8. Tạo Dataset, Chart và Dashboard.

Khi được yêu cầu Superset password, nhập mật khẩu tương ứng với SUPERSET_PASSWORD.

Nếu được yêu cầu BI Reader password, nhập BI_READER_PASSWORD.

Kết quả thành công:

```text
BI SETUP COMPLETED
```

## 5. Truy cập hệ thống

- Superset: http://localhost:8089
- PostgreSQL: localhost:5433
- Database: phongtro_bi_demo

Dashboard:

- http://localhost:8089/superset/dashboard/phongtro-market/
- http://localhost:8089/superset/dashboard/phongtro-affordability/
- http://localhost:8089/superset/dashboard/phongtro-quality/

Đăng nhập Superset bằng tài khoản đã cấu hình.

## 6. Kiểm tra hoạt động

```bash
docker ps
curl -s http://localhost:8089/health
```

Health API phải trả về OK.

## 7. Dừng hệ thống

```bash
docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.superset.yml stop
```

Không sử dụng down -v nếu muốn giữ lại dữ liệu và Dashboard.

## 8. Lưu ý

Phiên bản mặc định sử dụng dữ liệu SYNTHETIC DEMO để phục vụ phát triển và kiểm thử.

Dữ liệu thực tế chỉ được nhập sau khi có bộ dữ liệu hợp lệ và được phép sử dụng từ TV1.

Không chia sẻ mật khẩu, Secret Key hoặc dữ liệu nguồn chưa được cấp quyền.