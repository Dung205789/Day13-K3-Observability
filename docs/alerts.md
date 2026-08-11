# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighLatencyP95
- Severity: warning
- SLI/SLO liên quan: latency_p95_ms (SLO <= 3000ms, target 99.5%)
- Điều kiện và thời gian duy trì: p95(latency_ms) > 3000ms duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng bị phản hồi chậm, trải nghiệm chat bị ngắt quãng
- Ba bước kiểm tra đầu tiên:
  1. Đọc Dashboard Panel 1 (Latency) để xác định xem latency tăng ở P95/P99 hay P50.
  2. Mở Langfuse Traces của các request chậm, kiểm tra thời gian thực thi của từng span (RAG retrieve vs LLM generate).
  3. Lọc JSON log theo correlation_id của trace chậm để kiểm tra có log lỗi/timeout hoặc retry không.
- Mitigation tạm thời: Bật cache cho RAG retrieval hoặc giảm số lượng retrieved docs nếu bottleneck thuộc về RAG.
- Owner: oncall-engineer

## Alert 2

- Tên: HighErrorRate
- Severity: critical
- SLI/SLO liên quan: error_rate_pct (SLO <= 2%, target 99.0%)
- Điều kiện và thời gian duy trì: error_rate_pct > 2% duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Yêu cầu của người dùng bị từ chối với HTTP status 500
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Dashboard Panel 3 (Error Rate & Breakdown) để xem `error_type` chính gây lỗi (ví dụ ToolExecutionError, LLMTimeout).
  2. Kiểm tra log `request_failed` trong `data/logs.jsonl` thu thập stack trace và correlation ID.
  3. Mở trace tương ứng trên Langfuse để xem node/step nào phát sinh exception.
- Mitigation tạm thời: Khởi động lại service hoặc tắt bớt feature/tool bị lỗi bằng feature flag / incident toggle.
- Owner: oncall-engineer

## Alert 3

- Tên: CostSpikeOrExceeded
- Severity: warning
- SLI/SLO liên quan: daily_cost_usd (SLO <= $2.5, target 100.0%)
- Điều kiện và thời gian duy trì: total_cost_usd > $2.5 trong khung 1 giờ
- Ảnh hưởng tới người dùng: Không trực tiếp ảnh hưởng trải nghiệm người dùng, nhưng nguy cơ vượt ngân sách hệ thống.
- Ba bước kiểm tra đầu tiên:
  1. So sánh Panel 4 (Cost over time) và Panel 5 (Tokens) để xem chi phí tăng do input token hay output token.
  2. Tìm các trace có token_in / token_out lớn bất thường trên Langfuse.
  3. Kiểm tra log `response_sent` lọc theo `tokens_in` / `cost_usd` để tìm `session_id` hoặc `user_id_hash` tiêu thụ quá nhiều.
- Mitigation tạm thời: Áp dụng rate limiting / max token cap per request cho các session lạm dụng.
- Owner: finops-team
