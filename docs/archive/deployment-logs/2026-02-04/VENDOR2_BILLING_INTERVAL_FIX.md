# 業者 2 電費寄送區間查詢功能修正報告

**日期**: 2026-02-04
**問題**: 業者 2 無法觸發電費寄送區間查詢表單
**狀態**: ✅ 已修復並測試通過

---

## 問題描述

業者 1 (甲山林) 可以正常觸發電費寄送區間查詢表單，但業者 2 (信義包租代管) 卻無法觸發，返回「我目前沒有找到符合您問題的資訊」。

### 測試結果對比

| 項目 | 業者 1 | 業者 2 (修正前) | 業者 2 (修正後) |
|------|--------|----------------|----------------|
| 表單觸發 | ✅ 成功 | ❌ 失敗 | ✅ 成功 |
| Form ID | billing_address_form | - | billing_address_form_v2 |
| 知識庫檢索 | ID 1296 (分數 0.978) | 0 筆結果 | ID 1297 |

---

## 根本原因

知識庫項目 ID 1297 的配置錯誤，導致無法通過檢索 SQL 的 WHERE 條件：

### 錯誤配置

```sql
-- ID 1297 (業者 2) - 錯誤配置
vendor_id = 2
scope = 'global'           -- ❌ 錯誤！
business_types = NULL      -- ❌ 錯誤！
```

### SQL WHERE 條件

```sql
WHERE
    -- Scope 過濾
    (
        (kb.vendor_id = %s AND kb.scope IN ('customized', 'vendor'))
        OR
        (kb.vendor_id IS NULL AND kb.scope = 'global')
    )
    -- 業態類型過濾
    AND (kb.business_types IS NULL OR kb.business_types && %s::text[])
```

### 為什麼失敗？

ID 1297 的配置 `vendor_id = 2, scope = 'global'` 無法滿足任何一個條件：

1. **第一個條件**: `vendor_id = 2 AND scope IN ('customized', 'vendor')`
   ❌ 失敗：scope 是 'global'，不在 IN 列表中

2. **第二個條件**: `vendor_id IS NULL AND scope = 'global'`
   ❌ 失敗：vendor_id = 2，不是 NULL

---

## 修正內容

### 1. 資料庫修正 (本地環境)

```sql
UPDATE knowledge_base
SET
    scope = 'customized',
    business_types = ARRAY['property_management', 'full_service']::text[]
WHERE id = 1297;
```

### 2. 更新匯入腳本

已更新以下檔案，確保生產環境匯入時包含正確配置：

#### `database/seeds/import_vendor2_only.sql`

```sql
INSERT INTO knowledge_base (
    id,
    question_summary,
    answer,
    trigger_mode,
    form_id,
    immediate_prompt,
    trigger_keywords,
    target_user,
    action_type,
    vendor_id,
    keywords,
    priority,
    is_active,
    scope,                -- ✅ 新增
    business_types        -- ✅ 新增
) VALUES (
    1297,
    '查詢電費帳單寄送區間（單月/雙月）',
    E'...',
    'auto',
    'billing_address_form_v2',
    NULL,
    ARRAY['電費', '寄送', '區間', '單月', '雙月', '帳單'],
    ARRAY['tenant', 'customer', 'landlord', 'property_manager'],
    'form_fill',
    2,
    ARRAY['電費', '寄送區間', '單月', '雙月', '繳費時間', '帳單'],
    100,
    TRUE,
    'customized',                                              -- ✅ 修正
    ARRAY['property_management', 'full_service']::text[]       -- ✅ 修正
)
ON CONFLICT (id) DO UPDATE SET
    ...
    scope = EXCLUDED.scope,                                    -- ✅ 新增
    business_types = EXCLUDED.business_types,                  -- ✅ 新增
    updated_at = NOW();
```

#### `database/exports/billing_interval_complete_data.sql`

同樣新增 `scope` 和 `business_types` 欄位。

---

## 測試驗證

### 測試 1: 表單觸發 (業者 2)

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想查詢電費寄送區間",
    "vendor_id": 2,
    "user_role": "customer",
    "user_id": "test_user",
    "session_id": "local_test_003"
  }'
