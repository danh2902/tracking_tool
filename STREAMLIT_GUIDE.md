# Hướng dẫn sử dụng giao diện Streamlit

## Cài đặt

Đặt `app.py`, `track_qa.py`, `nuscenes_qa.py` và `requirements.txt` trong cùng thư mục.

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Truy cập `http://localhost:8501`.

## Quy trình

1. Tải lên file CVAT XML, BDD100K MOT JSON hoặc nuScenes Tracking JSON.
2. Chọn định dạng tương ứng; với nuScenes cần tải thêm `manifest.json`.
3. Điều chỉnh ngưỡng ở thanh bên nếu cần.
4. Nhấn **Bắt đầu kiểm tra**.
5. Xem thống kê, lọc cảnh báo và tải báo cáo ZIP/CSV/HTML.

## Lưu ý

- Giao diện gọi `track_qa.py` bằng tiến trình Python và không thay đổi file đầu vào.
- Các báo cáo trung gian được lưu tạm; mỗi lần chạy giới hạn 300 giây.
- Cảnh báo không đồng nghĩa với lỗi đã được xác nhận.
- Ứng dụng chưa có chức năng xem trực tiếp video và bounding box trên từng frame.
- Khi triển khai công khai cần chú ý giới hạn dung lượng file, thời gian xử lý và dữ liệu nhạy cảm.
