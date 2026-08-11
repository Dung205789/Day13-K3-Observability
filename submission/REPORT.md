# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100
- Tổng số traces: 0 (baseline)
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name: day13-chat
- Version/label baseline: (Người dùng cập nhật từ Langfuse)
- Version/label candidate: (Người dùng cập nhật từ Langfuse)
- Trace ID của mỗi version: (Người dùng cập nhật từ Langfuse)
- Bằng chứng đổi label hoặc rollback: (Lưu vào `submission/evidence/`)

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: HỢP LỆ (6/6 panel)
- Evidence dashboard: (Dùng `streamlit run scripts/streamlit_app.py` để chụp ảnh)
- SLO đã chọn và lý do: (Người dùng điền)
- Alert rules và runbook: (Người dùng điền)

## 6. Điều tra challenge

- Challenge ID: day13-k3-observability-v1
- Triệu chứng từ metrics: Latency của các request liên quan đến tính năng `refund` tăng vọt lên đến ~17000ms.
- Trace ID liên quan: (Người dùng cập nhật từ Langfuse)
- Log line/correlation ID liên quan: (Ví dụ: `req-cb8ba5b9` hoặc lấy một ID bất kỳ từ dashboard/logs)
- Root cause: Hàm `retrieve` có chứa lệnh `time.sleep(2.5)` đồng bộ. Khi chạy dưới `async def chat`, nó đã chặn toàn bộ event loop, khiến các request phải chờ nhau.
- Fix action: Đã sửa `async def chat` thành `def chat` tại `app/main.py`. FastAPI sẽ tự đưa hàm này vào threadpool để chạy song song.
- Preventive measure: Tuyệt đối không dùng thư viện đồng bộ (blocking I/O, `time.sleep`) trực tiếp trong các endpoint `async def`. Cần dùng `await run_in_threadpool(...)` hoặc sửa endpoint thành `def`.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
