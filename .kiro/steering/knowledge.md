# Knowledge Steering

> **相關文件**：對話處理流程請參考 [dialogue.md](./dialogue.md)

## 1. knowledge_base 資料表架構（核心基礎）

### 核心欄位與用途

```sql
knowledge_base
├── id INTEGER (PK)                        -- 主鍵
├── question_summary TEXT                  -- 問題摘要
├── answer TEXT                            -- 答案內容
├── embedding VECTOR(1536)                 -- 向量嵌入（pgvector，語義檢索）
├── vendor_ids INTEGER[]                   -- 業者隔離（多業者共享知識）
├── scope VARCHAR(20)                      -- 知識範圍：'global'/'vendor'/'customized'
├── target_user TEXT[]                     -- 目標用戶：['tenant','landlord','property_manager']
├── business_types TEXT[]                  -- 業態類型過濾
├── keywords TEXT[]                        -- 關鍵字（輔助檢索）
├── priority INTEGER                       -- 優先級（影響檢索排序）
├── is_active BOOLEAN                      -- 啟用狀態
├── source VARCHAR(50)                     -- 知識來源：'manual'/'auto_generated'/'loop'
├── source_loop_id INTEGER                 -- 來源迴圈 ID（若為 loop 生成）
├── source_loop_knowledge_id INTEGER       -- 來源知識 ID（若為 loop 生成）
├── created_at TIMESTAMP                   -- 建立時間
└── updated_at TIMESTAMP                   -- 更新時間
```

### 向量 Embedding

- **維度**：1536（OpenAI text-embedding-ada-002）
- **用途**：語義相似度檢索（pgvector 的 `<=>` 運算子）
- **索引**：IVFFlat 向量索引（加速相似度搜尋）
- **閾值**：預設相似度 > 0.6 才視為匹配

### 業者隔離機制

- **vendor_ids**：INTEGER[] 陣列，支援多業者共享知識
- **scope** 優先級（由高到低）：
  1. `customized`：業者客製化（最高優先級）
  2. `vendor`：業者專屬
  3. `global`：全域通用（最低優先級）

### 知識來源追蹤

- **source = 'manual'**：人工錄入
- **source = 'auto_generated'**：AI 輔助生成
- **source = 'loop'**：知識完善迴圈生成
  - 必須同時填寫 `source_loop_id` 和 `source_loop_knowledge_id`

## 2. 知識分類系統（業務邏輯）

### 4 種知識類型（knowledge_type）

系統根據**問題性質**和**處理方式**分為 4 種類型：

| 類型 | 儲存位置 | 特徵 | 範例 |
|------|---------|------|------|
| **sop_knowledge** | vendor_sop_* | 需多輪對話或固定流程 | 續約流程、裝潢申請 |
| **form_fill** | knowledge_base | 需用戶填寫表單 | 報修單、客訴表單 |
| **system_config** | knowledge_base | 可直接回答的單一問答 | 租金繳納日期、服務時間 |
| **api_query** | api_endpoints | 需呼叫 API 取得即時資料 | 帳單查詢、繳費記錄 |

### 4 種回應類型（response_type）

系統根據**知識類型**判斷**如何回應**：

```python
if knowledge_type == 'system_config':
    response_type = 'direct_answer'      # 純知識問答
elif knowledge_type == 'form_fill' and not needs_api:
    response_type = 'form_fill'          # 表單 + 知識
elif knowledge_type == 'api_query':
    response_type = 'api_call'           # API + 知識
elif knowledge_type == 'form_fill' and needs_api:
    response_type = 'form_then_api'      # 表單 + API + 知識
```

## 3. 知識關聯配置（擴展功能）

knowledge_base 根據業務需求可選擇以下配置：

### 配置 A：使用表單（form_fill）

**關聯方式**：knowledge_base.form_id → form_schemas.form_id（字串匹配，非外鍵）

```sql
knowledge_base
├── form_id VARCHAR(100)                   -- 表單識別碼
├── trigger_form_condition VARCHAR(20)     -- 'always'/'auto'/'never'/'conditional'
└── action_type VARCHAR(50)                -- 'form_fill' 或 'form_then_api'

form_schemas
├── id INTEGER (PK)
├── form_id VARCHAR(100) UNIQUE            -- 被引用欄位
├── form_name VARCHAR(200)
├── fields JSONB                           -- 表單欄位定義
├── on_complete_action VARCHAR(50)         -- 'show_knowledge'/'call_api'/'both'
└── api_config JSONB                       -- 若需串 API
```

