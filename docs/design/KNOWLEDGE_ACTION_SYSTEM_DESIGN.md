# 知識庫動作系統設計文檔

**版本**: 1.1
**日期**: 2026-02-03（更新）
**狀態**: 已實現
**作者**: 系統架構團隊

---

## 📋 目錄

1. [概述](#概述)
2. [背景與問題](#背景與問題)
3. [系統架構設計](#系統架構設計)
4. [場景分析](#場景分析)
5. [資料庫設計](#資料庫設計)
6. [配置範例](#配置範例)
7. [處理邏輯](#處理邏輯)
8. [實作指南](#實作指南)
9. [測試建議](#測試建議)
10. [最佳實踐](#最佳實踐)

---

## 概述

### 系統目標

設計一套統一的知識庫動作系統，支援以下功能組合：

- ✅ **純知識問答**：直接返回 FAQ 答案
- ✅ **表單填寫**：收集結構化資料
- ✅ **API 調用**：查詢實時數據
- ✅ **表單 + API**：先收集資訊再調用 API
- ✅ **混合模式**：組合知識答案與 API 結果

### 核心概念

**知識庫 = 觸發器 + 行為定義 + 回應模板**

每筆知識可以定義：
1. **觸發條件**：用戶問什麼問題時觸發
2. **行為類型**：觸發後執行什麼動作（表單/API/直接回答）
3. **回應方式**：如何呈現結果給用戶

---

## 背景與問題

### 業務需求

在 AI 客服系統中，用戶的問題可以分為三大類：

1. **資訊查詢類**：「租金怎麼繳？」→ 靜態知識，直接回答
2. **資料收集類**：「我想租房子」→ 需要收集用戶資訊
3. **實時查詢類**：「我的帳單怎麼沒收到」→ 需要查詢即時數據

### 實際案例：帳單查詢

**場景 1：已登入用戶**
```
用戶：「我的帳單怎麼沒收到」
系統：已知 user_id → 直接調用 API → 返回帳單狀態
```

**場景 2：未登入用戶**
```
用戶：「我的帳單怎麼沒收到」
系統：需要驗證身份 → 觸發表單收集資訊 → 調用 API → 返回結果
```

**場景 3：只是詢問流程**
```
用戶：「帳單怎麼寄送？」
系統：這是 FAQ → 直接返回知識庫答案
```

### 問題

現有系統只支援「表單觸發」模式（通過 `form_id` 欄位），無法靈活處理「API 調用」或「表單 + API」組合。

---

## 系統架構設計

### 核心架構

```
用戶問題
    ↓
意圖分類
    ↓
檢索知識庫（向量搜索 + 意圖過濾）
    ↓
檢查知識的 action_type
    ↓
根據 action_type 執行對應動作
    ├─ direct_answer    → 直接返回知識答案
    ├─ form_fill        → 檢查 trigger_mode
    │   ├─ NULL/auto   → 直接觸發表單 → 返回知識答案
    │   ├─ manual      → 顯示內容 + 等待關鍵詞 → 觸發表單
    │   └─ immediate   → 顯示內容 + 立即詢問 → 等待關鍵詞 → 觸發表單
    ├─ api_call         → 調用 API → 結合知識答案
    └─ form_then_api    → 觸發表單 → 調用 API → 結合知識答案
```

### 設計原則

1. **統一入口**：所有功能都通過知識庫觸發，保持架構一致性
2. **配置驅動**：行為由配置決定，不需要修改程式碼
3. **可組合性**：表單、API、知識答案可靈活組合
4. **向後兼容**：保持與現有表單系統的兼容性

---

## 場景分析

### 場景矩陣

| 場景 | 表單 | API | 知識答案 | action_type | 範例 |
|-----|------|-----|---------|-------------|------|
| **A** | ❌ | ❌ | ✅ | `direct_answer` | 「如何繳納租金」 |
| **B** | ✅ | ❌ | ✅ | `form_fill` | 「我想租房子」 |
| **C** | ❌ | ✅ | ✅ | `api_call` | 「我的帳單」（已登入）|
| **D** | ✅ | ✅ | ✅ | `form_then_api` | 「我的帳單」（未登入）|
| **E** | ✅ | ✅ | ❌ | `form_then_api` | 「我要報修」|
| **F** | ❌ | ✅ | ❌ | `api_call` | 「查詢繳費記錄」|

### 場景 A：純知識問答

**用戶問題**：「租金怎麼繳？」

**流程**：
```
檢索知識庫 → action_type = "direct_answer" → 直接返回答案
```

**配置**：
```json
{
  "question_summary": "如何繳納租金",
  "answer": "租金繳納方式：\n1. 線上信用卡\n2. ATM轉帳\n3. 超商繳費",
  "action_type": "direct_answer"
}
```

---

### 場景 B：表單 + 知識

**用戶問題**：「我想租房子」

**流程**：
```
檢索知識庫 → action_type = "form_fill" → 觸發表單 → 收集資料 → 返回知識答案
```

**配置**：
```json
{
  "question_summary": "租房申請",
  "answer": "感謝您的申請！我們會在 24 小時內與您聯繫。",
  "action_type": "form_fill",
  "form_id": "rental_application"
}
```

**對話範例**：
```
用戶：「我想租房子」
AI：「好的！請填寫以下資訊：」
AI：「請提供您的姓名：」
用戶：「王小明」
AI：「請提供您的電話：」
用戶：「0912345678」
AI：「請提供您的預算：」
用戶：「20000」
AI：「✅ 表單填寫完成！
     感謝您的申請！我們會在 24 小時內與您聯繫。」
```

---

### 場景 C：API + 知識（已登入用戶）

**用戶問題**：「我的帳單怎麼沒收到」（已登入）

**流程**：
```
檢索知識庫 → action_type = "api_call"
    → 檢查參數（user_id 從 session 取得）
    → 調用 API
    → 結合知識答案返回
```

**配置**：
```json
{
  "question_summary": "帳單查詢（已登入）",
  "answer": "如仍未收到，建議檢查垃圾郵件或聯繫客服 {{service_hotline}}。",
  "action_type": "api_call",
  "api_config": {
    "endpoint": "billing_inquiry",
    "params": {
      "user_id": "{session.user_id}",
      "month": "{user_input.month}"
    },
    "combine_with_knowledge": true,
    "response_template": "查詢結果：\n{api_response}\n\n{knowledge_answer}"
  }
}
```

**對話範例**：
```
用戶：「我的帳單怎麼沒收到」
AI：「查詢中...」（調用 API）
AI：「查詢結果：
     📄 帳單編號：INV-2026-01-001
     💰 金額：$15,000
     📅 到期日：2026-01-05

     寄送狀態：✅ 已寄送
     寄送時間：01/01 10:00
     寄送信箱：user_***@example.com

     如仍未收到，建議檢查垃圾郵件或聯繫客服 02-1234-5678。」
```

---

### 場景 D：表單 + API + 知識（未登入用戶）

**用戶問題**：「我的帳單怎麼沒收到」（未登入）

**流程**：
```
檢索知識庫 → action_type = "form_then_api"
    → 觸發表單收集身份資訊
    → 表單完成後自動調用 API
    → 結合知識答案返回
```

**配置**：
```json
{
  "question_summary": "帳單查詢（未登入）",
  "answer": "如仍未收到，建議檢查垃圾郵件或聯繫客服。",
  "action_type": "form_then_api",
  "form_id": "billing_inquiry_guest",
  "api_config": {
    "endpoint": "billing_inquiry",
    "verify_identity_first": true,
    "params_from_form": {
      "user_id": "tenant_id",
      "month": "inquiry_month"
    },
    "verification_params": {
      "tenant_id": "tenant_id",
      "id_last_4": "verification_code"
    },
    "combine_with_knowledge": true
  }
}
```

**對話範例**：
```
用戶：「我的帳單怎麼沒收到」
AI：「為了保護您的隱私，需要驗證身份。」
AI：「請提供租客編號：」
用戶：「T12345」
AI：「請提供身份證後4碼：」
用戶：「1234」
AI：「查詢哪個月份的帳單？（例如：2026-01）」
用戶：「2026-01」
AI：「驗證中...」（驗證身份 API）
AI：「✅ 身份驗證通過！」（調用帳單查詢 API）
AI：「查詢結果：
     📄 帳單編號：INV-2026-01-001
     💰 金額：$15,000
     ...

     如仍未收到，建議檢查垃圾郵件或聯繫客服。」
```

---

### 場景 E：表單 + API（不需要知識答案）

**用戶問題**：「我要報修」

**流程**：
```
檢索知識庫 → action_type = "form_then_api"
    → 觸發表單收集報修資訊
    → 表單完成後調用報修提交 API
    → 只返回 API 結果（不結合知識答案）
```

**配置**：
```json
{
  "question_summary": "報修申請",
  "answer": null,
  "action_type": "form_then_api",
  "form_id": "repair_request",
  "api_config": {
    "endpoint": "repair_submit",
    "params_from_form": {
      "user_id": "session.user_id",
      "item": "repair_item",
      "description": "description",
      "urgency": "urgency"
    },
    "combine_with_knowledge": false,
    "response_template": "✅ 報修申請已提交！\n\n🔧 報修單號：{ticket_id}\n📅 預計處理時間：{estimated_time}\n📞 如有疑問請撥：{{service_hotline}}"
  }
}
```

**對話範例**：
```
用戶：「我要報修」
AI：「請提供報修項目：」
用戶：「冷氣不冷」
AI：「請描述問題：」
用戶：「冷氣開了但完全不冷，可能壞掉了」
AI：「請選擇緊急程度：[一般] [緊急] [非常緊急]」
用戶：「緊急」
AI：「✅ 報修申請已提交！

     🔧 報修單號：R-2026-001
     📅 預計處理時間：24小時內
     📞 如有疑問請撥：02-1234-5678」
```

---

### 場景 F：純 API（不需要知識答案）

**用戶問題**：「查詢我的繳費記錄」

**流程**：
```
檢索知識庫 → action_type = "api_call"
    → 調用 API
    → 只返回 API 結果（格式化的列表）
```

**配置**：
```json
{
  "question_summary": "繳費記錄查詢",
  "answer": null,
  "action_type": "api_call",
  "api_config": {
    "endpoint": "payment_history",
    "params": {
      "user_id": "{session.user_id}",
      "limit": "10"
    },
    "combine_with_knowledge": false,
    "response_template": "📋 **您的繳費記錄**\n\n{formatted_history}"
  }
}
```

---

## 資料庫設計

### knowledge_base 表擴展

```sql
-- 添加欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS action_type VARCHAR(50) DEFAULT 'direct_answer',
ADD COLUMN IF NOT EXISTS api_config JSONB;

-- 添加註解
COMMENT ON COLUMN knowledge_base.action_type IS '
行為類型：
- direct_answer: 純知識問答
- form_fill: 觸發表單填寫
- api_call: 調用 API
- form_then_api: 先表單後 API
';

COMMENT ON COLUMN knowledge_base.api_config IS '
API 配置 (JSON):
{
  "endpoint": "billing_inquiry",          // API 端點
  "params": {...},                        // API 參數映射
  "verify_identity_first": true,          // 是否先驗證身份
  "verification_params": {...},           // 驗證參數映射
  "combine_with_knowledge": true,         // 是否結合知識答案
  "response_template": "...",             // 回應模板
  "fallback_message": "..."               // 失敗降級訊息
}
';

-- 添加索引
CREATE INDEX idx_kb_action_type ON knowledge_base(action_type);
CREATE INDEX idx_kb_api_endpoint ON knowledge_base((api_config->>'endpoint'));
```

### form_schemas 表擴展

```sql
-- 添加欄位（支援表單完成後調用 API）
ALTER TABLE form_schemas
ADD COLUMN IF NOT EXISTS on_complete_action VARCHAR(50) DEFAULT 'show_knowledge',
ADD COLUMN IF NOT EXISTS api_config JSONB;

COMMENT ON COLUMN form_schemas.on_complete_action IS '
表單完成後的動作：
- show_knowledge: 顯示知識庫答案
- call_api: 調用 API
- both: 兩者都執行
';

COMMENT ON COLUMN form_schemas.api_config IS '
表單完成後調用的 API 配置 (JSON):
{
  "endpoint": "billing_inquiry",
  "param_mapping": {
    "user_id": "tenant_id",              // 表單欄位 → API 參數
    "month": "inquiry_month"
  },
  "verify_identity_first": true,
  "verification_params": {...},
  "response_template": "..."
}
';
```

### 完整的 api_config 結構

```json
{
  // === 基本配置 ===
  "endpoint": "billing_inquiry",          // API 端點名稱

  // === 參數配置 ===
  "params": {
    "user_id": "{session.user_id}",      // 從 session 取得
    "month": "{form.inquiry_month}",     // 從表單取得
    "vendor_id": "{vendor.id}"           // 從業者配置取得
  },

  // === 或：從表單映射參數 ===
  "params_from_form": {
    "user_id": "tenant_id",              // 表單欄位名 → API 參數名
    "month": "inquiry_month"
  },

  // === 身份驗證配置 ===
  "verify_identity_first": true,         // 是否先驗證身份
  "verification_params": {
    "tenant_id": "tenant_id",
    "id_last_4": "verification_code"
  },

  // === 回應配置 ===
  "combine_with_knowledge": true,        // 是否結合知識答案
  "response_template": "查詢結果：\n{api_response}\n\n{knowledge_answer}",
  "fallback_message": "目前無法查詢，{knowledge_answer}",

  // === 條件配置 ===
  "skip_if": "user.is_logged_in",        // 條件跳過（可選）
  "required_role": "tenant"              // 權限要求（可選）
}
```

---

## 配置範例

### 範例 1：帳單查詢（已登入）

```sql
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    api_config,
    scope,
    is_active
) VALUES (
    '帳單寄送狀態查詢（已登入）',
    '如仍未收到，建議檢查垃圾郵件或聯繫客服 {{service_hotline}}。',
    'api_call',
    '{
        "endpoint": "billing_inquiry",
        "params": {
            "user_id": "{session.user_id}",
            "month": "{user_input.month}"
        },
        "combine_with_knowledge": true,
        "response_template": "查詢結果：\n\n{api_response}\n\n{knowledge_answer}",
        "fallback_message": "目前無法查詢帳單狀態。\n\n{knowledge_answer}"
    }'::jsonb,
    'global',
    true
);
```

### 範例 2：帳單查詢（未登入）- 知識庫配置

```sql
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    form_id,
    api_config,
    scope,
    is_active
) VALUES (
    '帳單寄送狀態查詢（未登入）',
    '如仍未收到，建議檢查垃圾郵件或聯繫客服。',
    'form_then_api',
    'billing_inquiry_guest',
    '{
        "endpoint": "billing_inquiry",
        "verify_identity_first": true,
        "verification_params": {
            "tenant_id": "tenant_id",
            "id_last_4": "verification_code"
        },
        "params_from_form": {
            "user_id": "tenant_id",
            "month": "inquiry_month"
        },
        "combine_with_knowledge": true,
        "response_template": "✅ 身份驗證通過！\n\n查詢結果：\n{api_response}\n\n{knowledge_answer}"
    }'::jsonb,
    'global',
    true
);
```

### 範例 2：帳單查詢（未登入）- 表單配置

```sql
INSERT INTO form_schemas (
    form_id,
    form_name,
    description,
    fields,
    trigger_intents,
    on_complete_action,
    api_config,
    is_active
) VALUES (
    'billing_inquiry_guest',
    '帳單查詢（訪客）',
    '未登入用戶查詢帳單時的身份驗證表單',
    '[
        {
            "name": "tenant_id",
            "label": "租客編號（合約上的編號）",
            "type": "text",
            "required": true,
            "validation": {
                "pattern": "^T\\d+$",
                "message": "請輸入正確的租客編號格式（例如：T12345）"
            }
        },
        {
            "name": "verification_code",
            "label": "身份證後4碼",
            "type": "text",
            "required": true,
            "validation": {
                "pattern": "^\\d{4}$",
                "message": "請輸入4位數字"
            }
        },
        {
            "name": "inquiry_month",
            "label": "查詢月份（例如：2026-01）",
            "type": "text",
            "required": true,
            "validation": {
                "pattern": "^\\d{4}-\\d{2}$",
                "message": "請輸入正確的月份格式（例如：2026-01）"
            }
        }
    ]'::jsonb,
    '["帳單查詢"]'::jsonb,
    'call_api',
    '{
        "endpoint": "billing_inquiry",
        "verify_identity_first": true,
        "verification_params": {
            "tenant_id": "tenant_id",
            "id_last_4": "verification_code"
        },
        "param_mapping": {
            "user_id": "tenant_id",
            "month": "inquiry_month"
        },
        "combine_with_knowledge": true,
        "response_template": "✅ 身份驗證通過！\n\n{api_response}\n\n{knowledge_answer}",
        "fallback_message": "驗證失敗或無法查詢。\n\n{knowledge_answer}"
    }'::jsonb,
    true
);
```

### 範例 3：報修申請

```sql
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    form_id,
    api_config,
    scope,
    is_active
) VALUES (
    '報修申請',
    null,
    'form_then_api',
    'repair_request',
    '{
        "endpoint": "repair_submit",
        "params_from_form": {
            "user_id": "session.user_id",
            "item": "repair_item",
            "description": "description",
            "urgency": "urgency"
        },
        "combine_with_knowledge": false,
        "response_template": "✅ 報修申請已提交！\n\n🔧 報修單號：{ticket_id}\n📅 預計處理時間：{estimated_time}\n📞 如有疑問請撥：{{service_hotline}}"
    }'::jsonb,
    'global',
    true
);
```

---

## 處理邏輯

### 主要流程（chat.py）

```python
async def _build_knowledge_response(
    request: VendorChatRequest,
    req: Request,
    intent_result: dict,
    knowledge_list: list,
    resolver,
    vendor_info: dict,
    cache_service
) -> VendorChatResponse:
    """使用知識庫結果構建優化回應"""

    if not knowledge_list:
        return await _handle_no_knowledge_found(...)

    best_knowledge = knowledge_list[0]
    action_type = best_knowledge.get('action_type', 'direct_answer')

    # === 決策樹 ===

    if action_type == 'direct_answer':
        # 場景 A：純知識問答
        return await _build_simple_answer(
            best_knowledge, request, intent_result
        )

    elif action_type == 'form_fill':
        # 場景 B：觸發表單
        form_id = best_knowledge.get('form_id')
        if not form_id:
            raise ValueError(f"Knowledge {best_knowledge['id']} has action_type=form_fill but no form_id")

        return await _trigger_form(
            form_id=form_id,
            knowledge_id=best_knowledge['id'],
            request=request,
            req=req
        )

    elif action_type == 'api_call':
        # 場景 C/F：直接調用 API
        api_config = best_knowledge.get('api_config')
        if not api_config:
            raise ValueError(f"Knowledge {best_knowledge['id']} has action_type=api_call but no api_config")

        # 檢查參數是否齊全
        params_check = await _check_api_params(api_config, request)

        if not params_check['all_ready']:
            # 缺少參數 → 詢問用戶或觸發表單
            if api_config.get('use_form_for_params'):
                return await _trigger_form(
                    form_id=api_config['form_id'],
                    knowledge_id=best_knowledge['id'],
                    request=request,
                    req=req
                )
            else:
                return _ask_missing_params(
                    params_check['missing'],
                    request,
                    intent_result
                )

        # 參數齊全 → 調用 API
        api_result = await _call_api(api_config, params_check['params'], request)

        # 格式化回應
        combine_knowledge = api_config.get('combine_with_knowledge', True)
        if combine_knowledge and best_knowledge.get('answer'):
            return _format_api_with_knowledge(
                api_result, best_knowledge, api_config, request, intent_result
            )
        else:
            return _format_api_only(
                api_result, api_config, request, intent_result
            )

    elif action_type == 'form_then_api':
        # 場景 D/E：先表單後 API
        form_id = best_knowledge.get('form_id')
        if not form_id:
            raise ValueError(f"Knowledge {best_knowledge['id']} has action_type=form_then_api but no form_id")

        # 觸發表單（表單完成後會自動調用 API）
        return await _trigger_form_with_api(
            form_id=form_id,
            knowledge_id=best_knowledge['id'],
            api_config=best_knowledge.get('api_config'),
            request=request,
            req=req
        )

    else:
        raise ValueError(f"Unknown action_type: {action_type}")
```

### 決策樹圖示

```
用戶問題
    ↓
意圖分類
    ↓
檢索知識庫
    ↓
檢查 action_type
    ↓
    ├─ direct_answer ──────────→ 直接返回知識答案
    │
    ├─ form_fill ──────────────→ 觸發表單
    │                              ↓
    │                          表單完成
    │                              ↓
    │                          返回知識答案
    │
    ├─ api_call ───────────────→ 檢查參數
    │                              ├─ 參數不足 → 詢問用戶或觸發表單
    │                              └─ 參數齊全 → 調用 API
    │                                             ↓
    │                                         成功/失敗
    │                                             ↓
    │                                         格式化回應
    │                                             ├─ combine=true → API結果 + 知識答案
    │                                             └─ combine=false → 只返回 API 結果
    │
    └─ form_then_api ──────────→ 觸發表單
                                   ↓
                               表單完成
                                   ↓
                               調用 API（自動從表單取參數）
                                   ↓
                               格式化回應
```

---

## 實作指南

### Phase 1：資料庫準備（30 分鐘）

```sql
-- Step 1: 添加欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS action_type VARCHAR(50) DEFAULT 'direct_answer',
ADD COLUMN IF NOT EXISTS api_config JSONB;

ALTER TABLE form_schemas
ADD COLUMN IF NOT EXISTS on_complete_action VARCHAR(50) DEFAULT 'show_knowledge',
ADD COLUMN IF NOT EXISTS api_config JSONB;

-- Step 2: 添加索引
CREATE INDEX idx_kb_action_type ON knowledge_base(action_type);
CREATE INDEX idx_kb_api_endpoint ON knowledge_base((api_config->>'endpoint'));

-- Step 3: 更新現有知識的 action_type
UPDATE knowledge_base
SET action_type = 'form_fill'
WHERE form_id IS NOT NULL;

UPDATE knowledge_base
SET action_type = 'direct_answer'
WHERE form_id IS NULL AND action_type IS NULL;
```

### Phase 2：創建 API 服務（1-2 天）

**檔案結構**：
```
rag-orchestrator/services/
├── billing_api.py          # 帳單查詢 API 服務
├── api_call_handler.py     # 統一的 API 調用處理器
└── form_manager.py         # 修改：添加表單完成後調用 API
```

**billing_api.py**：
```python
"""
帳單查詢 API 服務
整合 JGB 主系統的帳單查詢功能
"""
import httpx
import os
from typing import Optional, Dict

class BillingAPIService:
    def __init__(self):
        self.base_url = os.getenv("JGB_BILLING_API_URL")
        self.api_key = os.getenv("JGB_BILLING_API_KEY")
        self.timeout = 10.0

    async def get_invoice_status(
        self,
        user_id: str,
        month: Optional[str] = None,
        requester_role: str = 'tenant'
    ) -> Dict:
        """查詢帳單狀態"""
        # 實作邏輯...
        pass

    async def verify_tenant_identity(
        self,
        tenant_id: str,
        id_last_4: str
    ) -> Dict:
        """驗證租客身份"""
        # 實作邏輯...
        pass
```

### Phase 3：修改處理邏輯（2-3 天）

**修改 chat.py**：
1. 在 `_build_knowledge_response` 添加 action_type 檢查
2. 實作各種 action_type 的處理邏輯
3. 添加參數檢查與收集機制

**修改 form_manager.py**：
1. 在 `_complete_form` 添加 API 調用邏輯
2. 實作 `_execute_form_api` 方法
3. 實作 `_verify_user_identity` 方法
4. 實作 `_format_completion_message` 方法

### Phase 4：測試與驗證（1-2 天）

**測試案例**：
1. 場景 A：純知識問答
2. 場景 B：表單填寫
3. 場景 C：已登入用戶 API 查詢
4. 場景 D：未登入用戶表單 + API
5. 場景 E：報修申請（表單 + API，無知識答案）
6. API 失敗降級測試
7. 參數驗證測試

---

## 測試建議

### 單元測試

```python
# tests/test_action_system.py

import pytest
from services.api_call_handler import APICallHandler

@pytest.mark.asyncio
async def test_direct_answer():
    """測試場景 A：純知識問答"""
    knowledge = {
        "action_type": "direct_answer",
        "answer": "租金繳納方式：..."
    }
    result = await handle_knowledge(knowledge)
    assert result['answer'] == knowledge['answer']

@pytest.mark.asyncio
async def test_api_call_with_params():
    """測試場景 C：API 調用（參數齊全）"""
    knowledge = {
        "action_type": "api_call",
        "api_config": {
            "endpoint": "billing_inquiry",
            "params": {"user_id": "T12345"}
        }
    }
    result = await handle_knowledge(knowledge)
    assert 'api_response' in result

@pytest.mark.asyncio
async def test_form_then_api():
    """測試場景 D：表單 + API"""
    # 模擬表單完成
    form_data = {
        "tenant_id": "T12345",
        "verification_code": "1234",
        "inquiry_month": "2026-01"
    }
    result = await complete_form_with_api(form_data)
    assert result['form_completed'] == True
    assert 'api_result' in result
```

### 集成測試

```python
# tests/integration/test_billing_inquiry.py

@pytest.mark.asyncio
async def test_billing_inquiry_logged_in():
    """測試：已登入用戶查詢帳單"""
    response = await client.post("/api/v1/message", json={
        "message": "我的帳單怎麼沒收到",
        "vendor_id": 1,
        "user_id": "T12345",
        "session_id": "test_session"
    })
    assert response.status_code == 200
    data = response.json()
    assert "帳單編號" in data['answer']
    assert data['debug_info']['processing_path'] == 'api_call'

@pytest.mark.asyncio
async def test_billing_inquiry_guest():
    """測試：未登入用戶查詢帳單（觸發表單）"""
    # 第一輪：觸發表單
    response1 = await client.post("/api/v1/message", json={
        "message": "我的帳單怎麼沒收到",
        "vendor_id": 1,
        "session_id": "test_session"
    })
    assert "請提供租客編號" in response1.json()['answer']

    # 第二輪：提供租客編號
    response2 = await client.post("/api/v1/message", json={
        "message": "T12345",
        "vendor_id": 1,
        "session_id": "test_session"
    })
    assert "身份證後4碼" in response2.json()['answer']

    # ... 繼續填寫表單
```

### 手動測試檢查清單

- [ ] 場景 A：詢問「租金怎麼繳」→ 直接返回 FAQ
- [ ] 場景 B：詢問「我想租房子」→ 觸發表單 → 返回知識答案
- [ ] 場景 C：已登入用戶詢問「我的帳單」→ 調用 API → 返回結果 + 知識答案
- [ ] 場景 D：未登入用戶詢問「我的帳單」→ 觸發表單 → 調用 API → 返回結果
- [ ] 場景 E：詢問「我要報修」→ 觸發表單 → 調用 API → 只返回 API 結果
- [ ] API 失敗時顯示降級訊息
- [ ] 缺少參數時正確詢問用戶
- [ ] 身份驗證失敗時正確提示

---

## 最佳實踐

### 1. 配置命名規範

**知識庫命名**：
- 格式：`{功能}（{條件}）`
- 範例：
  - `帳單查詢（已登入）`
  - `帳單查詢（未登入）`
  - `報修申請`

**表單 ID 命名**：
- 格式：`{功能}_{角色}`
- 範例：
  - `billing_inquiry_guest`（訪客帳單查詢）
  - `repair_request`（報修申請）
  - `rental_application`（租房申請）

### 2. API 端點命名

**建議使用語義化命名**：
- `billing_inquiry` - 帳單查詢
- `repair_submit` - 報修提交
- `contract_info` - 合約資訊查詢
- `payment_history` - 繳費記錄查詢

### 3. 錯誤處理

**API 調用失敗時的降級策略**：

```json
{
  "api_config": {
    "endpoint": "billing_inquiry",
    "fallback_message": "目前無法查詢帳單狀態。\n\n建議：\n1. 檢查垃圾郵件夾\n2. 聯繫客服 {{service_hotline}}\n\n{knowledge_answer}"
  }
}
```

**表單驗證失敗**：
- 提供清楚的錯誤訊息
- 允許用戶重新輸入
- 記錄驗證失敗次數（防止暴力破解）

### 4. 安全性考量

**身份驗證**：
```json
{
  "api_config": {
    "verify_identity_first": true,
    "verification_params": {
      "tenant_id": "tenant_id",
      "id_last_4": "verification_code"
    }
  }
}
```

**敏感資訊遮罩**：
- Email：`user_***@example.com`
- 手機：`0912***678`
- 身份證：只要求後 4 碼

**頻率限制**：
- 限制每個 session 10 分鐘內最多查詢 10 次
- 身份驗證失敗 3 次後鎖定 1 小時

### 5. 監控與日誌

**關鍵指標**：
- API 調用成功率
- 平均回應時間
- 表單完成率
- 用戶滿意度

**日誌記錄**：
```python
# 記錄 API 調用
logger.info(f"API Call: endpoint={endpoint}, user={user_id}, result={result['status']}")

# 記錄表單完成
logger.info(f"Form Completed: form_id={form_id}, user={user_id}, api_called={api_called}")
```

### 6. 性能優化

**緩存策略**：
- 已登入用戶的帳單狀態緩存 5 分鐘
- API 配置緩存 1 小時
- 知識庫檢索結果緩存 10 分鐘

**異步處理**：
- API 調用使用異步 httpx
- 多個 API 調用時並行處理
- 超時設定：10 秒

---

## 附錄

### A. 完整的 action_type 枚舉

```sql
CREATE TYPE action_type_enum AS ENUM (
    'direct_answer',      -- 純知識問答
    'form_fill',          -- 觸發表單填寫
    'api_call',           -- 調用 API
    'form_then_api'       -- 先表單後 API
);
```

### B. API 端點清單

| 端點名稱 | 功能 | 參數 | 回應 |
|---------|------|------|------|
| `billing_inquiry` | 帳單查詢 | user_id, month | 帳單詳情 |
| `auth/verify_tenant` | 租客身份驗證 | tenant_id, id_last_4 | 驗證結果 |
| `repair_submit` | 報修提交 | user_id, item, description | 報修單號 |
| `payment_history` | 繳費記錄 | user_id, limit | 繳費列表 |
| `contract_info` | 合約資訊 | user_id | 合約詳情 |

### C. 常見問題 (FAQ)

**Q1：如何決定使用 `api_call` 還是 `form_then_api`？**

A：根據是否需要收集參數決定：
- 已登入用戶，參數從 session 取得 → `api_call`
- 未登入用戶，需要收集身份資訊 → `form_then_api`

**Q2：`combine_with_knowledge` 設為 true 還是 false？**

A：
- 如果知識答案有補充資訊（FAQ、注意事項）→ `true`
- 如果只需要 API 結果（如報修單號）→ `false`

**Q3：如何處理 API 失敗？**

A：配置 `fallback_message`，系統會自動降級顯示該訊息。

**Q4：可以在表單中間調用 API 嗎？**

A：目前不支援。API 調用只能在表單完成後觸發。

**Q5：如何支援多步驟 API 調用（如先驗證再查詢）？**

A：使用 `verify_identity_first: true` 配置，系統會自動先調用驗證 API。

---

## 變更歷史

| 版本 | 日期 | 作者 | 變更內容 |
|-----|------|------|---------|
| 1.1 | 2026-02-03 | 系統架構團隊 | 實現 trigger_mode 支援（manual, immediate, auto），統一知識庫與 SOP 觸發機制 |
| 1.0 | 2026-01-16 | 系統架構團隊 | 初始版本 |

---

## 相關文檔

- [知識庫表單觸發模式實現](../features/KNOWLEDGE_FORM_TRIGGER_IMPLEMENTATION.md) - **NEW**
- [SOP 系統完整指南](../guides/SOP_GUIDE.md)
- [表單管理系統](./FORM_MANAGEMENT_SYSTEM.md)
- [API 參考文檔](../api/API_REFERENCE_PHASE1.md)
- [資料庫 Schema](../architecture/DATABASE_SCHEMA.md)
- [知識庫管理指南](../guides/KNOWLEDGE_MANAGEMENT.md)

---

**文檔結束**
