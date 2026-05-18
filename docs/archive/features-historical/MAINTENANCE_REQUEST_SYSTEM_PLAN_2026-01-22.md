# 🔧 維護請求系統規劃 - 基於現有架構

**日期**: 2026-01-22
**規劃者**: Claude Code
**規劃模式**: Ultra Deep Thinking - 現有系統評估 + 重新設計

---

## 📋 執行摘要

### 目標
基於現有的表單系統、知識庫系統和 API 整合功能，實現一個完整的維護請求管理系統，支援：
- 租戶透過對話報修（漏水、冷氣、門鎖等 10 類問題）
- 自動優先級分配（P0/P1/P2/P3）
- 表單引導資訊收集
- SOP 關聯與排查指導
- 維修派工與狀態追蹤

### 核心原則
✅ **最大化利用現有功能** - 不重複造輪子
✅ **最小化資料庫變更** - 優先使用現有表結構
✅ **零侵入性修改** - 不修改核心業務邏輯

---

## 🔍 現有系統評估

### 1. 表單系統 (Form System) ✅ 完整可用

#### 已有資料表
```sql
-- 表單定義
form_schemas (
    id, form_id, form_name,
    trigger_intents JSONB,  -- 觸發意圖
    fields JSONB,            -- 欄位定義
    vendor_id, is_active,
    description, default_intro  -- 2026-01-21 新增
)

-- 表單會話
form_sessions (
    id, session_id, user_id, vendor_id,
    form_id, state,          -- COLLECTING/DIGRESSION/REVIEWING/EDITING/COMPLETED/CANCELLED
    current_field_index,
    collected_data JSONB,    -- 已收集的資料
    started_at, last_activity_at, completed_at, cancelled_at
)

-- 表單提交
form_submissions (
    id, form_session_id, form_id,
    user_id, vendor_id,
    submitted_data JSONB,    -- 完整提交資料
    submitted_at,
    status VARCHAR(50),      -- 2026-01-21 新增：pending/approved/rejected
    notes TEXT,              -- 2026-01-21 新增：審核備註
    updated_at, updated_by
)
```

#### 已有功能
- ✅ **FormManager** (`rag-orchestrator/services/form_manager.py`)
  - 表單會話創建與管理
  - 狀態轉移：COLLECTING → DIGRESSION → REVIEWING → COMPLETED
  - 欄位驗證（FormValidator）
  - 離題偵測與恢復（DigressionDetector）

- ✅ **表單編輯器** (`knowledge-admin/frontend/src/views/FormEditorView.vue`)
  - 可視化表單設計
  - 支援 10+ 種欄位類型：text, textarea, select, number, email, date, checkbox, file_upload 等
  - 欄位條件顯示（show_if）
  - 欄位選項動態配置（conditional_options）

- ✅ **表單審核** (`knowledge-admin/frontend/src/views/FormSubmissionsView.vue`)
  - 提交記錄查看
  - 狀態管理（pending/approved/rejected）
  - 備註編輯

#### 評估結論
**表單系統已非常完整，可直接使用，無需新增資料表或修改核心邏輯。**

---

### 2. 知識庫系統 (Knowledge Base) ✅ 完整可用

#### 已有資料表
```sql
knowledge_base (
    id, question_summary, answer,
    intent_confidence, intent_assigned_by,
    business_types TEXT[],
    target_user TEXT[],
    keywords TEXT[],
    vendor_id, scope, priority,

    -- 表單關聯（2026-01-10 新增）
    form_id VARCHAR(100),                    -- 關聯到 form_schemas
    trigger_form_condition VARCHAR(50),      -- 'always', 'on_missing_info', 'manual'

    -- API 整合（2026-01-21 新增）
    action_type VARCHAR(50),                 -- 'direct_answer', 'form_fill', 'api_call', 'form_then_api'
    api_config JSONB,                        -- {endpoint, params, combine_with_knowledge}

    -- 其他
    embedding VECTOR(1536),
    video_url, video_s3_key,
    is_active, created_at, updated_at
)

CHECK (action_type IN ('direct_answer', 'form_fill', 'api_call', 'form_then_api'))
```

