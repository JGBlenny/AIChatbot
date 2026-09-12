# 知識庫動作系統 - 快速參考

> 快速參考指南，完整文檔請見 [KNOWLEDGE_ACTION_SYSTEM_DESIGN.md](./KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)（該檔 2026-09-11 已加註：動作**執行**機制已隨舊鏈退役，`action_type`／`api_config`欄位寫得進去但新線不會執行，詳見該檔檔頭）

> ⚠️ **2026-09-11**：下方 `action_type` 選擇指南與 SQL 配置範例描述的是**資料庫欄位**，欄位本身仍存在；但文末「程式碼修改」checklist 提到的 `chat.py`／`form_manager.py`／`api_call_handler.py` 已隨舊 REST 對話鏈於 2026-09-11 砍除（見 `.claude/DECISIONS.md` DSP-046），agentic-MCP 新線不讀 `action_type` 觸發任何行為——照本文配置 SQL 寫得進去，但不會有對應的表單／API 呼叫發生。

---

## 🎯 action_type 選擇指南

| 場景 | action_type | 使用時機 |
|-----|-------------|---------|
| 純 FAQ | `direct_answer` | 用戶問靜態問題，如「租金怎麼繳」 |
| 收集資料 | `form_fill` | 需要收集資訊但不調用 API，如「我想租房」 |
| 已登入查詢 | `api_call` | 用戶已登入，直接查詢數據，如「我的帳單」 |
| 未登入查詢 | `form_then_api` | 需要先收集身份再查詢，如訪客查帳單 |
| 提交申請 | `form_then_api` | 收集資料並提交，如「我要報修」 |

---

## 📋 快速配置範例

### 1. 純知識問答

```sql
INSERT INTO knowledge_base (question_summary, answer, action_type)
VALUES (
    '如何繳納租金',
    '租金繳納方式：\n1. 線上信用卡\n2. ATM轉帳...',
    'direct_answer'
);
```

### 2. 表單填寫

```sql
INSERT INTO knowledge_base (question_summary, answer, action_type, form_id)
VALUES (
    '租房申請',
    '感謝您的申請！我們會盡快與您聯繫。',
    'form_fill',
    'rental_application'
);
```

### 3. API 查詢（已登入）

```sql
INSERT INTO knowledge_base (question_summary, answer, action_type, api_config)
VALUES (
    '帳單查詢（已登入）',
    '如仍未收到，請聯繫客服。',
    'api_call',
    '{
        "endpoint": "billing_inquiry",
        "params": {"user_id": "{session.user_id}"},
        "combine_with_knowledge": true
    }'::jsonb
);
```

### 4. 表單 + API（未登入）

```sql
-- 知識庫配置
INSERT INTO knowledge_base (question_summary, answer, action_type, form_id, api_config)
VALUES (
    '帳單查詢（未登入）',
    '如仍未收到，請聯繫客服。',
    'form_then_api',
    'billing_inquiry_guest',
    '{
        "endpoint": "billing_inquiry",
        "params_from_form": {
            "user_id": "tenant_id",
            "month": "inquiry_month"
        },
        "combine_with_knowledge": true
    }'::jsonb
);

-- 表單配置
INSERT INTO form_schemas (form_id, fields, on_complete_action, api_config)
VALUES (
    'billing_inquiry_guest',
    '[
        {"name": "tenant_id", "label": "租客編號", "type": "text"},
        {"name": "inquiry_month", "label": "查詢月份", "type": "text"}
    ]'::jsonb,
    'call_api',
    '{
        "endpoint": "billing_inquiry",
        "param_mapping": {
            "user_id": "tenant_id",
            "month": "inquiry_month"
        }
    }'::jsonb
);
```

---

## 🔧 api_config 常用結構

### 基本配置

```json
{
  "endpoint": "billing_inquiry",
  "params": {
    "user_id": "{session.user_id}"
  },
  "combine_with_knowledge": true
}
```

### 從表單取參數

```json
{
  "endpoint": "billing_inquiry",
  "params_from_form": {
    "user_id": "tenant_id",
    "month": "inquiry_month"
  },
  "combine_with_knowledge": true
}
```

