# Dialogue Steering

> **相關文件**：知識資料結構請參考 [knowledge.md](./knowledge.md)

## 1. 對話處理核心流程（架構基礎）

### 主要流程

```
用戶問題
    ↓
業者驗證 + 緩存檢查
    ↓
表單會話檢查（進行中表單優先）
    ↓
意圖分類（LLM Function Calling）
    ↓
智能檢索（SOP + 知識庫並行）
    ↓
分數比較決策
    ↓
處理路徑選擇：
    ├─ SOP 路徑：觸發模式處理 + 後續動作
    └─ 知識庫路徑：信心度評估 → 答案優化
    ↓
業者參數注入
    ↓
答案清理 + 緩存存儲
    ↓
返回回應（JSON/串流）
```

### 請求/回應模型

**請求核心欄位**：
- `vendor_id`: 業者 ID（業者隔離）
- `message`: 用戶訊息
- `session_id`: 會話 ID（表單狀態追蹤）
- `target_user`: 目標角色（tenant/landlord/property_manager）
- `mode`: 業務模式（b2c/b2b）
- `debug`: Debug 模式（跳過緩存）

**回應核心欄位**：
- `answer`: 答案內容
- `intent_name` + `intent_type`: 意圖資訊
- `confidence`: 信心度（0-1）
- `action_type`: 動作類型（direct_answer/form_fill/api_call/sop_knowledge）
- `form_triggered` + `form_completed`: 表單狀態

### 緩存機制

**緩存鍵組成**：`vendor:{id}:user:{role}:config:{version}:q:{hash}`

**跳過緩存條件**：
- Debug 模式開啟
- 有進行中的表單會話
- 用戶訊息包含表單觸發關鍵字

## 2. 意圖識別系統（業務分類）

### 意圖分類邏輯

**LLM Function Calling 架構**：
```python
classify_intent(question, available_intents) → {
    primary_intent: {name, confidence},      # 主要意圖
    secondary_intents: [{name, confidence}]  # 次要意圖（最多2個）
}
```

### 多意圖支援

| 意圖級別 | 數量限制 | 用途 |
|---------|---------|------|
| 主要意圖 | 1 個 | RAG 檢索 1.3x 加成 |
| 次要意圖 | 最多 2 個 | RAG 檢索 1.1x 加成 |

**意圖配置來源**：
1. **資料庫** (intents 表)：動態配置，支援業者自定義
2. **YAML 配置** (fallback)：系統預設意圖

### 信心度評估

**獨立閾值檢查**：每個意圖有自己的 `confidence_threshold`

```python
for intent in [primary, *secondary]:
    if intent.confidence < intent.threshold:
        filtered_out()  # 不參與檢索加成
```

**信心度標準**：
- **0.9-1.0**：非常確定
- **0.7-0.9**：較為確定（預設閾值）
- **0.5-0.7**：不太確定
- **< 0.5**：不確定

### 降級機制

**主意圖失敗處理**：
```python
if primary_failed AND has_valid_secondary:
    promote_best_secondary_to_primary()
    demote_original_primary_to_secondary()
```

**無有效意圖**：
```python
if all_intents_failed:
    return unclear_intent  # intent_name = "unclear"
```

## 3. 檢索引擎（智能檢索）

### 雙軌並行檢索

**同時執行**：
```python
sop_result, knowledge_list = await asyncio.gather(
    sop_retrieval(question, intent_ids),
    knowledge_retrieval(question, intent_ids)
)
```

### SOP vs 知識庫決策邏輯

**閾值定義**：
- `SOP_MIN_THRESHOLD = 0.55`
- `KNOWLEDGE_MIN_THRESHOLD = 0.6`
- `SCORE_GAP_THRESHOLD = 0.15`（顯著差異）

**決策樹**：

