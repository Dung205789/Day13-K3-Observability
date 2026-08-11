# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: Nhóm K3 — Day 13 Observability
- Repository URL: https://github.com/Dung205789/Day13-K3-Observability

### Thành viên và vai trò

Theo bảng phân vai trong `README.md` (tối đa 4 vai trò), nhóm 6 người chia thành 4 nhóm vai trò, mỗi vai trò có 1-2 người phụ trách:

| # | Thành viên | MSSV | Vai trò | Phạm vi phụ trách |
|---|---|---|---|---|
| 1 | Phạm Tiến Anh | 2A202601549 | Logging & PII (A) | Correlation ID: middleware, contextvars, response headers |
| 2 | Phạm Tuấn Việt | 2A202601987 | Logging & PII (B) | PII redaction: pattern, scrub processor, log enrichment |
| 3 | Ngô Quang Dũng | 2A202601819 | Tracing & Prompt Version | Langfuse, prompt v1/v2, label/rollback, trace metadata; điều phối chung |
| 4 | Đỗ Đức Trường | 2A202601499 | Dashboard | 6 panel theo contract, timeline latency, dashboard live server |
| 5 | Nguyễn Bá Khánh Huy | 2A202601591 | SLO & Alert | SLO targets, alert rules, runbook, banner alert firing |
| 6 | Đinh Xuân Huy | 2A202601894 | Incident, Challenge & Demo | Chạy challenge chính thức, điều tra root cause, kịch bản demo |

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py` (lần chạy chính thức cuối, 20 record / 10 correlation ID): **100/100**.
  Trong lúc test mở rộng (gộp baseline, incident practice, challenge, prompt-versioning), script từng báo **70/100** do 1 false positive: `user_id_hash` (SHA256 rút gọn) của user thử nghiệm `promptcheck-02` tình cờ chứa 10 ký tự số liên tiếp trùng regex số điện thoại VN — không phải PII thật bị lộ vì hash không thể đảo ngược về số điện thoại gốc. Log đầy đủ của quá trình test lưu tại `submission/evidence/full_session_logs_backup.jsonl`, kết quả validator tại `submission/evidence/validate_logs_output.txt`.
- Tổng số traces trên Langfuse: **26 traces**, đều có đầy đủ metadata (`prompt_name`, `prompt_label`, `prompt_version`, `user_id`, `session_id`, `tags`). Phân bố: 23 trace `production`/v1, 1 trace `production`/v2, 1 trace `baseline`/v1, 1 trace `candidate`/v2. Xác nhận qua Langfuse public API vì giao diện Cloud UI có độ trễ index vài phút so với API — chi tiết trong `submission/evidence/langfuse_traces_api_evidence.json`.
- Số PII leak còn lại: **0** trong log chính thức cuối cùng.
- Dashboard: chạy `python scripts/serve_dashboard.py --port 8090` rồi mở http://127.0.0.1:8090/dashboard.html — dashboard **live**, tự build lại từ `data/logs.jsonl` ở mỗi lần tải trang và tự làm mới sau đúng `refresh_seconds` của contract. Bản tĩnh `data/dashboard.html` sinh bằng `python scripts/build_dashboard.py`. Ngoài 6 panel theo contract, dashboard còn có biểu đồ timeline latency theo từng request và banner **alert đang FIRING** đọc điều kiện trực tiếp từ `config/alert_rules.yaml`.
- `python -m pytest -q`: **22 passed**.
- `python scripts/validate_dashboard.py`: **HỢP LỆ 6/6 panel**.

## 3. Logging và tracing

*(Phụ trách: Phạm Tiến Anh — correlation ID; Phạm Tuấn Việt — PII & enrichment)*

- **Evidence correlation ID**: mỗi request có ID dạng `req-<8 hex>`, sinh trong `app/middleware.py`. Middleware đọc header `x-request-id` nếu client gửi lên, không có thì tự sinh; bind vào structlog contextvars và trả lại qua response header cùng `x-response-time-ms`. Quan trọng: gọi `clear_contextvars()` ở đầu mỗi request để context không rò rỉ giữa các request đồng thời trong cùng process.
  - Bằng chứng client tự đặt ID: `submission/evidence/demo_pii_live.jsonl` — request gửi header `x-request-id: req-demo01`, cả `request_received` và `response_sent` đều mang đúng ID đó.
  - Bằng chứng ID xuyên suốt khi có sự cố: `submission/evidence/log_correlation_rag_slow.jsonl` — cặp log của `req-da525b40` với `latency_ms: 2651`.
- **Evidence PII redaction**: `app/pii.py` redact email, SĐT VN, CCCD, thẻ tín dụng, passport và địa chỉ VN; processor `scrub_event` trong `app/logging_config.py` chạy trong pipeline structlog **trước** khi ghi ra file, nên PII không có đường nào chạm tới đĩa.
  - `submission/evidence/pii_redaction_evidence.jsonl`: các log thực tế với `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]`.
  - `submission/evidence/demo_pii_live.jsonl`: một request chứa đồng thời cả 3 loại PII — log ghi lại `"Toi ten Dung, email [REDACTED_EMAIL], SDT [REDACTED_PHONE_VN], the [REDACTED_CRE..."`, `user_id` gốc `demo-user` chỉ còn `user_id_hash: cebf292c038f`.
- **Log enrichment**: `app/main.py` bind `user_id_hash`, `session_id`, `feature`, `model`, `env` vào contextvars nên mọi log của request đều mang đủ context — `validate_logs.py` báo 0 record thiếu enrichment.
- **Evidence trace waterfall**: `submission/evidence/langfuse_trace_detail_metadata.jpg` — trace `2e6251a348ff56cd31b1a694e3cf950f` gồm span `run` (SPAN, toàn bộ agent) lồng span `run` (GENERATION, riêng LLM call), kèm metadata `prompt_name/prompt_label/prompt_version/prompt_source`.
- **Giải thích một span đáng chú ý**: span GENERATION có `prompt_source=langfuse`, xác nhận prompt được lấy managed từ Langfuse chứ không fallback local. Ở điều kiện bình thường generation chỉ tốn ~0.15s; khi bật incident `rag_slow`, span retrieval **phía trước** generation tăng lên ~2.5s (do `time.sleep(2.5)` trong `app/mock_rag.py`), kéo tổng latency lên ~2.65s. Đây chính là điểm mấu chốt của điều tra: metrics cho biết *có* sự cố, trace cho biết sự cố nằm ở *bước nào* — và nó không nằm ở LLM.

## 4. Prompt versioning

*(Phụ trách: Ngô Quang Dũng)*

- Prompt name: `day13-chat`
- Version/label baseline: **v1**, label `baseline` + `production` — trace `866a74af9b4bc0036e4131cedaa65f0f` (session `prompt-baseline-s1`)
- Version/label candidate: **v2**, label `candidate`, khác biệt: thêm ràng buộc `"Answer in at most 2 concise sentences."` — trace `1231be7292817dade695bf84f3193c2a` (session `prompt-candidate-s1`)
- **Bằng chứng đổi label và rollback** (label `production` là label server dùng mặc định):

| Bước | Hành động | Trace ID | `prompt_version` ghi trong trace |
|---|---|---|---|
| 1 | Trước khi đổi | `00ad996e634bf325b5e06ede4eb32d85` | 1 |
| 2 | Chuyển `production` → v2 | `7fe05569efe40f2f6eb8d2dd36d4d4c2` | 2 |
| 3 | Rollback `production` → v1 | `9fe0d7a9078f6800fc96c9ed1d4f57bd` | 1 |

- Ảnh danh sách 2 version kèm label trên Langfuse: `submission/evidence/langfuse_prompt_versions.jpg`
- Chi tiết đầy đủ từng trace: `submission/evidence/langfuse_traces_api_evidence.json`
- **Lưu ý kỹ thuật rút ra**: Langfuse SDK cache prompt 60 giây. Ngay sau khi đổi label, request tiếp theo vẫn trả về version cũ — phải restart app (hoặc chờ hết TTL) mới thấy version mới. Nếu không biết điều này thì bằng chứng "đổi label có hiệu lực ngay" sẽ sai lệch. Bước 2 ở trên được đo lại sau khi restart để phản ánh đúng.

## 5. Dashboard, SLO và alerts

*(Phụ trách: Đỗ Đức Trường — dashboard; Nguyễn Bá Khánh Huy — SLO, alert, runbook)*

- **Kết quả `validate_dashboard.py`**: `HỢP LỆ: 6/6 panel có trong dashboard contract.` (`submission/evidence/validate_dashboard_and_build_output.txt`)
- **Evidence dashboard**:
  - `dashboard_baseline.jpg` — trạng thái bình thường, 6/6 panel PASS
  - `dashboard_incident_rag_slow.jpg` — P95 tăng 150ms → 2651ms sau khi bật `rag_slow`
  - `dashboard_alert_firing.jpg` — banner đỏ `1 ALERT DANG FIRING` với điều kiện, giá trị đo được và link runbook
  - `dashboard_final_clean.jpg` — trạng thái cuối trước khi nộp
- **Nguồn dữ liệu**: `data/logs.jsonl` đúng theo `docs/DASHBOARD_SETUP.md`. Dashboard được dựng bằng `scripts/build_dashboard.py`, phục vụ live bằng `scripts/serve_dashboard.py`.
- **SLO đã chọn và lý do** (`config/slo.yaml`):
  - `latency_p95_ms <= 2000` (target 99.5%) — **đây là mục nhóm đã phải sửa**. Ban đầu chọn 3000ms theo dashboard contract, nhưng khi kiểm tra bằng dashboard live thì phát hiện ngưỡng đó **không bao giờ bắt được** chính incident `rag_slow` mà alert được thiết kế để phát hiện: sự cố này tạo P95 ~2651ms, nằm *dưới* 3000ms nên alert im lặng. Đã hạ về **2000ms** cho khớp `latency_threshold_ms` của challenge chính thức. Sau khi sửa, alert bắn đúng lúc incident bật (bằng chứng: `dashboard_alert_firing.jpg`).
  - `error_rate_pct <= 2` (target 99.0%): chuẩn phổ biến cho API nội bộ giai đoạn thử nghiệm.
  - `daily_cost_usd <= 2.5` (target 100%): dựa trên chi phí thực đo ~0.0015–0.003 USD/request.
  - `quality_score_avg >= 0.75` (target 95%): theo heuristic quality proxy trong `app/agent.py` (trung bình quan sát ~0.88 ở trạng thái bình thường).
- **Alert rules và runbook** (`config/alert_rules.yaml`, `docs/alerts.md`): 3 alert symptom-based, ánh xạ đúng 3 incident scenario:

| Alert | Severity | Điều kiện | Bắt được scenario |
|---|---|---|---|
| `high_latency_p95` | warning | `latency_p95_ms > 2000 for 5m` | `rag_slow` |
| `elevated_error_rate` | critical | `error_rate_pct > 2 for 5m` | `tool_fail` |
| `daily_cost_budget_exceeded` | warning | `daily_cost_usd > 2.5 for 1h` | `cost_spike` |

  Mỗi alert có runbook đầy đủ trong `docs/alerts.md`: SLI/SLO liên quan, điều kiện + thời gian duy trì, ảnh hưởng tới người dùng, 3 bước kiểm tra đầu tiên, mitigation tạm thời, owner. Dashboard đánh giá các điều kiện này với số đo thực và hiển thị alert nào đang FIRING — alert không chỉ nằm trên giấy.

## 6. Điều tra challenge

*(Phụ trách: Đinh Xuân Huy)*

- **Challenge ID**: `day13-k3-observability-v1` (cohort K3, incident `rag_slow`, `affected_feature=refund`, `latency_threshold_ms=2000`)
- **Triệu chứng từ metrics**: sau khi chạy `python scripts/inject_incident.py` (đọc `config/challenge.json` → bật `rag_slow`) và `python scripts/load_test.py --challenge --concurrency 5`, panel Latency cho thấy P95 tăng vọt trên toàn bộ request `feature=refund`. Latency phía client đo được 7.9–13.3s do các request dồn hàng (retrieval đồng bộ chặn event loop khi chạy concurrency 5).
- **Trace ID liên quan**: tại thời điểm chạy challenge, key Langfuse chưa được cấu hình nên các request challenge không tạo trace trên Langfuse (log ghi `prompt_source=local`). Sau khi có key, cơ chế root cause tương đương đã được tái hiện và xác nhận có trace — ví dụ trace `7fe05569efe40f2f6eb8d2dd36d4d4c2`. **Đây là giới hạn thực tế của lần chạy challenge, được ghi nhận trung thực thay vì dựng bằng chứng giả.**
- **Log line/correlation ID liên quan**: 5 correlation ID của 5 query challenge — `req-2d6dbd80`, `req-36127b99`, `req-fba817ae`, `req-0986a512`, `req-b3451184` — mỗi request có `latency_ms` trong khoảng **2650–2651ms**, đều vượt `latency_threshold_ms=2000ms`. Chi tiết đầy đủ (cả `request_received` lẫn `response_sent`) tại `submission/evidence/challenge_investigation_logs.jsonl`.
- **Root cause**: `app/mock_rag.py:retrieve()` thực thi `time.sleep(2.5)` khi `STATE["rag_slow"] = True` (`app/incidents.py`), được kích hoạt bởi `POST /incidents/rag_slow/enable` mà `scripts/inject_incident.py` gọi dựa trên trường `incident` trong `config/challenge.json`. Latency đo được (2650–2651ms) khớp gần như tuyệt đối với 2.5s sleep + ~0.15s xử lý LLM giả lập → xác nhận nguyên nhân trực tiếp là bước **retrieval** bị làm chậm, không phải LLM hay downstream khác. 5/5 request `refund` đều vượt ngưỡng.
- **Fix action**:
  1. Thêm timeout cho bước gọi vector store, trả fallback "no context" thay vì chờ vô hạn.
  2. Cache kết quả retrieval cho các câu hỏi refund phổ biến (policy tương đối tĩnh).
  3. Chuyển retrieval sang gọi bất đồng bộ để không chặn event loop — đây là lý do latency client vọt tới 13s dù bản thân sleep chỉ 2.5s.
- **Preventive measure**:
  1. Alert `high_latency_p95` cảnh báo khi P95 > 2000ms duy trì 5 phút (đã chứng minh bắn đúng).
  2. Health-check định kỳ vector store để phát hiện suy giảm hiệu năng trước khi ảnh hưởng người dùng.
  3. Circuit breaker tự động fallback sang câu trả lời generic khi retrieval vượt ngưỡng, tránh lan truyền latency ra toàn pipeline.

## 7. Đóng góp cá nhân

### Trạng thái Git hiện tại — cần các thành viên bổ sung

**Cần lưu ý trước khi nộp:** bài nộp nằm trên branch `main`. Toàn bộ code hiện được gom trong các commit đứng tên một tài khoản (người điều phối), do nhóm làm chung trên cùng một máy trong buổi lab. RUBRIC mục B2 yêu cầu *"Có commit/PR cụ thể và có thể kiểm tra"* và *"phần khai báo trong report khớp với thay đổi trong Git"*. Vì vậy cột Commit/PR dưới đây **để trống có chủ đích** — nhóm không điền SHA giả.

Cách để phần khai báo khớp với Git trước buổi chấm: mỗi thành viên clone repo, tự review và bổ sung phần mình phụ trách (thêm test, mở rộng pattern PII, thêm panel, viết thêm runbook, bổ sung script...), rồi commit bằng tài khoản Git của chính mình. Sau đó điền SHA thật vào bảng.

### Bảng phân công và đóng góp

| Thành viên | MSSV | Phần việc phụ trách | File/artifact chính | Commit/PR | Điều đã học |
|---|---|---|---|---|---|
| Phạm Tiến Anh | 2A202601549 | Correlation ID xuyên suốt request: middleware đọc/sinh `x-request-id`, bind structlog contextvars, trả header `x-request-id` + `x-response-time-ms` | `app/middleware.py` | *(chờ commit)* | Phải `clear_contextvars()` ở đầu mỗi request, nếu không context của request trước sẽ rò sang request sau khi chạy đồng thời — lỗi này không lộ ra khi test tuần tự, chỉ hiện khi concurrency > 1 |
| Phạm Tuấn Việt | 2A202601987 | PII redaction và log enrichment: pattern regex, processor scrub trong pipeline structlog, bind context (`user_id_hash`, `session_id`, `feature`, `model`, `env`) | `app/pii.py`, `app/logging_config.py`, `app/main.py` | *(chờ commit)* | Vị trí đặt processor quyết định tính an toàn: `scrub_event` phải chạy **trước** bước ghi file, nếu đặt sau thì PII đã nằm trên đĩa rồi. Hash `user_id` thay vì log thẳng giúp vẫn truy vết được người dùng mà không lưu định danh |
| Ngô Quang Dũng | 2A202601819 | Langfuse: cấu hình project, tạo prompt v1/v2, đổi label `production`, rollback, xác minh trace metadata; điều phối chung và tổng hợp báo cáo | `.env` (không commit), prompt trên Langfuse, `submission/REPORT.md` | các commit trên `main` | Langfuse SDK cache prompt 60s — đổi label xong request tiếp theo vẫn dùng version cũ. Nếu không restart app trước khi đo thì bằng chứng rollback sẽ sai. UI Cloud cũng trễ index vài phút so với API, nên xác minh bằng API đáng tin hơn chụp màn hình vội |
| Đỗ Đức Trường | 2A202601499 | Dashboard: 6 panel đúng contract từ `data/logs.jsonl`, biểu đồ timeline latency theo từng request, server tự build lại mỗi lần tải trang, auto-refresh theo `refresh_seconds` | `scripts/build_dashboard.py`, `scripts/serve_dashboard.py` | *(chờ commit)* | Ba cột P50/P95/P99 không cho thấy sự cố *diễn ra khi nào*; thêm timeline theo từng request thì spike hiện ra ngay lập tức. Dashboard tĩnh phải build tay là vô dụng khi demo — contract đã yêu cầu `refresh_seconds` chính là vì lý do đó |
| Nguyễn Bá Khánh Huy | 2A202601591 | SLO targets, 3 alert symptom-based, runbook đầy đủ, logic đánh giá alert FIRING hiển thị trên dashboard | `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md` | Branch `2a202601591_nguyenbakhanhhuy` | Đặt ngưỡng alert mà không đối chiếu với sự cố thật thì alert thành vô dụng: ngưỡng 3000ms ban đầu không bao giờ bắt được `rag_slow` (~2651ms). Chỉ phát hiện được khi cho alert chạy với dữ liệu thật thay vì chỉ viết ra file YAML |
| Đinh Xuân Huy | 2A202601894 | Chạy challenge chính thức, điều tra Metrics → Traces → Logs, xác định root cause, đề xuất fix/preventive, viết kịch bản demo | `submission/evidence/challenge_investigation_logs.jsonl`, `submission/DEMO_SCRIPT.md` | *(chờ commit)* | Con số latency là bằng chứng mạnh nhất: 2650ms khớp gần như tuyệt đối với 2.5s sleep + 0.15s LLM, đủ để chỉ đích danh bước retrieval mà không cần đoán. Ngoài ra latency client 13s > 2.65s server cho thấy vấn đề thứ hai — retrieval đồng bộ chặn event loop |

### Tự đánh giá mức độ hoàn thành

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| Hoàn thiện `TODO` trong `app/` và `config/` | Xong (0 TODO còn lại) | `grep -rn TODO app/ config/ scripts/` không còn kết quả |
| Tối thiểu 10 traces có metadata | Xong — 26 traces | `langfuse_traces_api_evidence.json` |
| Prompt v1/v2 + label + rollback | Xong | 3 trace ID trong mục 4, `langfuse_prompt_versions.jpg` |
| Dashboard 6 panel + validator | Xong — 6/6 panel | `validate_dashboard_and_build_output.txt`, 4 ảnh dashboard |
| SLO, alert rules, runbook | Xong | `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md` |
| Challenge chính thức + root cause | Xong | `challenge_investigation_logs.jsonl`, mục 6 |
| `validate_logs.py` ≥ 80/100 | Xong — 100/100 | `validate_logs_output.txt` |
| `python -m pytest -q` | Xong — 22 passed | Chạy lại được bất cứ lúc nào |
| Evidence trong `submission/evidence/` | Xong — 14 file | Xem thư mục |
| Không commit `.env`/secret/PII | Xong | `.env` nằm trong `.gitignore`, đã kiểm tra không có key trong file staged |
| `config/challenge.json` không bị sửa | Xong | `git diff config/challenge.json` trống |
| Commit khớp khai báo từng cá nhân | **Chưa** | Cần các thành viên tự commit phần mình — xem ghi chú đầu mục 7 |