```

**結果**:
```json
{
  "form_triggered": true,
  "form_id": "billing_address_form_v2",
  "current_field": "address",
  "answer": "好的！我來協助您查詢電費寄送區間。請提供以下資訊：\n\n📝 **電費寄送區間查詢**\n\n請提供完整的物件地址（例如：台北市大安區信義路四段1號3樓）\n\n（或輸入「**取消**」結束填寫）"
}
```

✅ **通過**: 表單成功觸發

---

### 測試 2: 完整流程 (業者 2)

```bash
# 步驟 1: 觸發表單
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想查詢電費寄送區間",
    "vendor_id": 2,
    "user_role": "customer",
    "user_id": "test_user",
    "session_id": "test_flow_001"
  }'

# 步驟 2: 提供地址
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "新北市新莊區新北大道七段312號10樓",
    "vendor_id": 2,
    "user_role": "customer",
    "user_id": "test_user",
    "session_id": "test_flow_001"
  }'
```

**結果**:
```json
{
  "form_completed": true,
  "answer": "✅ 查詢成功\n\n📋 **查詢結果**\n\n**地址**: 新北市新莊區新北大道七段312號10樓\n**寄送區間**: 雙月\n\n**說明**:  \n該物件的電費帳單採「雙月」寄送，台電會在雙數月（2、4、6、8、10、12月）寄發帳單。\n\n如有其他問題，請隨時聯繫我們！"
}
```

✅ **通過**: 完整流程正常運作

---

## 資料庫狀態驗證

### 知識庫配置對比

```sql
SELECT
    id,
    vendor_id,
    scope,
    business_types,
    question_summary
FROM knowledge_base
WHERE id IN (1296, 1297);
```

| id | vendor_id | scope | business_types | question_summary |
|----|-----------|-------|----------------|------------------|
| 1296 | 1 | customized | {property_management,full_service} | 查詢電費帳單寄送區間（單月/雙月） |
| 1297 | 2 | customized | {property_management,full_service} | 查詢電費帳單寄送區間（單月/雙月） |

✅ **一致**: 兩個業者的配置現已一致

---

## 影響範圍

### 已修改檔案

1. `database/seeds/import_vendor2_only.sql` - 業者 2 匯入腳本
2. `database/exports/billing_interval_complete_data.sql` - 完整匯出腳本
3. `docs/VENDOR2_BILLING_INTERVAL_FIX.md` - 本修正報告

### 資料庫變更

- 本地環境: ✅ 已直接更新 ID 1297
- 生產環境: 需執行更新後的匯入腳本

---

## 部署建議

### 生產環境部署

```bash
# 選項 1: 直接更新現有資料 (推薦)
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  UPDATE knowledge_base
  SET
      scope = 'customized',
      business_types = ARRAY['property_management', 'full_service']::text[]
  WHERE id = 1297;
"

# 選項 2: 重新執行完整匯入 (會覆蓋所有配置)
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/exports/billing_interval_complete_data.sql
```

### 驗證步驟

1. 執行更新 SQL
2. 重啟服務: `docker-compose restart rag-orchestrator`
3. 測試業者 2 表單觸發
4. 測試完整查詢流程

---

## 經驗教訓

### 問題根源

1. **欄位缺失**: 初始匯入腳本未包含 `scope` 和 `business_types` 欄位
2. **預設值錯誤**: 系統預設 `scope = 'global'` 不適用於業者專屬知識
3. **測試不足**: 業者 2 配置未經完整測試即上線

### 改進措施

1. ✅ 所有匯入腳本必須包含完整欄位定義
2. ✅ 新業者配置必須與現有業者對齊
3. ✅ 部署前必須執行跨業者測試
4. ✅ 建立標準化的業者配置檢查清單

---

## 相關檔案

- 業者 2 匯入腳本
- 完整匯出腳本
- [檔案索引](./BILLING_INTERVAL_FILES_INDEX.md)
- [配置總結](./BILLING_INTERVAL_SETUP_SUMMARY.md)

---

**修正者**: Claude Code
**測試者**: Claude Code
**審核者**: 待審核
**版本**: 1.0
