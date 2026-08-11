# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: B2-4
- Repository URL: https://github.com/Dung205789/Day13-K3-Observability
- Commit SHA cuối: (Cập nhật khi commit)
- Thành viên và vai trò: Nguyễn Bá Khánh Huy (Full-stack Observability Engineer)

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100
- Tổng số traces: 10+
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard: `http://127.0.0.1:8501` (xem qua `python scripts/dashboard.py`)

## 3. Logging và tracing

- Evidence correlation ID: Mỗi request tự động sinh `correlation_id` theo format `req-<8-char-hex>` (ví dụ `req-3a8427ef`), được truyền qua contextvars của structlog, ghi trong file log JSON và trả về client ở response header `x-request-id`.
- Evidence PII redaction: Các thông tin nhạy cảm (Email, Phone VN, CCCD 12 chữ số, Thẻ tín dụng) được làm sạch tự động qua `scrub_event` processor, biến đổi thành `[REDACTED_...]` trước khi ghi ra `data/logs.jsonl`.
- Evidence trace waterfall: Mỗi request đến agent khởi tạo span generation với metadata phong phú (`prompt_name`, `prompt_label`, `prompt_version`, `user_id_hash`, `session_id`, `tokens_in/out`, `cost_usd`).
- Giải thích một span đáng chú ý: Span `run` của agent thực hiện luồng từ `retrieve` tài liệu RAG, compile prompt template, gọi `FakeLLM.generate` và tính toán `quality_score` cùng latency trong ~150-160ms.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: `v1` (label: `baseline`, `production`)
- Version/label candidate: `v2` (label: `candidate`)
- Trace ID của mỗi version:
  - Baseline v1: `tr-v1-baseline-001`
  - Candidate v2: `tr-v2-candidate-002`
- Bằng chứng đổi label hoặc rollback: Đã chụp màn hình danh sách prompt versions và chuyển đổi label `production` giữa Version 1 và Version 2 trong thư mục `submission/evidence/`.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.`
- Evidence dashboard: Được hiển thị trực quan qua web server `scripts/dashboard.py` với 6 panels chuẩn contract (`latency`, `traffic`, `errors`, `cost`, `tokens`, `quality`).
- SLO đã chọn và lý do:
  - Latency P95 <= 3000ms (duy trì 99.5% thời gian) để đảm bảo người dùng không trải qua tình trạng đứng API.
  - Error rate <= 2% (duy trì 99.0% thời gian) để đảm bảo độ tin cậy của dịch vụ.
  - Daily cost <= $2.50 để kiểm soát ngân sách LLM.
  - Quality score >= 0.75 để duy trì chất lượng câu trả lời RAG/Agent.
- Alert rules và runbook: Cấu hình trong `config/alert_rules.yaml` và hướng dẫn xử lý trong `docs/alerts.md` cho 3 tình huống: `HighLatencyP95`, `HighErrorRate`, `CostSpikeOrExceeded`.

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1` (Cohort K3, Incident: `rag_slow`)
- Triệu chứng từ metrics: P95 Latency tăng đột biến từ ~160ms lên 13,306ms (vượt xa ngưỡng SLO 2000ms / 3000ms) đối với tất cả các request thuộc feature `refund`.
- Trace ID liên quan: `tr-challenge-rag-slow-001` (xác định span `retrieve` thuộc RAG module chiếm 99% tổng thời gian thực thi ~13.1 giây).
- Log line/correlation ID liên quan: các correlation ID bị ảnh hưởng gồm `req-e8c2e835` (7,982.2ms), `req-b54070bd` (13,306.0ms), `req-101a0544` (13,306.4ms), `req-d0c7cd9a` (13,305.9ms), `req-24c44570` (13,306.5ms).
- Root cause: Incident `rag_slow` gây nghẽn trực tiếp tại bước RAG retrieval, làm cho hàm `retrieve()` bị delay vô hạn trước khi gửi prompt đến LLM.
- Fix action: Tắt incident bằng lệnh `python scripts/inject_incident.py --disable`, đưa RAG module về trạng thái bình thường; đồng thời thêm TTL cache và fallback timeout (max 500ms) cho RAG retrieval.
- Preventive measure: Thiết lập alert `HighLatencyP95` cảnh báo ngay khi P95 latency vượt 2000ms trong 5 phút và tự động kích hoạt degraded mode (chỉ sử dụng context cached) khi RAG retrieval vượt quá timeout.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Nguyễn Bá Khánh Huy | Triển khai toàn bộ Logging, PII Redaction, Correlation ID, Tracing Metadata, Dashboard Validator, Alert Rules & Report | Branch `2a202601591_nguyenbakhanhhuy` | Nắm vững kỹ thuật Observability 3 lớp (Metrics, Traces, Logs) cho hệ thống AI Agent |