### 身份驗證

```json
{
  "endpoint": "billing_inquiry",
  "verify_identity_first": true,
  "verification_params": {
    "tenant_id": "tenant_id",
    "id_last_4": "verification_code"
  },
  "params_from_form": {...}
}
```

### 自訂回應模板

```json
{
  "endpoint": "billing_inquiry",
  "combine_with_knowledge": false,
  "response_template": "✅ 查詢結果：\n{api_response}"
}
```

### 失敗降級

```json
{
  "endpoint": "billing_inquiry",
  "fallback_message": "目前無法查詢，請稍後再試。\n\n{knowledge_answer}"
}
```

---

## 🎛️ combine_with_knowledge 決策

| 設定 | 使用時機 | 範例 |
|-----|---------|------|
| `true` | 知識答案有補充資訊 | 帳單查詢 + FAQ提示 |
| `false` | 只需要 API 結果 | 報修單號、繳費記錄 |

---

## 🚦 決策流程圖

```
用戶問題
    ↓
需要收集資訊嗎？
    ├─ 否 ──→ 需要實時數據嗎？
    │          ├─ 否 ──→ direct_answer
    │          └─ 是 ──→ api_call
    │
    └─ 是 ──→ 收集後需要調用 API 嗎？
               ├─ 否 ──→ form_fill
               └─ 是 ──→ form_then_api
```

---

## 🔍 參數來源語法

| 語法 | 說明 | 範例 |
|-----|------|------|
| `{session.user_id}` | 從 session 取得 | 已登入用戶 ID |
| `{form.field_name}` | 從表單取得 | 表單欄位值 |
| `{vendor.id}` | 從業者配置取得 | 業者 ID |
| `{user_input.field}` | 從用戶輸入取得 | 動態詢問 |

---

## 📊 常見場景速查

### 場景：帳單查詢

| 用戶狀態 | action_type | 需要表單 | 需要 API |
|---------|-------------|---------|---------|
| 已登入 | `api_call` | ❌ | ✅ |
| 未登入 | `form_then_api` | ✅ | ✅ |

### 場景：報修申請

| 步驟 | 配置 |
|-----|------|
| 1. 收集報修資訊 | `form_then_api` + 表單 |
| 2. 提交到系統 | 表單完成後調用 API |
| 3. 返回報修單號 | `combine_with_knowledge: false` |

### 場景：租房申請

| 步驟 | 配置 |
|-----|------|
| 1. 收集申請人資訊 | `form_fill` |
| 2. 儲存到資料庫 | 表單提交 |
| 3. 顯示下一步說明 | 知識庫答案 |

---

## ⚡ 實作檢查清單

### 資料庫準備
- [ ] 添加 `knowledge_base.action_type` 欄位
- [ ] 添加 `knowledge_base.api_config` 欄位
- [ ] 添加 `form_schemas.on_complete_action` 欄位
- [ ] 添加 `form_schemas.api_config` 欄位
- [ ] 創建索引

### 程式碼修改
- [ ] 修改 `chat.py` 的 `_build_knowledge_response`
- [ ] 修改 `form_manager.py` 的 `_complete_form`
- [ ] 創建 `api_call_handler.py`
- [ ] 創建 `billing_api.py`

### 測試
- [ ] 單元測試
- [ ] 集成測試
- [ ] 手動測試各場景

---

## 🐛 常見問題

**Q: 如何在表單中間調用 API？**
A: 目前不支援，只能在表單完成後調用。

**Q: API 失敗怎麼辦？**
A: 配置 `fallback_message`，系統會自動降級。

**Q: 如何決定 combine_with_knowledge？**
A: 如果知識答案有補充價值（FAQ、提示）→ `true`，否則 `false`。

**Q: 多個 API 調用怎麼處理？**
A: 使用 `verify_identity_first` 配置兩階段 API 調用。

---

## 📚 相關文檔

- [完整設計文檔](./KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
- [表單管理系統](../features/FORM_MANAGEMENT_SYSTEM.md)
- [API 參考](../api/API_REFERENCE_PHASE1.md)

---

**最後更新**: 2026-01-16
