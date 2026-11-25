# Hướng dẫn gán nhãn và đánh giá TV1 — dự thảo 0.1

**Trạng thái:** quy trình sẵn để dùng; đã khởi tạo tập đối chứng thực bước đầu tại `src/backend/bot/fixtures/real_eval_sample.json` (18 tin trích xuất chia `development`/`holdout`, 10 cặp trùng/không trùng, đã che PII) và tính P/R/F1 thực đo qua `evaluate.py` (kết quả cập nhật trong `bao_cao_chat_luong_2026-11-25.md`). Không chọn 9 tin lịch sử của Thuephongtro như thể phòng còn trống.

## Đơn vị và bảng nhãn

Một hàng nhãn trích xuất là một `listing_id` gắn với `raw_ref`, `run_id` và phiên bản bản gốc; lưu riêng khỏi CSV công bố. Cột gợi ý: `listing_id,raw_ref,source_name,split,transaction_label,property_label,price_vnd_month_gold,price_basis_gold,area_m2_gold,deposit_vnd_gold,deposit_months_gold,fees_json_gold,amenities_json_gold,district_gold,listing_status_gold,annotation_note,annotator,reviewer,rule_version`. `split` là `development` hoặc `holdout`. Đáp án thiếu thực sự để trống/JSON null, không điền 0.

Nhãn loại giao dịch: `rent_offer/sale/seeking/unclear`. Nhãn tài sản: mã trong `room_types.csv` hoặc `unclear`. Chỉ `rent_offer` với loại phòng thuộc phạm vi mới là ứng viên tập sạch. Nếu tiêu đề và mô tả mâu thuẫn, ghi `unclear` và nêu đúng đoạn chứng cứ; không ưu tiên một số bất kỳ.

## Quy tắc gán nhãn thuộc tính

| Trường | Đáp án đúng và trường hợp không chắc |
|---|---|
| Giá | Gán số VND/tháng và `room/person/unknown` riêng. “3,5 triệu/tháng” rõ giá nhưng chưa rõ theo phòng/người thì giữ `unknown`. Nhiều giá cho nhiều phòng không xác định phòng của tin → `ambiguous`, không chọn một. |
| Diện tích | Chỉ số m² của phòng/chỗ thuê được nêu rõ. Diện tích cả nhà/tòa không phải diện tích phòng. |
| Cọc | Gán tiền và số tháng ở hai cột độc lập; không suy tiền từ số tháng nếu cơ sở giá không rõ. |
| Phí | Mỗi mã phí cần `amount/unit/status`; “điện 4k/số” chỉ gán `vnd_per_kwh` khi ngữ cảnh “số điện” rõ. |
| Tiện ích | `true` khi có; `false` khi phủ định rõ; `null` khi không nhắc. “Không chung chủ” không phải một tiện ích điện/nước. |
| Khu vực | Đối chiếu quận từ địa chỉ tin, không chỉ từ trang danh sách. Mâu thuẫn ghi `unclear`. |
| Hiệu lực | Ngày hết hạn đã qua → `expired`; chưa qua → `unverified_available`, không gán “còn phòng” nếu chưa được xác nhận. |

Chỉ giữ đoạn chứng cứ tối thiểu cần chấm, đã che số điện thoại/email. Người chấm thứ hai kiểm tra chéo các ca mâu thuẫn và một phần ngẫu nhiên của mỗi nguồn; bất đồng được ghi và phân xử trước khi khóa holdout.

## Chọn mẫu và chia tập

Chọn từ nguồn có căn cứ sử dụng, phủ cả ba quận, nhiều cách ghi giá/diện tích/phí, tin thiếu trường, tin sai loại và tin nghi trùng. Chia theo `listing_id`; các quan sát cùng mã và các tin thuộc cùng nhóm nghi trùng phải vào **cùng split**, tránh rò rỉ nội dung từ development sang holdout. Khóa tập holdout trước khi điều chỉnh quy tắc lần cuối. Ghi cách lấy mẫu, số tin và nguồn; không suy kết quả trên mẫu hẹp thành độ chính xác toàn thị trường.

Đối với trùng, lập bảng cặp `left_listing_id,right_listing_id,gold_same_room,evidence,split,annotator,reviewer`. Có cả cặp trùng và không trùng, gồm các cặp cùng giá/khu vực nhưng khác phòng. Không dùng cùng một cặp hoặc cặp đảo chiều `(B,A)` ở hai split. Chỉ `confirmed` khi bằng chứng đủ theo quy tắc; còn lại `suspected`/`unknown`.

## Cách tính chỉ số

Chấm **từng trường**: giá, cơ sở giá, diện tích, từng loại phí; đúng phải khớp giá trị và đơn vị/cơ sở. Với một trường:

- `TP`: dự đoán có giá trị, gold có giá trị và khớp đầy đủ.
- `FP`: dự đoán có nhưng gold thiếu, hoặc dự đoán sai giá trị/đơn vị.
- `FN`: gold có nhưng không dự đoán hoặc dự đoán sai. Một dự đoán sai khi gold có đóng góp cả `FP` và `FN`.
- Cả hai thiếu: `TN`, **không** cộng vào TP.

`Precision = TP/(TP+FP)`, `Recall = TP/(TP+FN)`, `F1 = 2TP/(2TP+FP+FN)`. Mẫu số 0 báo `N/A` cùng `n`, không gọi là 100%. Có gold dương nhưng không dự đoán thì recall/F1 = 0. Báo `n` đủ điều kiện và số giá trị gold dương của từng trường.

Với cặp trùng, precision = số cặp **dự đoán trùng** và đúng / mọi cặp dự đoán trùng. Không có cặp dự đoán trùng → `N/A`, không báo 100%. Recall chỉ báo khi tập cặp đối chứng bao phủ đúng quần thể cặp cần đo; nếu chỉ chọn ứng viên hẹp, nêu giới hạn và không suy recall toàn thị trường.

Mục tiêu F1 ≥ 0,85 và precision trùng ≥ 0,90 từ đề cương chỉ được đối chiếu **sau khi có mẫu đối chứng thực đủ**. Báo lỗi cụ thể, quy mô mẫu, phiên bản quy tắc và `dataset_version` tương ứng. Không tạo nhãn thuận lợi để đạt mục tiêu.