#### 已有功能
- ✅ **VendorKnowledgeRetriever** (`rag-orchestrator/services/vendor_knowledge_retriever.py`)
  - 語義檢索（embedding + cosine similarity）
  - 意圖分類
  - 多條件過濾（business_types, target_user, scope）
  - 優先級排序

- ✅ **動作類型處理** (`rag-orchestrator/routers/chat.py`)
  - `direct_answer`: 直接回答
  - `form_fill`: 觸發表單填寫
  - `api_call`: 直接調用 API
  - `form_then_api`: 先填表單，完成後調用 API

#### 評估結論
**知識庫系統已支援表單關聯和 API 整合，可直接使用。**

---

### 3. API 整合系統 (API Integration) ✅ 完整可用

#### 已有資料表
```sql
api_endpoints (
    id, endpoint_id, endpoint_name, endpoint_icon, description,
    available_in_knowledge BOOLEAN,   -- 是否可在知識庫中使用
    available_in_form BOOLEAN,        -- 是否可在表單中使用
    implementation_type VARCHAR(20),  -- 'dynamic' 或 'custom'

    -- 動態配置（implementation_type = 'dynamic'）
    api_url TEXT,
    http_method VARCHAR(10),
    request_headers JSONB,
    request_body_template JSONB,
    param_mappings JSONB,             -- 參數映射
    response_format_type VARCHAR(50), -- 'template' 或 'json'
    response_template TEXT,

    -- 自定義配置（implementation_type = 'custom'）
    custom_handler_name VARCHAR(100),

    -- 其他
    retry_times INTEGER,
    cache_ttl INTEGER,
    display_order INTEGER,
    vendor_id, is_active
)
```

#### 已有功能
- ✅ **APICallHandler** (`rag-orchestrator/services/api_call_handler.py`)
  - 統一處理 API 調用
  - 支援動態配置和自定義處理兩種模式
  - 參數替換（從 session_data, form_data, user_input 提取）
  - 錯誤處理與降級策略

- ✅ **UniversalAPICallHandler** (`rag-orchestrator/services/universal_api_handler.py`)
  - 通用 API 調用處理器（動態配置）
  - 支援 GET/POST/PUT/DELETE
  - 支援 Header 和 Body 參數映射
  - 支援回應模板化

- ✅ **自定義 API 註冊表**
  ```python
  self.api_registry = {
      'billing_inquiry': self.billing_api.get_invoice_status,
      'verify_tenant_identity': self.billing_api.verify_tenant_identity,
      'resend_invoice': self.billing_api.resend_invoice,
      'maintenance_request': self.billing_api.submit_maintenance_request,  # 已存在！
  }
  ```

#### 評估結論
**API 系統已完整，甚至已經預留了 `maintenance_request` 端點！**

---

### 4. SOP 系統 (Vendor SOP) ⚠️ 部分可用

#### 已有資料表
```sql
vendor_sop_items (
    id, category_id, vendor_id, group_id,
    item_number, item_name, content,
    primary_embedding VECTOR(1536),
    related_intent_id,
    priority, is_active,
    created_at, updated_at,

    -- 金流相關（已有）
    requires_cashflow_check BOOLEAN,
    cashflow_through_company TEXT,
    cashflow_direct_to_landlord TEXT
)

vendor_sop_categories (
    id, vendor_id, category_name, display_order, is_active
)

vendor_sop_groups (
    id, vendor_id, group_name, description, display_order, is_active
)
```

#### 已有功能
- ✅ SOP 分類管理
- ✅ SOP 群組管理
- ✅ SOP 與意圖關聯
- ✅ SOP 檢索（透過 embedding）

#### 缺少功能
- ❌ SOP 與表單的關聯
- ❌ SOP 與知識庫的關聯
- ❌ SOP 優先級規則
- ❌ SOP 觸發條件

#### 評估結論
**SOP 系統基礎功能完善，但需要補充與表單/知識庫的關聯機制。**

---

## 🎯 重新設計方案

### 設計原則
1. **利用現有表單系統** - 不新增 maintenance_tickets 表
2. **利用現有 API 系統** - 不新增專門的工單 API
3. **最小化資料庫變更** - 只新增必要的關聯欄位

---

### 方案 A：純表單 + API 方案（推薦）✅

