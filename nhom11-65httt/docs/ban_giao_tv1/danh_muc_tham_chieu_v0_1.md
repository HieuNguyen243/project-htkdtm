# Danh mục tham chiếu TV1 — dự thảo 0.1

Sáu CSV trong `../../data/reference/` là danh mục **dự thảo**, mở bằng UTF-8 BOM. Workbook `reference_catalogs_v0_1_draft.xlsx` chứa cùng sáu bảng để xem và góp ý. Mã ổn định đề xuất cần TV2–4 xác nhận trước khi chốt schema 1.0. Dấu `|` trong `source_aliases` và `recognition_examples` chỉ phân tách ví dụ cách viết, không phải dữ liệu JSON để tự tách trong CSV tin.

| Tệp | Khóa và cách dùng |
|---|---|
| `areas.csv` | `area_code` cho ba khu vực nghiên cứu. Tên quận là nhãn phạm vi nhóm đã chọn; việc đổi địa giới/phường phải có bảng ánh xạ và kiểm tra địa chỉ nguồn, không tự suy. |
| `room_types.csv` | `room_type_code`, `include_in_scope`. Căn hộ/nhà nguyên căn/loại khác vẫn có mã để ghi lý do loại, không được đưa vào tập phòng thuê. |
| `amenity_catalog.csv` | `amenity_code` để dùng trong `amenities_json`. Từ khóa là ví dụ nhận diện; phải xử lý phủ định và ngữ cảnh. |
| `fee_catalog.csv` | `fee_code`, đơn vị có thể có trong `fees_json`. Không tự cộng mức theo kWh, theo người, theo phòng. |
| `quality_flag_catalog.csv` | `flag_code`, mức kiểm tra và ảnh hưởng. `review` không tự đồng nghĩa loại tin; quyết định nằm ở `record_status`. |
| `campuses.csv` | Mỗi cơ sở học một `campus_id`; hai địa chỉ hiện được ghi từ trang trường. Tọa độ để trống, `geo_confidence=unknown`, nên TV3/TV4 chưa tính hoặc hiển thị khoảng cách từ các tọa độ này. |

Địa chỉ cơ sở chính Trường Đại học Thủy lợi lấy từ [báo cáo công khai của trường](https://tlu.edu.vn/Portals/0/572bcdhtl.pdf), ghi 175 Tây Sơn, phường Kim Liên, Hà Nội. Địa chỉ Trường Đại học Giao thông Vận tải lấy từ [trang Khoa CNTT của trường](https://fit.utc.edu.vn/gioi-thieu/co-cau-to-chuc/van-phong-khoa), ghi số 3 Cầu Giấy, phường Láng, Hà Nội. Kiểm tra ngày 25/11/2026. Hai địa chỉ là thông tin cơ sở trường, **không** phải vị trí phòng trọ hay tọa độ đã xác minh.

Trước khi phát hành, TV1 phải kiểm tra khóa duy nhất, mã tham chiếu trong `listings.csv`, phiên bản danh mục và checksum. Khi đổi nghĩa hoặc xóa mã, tăng phiên bản và thông báo TV2–4; không thay âm thầm một mã đã dùng trong bản phát hành.
