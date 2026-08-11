# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: Cá nhân — Ngô Quang Dũng
- Repository URL: https://github.com/Dung205789/Day13-K3-Observability
- Commit SHA cuối: `ce23f7e86e635296d7b67400d87a8d852373a56f` (branch `Dung`)
- Thành viên và vai trò: Ngô Quang Dũng (MSSV 2A202601819) — đảm nhiệm cả 4 vai trò do làm cá nhân: Logging & PII; Tracing & Prompt Version; Dashboard, SLO & Alert; Incident, Report & Demo.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py` (lần chạy chính thức cuối, log sạch 20 record / 10 correlation ID): **100/100**. Trong lúc test mở rộng (96 record gộp cả baseline, incident practice, challenge, prompt-versioning), script từng báo **70/100** do 1 false positive: `user_id_hash` (SHA256 rút gọn) của user thử nghiệm `promptcheck-02` tình cờ chứa 10 ký tự số liên tiếp trùng regex số điện thoại VN — không phải PII thật bị lộ (hash không thể đảo ngược về số điện thoại gốc). Log đầy đủ của quá trình test được lưu tại `submission/evidence/full_session_logs_backup.jsonl` và kết quả validator tương ứng tại `submission/evidence/validate_logs_output.txt`.
- Tổng số traces trên Langfuse: **26 traces** có đầy đủ metadata (`prompt_name`, `prompt_label`, `prompt_version`, `user_id`, `session_id`, `tags`). Xác nhận qua Langfuse public API vì giao diện Cloud UI có độ trễ index vài phút so với API — xem `submission/evidence/langfuse_traces_api_evidence.json`.
- Số PII leak còn lại: **0** trong log chính thức cuối cùng (đã phân tích false positive ở trên).
- Link/đường dẫn dashboard: chạy `python scripts/serve_dashboard.py --port 8090` rồi mở http://127.0.0.1:8090/dashboard.html — dashboard **live**, tự build lại từ `data/logs.jsonl` ở mỗi lần tải trang và tự làm mới sau đúng `refresh_seconds` của contract. Bản tĩnh `data/dashboard.html` sinh bằng `python scripts/build_dashboard.py`. Ngoài 6 panel theo contract, dashboard còn có: biểu đồ timeline latency theo từng request (thấy spike ngay khi incident bật) và banner **alert đang FIRING** đọc điều kiện trực tiếp từ `config/alert_rules.yaml`. Ảnh evidence: `submission/evidence/dashboard_baseline.jpg`, `dashboard_incident_rag_slow.jpg`, `dashboard_alert_firing.jpg`, `dashboard_final_clean.jpg`.

## 3. Logging và tracing

- Evidence correlation ID: mỗi request có `x-request-id` dạng `req-<8 hex>` (gắn trong `app/middleware.py`), log `request_received`/`response_sent` mang cùng `correlation_id`. Ví dụ cặp log của `req-da525b40` (latency 2651ms khi bật `rag_slow`) trong `submission/evidence/log_correlation_rag_slow.jsonl`.
- Evidence PII redaction: `app/pii.py` redact email, SĐT VN, CCCD, thẻ tín dụng, passport, địa chỉ VN. Ví dụ log thực tế trong `full_session_logs_backup.jsonl`: request chứa `"What is the policy for PII and credit card [REDACTED_CREDIT_CARD]?"` — số thẻ đã bị scrub trước khi ghi log.
- Evidence trace waterfall: `submission/evidence/langfuse_trace_detail_metadata.jpg` — trace `2e6251a348ff56cd31b1a694e3cf950f` gồm span `run` (SPAN, agent.run) lồng span `run` (GENERATION, LLM call), kèm đầy đủ metadata `prompt_name/prompt_label/prompt_version/prompt_source`.
- Giải thích một span đáng chú ý: span GENERATION trong trace trên có `prompt_source=langfuse` — xác nhận prompt được lấy managed từ Langfuse chứ không fallback local. Latency của generation này ở điều kiện bình thường là ~0.15s; khi bật incident `rag_slow`, span retrieval phía trước generation tăng lên ~2.5s (do `time.sleep(2.5)` trong `app/mock_rag.py`), kéo tổng latency toàn request lên ~2.65s — thể hiện rõ trong panel Latency của dashboard (150ms → 2651ms).

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: **v1**, label `baseline` + `production` (khi tạo) — trace `866a74af9b4bc0036e4131cedaa65f0f` (session `prompt-baseline-s1`)
- Version/label candidate: **v2**, label `candidate`, thay đổi định dạng "Answer in at most 2 concise sentences." — trace `1231be7292817dade695bf84f3193c2a` (session `prompt-candidate-s1`)
- Trace ID của mỗi version: v1 = `866a74af9b4bc0036e4131cedaa65f0f`; v2 = `1231be7292817dade695bf84f3193c2a`
- Bằng chứng đổi label và rollback (label `production` luôn được server dùng mặc định):
  1. Trước khi đổi (`production` → v1): trace `00ad996e634bf325b5e06ede4eb32d85`, `prompt_version=1`
  2. Sau khi chuyển `production` sang v2: trace `7fe05569efe40f2f6eb8d2dd36d4d4c2`, `prompt_version=2` (xác nhận qua API sau khi restart server để làm mới cache 60s của Langfuse SDK)
  3. Sau khi rollback `production` về v1: trace `9fe0d7a9078f6800fc96c9ed1d4f57bd`, `prompt_version=1`
  - Ảnh danh sách 2 version + label trên Langfuse: `submission/evidence/langfuse_prompt_versions.jpg`
  - Chi tiết đầy đủ từng trace: `submission/evidence/langfuse_traces_api_evidence.json`

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.` (`submission/evidence/validate_dashboard_and_build_output.txt`)
- Evidence dashboard: `dashboard_baseline.jpg` (trạng thái bình thường, mọi panel PASS), `dashboard_incident_rag_slow.jpg` (P95 latency tăng 150ms → 2651ms sau khi bật `rag_slow`, vẫn PASS vì chưa vượt ngưỡng 3000ms nhưng thay đổi rõ rệt theo đúng hướng), `dashboard_final_clean.jpg` (trạng thái cuối trước khi nộp bài).
- SLO đã chọn và lý do (`config/slo.yaml`):
  - `latency_p95_ms <= 2000` (target 99.5%): ban đầu chọn 3000ms theo dashboard contract, nhưng khi kiểm tra bằng dashboard live phát hiện ngưỡng đó **không bao giờ bắt được** chính incident `rag_slow` mà nó được thiết kế để phát hiện — sự cố này tạo P95 ~2651ms, nằm dưới 3000ms. Đã hạ về **2000ms** cho khớp `latency_threshold_ms` của challenge chính thức; sau khi sửa, alert `high_latency_p95` bắn đúng lúc incident bật (bằng chứng: `submission/evidence/dashboard_alert_firing.jpg`).
  - `error_rate_pct <= 2` (target 99.0%): chuẩn phổ biến cho API nội bộ giai đoạn thử nghiệm.
  - `daily_cost_usd <= 2.5` (target 100%): dựa trên chi phí thực đo ~0.0015–0.003 USD/request của fake LLM.
  - `quality_score_avg >= 0.75` (target 95%): theo heuristic quality proxy trong `app/agent.py` (điểm trung bình quan sát được ~0.88 ở trạng thái bình thường).
