# Đặc tả dữ liệu phòng thuê — 1.0 dự thảo 1

**Schema version dự kiến:** `1.0.0-draft.1` (đã xuất bản thử nghiệm `dataset_version = v20261125_2139`, chờ TV2–4 xác nhận chốt `1.0.0`). Mỗi dòng là một **tin đăng nguồn** ở trạng thái quan sát mới nhất được giữ, không khẳng định một phòng duy nhất hay còn trống.

## Hợp đồng tệp

| Tệp | Dòng và mục đích | Phạm vi chia sẻ |
|---|---|---|
| `listings_all.csv` | Một dòng mới nhất cho mỗi `listing_id`, gồm tin nhận/chờ/loại và quan hệ trùng | Nội bộ, theo quyền nguồn |
| `listings.csv` | `record_status=accepted`; nhóm trùng `confirmed` chỉ một bản đại diện | Cùng một tệp cho TV2, TV3, TV4 khi được phép phát hành |
| `records_to_review.csv` | Tin `needs_review`, mã cờ và lý do | Nội bộ TV1/nhóm kiểm tra |
| `manifest.json` | Phiên bản, phạm vi, nguồn, run liên quan, checksum, số dòng và quy tắc đại diện | Đi cùng mọi bản phát hành |

`listings.csv` là **full export** của tập được công bố tại một thời điểm, không phải delta. Không trộn dữ liệu giả vào bản phát hành thực. Tệp CSV UTF-8 (có BOM hoặc không; bộ đọc phải chấp nhận cả hai), cột theo thứ tự đã chốt, giá trị số không có dấu phân cách hàng nghìn và dùng dấu `.` cho thập phân. Thiếu số/ngày để ô trống, không ghi `0` hay chuỗi `None`. CSV phải được ghi/đọc bằng thư viện CSV vì văn bản và JSON có dấu phẩy, dấu nháy.

## Từ điển cột đề xuất

`B` = bắt buộc trong `listings_all.csv`; `C` = có điều kiện; `T` = tùy chọn. Cột chưa biết để trống, riêng cột `*_json` dùng JSON hợp lệ. Tất cả mã/nhãn tham chiếu dùng danh mục tại `../../data/reference/`.

| Cột | Kiểu / mức | Ý nghĩa, đơn vị và ví dụ |
|---|---|---|
| `listing_id` | string, B | Mã ổn định `source_name:source_record_key`; ví dụ giả lập `source_a:123`. Không dùng số dòng/hash nội dung. |
| `source_name` | string, B | Mã nguồn ổn định theo sổ nguồn, ví dụ `mixstay`. |
| `source_record_key` | string, B | Mã tin/URL chuẩn hóa từ nguồn; không đổi khi giá hoặc tiêu đề đổi. |
| `source_url` | URL string, C | Chỉ xuất khi nguồn cho phép chia sẻ; nếu trống vẫn truy bằng khóa nguồn và `raw_ref`. |
| `raw_ref` | string, B nội bộ | Tham chiếu đến bản gốc/tệp nhận được lưu theo quyền nguồn; không phải URL công khai mặc định. |
| `run_id` | string, B | Mã lần thu nhận/xử lý tạo quan sát này; khác `dataset_version`. |
| `content_hash` | string SHA-256, B | Dấu kiểm nội dung đã chuẩn hóa để phát hiện thay đổi; không làm khóa tin. |
| `collected_at` | ISO 8601 UTC, B | Thời điểm **thực sự** quan sát nguồn; ví dụ `2026-11-25T08:52:52Z`. Chạy lại từ bản lưu không làm mới. |
| `posted_at` | ISO 8601 UTC, T | Thời điểm nguồn ghi có giờ/múi giờ. Nguồn chỉ có ngày thì để trống, không tự gán 00:00. |
| `posted_date` | `YYYY-MM-DD`, T | Ngày đăng/cập nhật khi nguồn chỉ công bố ngày. Không thay `collected_at`. |
| `expires_on` | `YYYY-MM-DD`, T | Ngày hết hạn mà nguồn ghi; không suy ra từ việc tin biến mất. |
| `title` | UTF-8 string, B | Tiêu đề đã giảm số điện thoại/email, vẫn đủ nhận diện tin. |
| `description_clean` | UTF-8 string, T | Mô tả rút gọn/giảm định danh theo quyền nguồn; trống nếu không được lưu. Không thay bản gốc. |
| `room_type` | enum string, C | Mã từ `room_types.csv`, ví dụ `self_contained`. Thiếu hoặc mâu thuẫn thì cờ kiểm tra. |
| `area_m2` | decimal > 0, T | Diện tích m² được nêu rõ. `25` hoặc `25.5`; thiếu để trống. |
| `rent_vnd_month` | integer > 0, C | Giá thuê VND/tháng khi xác định được. Không ghi 0 cho “liên hệ”. |
| `price_basis` | `room/person/unknown`, B | Giá cả phòng, mỗi người hoặc chưa biết. Không tự chia theo sức chứa. |
| `deposit_vnd` | integer ≥ 0, T | Tiền cọc VND nếu nguồn nêu rõ số tiền; miễn cọc xác nhận mới là 0. |
| `deposit_months` | decimal ≥ 0, T | Cọc theo số tháng khi nguồn nêu; chỉ quy tiền khi có cùng cơ sở giá. |
| `fees_json` | JSON object, B | Từng mã phí có `amount`, `unit`, `status`; ví dụ bên dưới. `{}` khi chưa trích xuất, không có nghĩa miễn phí. |
| `amenities_json` | JSON object, B | Mã tiện ích → `true/false/null`; ví dụ bên dưới. `{}` nghĩa chưa biết. |
| `district` | enum string, B | Nhãn `Thanh Xuân`, `Đống Đa`, `Cầu Giấy` theo phạm vi khảo sát; cần đối chiếu địa chỉ tin. |
| `ward` | string, T | Phường được nguồn ghi, không tự chuẩn hóa hành chính mới/cũ nếu thiếu bảng ánh xạ. |
| `address_clean` | string, T | Địa chỉ giảm định danh, loại văn bản giao diện như “Xem bản đồ”; không tự tạo địa chỉ số nhà. |
| `latitude`, `longitude` | decimal, T | Tọa độ phòng/tòa nhà có căn cứ; để trống nếu chỉ biết khu vực. Không dùng `(0,0)`. |
| `geo_confidence` | enum string, B | `confirmed/approximate/area_only/unknown`; mức chính xác, không phải điểm chất lượng chung. |
| `max_occupants` | integer > 0, T | Sức chứa được nêu rõ; không phải số người đang ở. |
| `duplicate_group_id` | string, T | Mã nhóm khi có bằng chứng hoặc ứng viên nghi trùng; phải ổn định. |
| `duplicate_status` | enum string, B | `unique/suspected/confirmed/unknown`. `unique` chỉ là chưa thấy trùng trong tập xét. |
| `is_representative` | boolean `true/false`, B | `true` cho tin độc lập, nghi trùng chưa xác nhận hoặc bản đại diện nhóm `confirmed`. |
| `listing_status` | enum string, B | `expired/unverified_available/unknown`; tình trạng quảng cáo, tách khỏi trạng thái xử lý. |
| `record_status` | enum string, B | `accepted/needs_review/rejected`; quyết định xử lý của TV1. |
| `quality_flags_json` | JSON array, B | Mảng mã từ `quality_flag_catalog.csv`, ví dụ `["UNKNOWN_PRICE_BASIS"]`. |