#### 核心思路
- **表單提交記錄 = 維護工單**
- 利用 `form_submissions` 表的 `status` 和 `notes` 欄位管理工單狀態
- 透過 `action_type = 'form_then_api'` 實現表單完成後自動調用維修派工 API

#### 資料流程
```
租戶報修
  ↓
觸發知識庫（action_type: form_fill）
  ↓
填寫維護分類表單 (maintenance_classification)
  ↓
自動接續問題排查表單 (maintenance_troubleshooting)
  ↓
自動接續派工資訊表單 (maintenance_dispatch)
  ↓
表單完成 → 觸發 API (action_type: form_then_api)
  ↓
調用維修派工 API (maintenance_request)
  ↓
創建工單 → 派工 → 追蹤
```

#### 需要新增的資源

##### 1. 三個表單定義（插入 form_schemas）

**表單 1: maintenance_classification**
```json
{
  "form_id": "maintenance_classification",
  "form_name": "維護請求分類",
  "description": "收集租戶基本資訊和問題類型",
  "default_intro": "我來協助您處理維護請求，請先提供一些基本資訊。",
  "trigger_intents": ["報修", "維修", "壞掉", "故障", "問題", "冷氣不冷", "漏水", "門鎖", "電燈", "熱水器"],
  "fields": [
    {
      "field_name": "tenant_name",
      "field_label": "您的姓名",
      "field_type": "text",
      "prompt": "請問您的姓名是？",
      "validation_type": "taiwan_name",
      "required": true
    },
    {
      "field_name": "tenant_phone",
      "field_label": "聯絡電話",
      "field_type": "text",
      "prompt": "請提供您的聯絡電話",
      "validation_type": "phone",
      "required": true
    },
    {
      "field_name": "unit_number",
      "field_label": "房號",
      "field_type": "text",
      "prompt": "請問您的房號是？（例如：3F-A）",
      "required": true
    },
    {
      "field_name": "problem_category",
      "field_label": "問題類型",
      "field_type": "select",
      "prompt": "請選擇您遇到的問題類型",
      "required": true,
      "options": [
        {"value": "water_leak", "label": "🚰 漏水問題"},
        {"value": "ac_maintenance", "label": "❄️ 冷氣維修"},
        {"value": "door_lock", "label": "🔑 門鎖/鑰匙問題"},
        {"value": "electricity", "label": "💡 電力問題"},
        {"value": "water_heater", "label": "🔥 熱水器問題"},
        {"value": "plumbing", "label": "🚿 給排水問題"},
        {"value": "appliance", "label": "🏠 家電設備問題"},
        {"value": "internet", "label": "📡 網路/電話問題"},
        {"value": "cleaning", "label": "🧹 清潔問題"},
        {"value": "other", "label": "📝 其他問題"}
      ]
    },
    {
      "field_name": "urgency_level",
      "field_label": "緊急程度",
      "field_type": "select",
      "prompt": "請評估問題的緊急程度",
      "required": true,
      "options": [
        {"value": "critical", "label": "🔴 非常緊急（無法居住，如大量漏水、斷電）"},
        {"value": "urgent", "label": "🟠 緊急（影響生活，如冷氣不冷、熱水器故障）"},
        {"value": "normal", "label": "🟡 一般（可以稍候處理）"},
        {"value": "low", "label": "🟢 不急（有空再處理即可）"}
      ]
    },
    {
      "field_name": "brief_description",
      "field_label": "簡述問題",
      "field_type": "textarea",
      "prompt": "請簡單描述您遇到的問題（100字以內）",
      "required": true,
      "max_length": 100
    }
  ]
}
```

