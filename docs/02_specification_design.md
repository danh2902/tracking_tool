# 2. Đặc tả và thiết kế — Tracking QA

## Phạm vi
QA annotation tracking 2D, phát hiện **nghi vấn** `ID_SWITCH`, `TRACK_FRAGMENT`, `BOX_JUMP`. Không tự sửa nhãn, không chạy detector/ReID, không đảm bảo phát hiện mọi lỗi.

## Yêu cầu chức năng
| ID | Chức năng | Cài đặt |
|---|---|---|
| FR01 | Đọc CVAT for video XML track/box | `parse_cvat` |
| FR02 | Đọc BDD100K MOT JSON list of frames | `parse_bdd` |
| FR03 | Phát hiện box jump | `jump_check` |
| FR04 | Tìm track bị phân mảnh | `fragmentation_check` |
| FR05 | Phát hiện đổi ID theo cặp | `switch_check` |
| FR06 | Xuất CSV/JSON/HTML/summary | `report` |
| FR07 | Điều chỉnh ngưỡng từ CLI | `argparse` |

## Thiết kế dữ liệu
`Box(frame:int, tid:str, label:str, xyxy:tuple, occluded:bool)`; các box có `outside=1` hoặc diện tích không hợp lệ bị loại. Với BDD, ID có tiền tố video. Dữ liệu cần là **một video mỗi lần chạy**. CVAT XML keyframe chưa được nội suy tự động.

## Thiết kế thuật toán
**BOX_JUMP:** Kalman trạng thái 8D `[cx,cy,w,h,vx,vy,vw,vh]`. Dự đoán rồi tính Mahalanobis bình phương `d²=(z-Hx)^T S^-1(z-Hx)`. Báo khi đủ lịch sử, hai frame liên tiếp, không occluded và `d² > chi2.ppf(jump_confidence,4)`.

**TRACK_FRAGMENT:** với hai ID khác nhau cùng class, `gap=start(B)-end(A)-1` thuộc `[0,max_gap]`; ngoại suy A theo vận tốc gần nhất đến đầu B; lọc theo khoảng cách tâm chuẩn hóa và IoU. Trả về cặp ứng viên, không tự merge.

**ID_SWITCH:** với các ID cùng xuất hiện tại `t-1` và `t`, cùng class, đủ lịch sử: ngoại suy vị trí, xây ma trận chi phí khoảng cách tâm chuẩn hóa, ghép Hungarian; báo hoán đổi cặp đối xứng nếu `identity_cost-swap_cost >= switch_min_gain` và cross-match đủ gần. Không phát hiện mọi trường hợp đổi ID.

## CLI
```powershell
python track_qa.py --input demo.xml --format cvat --output results
```
Các ngưỡng mặc định: `--max-gap 12`, `--fragment-max-dist 0.8`, `--fragment-min-iou 0.1`, `--switch-max-dist 0.8`, `--switch-min-gain 0.3`, `--min-history 3`, `--jump-confidence 0.999`.

## Output
`issues.json` và `issues.csv`: `type,frame,track_id,other_id,score,reason,details`; `summary.json`: thống kê; `report.html`: bảng để reviewer xem. Score không phải xác suất. Frame lấy theo chỉ số annotation.

## Giới hạn/rủi ro
Camera di chuyển, phối cảnh, occlusion, tăng giảm tốc và sparse keyframes có thể gây false positives/negatives. Track fragmentation có thể sinh nhiều cặp ứng viên. Cần reviewer xác nhận mọi cảnh báo.
