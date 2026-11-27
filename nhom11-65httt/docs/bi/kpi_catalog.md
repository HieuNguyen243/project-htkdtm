# DANH MỤC KPI - PHÂN HỆ BUSINESS INTELLIGENCE

## 1. Thông tin chung

- Đề tài: Hệ thống phân tích thị trường phòng trọ hỗ trợ sinh viên lựa chọn nơi ở.
- Nhóm: 11 - 65HTTT.
- Người thực hiện: Trần Thị Minh Thư.
- Nhiệm vụ: TV2-04.
- Phiên bản: 1.0.
- Trạng thái: Đặc tả thiết kế.

## 2. Nguyên tắc tính KPI

- Chỉ sử dụng dữ liệu từ batch nhập thành công.
- Mỗi tin đăng hiện tại được tính tối đa một lần.
- Không trộn dữ liệu thực và dữ liệu giả lập.
- Không trộn giá theo phòng và giá theo người.
- Không chuyển dữ liệu thiếu thành 0.
- Hiển thị số lượng mẫu khi phân tích giá.
- Khi mẫu số bằng 0, tỷ lệ trả về NULL.
- Số lượng tin đăng không đại diện cho toàn bộ số phòng trọ trên thị trường.

## 3. Dashboard 1 - Giá chào thuê

| Mã KPI | Tên KPI | Công thức |
|---|---|---|
| P01 | Tổng số tin đăng | COUNT(DISTINCT listing_id) |
| P02 | Số tin có giá hợp lệ | Đếm tin có giá dương và đúng price_basis |
| P03 | Trung vị giá thuê | PERCENTILE_CONT(0.5) |
| P04 | Phân vị P25 | PERCENTILE_CONT(0.25) |
| P05 | Phân vị P75 | PERCENTILE_CONT(0.75) |
| P06 | Giá thuê thấp nhất | MIN(rent_vnd_month) |
| P07 | Giá thuê cao nhất | MAX(rent_vnd_month) |
| P08 | Giá thuê trên m2 | rent_vnd_month / area_m2 |
| P09 | Trung vị giá thuê trên m2 | Trung vị của P08 |

### Quy tắc

- Giá thuê sử dụng đơn vị VND/tháng.
- Chỉ tính các thống kê giá trên tập giá hợp lệ.
- Tính riêng theo price_basis.
- Giá thuê trên m2 chỉ áp dụng cho giá theo phòng.
- Diện tích phải lớn hơn 0.
- P25 và P75 biểu diễn khoảng phân bố giữa của dữ liệu.
- Hiển thị số lượng mẫu bên cạnh trung vị.

### Biểu đồ dự kiến

- Big Number: Tổng số tin đăng.
- Big Number: Số tin có giá hợp lệ.
- Big Number: Trung vị giá thuê.
- Big Number: P25 và P75.
- Bar Chart: Trung vị giá thuê theo quận.
- Histogram: Phân bố giá thuê.
- Scatter Plot: Quan hệ diện tích và giá thuê.
- Table: Danh sách tin đăng.

## 4. Dashboard 2 - Khả năng chi trả

| Mã KPI | Tên KPI | Công thức |
|---|---|---|
| A01 | Tổng số tin trong phạm vi | COUNT(DISTINCT listing_id) |
| A02 | Số tin có giá hợp lệ | Đếm tin có giá sử dụng được |
| A03 | Số tin trong ngân sách | Đếm tin có giá nhỏ hơn hoặc bằng ngân sách |
| A04 | Tỷ lệ tin trong ngân sách | A03 / A02 * 100 |
| A05 | Độ phủ thông tin giá | A02 / A01 * 100 |
| A06 | Số tin thiếu giá sử dụng được | A01 - A02 |

### Mức ngân sách dự kiến

- 2.000.000 VND/tháng.
- 3.000.000 VND/tháng.
- 4.000.000 VND/tháng.
- 5.000.000 VND/tháng.

### Quy tắc

- Ngân sách được so sánh theo cùng price_basis.
- Không đưa tin thiếu giá vào mẫu số A04.
- Tin thiếu giá vẫn được tính khi đo độ phủ A05.
- Giá bằng ngân sách được tính là phù hợp.
- Giá thuê chưa bao gồm chi phí sinh hoạt nếu chưa có đủ thông tin phí.
- Không coi phí chưa biết là 0.
- Tiền đặt cọc được phân tích riêng.

### Biểu đồ dự kiến

