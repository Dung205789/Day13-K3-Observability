# Báo cáo Điều tra Challenge Incident (`day13-k3-observability-v1`)

## 1. Thông tin Challenge
- **Cohort:** K3
- **Challenge ID:** `day13-k3-observability-v1`
- **Affected Feature:** `refund`
- **Latency Threshold:** `2000 ms`
- **Incident State:** `rag_slow = True`

## 2. Luồng Điều tra Chi tiết (Metrics ➔ Traces ➔ Logs)

### Bước 1: Triệu chứng từ Metrics (Dashboard Alert)
- Panel **Latency percentiles** trên Dashboard phản ánh chỉ số **P95 Latency** của feature `refund` tăng đột biến từ **~150ms** lên **2651ms**, vượt ngưỡng SLO `2000ms` (vi phạm Alert `HighLatencyP95`).
- Panel Error rate không tăng (0%), chứng tỏ request vẫn hoàn thành (HTTP 200) nhưng bị trễ nghiêm trọng.

### Bước 2: Phân tích Trace trên Langfuse (Tracing Localization)
- Lọc các trace thuộc feature `refund` trong thời gian xảy ra sự cố.
- **Trace ID tiêu biểu:** `tr-2a995b1b` (Correlation ID: `req-2a995b1b`)
- Xem cây Span Waterfall:
  - Total latency: `2651 ms`
  - Span `retrieve()` (RAG Vector Store): `2500 ms` (Chiếm 94.3% tổng thời gian)
  - Span `generate()` (LLM Inference): `151 ms`
- **Kết luận bước 2:** Độ trễ không nằm ở mô hình LLM mà phát sinh từ thành phần **RAG Vector Search (`retrieve`)**.

### Bước 3: Chứng minh Nguyên nhân Gốc rễ qua Logs (Root Cause Verification)
- Tra cứu Log lines mang `correlation_id == "req-2a995b1b"` trong `data/logs.jsonl`:
  ```json
  {"service": "control", "payload": {"name": "rag_slow"}, "event": "incident_enabled", "correlation_id": "req-57590005", "level": "warning", "ts": "2026-08-11T03:34:42.264290Z"}
  {"service": "api", "payload": {"message_preview": "What is your refund policy?"}, "event": "request_received", "user_id_hash": "026c7a407135", "feature": "refund", "correlation_id": "req-2a995b1b", "model": "claude-sonnet-4-5", "env": "dev", "session_id": "k3-challenge-s01", "level": "info", "ts": "2026-08-11T03:34:43.040184Z"}
  {"service": "api", "latency_ms": 2651, "tokens_in": 29, "tokens_out": 158, "cost_usd": 0.002457, "quality_score": 0.9, "payload": {"answer_preview": "Starter answer. Teams should improve this output logic and add better quality ch..."}, "event": "response_sent", "user_id_hash": "026c7a407135", "feature": "refund", "correlation_id": "req-2a995b1b", "model": "claude-sonnet-4-5", "env": "dev", "session_id": "k3-challenge-s01", "level": "info", "ts": "2026-08-11T03:34:45.699104Z"}
  ```
- **Bằng chứng:** Log xác nhận ngay trước các request `refund`, hệ thống đã ghi nhận event `incident_enabled` cho kịch bản `rag_slow` tại timestamp `2026-08-11T03:34:42Z`. Code trong `app/mock_rag.py` thực hiện `time.sleep(2.5)` khi `STATE["rag_slow"] == True`.

## 3. Biện pháp Khắc phục & Phòng ngừa (Fix & Prevention)
- **Fix Action khẩn cấp:** Disable incident trạng thái bị chậm qua endpoint `/incidents/rag_slow/disable` (chạy script `python scripts/inject_incident.py --disable`).
- **Biện pháp phòng ngừa dài hạn:**
  1. Thêm bộ nhớ đệm (Cache layer - Redis) cho các câu hỏi phổ biến thuộc feature `refund` để giảm bớt số lượt gọi tới Vector Database.
  2. Đặt Timeout cho hàm RAG retrieval (ví dụ: max 1000ms), nếu vượt quá timeout thì fallback về prompt không dùng retrieval hoặc dùng cache cũ.
  3. Cấu hình Alert tự động bắn về channel Slack/PagerDuty khi Latency P95 của bất kỳ feature nào vượt `2000ms` quá 3 phút.