```python
# Case 0A: SOP 被用戶取消
if sop_cancelled:
    return sop_result  # 優先處理取消回應

# Case 0B: SOP 已觸發並執行動作
if sop_triggered_with_action:
    return sop_result  # 優先完成 SOP 流程

# Case 1: SOP 顯著更高
if sop_score >= 0.55 AND sop_score > kb_score + 0.15:
    return sop_result

# Case 2: 知識庫顯著更高
if kb_score >= 0.6 AND kb_score > sop_score + 0.15:
    return knowledge_result

# Case 3: 分數接近（兩者都達標）
if sop_score >= 0.55 AND kb_score >= 0.6:
    if sop_has_next_action:
        return sop_result  # 優先處理後續動作（表單/API）
    else:
        return higher_score_result

# Case 4: 只有 SOP 達標
if sop_score >= 0.55:
    return sop_result

# Case 5: 只有知識庫達標
if kb_score >= 0.6:
    return knowledge_result

# Case 6: 都不達標
return unclear_response
```

### 意圖加成策略

**加成係數**：
```python
intent_boost = {
    'primary_intent': 1.3,      # 主要意圖 30% 加成
    'secondary_intent': 1.1,    # 次要意圖 10% 加成
    'other': 1.0                # 其他意圖無加成
}

boosted_similarity = base_similarity * intent_boost
```

**優先級加成**（知識庫專屬）：
```python
if priority > 0 AND similarity >= 0.70:
    boosted_similarity += 0.15  # 固定加成
```

### 過濾機制

**業者隔離**：`vendor_ids @> ARRAY[$vendor_id]`
**角色隔離**：`target_user @> ARRAY[$user_role]`
**業態過濾**：`business_types IS NULL OR business_types @> ARRAY[$business_type]`
**啟用狀態**：`is_active = true`

## 4. 信心度評估（品質控制）

### 評估指標

**計算因子**：
1. **相似度**（權重 70%）：`max_similarity`
2. **結果數量**（權重 20%）：`min(result_count / 5, 1.0)`
3. **關鍵字匹配**（權重 10%）：`matched_keywords / total_keywords`

**加權分數**：
```python
confidence_score = (
    max_similarity * 0.7 +
    min(result_count / 5, 1.0) * 0.2 +
    keyword_match_rate * 0.1
)
```

### 信心度等級

| 等級 | 分數範圍 | 額外條件 | 處理決策 |
|------|---------|---------|---------|
| **high** | ≥ 0.85 | 結果數 ≥ 2 | 直接回答 |
| **medium** | 0.70-0.85 | - | LLM 優化 |
| **low** | < 0.70 | - | 標記未釐清 |

### 處理決策

```python
if level == "high":
    decision = "direct_answer"      # 可能啟用快速路徑
elif level == "medium":
    decision = "needs_enhancement"  # LLM 優化
else:
    decision = "unclear"            # 轉人工或提示重新描述
```

## 5. 答案優化（智能生成）

### 條件式優化決策樹

```python
# 1. 完美匹配（跳過 LLM）
if max_similarity >= 0.90:
    return original_answer

# 2. 答案合成（多高品質結果）
high_quality = [r for r in results if r.similarity > 0.80]
if len(high_quality) >= 2 AND is_complex_question:
    synthesize_answers(high_quality)

# 3. 快速路徑（單一高品質）
elif confidence >= 0.75 AND single_result:
    format_with_template()

# 4. 模板格式化（中等信心）
elif 0.55 <= confidence < 0.75:
    apply_template()

# 5. 完整 LLM 優化（低信心）
else:
    full_llm_optimization()
```

### 答案合成觸發條件

**必須同時滿足**：
1. `ENABLE_SYNTHESIS = true`（環境變數）
2. 結果數 ≥ 2
3. 包含複雜問題模式：
   - 流程問題：「如何」、「步驟」、「流程」
   - 多面向問題：「可以…嗎？還是…」
   - 比較問題：「差別」、「區別」
4. 無單一完美匹配（max_similarity < 0.90）

**合成策略**：
```python
LLM Prompt: """
整合以下多個答案片段，生成一個完整、連貫的回答：
1. [答案1]
2. [答案2]
3. [答案3]

要求：
- 保留所有關鍵資訊
- 去除重複內容
- 邏輯連貫
- 結構清晰（使用列表或步驟）
"""
```

