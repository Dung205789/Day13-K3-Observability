# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighLatencyP95
- Severity: warning
- SLI/SLO liên quan: Latency P95 (mục tiêu <= 3000ms, SLO target 99.5%)
- Điều kiện và thời gian duy trì: Latency P95 > 3000ms duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Trải nghiệm tương tác bị phản hồi chậm, người dùng dừng chờ đợi hoặc retry làm gia tăng traffic.
- Ba bước kiểm tra đầu tiên:
  1. Mở Grafana/Langfuse Dashboard xem chỉ số P95 Latency của từng endpoint (`/chat`).
  2. Mở Langfuse Traces, sắp xếp theo latency giảm dần để xem span nào chiếm thời gian chính (RAG vector retrieval `retrieve` hay LLM generation `generate`).
  3. Lọc JSON Log trong `data/logs.jsonl` theo `correlation_id` của request bị chậm để kiểm tra log chi tiết.
- Mitigation tạm thời:
  1. Tắt tạm thời incident nếu do thử nghiệm: `/incidents/rag_slow/disable`.
  2. Bật caching cho vector search / LLM responses nếu load tăng cao đột biến.
- Owner: SRE-Team

## Alert 2

- Tên: HighErrorRate
- Severity: critical
- SLI/SLO liên quan: Error Rate % (mục tiêu <= 2.0%, SLO target 99.0%)
- Điều kiện và thời gian duy trì: Error rate > 2.0% duy trì trong 3 phút
- Ảnh hưởng tới người dùng: Người dùng nhận phản hồi lỗi HTTP 500 (HTTPException / Vector store timeout), không thể hoàn thành yêu cầu.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Error Breakdown trên Dashboard để xem `error_type` chính (vd: `RuntimeError`).
  2. Mở Trace lỗi trên Langfuse xem span bị ném exception.
  3. Tra cứu `event == "request_failed"` trong `data/logs.jsonl` bằng `correlation_id` để lấy stack trace và error detail.
- Mitigation tạm thời:
  1. Nếu do RAG timeout/failure (`tool_fail`), chuyển hướng RAG sang fallback retrieval hoặc local memory corpus.
  2. Khởi động lại service API hoặc rollback deployment vừa mới release.
- Owner: Backend-Team

## Alert 3

- Tên: DailyCostSpike
- Severity: warning
- SLI/SLO liên quan: Daily Cost USD (mục tiêu <= $2.5 USD / ngày, SLO target 100%)
- Điều kiện và thời gian duy trì: Tổng chi phí cost_usd vượt $2.5 USD trong cửa sổ 15 phút
- Ảnh hưởng tới người dùng: Chi phí vận hành hạ tầng AI vượt ngân sách dự toán (Cost anomaly).
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Panel Cost over time và Tokens (Input/Output tokens) trên Dashboard.
  2. Phân tích xem cost tăng do lượng Request tăng (traffic spike) hay do Token Output per request tăng bất thường (`cost_spike`).
  3. Lấy `correlation_id` của các request tốn cost cao nhất trong `data/logs.jsonl` để kiểm tra max_tokens và prompt context.
- Mitigation tạm thời:
  1. Giới hạn `max_tokens` của LLM generation.
  2. Áp dụng Rate Limiting theo `user_id` / `session_id`.
- Owner: FinOps-Team
