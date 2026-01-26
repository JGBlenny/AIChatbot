# RAG Orchestrator 對話流程完整分析 - 2026-01-24

**日期**：2026-01-24
**分析範圍**：`POST /api/v1/message` 完整對話流程
**代碼版本**：2026-01-24 修正後版本
**文件位置**：`rag-orchestrator/routers/chat.py`

---

## 📋 目錄

1. [流程總覽](#流程總覽)
2. [Step 0: 表單會話檢查](#step-0-表單會話檢查)
3. [Step 1-3: 基礎處理](#step-1-3-基礎處理)
4. [Step 3.5: SOP Orchestrator](#step-35-sop-orchestrator)
5. [Step 6: 知識庫檢索](#step-6-知識庫檢索)
6. [Step 9: 構建知識回應](#step-9-構建知識回應)
7. [Step 8: 無知識處理](#step-8-無知識處理)
8. [關鍵決策點分析](#關鍵決策點分析)
9. [設計原則說明](#設計原則說明)

---

## 流程總覽

### 主流程入口

```
POST /api/v1/message
  ↓
vendor_chat_message(request, req)
  ↓
[10 個主要步驟]
  ↓
VendorChatResponse
```

### 完整流程圖

```
用戶訊息
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 0: 檢查表單會話狀態（優先級：最高）                       │
│ ⭐ 上下文優先於內容                                           │
└─────────────────────────────────────────────────────────────┘
    ├─ REVIEWING → 確認/取消/編輯
    ├─ EDITING → 收集編輯值
    ├─ COLLECTING/DIGRESSION/PAUSED → 收集欄位
    └─ 無表單會話 ↓

┌─────────────────────────────────────────────────────────────┐
│ Step 1: 驗證業者                                             │
│ Step 2: 緩存檢查                                             │
│ Step 3: 意圖分類                                             │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3.5: SOP Orchestrator 檢查                              │
│ ⭐ 優先級：SOP > 知識庫                                       │
└─────────────────────────────────────────────────────────────┘
    ├─ 有 SOP → 處理 4 種觸發模式 + 3 種後續動作 → 返回 ✅
    └─ 無 SOP ↓

┌─────────────────────────────────────────────────────────────┐
│ Step 6: 知識庫檢索（混合模式：向量 + 意圖）                    │
│ 閾值：0.55                                                   │
└─────────────────────────────────────────────────────────────┘
    ├─ 無知識 → Step 8（無知識處理）
    └─ 有知識 ↓

┌─────────────────────────────────────────────────────────────┐
│ Step 9: 構建知識回應                                          │
│ ⭐ 步驟 1：高質量過濾（閾值 0.8）                              │
│ ⭐ 步驟 2：檢查 action_type                                   │
│ ⭐ 步驟 3：direct_answer 流程                                 │
└─────────────────────────────────────────────────────────────┘
    ├─ action_type = form_fill → 觸發表單 ✅
    ├─ action_type = api_call → 調用 API ✅
    ├─ action_type = form_then_api → 表單 + API ✅
    └─ action_type = direct_answer → LLM 優化答案 ✅

┌─────────────────────────────────────────────────────────────┐
│ Step 8: 無知識處理（後備機制）                                 │
└─────────────────────────────────────────────────────────────┘
    ├─ 參數型問題 → 參數答案 ✅
    └─ 其他 → 兜底回應 + 記錄場景 ✅
```

---

## Step 0: 表單會話檢查

### 為什麼需要 Step 0？

**核心原則**：**上下文優先於內容**

表單對話是**有狀態的多輪對話**，需要保持上下文：

```
第一輪（觸發表單）：
  用戶：「冷氣壞了」
  → SOP/知識庫觸發表單
  → 創建 session_state (COLLECTING)
  → 返回：「請問您的聯絡電話是？」

第二輪（收集欄位）：
  用戶：「0912345678」← 這不是新問題，是回答表單欄位
  → ⭐ Step 0: 檢測到 session_state (COLLECTING)
  → 將「0912345678」當作表單資料收集
  → 返回：「請問維修地址是？」

如果沒有 Step 0：
  用戶：「0912345678」
  → Step 3: 意圖分類（unclear）
  → Step 6: 知識庫檢索（找不到）
  → Step 8: 兜底回應
  → 表單中斷 ❌
```

### 表單狀態機

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │ trigger_form()
                           ↓
                    ┌─────────────┐
                 ┌─→│  COLLECTING │←─┐
                 │  └──────┬──────┘  │
                 │         │         │
                 │         │ 離題？   │
                 │         ↓         │
                 │  ┌─────────────┐  │
   resume_form() │  │ DIGRESSION  │  │ 選擇恢復
                 │  └──────┬──────┘  │
                 │         │         │
                 │         │ 選擇取消 │
                 │         ↓         │
                 │  ┌─────────────┐  │
                 └──│   PAUSED    │──┘
                    └──────┬──────┘
                           │ 所有欄位收集完成
                           ↓
                    ┌─────────────┐
                 ┌─→│  REVIEWING  │
                 │  └──────┬──────┘
                 │         │
    修改請求      │         │ 確認
  handle_edit()  │         ↓
                 │  ┌─────────────┐
                 │  │  EDITING    │
                 │  └──────┬──────┘
                 │         │ collect_edited_field()
                 └─────────┘
                           │ 確認提交
                           ↓
                    ┌─────────────┐
                    │  COMPLETED  │
                    └─────────────┘
```

### Step 0 處理邏輯

**位置**：`chat.py` lines 1692-1775

```python
# Step 0: 檢查表單會話
if request.session_id:
    session_state = await form_manager.get_session_state(request.session_id)

    # 處理 REVIEWING 狀態（審核確認）
    if session_state and session_state['state'] == 'REVIEWING':
        user_choice = request.message.strip()

        if user_choice.lower() in ["確認", "confirm", "ok", "提交", "submit"]:
            # 完成表單
            return complete_form()
        elif user_choice.lower() in ["取消", "cancel", "放棄"]:
            # 取消表單
            return cancel_form()
        else:
            # 修改欄位
            return handle_edit_request()

    # 處理 EDITING 狀態（編輯欄位）
    if session_state and session_state['state'] == 'EDITING':
        return collect_edited_field()

    # 處理 COLLECTING、DIGRESSION、PAUSED 狀態（收集欄位）
    if session_state and session_state['state'] in ['COLLECTING', 'DIGRESSION', 'PAUSED']:
        # 收集欄位資料
        form_result = await form_manager.collect_field_data(...)

        # 如果用戶選擇取消表單並有待處理的問題
        if form_result.get('form_cancelled') and form_result.get('pending_question'):
            # 繼續處理待處理的問題（走後續流程）
            request.message = pending_question
        else:
            return form_result
```

### 防止「困住用戶」的機制

#### 1. 離題偵測（Digression Detection）

```
系統：「請問維修地址是？」
用戶：「冷氣壞了怎麼辦？」← 這是新問題，不是地址

→ 離題偵測器判斷：這是問題，不是表單資料
→ 狀態切換：COLLECTING → DIGRESSION
→ 詢問用戶：
   「您似乎有新問題。要：
    1. 先回答這個問題，稍後繼續填表單
    2. 取消表單」

用戶選擇 1：
  → 暫時處理問題
  → 問題回答完畢
  → 詢問：「要繼續填寫表單嗎？」
  → 用戶確認 → 恢復表單（DIGRESSION → COLLECTING）

用戶選擇 2：
  → 取消表單
  → 處理新問題
```

#### 2. 明確的取消指令

```
系統：「請問維修地址是？」
用戶：「取消」或「cancel」或「放棄」

→ 表單立即取消
→ 返回：「已取消表單填寫」
```

#### 3. 狀態過期（TTL）

```
表單會話有效期：30 分鐘（可配置）
→ 超過 30 分鐘未活動
→ 自動清除 session_state
→ 下次訊息走正常流程
```

---

## Step 1-3: 基礎處理

### Step 1: 驗證業者（Lines 1774-1775）

```python
resolver = get_vendor_param_resolver()
vendor_info = _validate_vendor(request.vendor_id, resolver)
```

**作用**：
- 驗證業者 ID 是否存在
- 獲取業者資訊（名稱、業態類型等）
- 失敗時拋出 404 錯誤

---

### Step 2: 緩存檢查（Lines 1778-1781）

```python
cache_service = req.app.state.cache_service
cached_response = _check_cache(cache_service, request.vendor_id, request.message, request.target_user)
if cached_response:
    return cached_response
```

**作用**：
- 檢查是否有相同問題的緩存答案
- 緩存策略：事件驅動 + TTL 混合
- 表單期間不使用緩存

**緩存失效場景**：
- 知識庫更新
- SOP 更新
- 意圖更新
- TTL 過期（可配置）

---

### Step 3: 意圖分類（Lines 1784-1785）

```python
intent_classifier = req.app.state.intent_classifier
intent_result = intent_classifier.classify(request.message)
```

**返回結果**：
```python
{
    "intent_name": "maintenance_request",  # 主要意圖
    "confidence": 0.92,                    # 信心度
    "intent_ids": [15, 23, 8],            # 所有相關意圖 ID
    "secondary_intents": [...],            # 次要意圖
    "all_intents": [...]                   # 所有意圖（含分數）
}
```

**特殊情況**：
- 信心度 < 0.7 → `intent_name = 'unclear'`
- unclear 時 `intent_id = None`（Step 5 會處理）

---

## Step 3.5: SOP Orchestrator

### 為什麼需要 SOP 優先？

**設計原則**：**流程化內容 > 靜態內容**

```
SOP（Standard Operating Procedure）：
  - 流程化的問題解決步驟
  - 支持多輪對話
  - 支持後續動作（表單、API）
  - 適合故障排查、操作指南

知識庫：
  - 靜態的問答內容
  - 單輪對話為主
  - 適合常見問題解答
```

### SOP Orchestrator 流程

**位置**：`chat.py` lines 1787-1809

```python
if not request.skip_sop and request.session_id:
    orchestrator_result = await sop_orchestrator.process_message(
        user_message=request.message,
        session_id=request.session_id,
        user_id=request.user_id or "unknown",
        vendor_id=request.vendor_id,
        intent_id=None,
        intent_ids=intent_result.get('intent_ids', [])
    )

    if orchestrator_result.get('has_sop'):
        return await _build_orchestrator_response(...)
```

### SOP 處理邏輯

```
SOP Orchestrator.process_message()
    ↓
  1. 檢查是否有 SOP Context（manual/immediate 模式）
    ├─ 有 Context → 匹配 trigger_keywords
    │   ├─ 匹配成功 → 執行 next_action
    │   └─ 不匹配 → 返回提示
    └─ 無 Context → 檢索 SOP
        ├─ 找到 SOP → 處理 trigger_mode
        └─ 未找到 → 返回 has_sop=False
```

### 4 種觸發模式

| trigger_mode | 說明 | 流程 | 使用場景 |
|-------------|------|------|---------|
| **none** | 純資訊 | 顯示內容 → 結束 | 操作說明、注意事項 |
| **manual** | 手動觸發 | 顯示內容 → 儲存 context → 等待關鍵字 | 故障排查（先自己試） |
| **immediate** | 立即詢問 | 顯示內容 → 立即詢問確認 → 儲存 context | 需要用戶確認的操作 |
| **auto** | 自動執行 | 顯示內容 → 自動執行 API | 緊急處理（例如報警） |

### 3 種後續動作

| next_action | 說明 | 適用場景 |
|------------|------|---------|
| **form_fill** | 觸發表單 | 需要收集用戶資訊 |
| **api_call** | 調用 API | 已有足夠資訊，直接執行 |
| **form_then_api** | 先填表單，完成後調用 API | 需要收集資訊後執行 |

### SOP 範例流程

#### 範例 1：manual 模式（故障排查）

```
SOP：冷氣故障排查
trigger_mode: manual
next_action: form_fill
trigger_keywords: ['還是不行', '試過了', '沒用']
followup_prompt: '如果還是無法解決，可以填寫報修表單'

流程：
  用戶：「冷氣不冷」
  → 找到 SOP
  → 顯示排查步驟：
    「請先檢查：
     1. 濾網是否乾淨
     2. 溫度設定是否正確
     3. 室外機是否運轉」
  → 儲存 context（等待關鍵字）
  → 返回 ✅

  用戶：「試過了還是不行」← 匹配到 trigger_keywords
  → 觸發 next_action (form_fill)
  → 開始填寫報修表單
  → 返回：「請問您的聯絡電話是？」✅
```

#### 範例 2：immediate 模式（確認操作）

```
SOP：重啟系統
trigger_mode: immediate
next_action: api_call
trigger_keywords: ['確認', '是的', '好']
immediate_prompt: '確定要重啟系統嗎？這會中斷目前的服務。'

流程：
  用戶：「系統卡住了」
  → 找到 SOP
  → 顯示內容 + 立即詢問：
    「確定要重啟系統嗎？這會中斷目前的服務。」
  → 儲存 context
  → 返回 ✅

  用戶：「確認」← 匹配到 trigger_keywords
  → 觸發 next_action (api_call)
  → 調用重啟 API
  → 返回：「系統正在重啟...」✅
```

---

## Step 6: 知識庫檢索

### 混合檢索模式

**位置**：`chat.py` lines 1817-1821

```python
# Step 5: 獲取意圖 ID
intent_id = None if intent_result['intent_name'] == 'unclear' else _get_intent_id(intent_result['intent_name'])

# Step 6: 檢索知識庫
knowledge_list = await _retrieve_knowledge(request, intent_id, intent_result)
```

### _retrieve_knowledge() 實現

```python
async def _retrieve_knowledge(request, intent_id, intent_result):
    """
    檢索知識庫（混合模式：intent + 向量相似度 + 語義匹配）

    ✅ 統一檢索路徑：
    - 降低閾值到 0.55（涵蓋原 RAG fallback 範圍）
    - 使用語義匹配動態計算 intent_boost
    - 支持 intent_id = None（unclear 情況）
    """
    retriever = get_vendor_knowledge_retriever()
    all_intent_ids = intent_result.get('intent_ids', [])

    kb_similarity_threshold = 0.55

    knowledge_list = await retriever.retrieve_knowledge_hybrid(
        query=request.message,
        intent_id=intent_id,
        vendor_id=request.vendor_id,
        top_k=request.top_k,
        similarity_threshold=kb_similarity_threshold,
        all_intent_ids=all_intent_ids,
        target_user=request.target_user,
        return_debug_info=request.include_debug_info
    )

    return knowledge_list
```

### 混合檢索詳細流程

```
retrieve_knowledge_hybrid()
    ↓
  1. 獲取問題向量 embedding
  2. SQL 查詢（向量相似度 >= 0.55 / 1.3）
  3. SQL 計算 intent_boost（精確匹配 1.3x）
  4. Python 重新計算 intent_boost（語義相似度）
  5. 計算最終相似度 = base_similarity × intent_boost
  6. 過濾 >= 0.55
  7. Scope 優先級排序
  8. 返回 top_k 結果
```

### Scope 優先級

| Scope | 優先級 | 說明 |
|-------|--------|------|
| **customized** | 1000 | 業者客製化知識（最高優先） |
| **vendor** | 500 | 業者專屬知識 |
| **global** | 100 | 全域通用知識 |

### Intent Boost 計算

```python
# 精確匹配主要意圖
if knowledge.intent_id == main_intent_id:
    boost = 1.3

# 精確匹配次要意圖
elif knowledge.intent_id in secondary_intent_ids:
    boost = 1.1

# 語義相似度計算
else:
    semantic_similarity = calculate_semantic_similarity(
        knowledge.intent_name,
        user_intent_name
    )
    if semantic_similarity >= 0.7:
        boost = 1.0 + (semantic_similarity - 0.7) × 0.3 / 0.3
    else:
        boost = 1.0
```

---

## Step 9: 構建知識回應

### ⭐ 2026-01-24 修正重點

**問題**：原本 action_type 檢查在高質量過濾之前，可能觸發低質量知識的表單。

**修正**：調整順序，先過濾再檢查 action_type。

### 新的處理順序

**位置**：`chat.py` lines 1006-1098

```python
async def _build_knowledge_response(...):
    """使用知識庫結果構建優化回應"""

    # ⭐ 步驟 1：高質量過濾（先過濾再處理 action_type）
    high_quality_threshold = 0.8
    filtered_knowledge_list = [k for k in knowledge_list if k['similarity'] >= high_quality_threshold]

    if not filtered_knowledge_list:
        # 所有知識都低於 0.8 → 無知識處理
        return await _handle_no_knowledge_found(...)

    # ⭐ 步驟 2：檢查 action_type（使用過濾後的知識）
    best_knowledge = filtered_knowledge_list[0]
    action_type = best_knowledge.get('action_type', 'direct_answer')

    if action_type == 'form_fill':
        # 檢查必要參數
        if not form_id:
            action_type = 'direct_answer'  # 降級
        elif not request.session_id or not request.user_id:
            action_type = 'direct_answer'  # 降級
        else:
            # 觸發表單
            return trigger_form()

    elif action_type == 'api_call':
        # 檢查 api_config
        if not api_config:
            action_type = 'direct_answer'  # 降級
        else:
            # 調用 API
            return call_api()

    elif action_type == 'form_then_api':
        # 檢查必要參數
        if not form_id or not request.session_id:
            action_type = 'direct_answer'  # 降級
        else:
            # 觸發表單（完成後會調用 API）
            return trigger_form()

    # ⭐ 步驟 3：direct_answer 流程
    # 信心度評估
    evaluation = confidence_evaluator.evaluate(...)

    # LLM 優化答案
    optimization_result = llm_optimizer.optimize_answer(...)

    # 返回優化答案
    return VendorChatResponse(...)
```

### action_type 支持的動作

| action_type | 說明 | 必要參數 | 降級條件 |
|------------|------|---------|---------|
| **direct_answer** | 直接回答 | 無 | - |
| **form_fill** | 觸發表單 | `form_id`, `session_id`, `user_id` | 缺少任一參數 |
| **api_call** | 調用 API | `api_config` | 缺少 api_config |
| **form_then_api** | 先表單後 API | `form_id`, `api_config`, `session_id` | 缺少任一參數 |

### 降級邏輯（明確設置）

**2026-01-24 修正**：所有降級場景都明確設置 `action_type = 'direct_answer'`

```python
# 修正前
if not form_id:
    print("缺少 form_id，降級")
    # ❌ action_type 仍是 'form_fill'

# 修正後
if not form_id:
    print("缺少 form_id，降級為 direct_answer")
    action_type = 'direct_answer'  # ✅ 明確降級
```

---

## Step 8: 無知識處理

### 後備機制層級

```
無知識處理 _handle_no_knowledge_found()
    ↓
  Step 1: 參數型問題檢查
    ├─ payment 類（繳費日、逾期費）→ 參數答案 ✅
    ├─ cashflow 類（帳號、轉帳資訊）→ 參數答案 ✅
    ├─ contract 類（租期、押金）→ 參數答案 ✅
    └─ 不匹配 ↓

  Step 2: 兜底回應 + 記錄場景
    ├─ 記錄到 test_scenarios 表
    ├─ 記錄到意圖建議系統
    └─ 返回兜底模板答案 ✅
```

### 參數型問題處理

**位置**：`chat.py` lines 854-891

```python
# Step 1: 檢查是否為參數型問題
param_category, param_answer = await check_param_question(
    vendor_config_service=req.app.state.vendor_config_service,
    question=request.message,
    vendor_id=request.vendor_id
)

if param_answer:
    return VendorChatResponse(
        answer=param_answer['answer'],
        intent_name="參數查詢",
        intent_type="config_param",
        confidence=1.0
    )
```

**範例**：
```
用戶：「繳費日是幾號？」
→ param_category = 'payment'
→ 從業者配置取得 payment_day = 5
→ 返回：「繳費日為每月 5 號」✅
```

### 兜底回應

**位置**：`chat.py` lines 897-933

```python
# Step 2: 記錄場景並返回兜底回應
await _record_no_knowledge_scenario(request, intent_result, req)

fallback_answer = "我目前沒有找到符合您問題的資訊，但我可以協助您轉給客服處理。如需立即協助，請撥打客服專線 {{service_hotline}}。"

final_answer, used_param_keys = _clean_answer_with_tracking(
    fallback_answer, request.vendor_id, resolver
)

return VendorChatResponse(
    answer=final_answer,
    sources=None,
    source_count=0
)
```

### 場景記錄機制

```python
async def _record_no_knowledge_scenario(...):
    """記錄找不到知識的場景"""

    # 1. 記錄到測試場景庫
    INSERT INTO test_scenarios (
        test_question,
        status,
        source,
        notes
    ) VALUES (
        request.message,
        'pending_review',
        'user_question',
        '系統無法提供答案'
    )

    # 2. 記錄到意圖建議系統
    suggestion_engine.analyze_unclear_question(
        question=request.message,
        vendor_id=request.vendor_id
    )
```

**目的**：
- 追蹤知識庫覆蓋率
- 識別需要新增的知識
- 改善意圖分類

---

## 關鍵決策點分析

### 1. 為什麼表單會話檢查是 Step 0？

**原則**：**上下文優先於內容**

| 對話類型 | 是否有狀態 | 每個訊息的解讀 | 優先級 |
|---------|-----------|--------------|-------|
| 表單填寫 | ✅ 有狀態 | 依據當前欄位 | 最高 |
| SOP 流程 | ✅ 有狀態 | 依據 context | 高 |
| 知識問答 | ❌ 無狀態 | 獨立解讀 | 中 |
| 參數查詢 | ❌ 無狀態 | 獨立解讀 | 低 |

**如果沒有 Step 0**：
```
用戶正在填表單，輸入「0912345678」
→ 系統誤認為新問題
→ 走知識庫檢索
→ 表單資料遺失 ❌
```

---

### 2. 為什麼 SOP 優先於知識庫？

**原則**：**流程化內容 > 靜態內容**

| 特性 | SOP | 知識庫 |
|------|-----|--------|
| 對話模式 | 多輪對話 | 單輪問答 |
| 內容類型 | 流程化步驟 | 靜態內容 |
| 後續動作 | 支持（表單/API） | 支持（透過 action_type） |
| 適用場景 | 故障排查、操作指南 | 常見問題解答 |

**範例**：
```
用戶：「冷氣壞了」

SOP 模式：
  1. 顯示排查步驟
  2. 等待用戶回報結果
  3. 如果無法解決 → 觸發報修表單
  → 完整的問題解決流程 ✅

知識庫模式：
  1. 顯示冷氣故障說明
  → 單次回答結束 ⚠️
```

---

### 3. 為什麼需要高質量過濾？

**原則**：**質量優先於數量**

**雙重閾值設計**：
- **檢索閾值 0.55**：廣泛檢索，避免遺漏
- **使用閾值 0.8**：嚴格過濾，確保質量

```
知識 A: similarity = 0.85 → ✅ 用於回答
知識 B: similarity = 0.70 → ❌ 不使用（但會顯示在 debug）
知識 C: similarity = 0.50 → ❌ 不檢索
```

**2026-01-24 修正的重要性**：
- 修正前：知識 B 可能觸發表單（similarity 0.70）
- 修正後：只有知識 A 會觸發表單（similarity 0.85）

---

### 4. 為什麼需要 action_type？

**原則**：**知識庫不只是靜態內容**

傳統設計：
```
知識庫 → 只能回答問題
需要收集資訊 → 必須透過 SOP
```

新設計：
```
知識庫 → 可以觸發後續動作
  ├─ direct_answer（回答問題）
  ├─ form_fill（收集資訊）
  ├─ api_call（執行操作）
  └─ form_then_api（收集後執行）
```

**好處**：
- 知識庫更靈活
- 減少 SOP 配置工作
- 統一管理介面

---

## 設計原則說明

### 原則 1：上下文優先於內容

**表單對話 > 其他對話**

```
表單填寫中：
  用戶：「123」
  → 不走意圖分類
  → 不走知識庫
  → 當作表單資料處理 ✅
```

### 原則 2：流程化內容 > 靜態內容

**SOP > 知識庫**

```
複雜問題：
  → 優先使用 SOP（支持多輪對話）
  → 知識庫作為後備（單輪問答）
```

### 原則 3：質量優先於數量

**高質量過濾（0.8）> 檢索閾值（0.55）**

```
檢索：廣撒網（0.55）
使用：嚴格篩選（0.8）
```

### 原則 4：內容優先於資料收集

**知識/SOP > 表單觸發**

```
有相關知識：
  → 先顯示知識內容
  → 知識可能包含 action_type=form_fill
  → 內容 + 表單結合 ✅

無相關知識：
  → 不觸發表單（修正前的錯誤）
  → 使用參數答案或兜底回應 ✅
```

### 原則 5：向量為主，意圖為輔

**向量相似度 > 意圖匹配**

```
檢索基礎：向量相似度（語義理解）
優化排序：意圖加成（1.0 ~ 1.3x）
降級處理：unclear 時 boost = 1.0
```

---

## 📊 流程統計

### 優先級層級

| 層級 | 檢查項目 | 優先級原則 | 返回率 |
|------|---------|-----------|--------|
| 0 | 表單會話 | 上下文優先 | ~5% |
| 1 | 業者驗證 | 基礎驗證 | 0% (失敗拋錯) |
| 2 | 緩存 | 性能優化 | ~20% |
| 3 | 意圖分類 | 所有請求 | 0% (必經) |
| 3.5 | SOP | 流程優先 | ~10% |
| 6 | 知識庫 | 內容主體 | ~60% |
| 8 | 無知識處理 | 後備機制 | ~5% |

### 響應時間估算

| 路徑 | 平均響應時間 | 說明 |
|------|------------|------|
| 緩存命中 | ~50ms | 直接返回緩存 |
| 表單收集 | ~100ms | 簡單驗證 + 狀態更新 |
| SOP 回應 | ~200ms | 檢索 + 處理 |
| 知識庫回應 | ~500ms | 向量檢索 + LLM 優化 |
| 無知識處理 | ~300ms | 參數查詢 + 記錄 |

---

## ✅ 總結

### 核心優勢

1. **清晰的優先級**：表單 > SOP > 知識庫 > 參數 > 兜底
2. **完整的狀態機**：表單 7 種狀態完整處理
3. **雙重閾值**：0.55 檢索 + 0.8 使用
4. **彈性的 action_type**：4 種後續動作
5. **完善的記錄**：無知識場景自動記錄

### 2026-01-24 修正成果

1. **高質量保證**：action_type 檢查在過濾之後
2. **PAUSED 支援**：SOP form_then_api 場景完整
3. **明確降級**：所有降級場景明確處理

### 相關文檔

- **修正報告**：[CHAT_LOGIC_FIXES_2026-01-24.md](../fixes/CHAT_LOGIC_FIXES_2026-01-24.md)
- **SOP 文檔**：[SOP_NEXT_ACTION.md](../features/SOP_NEXT_ACTION.md)
- **表單文檔**：[FORM_STATE_MACHINE.md](../features/FORM_STATE_MACHINE.md)

---

**文檔維護人員**：Claude
**最後更新**：2026-01-24
**狀態**：✅ 完整分析
