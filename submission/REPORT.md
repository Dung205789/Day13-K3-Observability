# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: Group Observability K3
- Repository URL: https://github.com/Dung205789/Day13-K3-Observability
- Commit SHA cuối: cd84f4f91f5dd6a4b869c93d95eb7c85412409f3
- Thành viên và vai trò:
  - Nguyễn Văn A: Logging & PII Redaction
  - Trần Thị B: Tracing & Prompt Versioning
  - Lê Văn C: Dashboard, SLO & Alert Rules
  - Phạm Văn D: Incident Investigation & Report

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** (Evidence: [validate_logs.txt](file:///D:/University/VinAI/Day13-K3-Observability/submission/evidence/validate_logs.txt))
- Tổng số traces: **33 traces**
- Số PII leak còn lại: **0**
- Link/đường dẫn dashboard: [dashboard_view.md](file:///D:/University/VinAI/Day13-K3-Observability/submission/evidence/dashboard_view.md) và [config/dashboard.yaml](file:///D:/University/VinAI/Day13-K3-Observability/config/dashboard.yaml)

## 3. Logging và tracing

- Evidence correlation ID: [correlation_id_log.json](file:///D:/University/VinAI/Day13-K3-Observability/submission/evidence/correlation_id_log.json)
  - Correlation ID có định dạng `req-<8-char-hex>` được truyền xuyên suốt qua `x-request-id` header và structlog contextvars.
- Evidence PII redaction: [pii_redacted_log.json](file:///D:/University/VinAI/Day13-K3-Observability/submission/evidence/pii_redacted_log.json)
  - Đã loại bỏ email, SĐT VN, CCCD, số thẻ ngân hàng thành `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]`. Hash `user_id` thành `user_id_hash` SHA-256 (12 ký tự).
- Evidence trace waterfall: [trace_waterfall.md](file:///D:/University/VinAI/Day13-K3-Observability/submission/evidence/trace_waterfall.md)
- Giải thích một span đáng chú ý: Span `RAG Vector Store Retrieval: retrieve()` trong Trace `tr-2a995b1b` chiếm 2500ms (94.3% tổng thời gian request) do incident `rag_slow` bị kích hoạt, làm nghẽn luồng xử lý trước khi sang bước LLM generation.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: `v1` (Label: `baseline`, `production`)
- Version/label candidate: `v2` (Label: `candidate`)
- Trace ID của mỗi version:
  - Baseline (v1): `tr-977f1e2a`
  - Candidate (v2): `tr-2a995b1b`
- Bằng chứng đổi label hoặc rollback: [prompt_rollback.md](file:///D:/University/VinAI/Day13-K3-Observability/submission/evidence/prompt_rollback.md) và [prompt_versions.md](file:///D:/University/VinAI/Day13-K3-Observability/submission/evidence/prompt_versions.md)

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: **HỢP LỆ: 6/6 panel có trong dashboard contract** (Evidence: [validate_dashboard.txt](file:///D:/University/VinAI/Day13-K3-Observability/submission/evidence/validate_dashboard.txt))
- Evidence dashboard: [dashboard_view.md](file:///D:/University/VinAI/Day13-K3-Observability/submission/evidence/dashboard_view.md)
- SLO đã chọn và lý do:
  - P95 Latency <= 3000ms (Target 99.5%): Đảm bảo trải nghiệm thời gian thực cho người dùng cuối.
  - Error rate <= 2.0% (Target 99.0%): Giới hạn tỷ lệ lỗi HTTP 500 do sự cố hạ tầng AI / Vector Store timeout.
  - Daily cost <= $2.5 USD: Kiểm soát ngân sách API token.
  - Quality score avg >= 0.75: Bảo đảm chất lượng phản hồi từ RAG và LLM.
- Alert rules và runbook: [config/alert_rules.yaml](file:///D:/University/VinAI/Day13-K3-Observability/config/alert_rules.yaml) và [docs/alerts.md](file:///D:/University/VinAI/Day13-K3-Observability/docs/alerts.md)

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1`
- Triệu chứng từ metrics: Panel P95 Latency trên Dashboard tăng đột biến từ ~150ms lên **2651ms**, vượt ngưỡng SLO 2000ms của feature `refund`.
- Trace ID liên quan: `tr-2a995b1b`, `tr-872fc449`, `tr-7b9b101e`
- Log line/correlation ID liên quan: `correlation_id == "req-2a995b1b"`, `req-872fc449`
- Root cause: Incident `rag_slow` bị kích hoạt làm cho hàm `retrieve()` trong `app/mock_rag.py` ngủ 2.5 giây (`time.sleep(2.5)`) đối với các query liên quan đến feature `refund`.
- Fix action: Chạy `/incidents/rag_slow/disable` (script `python scripts/inject_incident.py --disable`) để tắt chế độ nghẽn mạng giả lập.
- Preventive measure: Áp dụng Caching layer (Redis) cho các câu hỏi thường gặp về refund policy, thiết lập timeout (1000ms) cho RAG retrieval kèm chế độ fallback, và bật cảnh báo tự động về Slack khi P95 latency vượt 2000ms.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Nguyễn Văn A | Implemented JSON logging, Correlation ID middleware, and PII scrubbing | [Commit cd84f4f](https://github.com/Dung205789/Day13-K3-Observability/commit/cd84f4f) | Cách truyền contextvar xuyên suốt request và kỹ thuật scrub PII tự động trước khi log. |
| Trần Thị B | Integrated Langfuse tracing adapter and prompt versioning (v1/v2) | [Commit cd84f4f](https://github.com/Dung205789/Day13-K3-Observability/commit/cd84f4f) | Quản lý phiên bản prompt, quan sát cây span waterfall trên hệ thống LLM. |
| Lê Văn C | Configured Dashboard YAML contract, SLOs, and Alert Runbooks | [Commit cd84f4f](https://github.com/Dung205789/Day13-K3-Observability/commit/cd84f4f) | Thiết kế 6 nhóm chỉ số quan trọng, thiết lập ngưỡng SLO và cảnh báo dựa trên triệu chứng. |
| Phạm Văn D | Led Challenge incident investigation (Metrics -> Traces -> Logs) and final report | [Commit cd84f4f](https://github.com/Dung205789/Day13-K3-Observability/commit/cd84f4f) | Phương pháp điều tra sự cố chuẩn trong Observability để tìm root cause và bằng chứng. |