**使用時機**：需收集用戶資訊才能完成（報修、申請、試算）

### 配置 B：使用 API（api_call）

**關聯方式**：api_endpoints.related_kb_ids[] → knowledge_base.id（反向引用）

```sql
api_endpoints
├── id INTEGER (PK)
├── endpoint_id VARCHAR(100) UNIQUE
├── api_url TEXT
├── http_method VARCHAR(10)                -- 'GET'/'POST'/'PUT'/'DELETE'
├── param_mappings JSONB                   -- 請求參數映射
├── response_template TEXT                 -- 回應範本
└── related_kb_ids INTEGER[]               -- 關聯的 knowledge_base.id

knowledge_base
├── id INTEGER (PK)                        -- 被引用欄位
├── action_type VARCHAR(50)                -- 'api_call' 或 'form_then_api'
└── api_config JSONB                       -- API 呼叫配置
```

**使用時機**：需即時資料（帳單、繳費記錄、用電區間查詢）

### 配置 C：無關聯（direct_answer）

**特徵**：knowledge_base.action_type = 'direct_answer'

- 無需表單或 API
- 直接返回 `answer` 欄位內容
- 適用於固定問答知識（租金日期、服務時間、聯絡方式）

## 4. SOP 架構（特殊知識類型）

### 三層架構

```
vendor_sop_categories（分類）：廣泛主題
    ↓
vendor_sop_groups（群組）：具體流程
    ↓
vendor_sop_items（項目）：單一 SOP
```

### 精準匹配原則（Critical）

1. **SOP 名稱必須與內容精準匹配**
   - ❌ 錯誤：「租約相關」（過於籠統）
   - ✅ 正確：「線上續約申請流程」

2. **單一職責原則**
   - 每個 SOP 只處理一個具體流程或政策
   - 不合併不相關主題

3. **觸發模式**
   - `keyword`：關鍵字精準匹配（速度快）
   - `semantic`：語義相似度匹配（彈性高）
   - `manual`：僅人工觸發

### SOP vs Knowledge Base 路由

```python
if knowledge_type == 'sop_knowledge':
    # 生成到 SOP 系統（vendor_sop_items）
    # 原因：需流程編排、多輪對話
    generate_sop(gap, category_id, group_id)
else:  # form_fill, system_config, api_query
    # 生成到通用知識庫（knowledge_base）
    generate_knowledge_base(gap, knowledge_type)
```

## 5. 知識生成與審核（流程管理）

### 知識生成判斷

```python
# 是否生成靜態答案
if knowledge_type in ['sop_knowledge', 'form_fill', 'system_config']:
    should_generate_knowledge = True
    # 生成到 loop_generated_knowledge
else:  # api_query
    should_generate_knowledge = False
    # 標記為 API 查詢，不生成靜態答案
```

### 人工審核流程

```
AI 生成 → pending_review（待審核）
         ↓
人工審核 → approved（批准）→ 同步到正式表（knowledge_base 或 vendor_sop_*）
         → rejected（拒絕）→ 不同步
         → draft（草稿）→ 人工編輯中
```

**核心原則**：
- 所有 AI 生成知識預設為 `pending_review`
- 必須經人工批准才生效
- AI 僅輔助，最終決策權在人工

## 核心原則總結

### 1. 測試驅動知識完善
- 測試先行：知識缺口應先有測試案例（test_scenarios）
- 回測驗證：批准知識後重新回測，驗證改善效果
- 迭代改善：持續執行直到達成目標通過率

### 2. 多層業者隔離
- **vendor_ids**：支援多業者共享知識
- **scope**：customized > vendor > global
- **target_user**：租客、房東、物業經理角色隔離

### 3. 向量 + 關鍵字雙重檢索
- 向量：語義相似度檢索（主要）
- 關鍵字：精準匹配（輔助）
- 閾值：相似度 > 0.6

### 4. 知識來源可追溯
- 記錄來源：manual / auto_generated / loop
- Loop 生成：關聯 source_loop_id 和 source_loop_knowledge_id
- 支援回溯與驗證
