# Tracking QA Tool — Công cụ kiểm tra chất lượng gán nhãn theo dõi đối tượng

Công cụ phát hiện **các trường hợp nghi vấn** về **đổi ID**, **đứt quãng quỹ đạo** và **hộp giới hạn nhảy bất thường** trong dữ liệu Multi-Object Tracking. Công cụ **không tự sửa nhãn**.

## Định dạng được hỗ trợ

| Dữ liệu | Định dạng | Ghi chú |
|---|---|---|
| CVAT for Video | XML | Sử dụng các đối tượng được gán nhãn bằng chế độ Track |
| BDD100K MOT | JSON | Mỗi lần phân tích một video, có ID đối tượng theo frame |
| nuScenes Tracking 3D | JSON + manifest JSON | Cần metadata thứ tự frame, scene và thời gian |

## Cài đặt và chạy giao diện

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Mở `http://localhost:8501`, tải lên annotation, chọn đúng định dạng rồi nhấn **Bắt đầu kiểm tra**. Có thể lọc cảnh báo và tải báo cáo CSV, JSON, HTML, ZIP.

## Chạy bằng dòng lệnh

```powershell
python track_qa.py --input annotations.xml --format cvat --output results
python track_qa.py --input video.json --format bdd --output results_bdd
python track_qa.py --input results.json --format nuscenes --manifest manifest.json --output results_nuscenes
```

**Lưu ý:** `--format` là tham số kỹ thuật, giữ nguyên `cvat`, `bdd`, `nuscenes`. Kết quả gồm `issues.csv`, `issues.json`, `summary.json`, `report.html`; các tên file và khóa JSON giữ nguyên để tương thích với chương trình khác.

## Các phương pháp phát hiện

- **Box nhảy:** Kalman Filter và khoảng cách Mahalanobis cho dữ liệu 2D; với nuScenes dùng dự đoán vận tốc không đổi và các ngưỡng vị trí/tốc độ/yaw/kích thước.
- **Đứt quãng:** so sánh hai đoạn quỹ đạo cùng loại bằng dự đoán vị trí và độ gần.
- **Đổi ID:** ghép vị trí dự đoán và quan sát bằng thuật toán Hungarian, đánh dấu các trường hợp hoán đổi ID nghi vấn.

Điểm bất thường **không phải xác suất lỗi**. Các cảnh báo cần được đối chiếu với video và xác nhận thủ công. Đối với CVAT, cần lưu ý dữ liệu keyframe có thể chưa được nội suy đầy đủ. Các frame trong XML được đánh số từ 0.

## Tài liệu

- [Hướng dẫn Streamlit](STREAMLIT_GUIDE.md)
- [Hướng dẫn nuScenes](NUSCENES_GUIDE.md)
- [Sơ đồ kiến trúc](docs/01_architecture.md)
- [Đặc tả và thiết kế](docs/02_specification_design.md)
- [Kiểm thử](docs/03_testing.md)

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
```
