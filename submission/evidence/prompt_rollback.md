# Prompt Label Switch & Rollback Evidence

Thao tác quản lý phiên bản Prompt `day13-chat` trên môi trường Production:

## 1. Chuyển Label `production` từ v1 sang v2 (Promotion)
- **Trạng thái trước:** Label `production` chỉ tới `v1`.
- **Thực thi:** Đổi label `production` sang `v2` bằng biến môi trường `LANGFUSE_PROMPT_LABEL=production` (fetch prompt `v2`).
- **Trace bằng chứng v2 on production:** `tr-872fc449`
  - `prompt_name`: `day13-chat`
  - `prompt_label`: `production`
  - `prompt_version`: `v2`

## 2. Thao tác Rollback label `production` về v1 (Rollback)
- **Lý do:** Version v2 làm tăng đáng kể `tokens_out` và latency.
- **Thực thi:** Cập nhật label `production` chỉ ngược lại về `v1`.
- **Trace bằng chứng sau Rollback:** `tr-7b9b101e`
  - `prompt_name`: `day13-chat`
  - `prompt_label`: `production`
  - `prompt_version`: `v1`
  - `prompt_source`: `langfuse`
