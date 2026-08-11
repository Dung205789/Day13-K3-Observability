# Kịch bản demo — Day 13 Observability (Ngô Quang Dũng — 2A202601819)

Thời lượng: 6-7 phút. Nguyên tắc: **chỉ demo thứ thay đổi trước mắt người xem**, không đứng đọc chart tĩnh.

Luồng bắt buộc theo rubric: **Metrics → Traces → Logs → Root cause → Fix**.

---

## 0. Chuẩn bị (chạy trước khi vào phòng chấm)

**Terminal 1** — API (giữ chạy suốt buổi):
```bash
cd D:\VIN_LAB\Day13-K3-Observability
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --env-file .env
```

**Terminal 2** — dashboard live (tự build lại từ log mỗi lần tải trang):
```bash
cd D:\VIN_LAB\Day13-K3-Observability
python scripts/serve_dashboard.py --port 8090
```

**Terminal 3** — terminal trống để gõ lệnh demo.

Mở sẵn 2 tab trình duyệt:
- Dashboard: http://127.0.0.1:8090/dashboard.html
- Langfuse: https://cloud.langfuse.com/project/cmso41ttp048wad0j72rosv2a/traces

Kiểm tra trạng thái sạch:
```bash
curl http://127.0.0.1:8010/health
```
Phải thấy `"ok":true`, `"tracing_enabled":true`, mọi incident đều `false`.

---

## MÀN 1 — PII redaction live (90 giây) ⭐ mở đầu bằng màn này

Đây là màn mạnh nhất: **một câu lệnh chứng minh 3 tính năng cùng lúc**.

Nói trước: *"Em sẽ gửi một request chứa email, số điện thoại và số thẻ tín dụng thật, rồi mở log ra xem hệ thống ghi lại cái gì."*

```bash
curl -i -X POST http://127.0.0.1:8010/chat \
  -H "Content-Type: application/json" \
  -H "x-request-id: req-demo01" \
  -d '{"user_id":"demo-user","feature":"refund","session_id":"demo-live","message":"Toi ten Dung, email dung@vinuni.edu.vn, SDT 0901234567, the 4111 1111 1111 1111. Cho toi biet chinh sach refund?"}'
```

Chỉ vào response headers:
- `x-request-id: req-demo01` → **correlation ID em tự đặt được hệ thống giữ nguyên và trả về**
- `x-response-time-ms: 155.87` → thời gian xử lý đo tại middleware

Rồi mở log:
```bash
python -c "import json;[print(json.dumps(json.loads(l),ensure_ascii=False,indent=2)) for l in open('data/logs.jsonl',encoding='utf-8') if 'req-demo01' in l]"
```

Chỉ vào kết quả:
```
"message_preview": "Toi ten Dung, email [REDACTED_EMAIL], SDT [REDACTED_PHONE_VN], the [REDACTED_CRE..."
"user_id_hash": "cebf292c038f"
```

Nói: *"Ba loại PII bị che trước khi chạm vào file log. `user_id` gốc là `demo-user`, log chỉ lưu hash SHA256 rút gọn — không thể đảo ngược. Việc che diễn ra ở processor `scrub_event` trong `app/logging_config.py`, chạy trong pipeline structlog TRƯỚC khi ghi file, nên không có đường nào PII lọt ra đĩa."*

Nếu giám khảo muốn thử: **mời họ đọc một email/SĐT bất kỳ**, thay vào lệnh curl và chạy lại. Đây là điểm ăn tiền — chứng minh không phải hard-code.

---

## MÀN 2 — Sự cố sống: dashboard tự đổi + alert tự bắn (2 phút) ⭐ màn chính

Mở tab dashboard, chỉ trạng thái hiện tại: banner xanh *"Khong co alert nao dang FIRING"*, P95 ~150ms, đường timeline phẳng.

Nói: *"Bây giờ em bật sự cố y hệt challenge chính thức đã điều tra."*

```bash
python scripts/inject_incident.py --scenario rag_slow
python scripts/load_test.py --concurrency 5
```

Trong lúc load test chạy (~15 giây), **quay sang tab dashboard và bấm nút "Lam moi ngay"** (hoặc chờ countdown tự refresh 30s).

Người xem sẽ thấy **ba thứ đổi cùng lúc**:
1. Banner chuyển đỏ: `1 ALERT DANG FIRING — WARNING high_latency_p95, dieu kien latency_p95_ms > 2000 for 5m, do duoc 2651, runbook: docs/alerts.md#alert-1`
2. Panel Latency: P95 nhảy từ 150ms lên **2651ms**
3. Biểu đồ timeline dưới panel Latency: đường latency **vọt dựng đứng** ở các request cuối

