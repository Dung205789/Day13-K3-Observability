# Trace List Evidence (Langfuse / Observability Traces)

Tối thiểu 10 traces thu thập được với đầy đủ metadata (`prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`, `user_id_hash`, `session_id`):

| Trace ID | Correlation ID | Timestamp | Feature | Model | Latency (ms) | Tokens (In/Out) | Cost (USD) | Prompt Name / Label / Version |
|---|---|---|---|---|---|---|---|---|
| `tr-977f1e2a` | `req-977f1e2a` | 2026-08-11T03:33:56Z | summary | claude-sonnet-4-5 | 151 ms | 35 / 97 | $0.001560 | `day13-chat` / `production` / `v1` |
| `tr-06271254` | `req-06271254` | 2026-08-11T03:33:56Z | qa | claude-sonnet-4-5 | 151 ms | 29 / 100 | $0.001587 | `day13-chat` / `production` / `v1` |
| `tr-d99a91f8` | `req-d99a91f8` | 2026-08-11T03:33:56Z | qa | claude-sonnet-4-5 | 150 ms | 27 / 103 | $0.001626 | `day13-chat` / `production` / `v1` |
| `tr-0c4d17fa` | `req-0c4d17fa` | 2026-08-11T03:33:56Z | qa | claude-sonnet-4-5 | 152 ms | 36 / 118 | $0.001878 | `day13-chat` / `production` / `v1` |
| `tr-a342e195` | `req-a342e195` | 2026-08-11T03:33:57Z | qa | claude-sonnet-4-5 | 150 ms | 28 / 159 | $0.002469 | `day13-chat` / `production` / `v1` |
| `tr-2a995b1b` | `req-2a995b1b` | 2026-08-11T03:34:43Z | refund | claude-sonnet-4-5 | 2651 ms | 29 / 158 | $0.002457 | `day13-chat` / `candidate` / `v2` |
| `tr-872fc449` | `req-872fc449` | 2026-08-11T03:34:45Z | refund | claude-sonnet-4-5 | 2651 ms | 34 / 94 | $0.001512 | `day13-chat` / `candidate` / `v2` |
| `tr-7b9b101e` | `req-7b9b101e` | 2026-08-11T03:34:48Z | refund | claude-sonnet-4-5 | 2651 ms | 31 / 147 | $0.002298 | `day13-chat` / `production` / `v1` |
| `tr-caa1b256` | `req-caa1b256` | 2026-08-11T03:34:51Z | refund | claude-sonnet-4-5 | 2651 ms | 34 / 86 | $0.001392 | `day13-chat` / `production` / `v1` |
| `tr-810af260` | `req-810af260` | 2026-08-11T03:34:53Z | refund | claude-sonnet-4-5 | 2651 ms | 34 / 133 | $0.002097 | `day13-chat` / `production` / `v1` |
