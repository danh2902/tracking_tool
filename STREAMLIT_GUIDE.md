# Tracking QA Dashboard (Streamlit)

## Cài đặt trên Windows / PowerShell

Đặt `app.py`, `requirements.txt` cạnh `track_qa.py` và `requirements.txt` trong repository hiện có.

```powershell
cd E:\tracking_qa_tool_1\tracking_qa_tool
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Trình duyệt mở `http://localhost:8501`. Upload **CVAT for video XML** hoặc **BDD100K MOT JSON của một video**, chọn đúng định dạng, điều chỉnh ngưỡng và bấm **Chạy Tracking QA**. Xem bảng cảnh báo, lọc theo loại lỗi và tải ZIP gồm CSV/JSON/HTML/summary.

## Ghi chú

- Giao diện gọi `track_qa.py` hiện có bằng Python subprocess, không thay đổi thuật toán.
- Đầu vào và báo cáo trung gian đặt trong thư mục tạm; file gốc không bị sửa.
- Chỉ dùng trên máy cá nhân/local, không đưa lên server công khai khi chưa bổ sung xác thực và giới hạn tài nguyên.
- Giới hạn mỗi lần chạy 300 giây; với dữ liệu lớn nên chia theo video.
- XML chỉ có keyframe có thể thiếu dữ liệu chuyển động; cần xuất dense annotation để đánh giá tốt hơn.
- Không hiển thị video/overlay vì chưa nhận dữ liệu frame hình ảnh.
- Đây là các cảnh báo heuristic; không tự động sửa annotation.

## Cập nhật GitHub

```powershell
git add app.py requirements.txt STREAMLIT_GUIDE.md
git commit -m "Add Streamlit dashboard for tracking QA"
git push
```
