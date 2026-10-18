# 3. Tài liệu kiểm thử — Tracking QA

## Chiến lược
- **Unit tests:** parser, IoU, Kalman/detectors, lỗi input.
- **Integration:** chạy CLI trên `demo.xml`, kiểm tra 4 output và không thay đổi input.
- **Acceptance:** test trên video thực tế với manifest lỗi do reviewer xác nhận.

## Test cases
| ID | Tình huống | Kết quả mong đợi |
|---|---|---|
| TC01 | IoU của hai box | Tính đúng |
| TC02 | CVAT `outside=1` | Bỏ box |
| TC03 | CVAT không có track | Báo ValueError |
| TC04 | BDD JSON có video và track ID | Parse thành công |
| TC05 | Box di chuyển ổn định | Không báo jump sai trong fixture |
| TC06 | Box nhảy mạnh | Báo BOX_JUMP |
| TC07 | A kết thúc, B xuất hiện gần dự đoán | Báo TRACK_FRAGMENT |
| TC08 | A/B khác class | Không báo fragment |
| TC09 | Hai ID đổi vị trí với lịch sử đủ | Báo ID_SWITCH trong fixture |
| TC10 | CLI demo | Exit code 0, sinh đủ 4 file |
| TC11 | CLI demo | Input hash không thay đổi |

## Chạy kiểm thử
```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python track_qa.py --input demo.xml --format cvat --output results
start .\results\report.html
```

## Kế hoạch test dataset
Gợi ý 10 video, ~2.000 frame: development 3 video, validation 2, test 5. Tạo manifest khoảng 30 trường hợp có kiểm soát **mỗi loại** trên tập test; giữ cả các trường hợp không lỗi, che khuất, giao nhau. Tách video trước khi tinh chỉnh ngưỡng để tránh rò rỉ test.

## Metrics và điều kiện nghiệm thu
Precision = TP/(TP+FP); Recall = TP/(TP+FN); F1 = 2PR/(P+R); FP/1000 frames. Cần quy định matching event (loại lỗi, ID, khoảng dung sai frame; một ground-truth event khớp tối đa một cảnh báo). Không coi số alert trong demo là độ chính xác. Nghiệm thu kỹ thuật: unit/integration PASS, đủ 4 output, giữ nguyên input, mỗi cảnh báo có frame/ID/lý do; chất lượng thuật toán đánh giá riêng trên test set.
