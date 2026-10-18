# 1. Sơ đồ kiến trúc — Tracking QA Tool

```mermaid
flowchart TD
    A[CVAT XML] --> UI[Giao diện Streamlit hoặc CLI]
    B[BDD100K MOT JSON] --> UI
    C[nuScenes Tracking JSON và manifest] --> UI
    UI --> P[Bộ đọc và chuẩn hóa dữ liệu]
    P --> D{Loại dữ liệu}
    D --> E[Kiểm tra quỹ đạo 2D]
    D --> F[Kiểm tra quỹ đạo 3D]
    E --> G[Đổi ID / Đứt quãng / Box nhảy]
    F --> G
    G --> H[Tổng hợp cảnh báo]
    H --> I[Báo cáo CSV / JSON / HTML / ZIP]
    I --> K[Người kiểm tra xác minh trên CVAT hoặc video]
```

**Luồng xử lý:** nhập annotation → kiểm tra cấu trúc → gom đối tượng theo quỹ đạo → phân tích chuyển động → sinh cảnh báo → xuất báo cáo. Tệp gốc không bị sửa đổi.

**Công nghệ:** Python, NumPy, SciPy, Streamlit và pandas. Phân tích annotation không bắt buộc có GPU. Giao diện Streamlit gọi công cụ dòng lệnh và hiển thị kết quả.

**Lưu ý:** Dữ liệu nuScenes cần manifest chứa thứ tự frame và timestamp; dữ liệu 2D và 3D được xử lý bằng các phép kiểm tra khác nhau.
