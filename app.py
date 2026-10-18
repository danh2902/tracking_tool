"""Giao diện Streamlit cho công cụ kiểm tra chất lượng dữ liệu tracking."""
import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / 'track_qa.py'

st.set_page_config(page_title='Bảng điều khiển QA Tracking', page_icon='🔎', layout='wide')
st.title('🔎 Kiểm tra chất lượng dữ liệu Tracking')
st.caption('Kiểm tra đổi ID · Đứt quãng quỹ đạo · Bounding box nhảy bất thường — chỉ cảnh báo, không sửa nhãn.')

with st.sidebar:
    st.header('Cấu hình QA')
    max_gap = st.slider('Khoảng gián đoạn tối đa (frame)', 0, 60, 12)
    fragment_max_dist = st.slider('Phân mảnh: khoảng cách chuẩn hóa tối đa', 0.0, 5.0, 0.8, 0.05)
    fragment_min_iou = st.slider('Phân mảnh: IoU tối thiểu', 0.0, 1.0, 0.1, 0.05)
    switch_max_dist = st.slider('Đổi ID: khoảng cách chuẩn hóa tối đa', 0.0, 5.0, 0.8, 0.05)
    switch_min_gain = st.slider('Đổi ID: mức cải thiện chi phí tối thiểu', 0.0, 5.0, 0.3, 0.05)
    min_history = st.slider('Số frame lịch sử tối thiểu', 2, 15, 3)
    jump_confidence = st.select_slider('Độ tin cậy ngưỡng phát hiện box nhảy', options=[0.90, 0.95, 0.99, 0.995, 0.999, 0.9999], value=0.999)
    st.info('Các ngưỡng là giá trị khởi đầu, cần hiệu chỉnh trên tập dữ liệu kiểm định.')
    st.subheader('Cấu hình nuScenes 3D (m, giây, rad)')
    max_speed = st.number_input('Tốc độ tối đa (m/s)', 1.0, 200.0, 55.0)
    max_yaw_rate = st.number_input('Tốc độ đổi hướng tối đa (rad/s)', 0.1, 20.0, 3.0)
    max_size_change = st.slider('Mức thay đổi kích thước tương đối tối đa', 0.05, 2.0, 0.6, 0.05)
    max_time_gap = st.number_input('Khoảng gián đoạn thời gian tối đa (giây)', 0.1, 60.0, 10.0)
    fragment_max_dist_3d = st.number_input('Phân mảnh: khoảng cách tối đa (m)', 0.1, 100.0, 4.0)
    switch_max_dist_3d = st.number_input('Đổi ID: khoảng cách tối đa (m)', 0.1, 100.0, 4.0)
    switch_min_gain_3d = st.number_input('Đổi ID: mức cải thiện chi phí tối thiểu (m)', 0.1, 100.0, 1.0)

uploaded = st.file_uploader('Tải lên dữ liệu gán nhãn CVAT XML, BDD100K MOT JSON hoặc nuScenes Tracking JSON', type=['xml','json'])
format_name = st.radio('Định dạng', ['cvat', 'bdd', 'nuscenes'], horizontal=True,
                       index=1 if uploaded and uploaded.name.lower().endswith('.json') else 0)
manifest = st.file_uploader('Tệp thông tin frame nuScenes (manifest JSON, bắt buộc)', type=['json']) if format_name == 'nuscenes' else None
if format_name == 'nuscenes':
    st.caption('Manifest gồm sample_token, scene_token, frame_index, timestamp (giây) hoặc timestamp_us (micro giây).')
if uploaded and ((format_name == 'cvat' and not uploaded.name.lower().endswith('.xml')) or (format_name in ('bdd','nuscenes') and not uploaded.name.lower().endswith('.json'))):
    st.warning('Định dạng được chọn không khớp phần mở rộng file.')