**表單 2: maintenance_troubleshooting**
```json
{
  "form_id": "maintenance_troubleshooting",
  "form_name": "問題詳細排查",
  "description": "收集問題的詳細資訊和排查結果",
  "default_intro": "謝謝！接下來需要了解更多細節，以便我們安排最合適的維修人員。",
  "fields": [
    {
      "field_name": "specific_problem",
      "field_label": "具體問題",
      "field_type": "select",
      "prompt": "請選擇最符合您情況的具體問題",
      "required": true,
      "conditional_options": {
        "water_leak": [
          {"value": "ceiling_leak", "label": "天花板漏水"},
          {"value": "wall_leak", "label": "牆壁滲水"},
          {"value": "pipe_leak", "label": "水管破裂"},
          {"value": "toilet_leak", "label": "馬桶漏水"},
          {"value": "faucet_leak", "label": "水龍頭漏水"}
        ],
        "ac_maintenance": [
          {"value": "ac_not_cooling", "label": "冷氣不冷"},
          {"value": "ac_noise", "label": "冷氣異常聲響"},
          {"value": "ac_water_leak", "label": "冷氣漏水"},
          {"value": "ac_not_starting", "label": "冷氣無法啟動"},
          {"value": "ac_smell", "label": "冷氣異味"}
        ]
      }
    },
    {
      "field_name": "problem_location",
      "field_label": "問題位置",
      "field_type": "text",
      "prompt": "請說明問題發生的具體位置（例如：主臥室、浴室）",
      "required": true,
      "max_length": 100
    },
    {
      "field_name": "when_started",
      "field_label": "發生時間",
      "field_type": "select",
      "prompt": "問題大約什麼時候開始的？",
      "required": true,
      "options": [
        {"value": "just_now", "label": "剛剛發生"},
        {"value": "today", "label": "今天發生"},
        {"value": "yesterday", "label": "昨天發生"},
        {"value": "this_week", "label": "這週內"},
        {"value": "long_time", "label": "已經很久了"}
      ]
    },
    {
      "field_name": "tried_troubleshooting",
      "field_label": "是否嘗試過排查",
      "field_type": "select",
      "prompt": "您是否有嘗試過簡單的排查步驟？",
      "required": true,
      "options": [
        {"value": "yes", "label": "有，但沒有改善"},
        {"value": "no", "label": "沒有，不知道怎麼做"},
        {"value": "partial", "label": "試了一些，但不確定"}
      ]
    },
    {
      "field_name": "troubleshooting_details",
      "field_label": "排查詳情",
      "field_type": "textarea",
      "prompt": "如果有嘗試過排查，請說明您做了什麼？（選填）",
      "required": false,
      "max_length": 200,
      "show_if": {
        "field": "tried_troubleshooting",
        "value": ["yes", "partial"]
      }
    },
    {
      "field_name": "detailed_description",
      "field_label": "詳細描述",
      "field_type": "textarea",
      "prompt": "請詳細描述問題的狀況（例如：漏水量大小、異響類型、影響範圍等）",
      "required": true,
      "max_length": 500
    }
  ]
}
```

**表單 3: maintenance_dispatch**
```json
{
  "form_id": "maintenance_dispatch",
  "form_name": "派工資訊收集",
  "description": "收集維修預約和進入方式資訊",
  "default_intro": "最後，請提供維修預約相關資訊。",
  "fields": [
    {
      "field_name": "preferred_time",
      "field_label": "偏好維修時間",
      "field_type": "select",
      "prompt": "請選擇您方便的維修時間",
      "required": true,
      "options": [
        {"value": "asap", "label": "⏰ 越快越好"},
        {"value": "morning", "label": "🌅 上午（9:00-12:00）"},
        {"value": "afternoon", "label": "☀️ 下午（13:00-17:00）"},
        {"value": "evening", "label": "🌆 傍晚（17:00-20:00）"},
        {"value": "weekend", "label": "📅 週末"},
        {"value": "discuss", "label": "💬 需要討論"}
      ]
    },
    {
      "field_name": "access_method",
      "field_label": "進入方式",
      "field_type": "select",
      "prompt": "維修人員如何進入您的房間？",
      "required": true,
      "options": [
        {"value": "tenant_present", "label": "👤 我會在場"},
        {"value": "landlord_present", "label": "🏠 房東/管理員陪同"},
        {"value": "spare_key", "label": "🔑 使用備用鑰匙"},
        {"value": "doorman", "label": "🚪 管理處協助開門"}
      ]
    },
    {
      "field_name": "contact_before",
      "field_label": "事前聯絡",
      "field_type": "select",
      "prompt": "維修人員是否需要事前聯絡您？",
      "required": true,
      "options": [
        {"value": "yes", "label": "是，請務必先打電話"},
        {"value": "no", "label": "不用，可以直接過來"},
        {"value": "message", "label": "傳訊息即可"}
      ]
    },
    {
      "field_name": "additional_notes",
      "field_label": "其他說明",
      "field_type": "textarea",
      "prompt": "還有其他需要我們知道的事項嗎？（選填）",
      "required": false,
      "max_length": 300
    },
    {
      "field_name": "confirm_submit",
      "field_label": "確認提交",
      "field_type": "checkbox",
      "prompt": "我確認以上資訊正確，同意提交維修請求",
      "required": true,
      "options": [
        {"value": "confirmed", "label": "我確認提交"}
      ]
    }
  ]
}
```