## Quy ước JSON

```json
{
  "amenities_json": {"air_conditioner": true, "parking": null},
  "fees_json": {
    "electricity": {"amount": 4000, "unit": "vnd_per_kwh", "status": "known"},
    "water": {"amount": null, "unit": null, "status": "unknown"}
  },
  "quality_flags_json": ["UNKNOWN_PRICE_BASIS", "GEO_AREA_ONLY"]
}
```

Đây là **ví dụ giả lập**, không phải một tin thực. `false` tiện ích chỉ khi nguồn phủ định rõ; không nhắc đến = `null`/vắng mã. Trạng thái phí: `known`, `included`, `free`, `unknown`, `not_applicable`. Không cộng phí khác đơn vị; không coi `unknown` là miễn phí.

## Mẫu hợp lệ và mẫu lỗi để thống nhất cách đọc

| Đầu vào giả lập | Kết quả mong đợi |
|---|---|
| “Cho thuê phòng khép kín 25 m², 3,5 triệu/tháng, Đống Đa” | `room_type=self_contained`, `area_m2=25`, `rent_vnd_month=3500000`, `district=Đống Đa`; `price_basis=unknown` nếu không nói giá/phòng hay/người. |
| “1,8 triệu/người/tháng; không có điều hòa” | `rent_vnd_month=1800000`, `price_basis=person`, `amenities_json.air_conditioner=false`. |
| “Giá liên hệ, nước 100k/người” | `rent_vnd_month` trống; giá nước giữ đơn vị người, kỳ thu chưa rõ thì `status=unknown`/cờ; không biến thành 0 hoặc phí tháng. |
| “Bán căn hộ 2N1K tại Cầu Giấy” trong chuyên mục phòng trọ | `record_status=rejected`, `quality_flags_json=["NON_ROOM"]`. |

## Manifest của bản phát hành

`manifest.json` có tối thiểu `schema_version`, `dataset_version`, `released_at`, `export_mode=full`, phạm vi quận/loại tin, `input_run_ids`, trạng thái quyền nguồn, từng tệp với `sha256` và `row_count`, số dòng từng bước, quy tắc chọn bản đại diện và nhãn `real` hoặc `synthetic`. Đã sinh `data/manifest.json` và bản snapshot `data/releases/v20261125_2139/` sau khi vượt qua `pipeline.py --validate`; trạng thái quyền chia sẻ hiện vẫn ở mức mẫu kỹ thuật nội bộ (`internal_technical_sample_pending_written_sharing_approval`).