if st.button('▶ Bắt đầu kiểm tra', type='primary', disabled=uploaded is None or (format_name == 'nuscenes' and manifest is None)):
    with st.spinner('Đang phân tích annotation...'):
        with tempfile.TemporaryDirectory(prefix='tracking_qa_') as tmp:
            tmpdir = Path(tmp)
            source = tmpdir / ('input.xml' if format_name == 'cvat' else 'input.json')
            source.write_bytes(uploaded.getvalue())
            output = tmpdir / 'results'
            if format_name == 'nuscenes':
                manifest_path = tmpdir / 'manifest.json'
                manifest_path.write_bytes(manifest.getvalue())
            command = [sys.executable, str(ENGINE), '--input', str(source), '--format', format_name,
                       '--output', str(output), '--max-gap', str(max_gap),
                       '--fragment-max-dist', str(fragment_max_dist),
                       '--fragment-min-iou', str(fragment_min_iou),
                       '--switch-max-dist', str(switch_max_dist),
                       '--switch-min-gain', str(switch_min_gain),
                       '--min-history', str(min_history),
                       '--jump-confidence', str(jump_confidence)]
            if format_name == 'nuscenes':
                command.extend(['--manifest', str(manifest_path),
                    '--max-speed', str(max_speed), '--max-yaw-rate', str(max_yaw_rate),
                    '--max-size-change', str(max_size_change), '--max-time-gap', str(max_time_gap),
                    '--fragment-max-dist-3d', str(fragment_max_dist_3d),
                    '--switch-max-dist-3d', str(switch_max_dist_3d),
                    '--switch-min-gain-3d', str(switch_min_gain_3d)])
            try:
                completed = subprocess.run(command, capture_output=True, text=True, timeout=300, cwd=ROOT)
                if completed.returncode:
                    st.error('Kiểm tra không thành công. Hãy kiểm tra cấu trúc dữ liệu gán nhãn.')
                    st.code((completed.stderr or completed.stdout)[-6000:])
                else:
                    summary = json.loads((output / 'summary.json').read_text(encoding='utf-8'))
                    issues = json.loads((output / 'issues.json').read_text(encoding='utf-8'))
                    report_files = {name: (output / name).read_bytes() for name in ('issues.csv','issues.json','summary.json','report.html')}
                    archive = io.BytesIO()
                    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
                        for name, content in report_files.items():
                            z.writestr(name, content)
                    st.session_state['qa_result'] = {
                        'summary': summary, 'issues': issues,
                        'reports': report_files, 'zip': archive.getvalue(),
                        'input_name': uploaded.name
                    }
                    st.success('Phân tích hoàn tất.')
            except subprocess.TimeoutExpired:
                st.error('Phân tích vượt quá 300 giây. Hãy thử một video ngắn hơn.')
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                st.error(f'Không thể xử lý kết quả: {exc}')

result = st.session_state.get('qa_result')
if result:
    st.subheader(f"Kết quả gần nhất: {result['input_name']}")
    summary = result['summary']
    counts = summary.get('issues', {})
    cols = st.columns(5)
    for col, label, val in zip(cols, ['Quỹ đạo','Hộp giới hạn','Đổi ID','Đứt quãng','Box nhảy'],
                               [summary.get('tracks',0), summary.get('boxes',0), counts.get('ID_SWITCH',0),
                                counts.get('TRACK_FRAGMENT',0), counts.get('BOX_JUMP',0)]):
        col.metric(label, val)
    issues = result['issues']
    if issues:
        types = sorted(set(issue.get('type','') for issue in issues))
        selected = st.multiselect('Lọc loại cảnh báo', types, default=types, format_func=lambda x: {'ID_SWITCH':'Đổi ID', 'TRACK_FRAGMENT':'Đứt quãng quỹ đạo', 'BOX_JUMP':'Box nhảy bất thường'}.get(x,x))
        filtered = [issue for issue in issues if issue.get('type') in selected]
        df = pd.DataFrame(filtered)
        columns = [col for col in ['type','frame','track_id','other_id','score','reason'] if col in df.columns]
        display_df = (df[columns] if columns else df).rename(columns={
            'type': 'Loại cảnh báo', 'frame': 'Frame', 'track_id': 'ID quỹ đạo',
            'other_id': 'ID liên quan', 'score': 'Điểm bất thường', 'reason': 'Nguyên nhân',
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.caption('Điểm bất thường không phải xác suất lỗi. Người kiểm tra cần xác nhận trên video/CVAT.')
    else:
        st.info('Không có cảnh báo với các ngưỡng đã chọn.')
    st.download_button('⬇ Tải toàn bộ báo cáo (ZIP)', result['zip'], file_name='tracking_qa_results.zip', mime='application/zip')
    d1, d2 = st.columns(2)
    with d1:
        st.download_button('Tải danh sách cảnh báo (CSV)', result['reports']['issues.csv'], file_name='issues.csv', mime='text/csv')
    with d2:
        st.download_button('Tải báo cáo tổng hợp (HTML)', result['reports']['report.html'], file_name='report.html', mime='text/html')
else:
    st.info('Hãy tải lên một tệp gán nhãn rồi nhấn “Bắt đầu kiểm tra”.')