##### 2. 知識庫項目（插入 knowledge_base）

```sql
-- 維護請求入口知識
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    form_id,
    trigger_form_condition,
    api_config,
    business_types,
    target_user,
    keywords,
    vendor_id,
    scope,
    priority,
    is_active
) VALUES (
    '我要報修',
    '好的，我會協助您處理維修請求。請先提供一些基本資訊。',
    'form_then_api',  -- 先填表單，完成後調用 API
    'maintenance_classification',  -- 起始表單
    'always',
    '{
        "endpoint": "maintenance_request",
        "params": {},
        "combine_with_knowledge": false
    }'::jsonb,
    ARRAY['property_management'],
    ARRAY['tenant'],
    ARRAY['報修', '維修', '故障', '壞掉', '問題', '漏水', '冷氣', '門鎖', '電燈', '熱水器'],
    NULL,  -- vendor_id，NULL 表示全局
    'global',
    10,
    true
);
```

##### 3. API 端點（插入 api_endpoints）

```sql
-- 維修派工 API 端點（使用自定義處理器）
INSERT INTO api_endpoints (
    endpoint_id,
    endpoint_name,
    endpoint_icon,
    description,
    available_in_knowledge,
    available_in_form,
    implementation_type,
    custom_handler_name,
    is_active,
    display_order
) VALUES (
    'maintenance_request',
    '維修派工',
    '🔧',
    '提交維修請求並創建工單',
    true,
    true,
    'custom',  -- 使用自定義處理器
    'submit_maintenance_request',  -- 已在 api_registry 中
    true,
    10
);
```

##### 4. SOP 項目（插入 vendor_sop_items）

需要為 10 種問題類型建立 SOP 項目：

```sql
-- 1. 漏水問題 SOP
INSERT INTO vendor_sop_items (
    category_id, vendor_id, item_name, content, priority, is_active
) VALUES (
    (SELECT id FROM vendor_sop_categories WHERE category_name = '維護請求' LIMIT 1),
    NULL,  -- 全局 SOP
    '漏水問題處理流程',
    '【問題分類】
1. 天花板漏水 - 優先級：P0（緊急）
2. 牆壁滲水 - 優先級：P1（重要）
3. 水管破裂 - 優先級：P0（緊急）
4. 馬桶漏水 - 優先級：P1（重要）
5. 水龍頭漏水 - 優先級：P2（一般）

【排查步驟】
1. 確認漏水位置和範圍
2. 檢查是否有明顯損壞
3. 關閉相關水源（如水管破裂）
4. 使用容器收集漏水（避免擴大損害）
5. 拍照記錄現場狀況

【派工標準】
- P0：立即派工（1 小時內）
- P1：緊急派工（4 小時內）
- P2：正常派工（24 小時內）

【費用說明】
- 非人為損壞：房東承擔
- 人為損壞：租戶承擔
- 老舊損壞：雙方協商',
    10,
    true
);

-- 2. 冷氣維修 SOP
INSERT INTO vendor_sop_items (
    category_id, vendor_id, item_name, content, priority, is_active
) VALUES (
    (SELECT id FROM vendor_sop_categories WHERE category_name = '維護請求' LIMIT 1),
    NULL,
    '冷氣維修處理流程',
    '【問題分類】
1. 冷氣不冷 - 優先級：P1（夏季）/ P2（其他季節）
2. 冷氣異常聲響 - 優先級：P2（一般）
3. 冷氣漏水 - 優先級：P1（重要）
4. 冷氣無法啟動 - 優先級：P1（重要）
5. 冷氣異味 - 優先級：P2（一般）

【排查步驟】
1. 檢查遙控器電池
2. 確認電源是否正常
3. 檢查濾網是否需要清潔
4. 確認室外機是否運轉
5. 記錄溫度設定和實際室溫

【派工標準】
- 夏季高溫（> 30°C）：4 小時內
- 其他季節：24 小時內
- 漏水問題：4 小時內

【費用說明】
- 濾網清潔：租戶自行處理
- 設備故障：房東承擔
- 人為損壞：租戶承擔',
    10,
    true
);

-- （其他 8 個 SOP 類似結構...）
```