### 業者參數注入

**兩階段替換**：

**階段 1：確定性替換**（正則表達式）
```python
# 模板變數替換
{company_name} → 實際公司名稱
{service_phone} → 實際服務電話
{business_hours} → 實際營業時間

# 智能替換（語境感知）
"我們的客服" → "{company_name}的客服"
"撥打服務專線" → "撥打 {service_phone}"
```

**階段 2：語氣調整**（已停用）
- 原因：避免 LLM 誤刪替換後的參數

### 優化參數配置

| 參數 | 預設值 | 用途 |
|------|--------|------|
| `PERFECT_MATCH_THRESHOLD` | 0.90 | 完美匹配閾值 |
| `SYNTHESIS_THRESHOLD` | 0.80 | 答案合成閾值 |
| `FAST_PATH_THRESHOLD` | 0.75 | 快速路徑閾值 |
| `LLM_ANSWER_TEMPERATURE` | 0.7 | 答案生成溫度 |
| `LLM_SYNTHESIS_TEMP` | 0.5 | 合成專用溫度 |
| `LLM_ANSWER_MAX_TOKENS` | 800 | 最大 token 數 |

## 6. SOP 編排（流程管理）

### 觸發模式

| 模式 | 行為 | 等待條件 | 使用場景 |
|------|------|---------|---------|
| `none` | 純資訊展示 | 無 | 政策說明、規範解釋 |
| `manual` | 等待特定關鍵詞 | `trigger_keywords` | 需用戶主動確認的流程 |
| `immediate` | 立即詢問確認 | 確認詞列表 | 需即時確認的操作 |
| `auto` | 自動執行 | 無 | 自動化流程（表單/API） |

### 觸發關鍵字匹配邏輯

**immediate 模式特殊處理**：
```python
# 1. 純粹否定詞（優先級最高）
if message in ['不用', '不要', '算了', '取消']:
    cancel_action()

# 2. 問句檢測（不視為確認）
elif '?' in message OR is_question_keyword(message):
    not_confirmed()

# 3. 訊息過長（可能是新問題）
elif len(message) > 10:
    not_confirmed()

# 4. 確認詞匹配
elif message in ['確認', '好', '是的', '沒問題', 'OK', ...]:
    trigger_action()
```

**manual 模式**：
```python
if any(keyword in message for keyword in trigger_keywords):
    trigger_action()
```

### 多輪對話管理

**Context 結構**：
```python
{
    'sop_id': int,
    'sop_name': str,
    'trigger_mode': str,
    'trigger_keywords': List[str],
    'next_action': str,              # none/form_fill/api_call/form_then_api
    'next_form_id': int,
    'next_api_config': dict,
    'state': 'WAITING' | 'TRIGGERED',
    'original_question': str         # 相似問題檢測用
}
```

**相似問題處理**：
```python
if has_pending_context:
    similarity = compare(new_question, original_question)

    if similarity >= 0.7:
        # 視為新問題，重新檢索
        clear_context()
        start_new_retrieval()
    else:
        # 視為回應，檢查關鍵字
        check_keywords()
```

### 後續動作執行

```python
if next_action == 'form_fill':
    trigger_form(next_form_id)

elif next_action == 'api_call':
    execute_api(next_api_config)

elif next_action == 'form_then_api':
    trigger_form(next_form_id, pause_mode=True)
    # 表單完成後自動執行 API
```

## 7. 表單管理（數據收集）

### 狀態機

```
COLLECTING  → DIGRESSION (離題偵測)
            → REVIEWING (填寫完成)
            → PAUSED (SOP form_then_api)
            → CANCELLED (取消)

DIGRESSION  → COLLECTING (繼續填寫)
            → CANCELLED (放棄表單)

REVIEWING   → EDITING (修改欄位)
            → COMPLETED (確認提交)
            → CANCELLED (取消)

EDITING     → REVIEWING (完成編輯)

PAUSED      → COLLECTING (恢復填寫)
```

