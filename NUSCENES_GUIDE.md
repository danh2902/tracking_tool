# Hướng dẫn kiểm tra dữ liệu nuScenes Tracking 3D

## Dữ liệu đầu vào

Cần **hai tệp JSON**:

1. `results.json`: dữ liệu theo định dạng kết quả tracking nuScenes, gồm `results` ánh xạ `sample_token` tới danh sách đối tượng. Mỗi đối tượng có `tracking_id`, `tracking_name`, `translation` (x, y, z theo mét), `size` (rộng, dài, cao theo mét), `rotation` (quaternion theo thứ tự w, x, y, z).
2. `manifest.json`: thông tin thứ tự frame, scene và timestamp của từng sample. Có thể dùng danh sách JSON hoặc object có khóa `samples`.

Ví dụ:

```json
[
  {"sample_token": "sample-0", "scene_token": "scene-1", "frame_index": 0, "timestamp": 0.0},
  {"sample_token": "sample-1", "scene_token": "scene-1", "frame_index": 1, "timestamp": 0.5}
]
```

`timestamp` tính bằng **giây**; có thể thay bằng `timestamp_us` tính bằng micro giây. `frame_index` bắt đầu từ 0 và tăng theo từng sample trong scene. **Không sắp xếp `sample_token` theo chữ cái để suy ra thứ tự thời gian.** Dữ liệu vị trí phải ở hệ tọa độ toàn cục của nuScenes.

## Chạy

```powershell
python -m pip install -r requirements.txt
python track_qa.py --format nuscenes --input results.json --manifest manifest.json --output results_nuscenes
python -m streamlit run app.py
```

Trên giao diện, chọn `nuscenes`, tải file tracking JSON và manifest rồi nhấn **Bắt đầu kiểm tra**.

## Giới hạn

- Công cụ kiểm tra kết quả tracking đã có, **không chạy mô hình nhận diện/tracking mới**.
- Phép đo chuyển động 3D hiện dùng mô hình vận tốc không đổi và các ngưỡng gần đúng, chưa phải Kalman 3D đầy đủ hoặc IoU 3D.
- Mỗi cảnh báo phải được kiểm tra thủ công trước khi kết luận sai nhãn.
