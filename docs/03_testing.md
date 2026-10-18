# 3. Tài liệu kiểm thử — Tracking QA

## Chiến lược
- **Kiểm thử đơn vị:** parser, IoU, Kalman/detectors, lỗi đầu vào.
- **Kiểm thử tích hợp:** chạy CLI trên `demo.xml`, kiểm tra 4 đầu ra và không thay đổi đầu vào.
- **Kiểm thử nghiệm thu:** test trên video thực tế với manifest lỗi do reviewer xác nhận.

## Các trường hợp kiểm thử
| ID | Tình huống | Kết quả mong đợi |
|---|---|---|
| TC01 | IoU của hai box | Tính đúng |
| TC02 | CVAT `outside=1` | Bỏ box |
| TC03 | CVAT không có track | Báo ValueError |
| TC04 | BDD JSON có video và track ID | Đọc dữ liệu thành công |
| TC05 | Box di chuyển ổn định | Không báo jump sai trong dữ liệu kiểm thử |
| TC06 | Box nhảy mạnh | Báo BOX_JUMP |
| TC07 | A kết thúc, B xuất hiện gần dự đoán | Báo TRACK_FRAGMENT |
| TC08 | A/B khác class | Không báo fragment |
| TC09 | Hai ID đổi vị trí với lịch sử đủ | Báo ID_SWITCH trong dữ liệu kiểm thử |
| TC10 | CLI demo | Mã thoát 0, sinh đủ 4 file |
| TC11 | CLI demo | Input hash không thay đổi |

## Chạy kiểm thử
```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python track_qa.py --đầu vào demo.xml --format cvat --đầu ra results
start .\results\report.html
```

## Kế hoạch test dataset
Gợi ý 10 video, ~2.000 frame: development 3 video, validation 2, test 5. Tạo manifest khoảng 30 trường hợp có kiểm soát **mỗi loại** trên tập test; giữ cả các trường hợp không lỗi, che khuất, giao nhau. Tách video trước khi tinh chỉnh ngưỡng để tránh rò rỉ test.

## Metrics và điều kiện nghiệm thu
Precision = TP/(TP+FP); Recall = TP/(TP+FN); F1 = 2PR/(P+R); FP/1000 frames. Cần quy định matching event (loại lỗi, ID, khoảng dung sai frame; một ground-truth event khớp tối đa một cảnh báo). Không coi số alert trong demo là độ chính xác. Nghiệm thu kỹ thuật: unit/integration PASS, đủ 4 đầu ra, giữ nguyên đầu vào, mỗi cảnh báo có frame/ID/lý do; chất lượng thuật toán đánh giá riêng trên test set.
