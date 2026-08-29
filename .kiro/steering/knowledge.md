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

- **維度**：1536（OpenAI text-embedding-3-small）
- **輸入文字**：只用標題（`question_summary`），不混入 keywords（避免語義稀釋）
- **用途**：語義相似度檢索（pgvector 的 `<=>` 運算子）
- **索引**：IVFFlat 向量索引（加速相似度搜尋）
- **閾值**：預設相似度 >= 0.6 才視為匹配（KNOWLEDGE_MIN_THRESHOLD）
- **生成一致性**：所有寫入 `knowledge_base.embedding` 的路徑都須使用 `get_embedding_client()`，輸入文字統一為 `question_summary`（避免與搜尋時的 query embedding 來源不一致）
- **keywords 機制**：透過 `BaseRetriever._keyword_search` 獨立進行關鍵字匹配（向量備選），不混入 embedding

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
平台層（範本）：
  platform_sop_categories → platform_sop_groups → platform_sop_templates

業者層（實例，可覆寫範本）：
  vendor_sop_categories → vendor_sop_groups → vendor_sop_items
  vendor_sop_overrides（覆寫平台範本的內容）
```

> vendor_sop_items 使用雙向量策略：`primary_embedding` + `fallback_embedding`（皆 1536 維）

### 精準匹配原則（Critical）

1. **SOP 名稱必須與內容精準匹配**
   - ❌ 錯誤：「租約相關」（過於籠統）
   - ✅ 正確：「線上續約申請流程」

2. **單一職責原則**
   - 每個 SOP 只處理一個具體流程或政策
   - 不合併不相關主題

3. **觸發模式**（trigger_mode）
   - `none`/null：純資訊展示，無後續動作
   - `manual`：等待特定 trigger_keywords 觸發
   - `immediate`：立即詢問確認（確認詞/否定詞）
   - `auto`：立即執行後續動作（不等待）

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

## 6. `categories`：entry nomination metadata（**不是 ownership 宣告**）

知識列上的 `categories`（多值優先，無則退單值 `category`）是**進場提名用的中介資料**：
它讓「檢索到這列」能夠**提出**某個面向作為候選，僅此而已。

```text
categories 命中          ＝ 這列知識**可以提名**該面向
                        ≠ 該面向**應該**承擔這個 query（那是 persona scope contract 的事）
                        ≠ 進場一定成立（仍須 similarity ≥ FORM_TRIGGER_THRESHOLD 0.75）
```

- **它是目前 responsibility 與 nomination 之間唯一的耦合，而且是人工維護的間接連結。**
  entry 層**不讀** persona 的 responsibility contract；兩層各走各的契約（母圖 §0.3）。
- **禁止的推論**：實測曾出現「responsibility owner 存在且穩定接受，但 entry 從未提出它」
  （分類 `OWNER_EXISTS_BUT_NOT_PROPOSED`）。**不得**據此推導「某列應該補上某個 category」——
  那是在決定**誰該擁有這個 query**，屬 governance 的 normative decision，不是資料完整性修復。
- 對齊母圖 §0.5 的三層讀法：`categories`＝① Routing Hint；`form_id`／`action_type`／
  `trigger_mode`＝② Action Declaration（**帶 `form_id` ≠ 直接開表單**，`trigger_mode` 另有分支）；
  面向配置的 `grounding_scope`＝③ Execution Configuration（**僅在選定後生效**，非 routing 選項）。
- `result_mapping.skip_refine` 屬對話政策，不屬 routing：它跳過的是「請補更明確識別」那一輪，
  **不是**選定候選後的重查（重查仍會發生並收斂單筆）。

---

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
- 閾值：相似度 >= 0.6（KNOWLEDGE_MIN_THRESHOLD）

### 4. 知識來源可追溯
- 記錄來源：manual / auto_generated / loop
- Loop 生成：關聯 source_loop_id 和 source_loop_knowledge_id
- 支援回溯與驗證

---

## instance applicability —— 新增／修改知識的**必填契約**（P1d，2026-08-30 生效）

### 規則

```text
所有**新增或實質修改**的情境知識 row，必須在
`generation_metadata.instance_applicability` 明示：

  "instance"  正確完成這個問題，需要讀取「這個使用者自己的」
              帳號／合約／帳單／物件／訂閱／系統狀態等資料
  "general"   不需要任何該使用者自己的系統資料，
              僅靠制度、流程、產品通則即可完整回答

### ⚠️ 兩個值的**證據門檻不對稱**（2026-08-29 業主裁定②）

```text
instance  可由可重播的 machine capability evidence（診斷引擎契約／識別碼表單／
          動作端點）建立，或由 reviewed declaration 建立
general   **必須**有正面的 reviewed declaration：
          「此 intent 的正確完成不依賴任何使用者特定 runtime state，
            即使相關 user-specific capability 存在也不需要讀取」
          ⛔ **不得**由 absence-of-instance-evidence 推導
```

⚠️ 實證：兩位隔離標註者對 839 筆達成 97.5% 一致，卻把**已證實需要實值**的
知識 3509 合議判成 `general`（因為它的答案文字寫成通用指引）。
⇒ **knowledge text alone is insufficient evidence for authoritative `general`.**

⛔ 也不得用「能讀到使用者資料會不會答得更好」判 general——
那是把判準從**必要性**偷換成**有沒有增益**。

⚠️ **UNKNOWN 是 migration state，⛔ 不是正常終態；
   但 UNKNOWN 比 false general 安全，⛔ 不得為了壓低 UNKNOWN 而放寬 general 門檻。**
   2026-08-30 之前的既有列允許 UNKNOWN（legacy）；
   之後建立／修改的列未宣告 → `make audit` 不變量 10 直接 FAIL。
```

### 為什麼需要這條（2026-08-29 U1 盤查的結論）

```text
決定「這一題該不該由對話面向擁有」的屬性——「需不需要使用者自己的資料」——
**過去沒有被任何欄位記錄**。架構早就為它留了位置
（`grounding_scope.requires_instance_reference`），但實查宣告數＝0
⇒ instance gate 的條件恆為 False
⇒ **授權機制是在一個授權輸入結構性缺席的系統上被評估的**。
```

### ⛔ 不得用這些推導

```text
沒有 API／沒有 form／沒有 diagnostic engine  → **不等於** general
有 form／有 api_config                      → **不等於** 一定 instance

反證：知識 3509「訂閱扣款失敗導致功能異常」是 direct_answer、無 form_id，
      卻必須查該帳號的訂閱狀態。
⇒ `form_id`／`action_type`／`api_config` 編碼的是**執行**，不是**實值依賴**。
```

### 與其他欄位的界線

```text
`knowledge_base.scope`（global／vendor）＝**可見範圍**，⛔ 語義無關，不可挪用
`categories`                           ＝ 主題／提名證據（裁定 001）
`instance_applicability`               ＝ **實值依賴**，與前兩者正交
```

### 讀取方式

```text
一律經 `services/instance_applicability.py`：
  knowledge_instance_applicability(row) → instance / general / unknown
⛔ 不得在別處直接讀該鍵——不變量 10 會 FAIL（AST 掃描，docstring/註解不誤報）。
```
