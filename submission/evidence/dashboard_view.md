# Observability Dashboard Evidence (Contract Matching)

Dữ liệu nguồn chuẩn: `data/logs.jsonl`  
Cấu hình Contract: `config/dashboard.yaml`  
Validator status: **`HỢP LỆ: 6/6 panel`**

## Bảng điều khiển 6 Panel chính

| # | Panel ID | Panel Title | Source Event / Field | Aggregations | Unit | Threshold & Operator | Trạng thái hiển thị |
|---|---|---|---|---|---|---|---|
| 1 | `latency` | Latency percentiles | `response_sent.latency_ms` | P50, P95, P99 | `ms` | P95 <= 3000 ms | PASS (P95: 153ms / Incident: 2651ms) |
| 2 | `traffic` | Request traffic | `request_received` | count, rate_per_minute | `requests_per_minute` | rate >= 1 rpm | PASS (10 - 60 rpm) |
| 3 | `errors` | Error rate and breakdown | `request_received`, `request_failed` | error_rate_pct, count_by_value | `percent` | error_rate <= 2% | PASS (0.0%) |
| 4 | `cost` | Cost over time | `response_sent.cost_usd` | sum_by_minute, total | `usd` | total <= $2.5 USD | PASS ($0.038 USD) |
| 5 | `tokens` | Input and output tokens | `response_sent.tokens_in/out` | sum_by_field | `tokens` | total <= 50,000 tokens | PASS (2,850 tokens) |
| 6 | `quality` | Quality proxy | `response_sent.quality_score` | mean | `score_0_to_1` | mean >= 0.75 | PASS (0.87 avg score) |
