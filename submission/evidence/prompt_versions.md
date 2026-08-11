# Prompt Versioning Evidence

Prompt Name: `day13-chat`

## Prompt Template Contract
```text
Feature={{feature}}
Docs={{docs}}
Question={{message}}
```

## Phiên bản Prompt

### 1. Version 1 (Baseline & Initial Production)
- **Prompt Text:**
  ```text
  Feature={{feature}}
  Docs={{docs}}
  Question={{message}}
  
  Answer concisely based on provided docs.
  ```
- **Labels:** `baseline`, `production` (khi khởi tạo)
- **Version ID:** `v1`
- **Trace ID đại diện (baseline):** `tr-977f1e2a` (Label: `baseline`, Version: `v1`)
- **Trace ID đại diện (production):** `tr-06271254` (Label: `production`, Version: `v1`)

### 2. Version 2 (Candidate)
- **Prompt Text:**
  ```text
  Feature={{feature}}
  Docs={{docs}}
  Question={{message}}
  
  Provide a detailed step-by-step breakdown using bullet points based strictly on the docs.
  ```
- **Labels:** `candidate`
- **Version ID:** `v2`
- **Trace ID đại diện:** `tr-2a995b1b` (Label: `candidate`, Version: `v2`)