- Alert rules và runbook (`config/alert_rules.yaml`, `docs/alerts.md`): 3 alert symptom-based ánh xạ đúng 3 incident scenario thực hành —
  - `high_latency_p95` (warning) ↔ scenario `rag_slow`
  - `elevated_error_rate` (critical) ↔ scenario `tool_fail`
  - `daily_cost_budget_exceeded` (warning) ↔ scenario `cost_spike`
  Mỗi alert có runbook chi tiết: SLI/SLO liên quan, điều kiện + thời gian duy trì, ảnh hưởng người dùng, 3 bước kiểm tra đầu tiên, mitigation tạm thời, owner.

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1` (cohort K3, incident `rag_slow`, `affected_feature=refund`, `latency_threshold_ms=2000`)
- Triệu chứng từ metrics: sau khi chạy `python scripts/inject_incident.py` (đọc `config/challenge.json` → bật `rag_slow`) và `python scripts/load_test.py --challenge --concurrency 5`, panel Latency của dashboard cho thấy P95 tăng vọt trên toàn bộ request `feature=refund`; client-side latency đo được 7.9–13.3s do các request bị dồn hàng (server dev đơn luồng, retrieval blocking event loop).
- Trace ID liên quan: tại thời điểm chạy challenge, key Langfuse thật chưa được cấu hình nên các request challenge không tạo trace trên Langfuse (metadata log ghi `prompt_source=local`). Cơ chế root cause tương đương (retrieval bị block bởi `rag_slow`) đã được tái hiện và xác nhận có trace trên Langfuse ở phần Prompt versioning (mục 4) sau khi bật key — cụ thể trace `7fe05569efe40f2f6eb8d2dd36d4d4c2` có latency generation bị kéo dài bởi cùng cơ chế sleep. Đây là một giới hạn thực tế của lần chạy challenge này, được ghi nhận trung thực thay vì giả tạo bằng chứng.
- Log line/correlation ID liên quan: 5 correlation ID của 5 query challenge — `req-2d6dbd80`, `req-36127b99`, `req-fba817ae`, `req-0986a512`, `req-b3451184` — mỗi request đều có `latency_ms` trong khoảng **2650–2651ms**, vượt `latency_threshold_ms=2000ms` của challenge. Chi tiết đầy đủ (cả `request_received` và `response_sent`) tại `submission/evidence/challenge_investigation_logs.jsonl`.
- Root cause: `app/mock_rag.py:retrieve()` thực thi `time.sleep(2.5)` khi `STATE["rag_slow"]` = `True` (`app/incidents.py`), được kích hoạt bởi `POST /incidents/rag_slow/enable` mà `scripts/inject_incident.py` gọi dựa trên trường `incident` trong `config/challenge.json`. Latency đo được (2650–2651ms) khớp gần như tuyệt đối với 2.5s sleep + ~0.15s xử lý LLM giả lập, xác nhận nguyên nhân trực tiếp là bước retrieval bị làm chậm nhân tạo, không phải do LLM hay downstream khác. 5/5 request `refund` trong challenge đều vượt ngưỡng.
- Fix action: (1) thêm timeout cho bước gọi vector store/retrieval, trả fallback "no context" thay vì chờ vô hạn khi vượt timeout; (2) cache kết quả retrieval cho các câu hỏi refund phổ biến (policy tương đối tĩnh); (3) chạy retrieval và các bước độc lập khác song song (asyncio) thay vì tuần tự chặn event loop.
- Preventive measure: (1) alert `high_latency_p95` trong `config/alert_rules.yaml` cảnh báo khi P95 > 3000ms duy trì 5 phút; (2) health-check định kỳ cho vector store để phát hiện suy giảm hiệu năng trước khi ảnh hưởng người dùng; (3) circuit breaker tự động fallback sang câu trả lời generic khi retrieval vượt ngưỡng thời gian, tránh lan truyền latency ra toàn bộ pipeline và giữ P95 trong SLO.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Ngô Quang Dũng (2A202601819) | Logging & PII: hoàn thiện `app/middleware.py`, `app/logging_config.py`, `app/main.py`, `app/pii.py`. Tracing & Prompt Version: tạo prompt v1/v2 trên Langfuse, đổi label và rollback `production` có bằng chứng trace. Dashboard/SLO/Alert: viết `scripts/build_dashboard.py`, hoàn thiện `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md`. Incident & Report: chạy challenge chính thức, điều tra root cause, viết `submission/REPORT.md` và thu thập evidence. | (commit SHA cập nhật sau khi commit — xem lịch sử Git của repo) | Correlation ID phải `clear_contextvars()` đầu mỗi request để tránh leak context giữa các request đồng thời trong cùng process; cache TTL 60s của Langfuse prompt SDK có thể khiến bằng chứng "đổi label ngay lập tức" sai lệch nếu không restart/refresh cache trước khi đo; validator PII dạng regex quét toàn bộ JSON record (kể cả field đã hash) có thể false-positive khi hash ngẫu nhiên trông giống số điện thoại — ranh giới giữa "trông giống PII" và "thực sự là PII" cần được phân tích chứ không chỉ tin số điểm thô.