---

#### 實施步驟

**Phase 1: 資料準備（1 週）**
1. 使用 Knowledge Admin 前端表單編輯器建立三個表單
2. 在知識庫管理界面新增維護請求入口知識
3. 在 API 端點管理界面新增 maintenance_request 端點
4. 建立 10 個維護類型的 SOP 項目

**Phase 2: 自定義 API 實作（1 週）**
5. 實作 `submit_maintenance_request` 處理函數
   - 從 form_data 提取所有欄位
   - 計算優先級（根據 urgency_level 和 problem_category）
   - 創建 form_submission 記錄（status = 'pending'）
   - 發送通知給維修團隊
   - 返回工單編號

**Phase 3: 前端增強（1 週）**
6. 在 FormSubmissionsView 中新增「維護工單」篩選
7. 新增工單狀態管理功能（pending → assigned → in_progress → completed）
8. 新增派工功能（指定維修人員）

**Phase 4: 測試與優化（1 週）**
9. 端到端測試（租戶報修 → 表單填寫 → API 調用 → 工單創建）
10. SOP 內容優化
11. 表單流程優化

---

#### 優點
✅ **零侵入性** - 不修改核心表結構
✅ **最大復用** - 完全利用現有功能
✅ **易於維護** - 表單和 SOP 可透過前端管理
✅ **擴展性強** - 可輕鬆新增更多維護類型

#### 缺點
⚠️ form_submissions 表會包含所有類型的表單提交（不只維護工單）
⚠️ 需要透過 form_id 和 status 篩選維護工單

---

### 方案 B：新增專用表方案（備選）

#### 核心思路
- 新增 `maintenance_tickets` 表專門管理維護工單
- `form_submissions` 只作為資料收集記錄
- API 調用時從 `form_submissions` 讀取資料，寫入 `maintenance_tickets`

#### 優點
✅ 工單資料獨立，查詢更簡單
✅ 可新增更多維護專屬欄位（SLA, 維修人員, 費用等）

#### 缺點
❌ 需要新增資料表（增加複雜度）
❌ 資料重複（form_submissions 和 maintenance_tickets 都有相同資料）
❌ 需要維護兩個系統的資料一致性

#### 評估結論
**不推薦，除非未來有大量維護專屬需求。**

---

## 🎯 推薦方案

**採用方案 A：純表單 + API 方案**

### 理由
1. ✅ **符合系統設計哲學** - 表單系統本來就是用來收集和管理結構化資料
2. ✅ **最小化變更** - 不新增資料表，只新增配置
3. ✅ **靈活性高** - 表單欄位可透過前端隨時調整
4. ✅ **易於擴展** - 未來可輕鬆新增更多維護類型或其他服務請求
5. ✅ **符合現有架構** - 2026-01-21 剛修復的 API 整合功能正好可以使用

---

## 📊 資料庫變更總結

### 需要新增的資料（全部透過 SQL INSERT，不修改表結構）

1. **form_schemas**: 3 筆記錄（三個維護表單）
2. **knowledge_base**: 1 筆記錄（維護請求入口知識）
3. **api_endpoints**: 1 筆記錄（maintenance_request API）
4. **vendor_sop_categories**: 1 筆記錄（維護請求分類）
5. **vendor_sop_items**: 10 筆記錄（10 種問題類型的 SOP）

### 需要修改的代碼

1. **rag-orchestrator/services/billing_api.py** - 實作 `submit_maintenance_request` 函數

---

## 📝 後續步驟

1. **確認方案** - 用戶確認採用方案 A
2. **建立 Migration** - 創建 SQL migration 插入表單和知識庫資料
3. **實作 API** - 實作 submit_maintenance_request 函數
4. **測試** - 端到端測試報修流程
5. **優化** - 根據測試結果優化表單和 SOP

---

**評估完成時間**: 2026-01-22
**預計實施時間**: 4 週（分 4 個 Phase）
**風險等級**: 低（不修改核心結構）