### 離題偵測

**偵測邏輯**：
```python
detect_digression(message, current_field, form_schema, intent) → {
    is_digression: bool,
    digression_type: str,  # explicit_exit/question/irrelevant_response
    confidence: float
}
```

**離題類型**：
1. **明確退出**：「取消」、「算了」、「不填了」
2. **詢問問題**：包含 "?" 或問題關鍵字
3. **無關回應**：與當前欄位無關的內容

**處理策略**：
```python
if digression_type == 'explicit_exit':
    cancel_form()

elif digression_type == 'question':
    answer_question()
    show_current_field_prompt()  # 回到當前欄位

elif digression_type == 'irrelevant_response':
    clarify_and_retry()
```

### 欄位驗證

**驗證類型**：
- `text`: 文字長度、格式
- `phone`: 台灣手機格式（09xxxxxxxx）
- `email`: Email 格式
- `date`: 日期格式（YYYY-MM-DD）
- `number`: 數字範圍
- `select`: 選項匹配

**驗證失敗處理**：
```python
if not is_valid:
    return {
        "answer": f"{error_message}\n\n{field_prompt}",
        "validation_failed": True
    }
```

### 審核與編輯

**審核模式觸發**：
```python
if all_fields_collected:
    if form_schema.skip_review:
        complete_form()  # 直接完成
    else:
        show_review_summary()  # 進入審核模式
```

**審核摘要格式**：
```
請確認以下資訊是否正確：

1. 姓名：王小明
2. 電話：0912345678
3. 地址：台北市信義區...

輸入「確認」提交，或輸入欄位編號修改（例如：「修改2」）
```

**編輯模式**：
```python
if message.startswith('修改'):
    field_number = extract_number(message)
    enter_editing_mode(field_number)
```

### 完成後動作

```python
if on_complete_action == 'call_api':
    result = execute_api(form_data)
    show_result(result)

elif on_complete_action == 'show_knowledge':
    show_knowledge_answer(related_kb_id)

elif on_complete_action == 'both':
    result = execute_api(form_data)
    knowledge = get_knowledge(related_kb_id)
    show_combined_response(result, knowledge)
```

### API 重試機制

```python
MAX_RETRIES = 2

if api_error in ['ambiguous_match', 'no_match', 'invalid_input']:
    retry_count += 1

    if retry_count >= MAX_RETRIES:
        cancel_form()  # 自動取消，避免無限重試
        notify_manual_intervention()
    else:
        show_retry_hint(api_error)
```

## 核心原則總結

### 1. 智能決策層次化
- **意圖層**：多意圖支援，獨立信心度評估
- **檢索層**：SOP vs 知識庫智能決策
- **優化層**：條件式優化，避免不必要的 LLM 調用
- **執行層**：表單/API 自動化處理

### 2. 性能優先策略
- **緩存機制**：減少重複計算
- **並行檢索**：SOP 和知識庫同時執行
- **快速路徑**：高信心度跳過 LLM
- **模型選擇**：分類用 3.5-turbo，優化用 3.5-turbo

### 3. 用戶體驗優化
- **離題處理**：智能識別問題，允許中斷填表
- **審核機制**：表單提交前確認，支援編輯
- **相似問題檢測**：避免 SOP 上下文誤判
- **錯誤降級**：API 失敗自動重試或取消

### 4. 業務規則可配置化
- **意圖閾值**：每個意圖獨立配置
- **觸發模式**：支援 4 種 SOP 觸發策略
- **優化策略**：閾值可調整（完美匹配/合成/快速路徑）
- **業者參數**：動態注入，支援多租戶

### 5. 容錯與監控
- **Debug 模式**：完整流程追蹤，跳過緩存
- **降級機制**：主意圖失敗時提升次意圖
- **錯誤處理**：API 失敗、LLM 失敗都有 fallback
- **狀態管理**：表單/SOP 狀態持久化，會話可恢復