Nói: *"Alert này không phải trang trí — điều kiện của nó đọc trực tiếp từ `config/alert_rules.yaml`, đối chiếu với số đo thật, và chỉ vào runbook tương ứng. Ngưỡng 2000ms được chọn khớp `latency_threshold_ms` của challenge chính thức; nếu để 3000ms như dashboard contract thì alert sẽ không bao giờ bắt được sự cố này."*

---

## MÀN 3 — Traces: khoanh vùng nguyên nhân (1.5 phút)

Chuyển sang tab Langfuse → Tracing → mở một trace vừa tạo.

Chỉ vào:
- **Waterfall**: span `run` (SPAN — toàn bộ agent) lồng span `run` (GENERATION — riêng LLM)
- **Metadata**: `prompt_name=day13-chat`, `prompt_label`, `prompt_version`, `prompt_source=langfuse`

Nói: *"Trace cho thấy generation chỉ tốn ~0.15s. Phần thời gian còn lại nằm ở bước retrieval TRƯỚC generation. Vậy nguyên nhân không phải LLM — metrics cho em biết CÓ sự cố, trace cho em biết sự cố NẰM Ở ĐÂU."*

Nếu được hỏi về prompt versioning → Prompts → `day13-chat`: v1 (`baseline` + `production`), v2 (`candidate`). Giải thích đã chuyển `production` sang v2 rồi rollback về v1, ba trace ID minh chứng nằm trong `submission/REPORT.md` mục 4.

---

## MÀN 4 — Logs: bằng chứng cuối cùng (45 giây)

```bash
python -c "import json;[print(r['correlation_id'],r['event'],r.get('latency_ms')) for r in map(json.loads,open('data/logs.jsonl',encoding='utf-8'))][-6:]"
```

Chọn 1 correlation ID, chỉ cặp `request_received` / `response_sent` cùng ID, `latency_ms` ~2650.

Nói: *"Cùng một correlation ID nối request tới response. Latency đo được 2650ms — khớp gần như tuyệt đối với 2.5 giây sleep cộng 0.15 giây LLM."*

---

## MÀN 5 — Root cause + Fix (1 phút)

Mở `app/mock_rag.py`, chỉ đúng 2 dòng:
```python
if STATE["rag_slow"]:
    time.sleep(2.5)
```

Nói: *"Root cause: bước retrieval bị chặn cứng 2.5 giây, gọi đồng bộ nên nghẽn cả event loop — với concurrency 5 thì latency phía client dồn lên tới 13 giây."*

**Fix**: timeout + fallback cho retrieval; cache câu hỏi refund phổ biến; chuyển sang gọi bất đồng bộ.
**Preventive**: alert `high_latency_p95` vừa thấy bắn; health-check định kỳ vector store; circuit breaker fallback câu trả lời generic khi retrieval vượt ngưỡng.

---

## 6. Dọn dẹp

```bash
python scripts/inject_incident.py --scenario rag_slow --disable
python scripts/load_test.py --concurrency 3
```
Bấm "Lam moi ngay" → banner trở lại xanh, P95 về ~150ms. Kết bài: *"Alert tự tắt khi hệ thống hồi phục."*

---

## Câu hỏi hay bị hỏi — trả lời ngắn

| Câu hỏi | Trả lời |
|---|---|
| Correlation ID sinh ra thế nào? | `app/middleware.py`: đọc header `x-request-id`, không có thì sinh `req-<8 hex>`. Gọi `clear_contextvars()` đầu mỗi request để không rò context giữa các request đồng thời. |
| Vì sao ngưỡng SLO là 2000ms? | Khớp `latency_threshold_ms` của challenge chính thức. Dashboard contract để 3000ms nhưng ngưỡng đó không bắt được `rag_slow` (~2650ms) — đã ghi rõ lý do trong `config/slo.yaml`. |
| PII được che ở đâu? | Processor `scrub_event` trong pipeline structlog (`app/logging_config.py`), chạy trước khi ghi file. Pattern trong `app/pii.py`: email, SĐT VN, CCCD, thẻ tín dụng, passport, địa chỉ VN. |
| Dashboard lấy dữ liệu từ đâu? | `data/logs.jsonl` — đúng nguồn chuẩn theo `docs/DASHBOARD_SETUP.md`. `scripts/serve_dashboard.py` build lại mỗi lần tải trang nên số liệu luôn tươi. |
| Vì sao có lúc `validate_logs.py` không đạt 100? | Một false positive: hash SHA256 của user thử nghiệm tình cờ chứa 10 chữ số liên tiếp trùng regex số điện thoại. Không phải PII thật vì hash không đảo ngược được — phân tích trong `REPORT.md` mục 2. |
| Đã chạy challenge chính thức chưa? | Rồi — `day13-k3-observability-v1`, 5/5 request `refund` vượt ngưỡng 2000ms, log đầy đủ trong `submission/evidence/challenge_investigation_logs.jsonl`. |