- Big Number: Số tin trong ngân sách.
- Big Number: Tỷ lệ tin trong ngân sách.
- Big Number: Độ phủ thông tin giá.
- Bar Chart: Tỷ lệ phù hợp theo quận.
- Bar Chart: So sánh các mức ngân sách.
- Table: Danh sách tin phù hợp.

## 5. Dashboard 3 - Chất lượng dữ liệu

| Mã KPI | Tên KPI | Công thức |
|---|---|---|
| Q01 | Tỷ lệ thiếu giá | Số tin thiếu giá / tổng số tin * 100 |
| Q02 | Tỷ lệ thiếu diện tích | Số tin thiếu diện tích / tổng số tin * 100 |
| Q03 | Tỷ lệ thiếu thông tin phí | Số tin thiếu phí theo quy tắc / tổng số tin * 100 |
| Q04 | Tỷ lệ thiếu địa chỉ | Số tin thiếu địa chỉ / tổng số tin * 100 |
| Q05 | Độ phủ tọa độ | Số tin có cặp tọa độ hợp lệ / tổng số tin * 100 |
| Q06 | Tỷ lệ nghi ngờ trùng | Số tin suspected / tổng số tin * 100 |
| Q07 | Độ mới dữ liệu | Thời điểm đánh giá - collected_at |
| Q08 | Số dòng đầu vào | total_rows của batch |
| Q09 | Số dòng nhập hợp lệ | accepted_rows của batch |
| Q10 | Số dòng bị từ chối | rejected_rows của batch |
| Q11 | Tỷ lệ nhập hợp lệ | accepted_rows / total_rows * 100 |
| Q12 | Số lỗi nhập dữ liệu | COUNT(issue_id) |

### Quy tắc

- Dữ liệu thiếu gồm NULL hoặc chuỗi rỗng đối với trường văn bản.
- Phí thiếu được xác định theo danh mục phí áp dụng.
- Phí unknown hoặc thiếu trường bắt buộc được coi là thiếu thông tin.
- Phí free, included và not_applicable không tự động coi là thiếu.
- Sử dụng nhãn trùng lặp do TV1 cung cấp.
- Không tự suy diễn tọa độ hoặc trạng thái tin.
- Phân biệt lỗi nhập với số dòng bị từ chối.
- Thống kê tin bị loại từ TV1 cần manifest hoặc dữ liệu đối soát được phép sử dụng.

### Biểu đồ dự kiến

- Big Number: Tổng số tin đăng.
- Big Number: Tỷ lệ thiếu giá.
- Big Number: Tỷ lệ thiếu diện tích.
- Bar Chart: Tỷ lệ thiếu theo trường dữ liệu.
- Bar Chart: Chất lượng theo nguồn.
- Pie Chart: Phân bố geo_confidence.
- Bar Chart: Phân bố duplicate_status.
- Table: Lịch sử nhập dữ liệu và lỗi.

## 6. Bộ lọc dashboard

- Nguồn dữ liệu: source_name.
- Quận: district.
- Loại phòng: room_type.
- Đơn vị tính giá: price_basis.
- Đợt dữ liệu: batch_id.
- Phạm vi phân tích: hiện tại hoặc lịch sử.
- Ngân sách: áp dụng cho Dashboard 2.

## 7. Nguồn dữ liệu KPI

| Dashboard | View hoặc bảng sử dụng |
|---|---|
| Giá chào thuê | analytics.vw_market_price |
| Khả năng chi trả | analytics.vw_affordability |
| Chất lượng dữ liệu | analytics.vw_listing_quality |
| Kết quả nhập | View tổng hợp từ ingest_batch |
| Lỗi nhập | View tổng hợp từ import_issue |

## 8. Tiêu chí nghiệm thu

- KPI có công thức và mẫu số rõ ràng.
- Các chỉ số giá được phân tách theo price_basis.
- Không tính sai do dữ liệu thiếu.
- Bộ lọc hoạt động nhất quán.
- Không nhân đôi số tin do phép JOIN.
- Kết quả dashboard khớp với SQL đối soát.
- Dữ liệu giả lập được ghi nhãn rõ ràng.

## 9. Tài liệu tham chiếu

- data_contract.md
- erd.md
- data_dictionary.md
- Nhiệm vụ chi tiết TV2 - CSDL và BI.

## 10. Trạng thái

Đã xây dựng danh mục KPI dự kiến.
Chưa kiểm chứng bằng PostgreSQL và Apache Superset.