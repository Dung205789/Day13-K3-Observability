# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: high_latency_p95
- Severity: warning
- SLI/SLO liên quan: `latency_p95_ms` (`config/slo.yaml`, objective 3000ms, target 99.5%)
- Điều kiện và thời gian duy trì: P95 latency (panel `latency` trong dashboard) > 3000ms, duy trì liên tục 5 phút
- Ảnh hưởng tới người dùng: Câu trả lời chậm rõ rệt, người dùng chờ lâu hơn ngưỡng chấp nhận được, có thể bỏ cuộc trước khi nhận được câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Xem panel Latency trên dashboard để xác nhận P95 đang vượt ngưỡng và từ thời điểm nào
  2. Mở Langfuse, lọc trace theo khoảng thời gian đó, tìm span có duration lớn bất thường (thường là span retrieval/RAG)
  3. Đối chiếu `correlation_id` của trace chậm với `data/logs.jsonl` để xem log `response_sent.latency_ms` và context liên quan (feature, model)
- Mitigation tạm thời: Bật lại các fallback nhanh (giảm số doc RAG truy hồi, tắt incident practice nếu đang bật `rag_slow`), thông báo tạm thời cho người dùng nếu latency không hạ trong vài phút
- Owner: dung.ngo

## Alert 2

- Tên: elevated_error_rate
- Severity: critical
- SLI/SLO liên quan: `error_rate_pct` (`config/slo.yaml`, objective 2%, target 99.0%)
- Điều kiện và thời gian duy trì: Tỷ lệ `request_failed`/`request_received` (panel `errors`) > 2%, duy trì liên tục 5 phút
- Ảnh hưởng tới người dùng: Một phần request nhận lỗi 500 thay vì câu trả lời, tính năng bị gián đoạn
- Ba bước kiểm tra đầu tiên:
  1. Xem panel Errors để lấy breakdown theo `error_type`
  2. Lọc log `event=request_failed` trong `data/logs.jsonl`, đọc `payload.detail` và `correlation_id` tương ứng
  3. Mở trace lỗi trên Langfuse bằng cùng `correlation_id` để xác định span/tool nào ném exception (thường là tool call khi `tool_fail` được bật)
- Mitigation tạm thời: Tắt incident nếu là practice (`python scripts/inject_incident.py --scenario tool_fail --disable`), retry theo exponential backoff ở phía client, thông báo mức độ ảnh hưởng cho owner feature bị lỗi
- Owner: dung.ngo

## Alert 3

- Tên: daily_cost_budget_exceeded
- Severity: warning
- SLI/SLO liên quan: `daily_cost_usd` (`config/slo.yaml`, objective 2.5 USD/ngày, target 100%)
- Điều kiện và thời gian duy trì: Tổng `cost_usd` cộng dồn (panel `cost`) > 2.5 USD trong cửa sổ 60 phút, duy trì 1 giờ
- Ảnh hưởng tới người dùng: Không ảnh hưởng trực tiếp tức thời, nhưng rủi ro vượt ngân sách vận hành nếu không xử lý, có thể dẫn tới việc phải giới hạn (rate-limit) tính năng cho toàn bộ người dùng
- Ba bước kiểm tra đầu tiên:
  1. Xem panel Cost và panel Tokens để xác nhận cost tăng do tăng traffic hay do tăng token/request
  2. Lọc `data/logs.jsonl` theo `event=response_sent`, kiểm tra `tokens_in`/`tokens_out` bất thường theo `feature`/`model`
  3. Mở trace tương ứng trên Langfuse để xem generation nào có usage cao bất thường (thường xảy ra khi `cost_spike` được bật)
- Mitigation tạm thời: Tắt incident nếu là practice (`python scripts/inject_incident.py --scenario cost_spike --disable`), giới hạn tạm thời độ dài context/số token tối đa mỗi request cho tới khi xác định nguyên nhân
- Owner: dung.ngo
