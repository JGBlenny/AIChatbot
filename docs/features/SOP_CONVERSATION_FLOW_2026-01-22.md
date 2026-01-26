# 🔄 SOP 後續動作 - 完整對話流程

**日期**: 2026-01-22
**目的**: 詳細說明 SOP 後續動作在實際對話中的執行流程

---

## 📊 完整對話流程圖

```
┌─────────────────────────────────────────────────────────────────┐
│ 第一輪對話：租戶提出問題                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        POST /v1/chat/vendor
        {
          "vendor_id": 1,
          "user_id": "user_123",
          "session_id": "session_abc",
          "message": "冷氣無法啟動",
          "user_role": "tenant"
        }
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 檢查是否有待處理的 SOP 後續動作                           │
│                                                                  │
│ sop_context = get_sop_context_from_session(session_id, user_id) │
│ → 結果: None（首次對話）                                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 意圖分類                                                 │
│                                                                  │
│ IntentClassifier.classify("冷氣無法啟動")                        │
│ → intent_id: 25                                                 │
│ → intent_name: "冷氣維修"                                        │
│ → confidence: 0.95                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: SOP 檢索（優先級最高）                                    │
│                                                                  │
│ VendorSOPRetriever.retrieve_sop_hybrid(                         │
│   vendor_id=1,                                                  │
│   intent_ids=[25],                                              │
│   query="冷氣無法啟動"                                           │
│ )                                                               │
│                                                                  │
│ → 找到 SOP: "空調無法啟動"                                       │
│   {                                                             │
│     id: 123,                                                    │
│     item_name: "空調無法啟動",                                   │
│     content: "【排查步驟】\n1️⃣ 檢查電源...",                     │
│     next_action: "form_then_api",                               │
│     next_form_id: "maintenance_troubleshooting",                │
│     trigger_keywords: ["還是不行", "試過了", "需要維修"],        │
│     followup_prompt: "好的，我來協助您提交維修請求...",          │
│     next_api_config: {                                          │
│       endpoint: "maintenance_request",                          │
│       params: {                                                 │
│         problem_category: "ac_maintenance",                     │
│         specific_problem: "ac_not_starting",                    │
│         urgency_level: "urgent"                                 │
│       }                                                         │
│     }                                                           │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: 構建 SOP 回應                                            │
│                                                                  │
│ async def _build_sop_response(...):                             │
│   # 4.1 格式化 SOP 內容                                         │
│   raw_answer = _format_sop_answer(sop_items, group_name)       │
│                                                                  │
│   # 4.2 替換模板變數                                            │
│   final_answer = _clean_answer(raw_answer, vendor_id)          │
│                                                                  │
│   # 4.3 ✨ 如果 SOP 有 next_action，記錄到 session              │
│   if sop_items[0].get('next_action') != 'none':                 │
│     await save_sop_context_to_session(                          │
│       session_id=request.session_id,                            │
│       user_id=request.user_id,                                  │
│       vendor_id=request.vendor_id,                              │
│       sop_item_id=sop_items[0]['id'],                           │
│       next_action=sop_items[0]['next_action'],                  │
│       next_form_id=sop_items[0].get('next_form_id'),            │
│       next_api_config=sop_items[0].get('next_api_config'),      │
│       trigger_keywords=sop_items[0].get('trigger_keywords'),    │
│       followup_prompt=sop_items[0].get('followup_prompt')       │
│     )                                                           │
│                                                                  │
│   # 4.4 返回回應                                                │
│   return VendorChatResponse(                                    │
│     answer=final_answer,                                        │
│     ...                                                         │
│   )                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 系統回應給租戶                                                   │
│                                                                  │
│ {                                                               │
│   "answer": "【排查步驟】\n1️⃣ 檢查電源插座...\n若無法解決，請提交維修請求。",│
│   "intent_name": "冷氣維修",                                     │
│   "confidence": 0.95                                            │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        Session 中記錄了 SOP Context:
        {
          "sop_item_id": 123,
          "next_action": "form_then_api",
          "next_form_id": "maintenance_troubleshooting",
          "trigger_keywords": ["還是不行", "試過了", "需要維修"],
          "followup_prompt": "好的，我來協助您...",
          "next_api_config": {...},
          "created_at": "2026-01-22T10:30:00",
          "is_triggered": false
        }


┌─────────────────────────────────────────────────────────────────┐
│ 第二輪對話：租戶回覆排查結果                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        POST /v1/chat/vendor
        {
          "vendor_id": 1,
          "user_id": "user_123",
          "session_id": "session_abc",  ← 同一個 session
          "message": "都試過了，還是不行",
          "user_role": "tenant"
        }
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 檢查是否有待處理的 SOP 後續動作                           │
│                                                                  │
│ sop_context = get_sop_context_from_session(                     │
│   session_id="session_abc",                                     │
│   user_id="user_123"                                            │
│ )                                                               │
│                                                                  │
│ → 找到 SOP Context:                                             │
│   {                                                             │
│     sop_item_id: 123,                                           │
│     next_action: "form_then_api",                               │
│     trigger_keywords: ["還是不行", "試過了", "需要維修"],        │
│     is_triggered: false  ← 尚未觸發                             │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 檢測關鍵詞                                               │
│                                                                  │
│ user_message = "都試過了，還是不行".lower()                      │
│ trigger_keywords = ["還是不行", "試過了", "需要維修"]            │
│                                                                  │
│ matched = any(keyword in user_message for keyword in trigger_keywords)│
│ → matched = True  （包含「還是不行」和「試過了」）               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 觸發後續動作                                             │
│                                                                  │
│ if matched:                                                     │
│   # 3.1 標記為已觸發（防止重複觸發）                             │
│   mark_sop_context_as_triggered(session_id, user_id)           │
│                                                                  │
│   # 3.2 根據 next_action 類型執行                               │
│   if next_action == 'form_then_api':                            │
│     return await trigger_form_from_sop(request, sop_context)    │
│   elif next_action == 'form_fill':                              │
│     return await trigger_form_from_sop(request, sop_context)    │
│   elif next_action == 'api_call':                               │
│     return await trigger_api_from_sop(request, sop_context)     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: 觸發表單（trigger_form_from_sop）                        │
│                                                                  │
│ async def trigger_form_from_sop(request, sop_context):          │
│   form_id = sop_context['next_form_id']                         │
│   followup_prompt = sop_context['followup_prompt']              │
│   api_config = sop_context.get('next_api_config')               │
│                                                                  │
│   # 4.1 從 api_config.params 中提取預填資料                      │
│   prefill_data = api_config.get('params', {}) if api_config else {}│
│                                                                  │
│   # 4.2 啟動表單                                                │
│   form_manager = get_form_manager()                             │
│   form_result = await form_manager.start_form(                  │
│     session_id=request.session_id,                              │
│     user_id=request.user_id,                                    │
│     vendor_id=request.vendor_id,                                │
│     form_id=form_id,                                            │
│     intro_message=followup_prompt,                              │
│     prefill_data=prefill_data  ← 預填 SOP 提供的資訊            │
│   )                                                             │
│                                                                  │
│   # 4.3 如果是 form_then_api，記錄 API callback                 │
│   if sop_context['next_action'] == 'form_then_api':             │
│     await save_form_completion_callback(                        │
│       form_session_id=form_result['form_session_id'],           │
│       callback_type='api_call',                                 │
│       callback_config=api_config                                │
│     )                                                           │
│                                                                  │
│   # 4.4 返回表單回應                                            │
│   return form_result                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 系統回應給租戶（觸發表單）                                        │
│                                                                  │
│ {                                                               │
│   "answer": "好的，我來協助您提交維修請求。請提供一些詳細資訊。\n\n請說明問題發生的具體位置（例如：主臥室、浴室）",│
│   "form_session_id": "form_session_xyz",                        │
│   "form_id": "maintenance_troubleshooting",                     │
│   "current_field": "problem_location",                          │
│   "form_state": "COLLECTING"                                    │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        form_sessions 表記錄:
        {
          session_id: "session_abc",
          user_id: "user_123",
          form_id: "maintenance_troubleshooting",
          state: "COLLECTING",
          current_field_index: 0,
          collected_data: {
            "problem_category": "ac_maintenance",  ← 預填
            "specific_problem": "ac_not_starting", ← 預填
            "urgency_level": "urgent"              ← 預填
          }
        }


┌─────────────────────────────────────────────────────────────────┐
│ 第三輪對話：租戶回答第一個問題                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        POST /v1/chat/vendor
        {
          "session_id": "session_abc",
          "message": "主臥室",
          "user_role": "tenant"
        }
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 檢查表單會話                                             │
│                                                                  │
│ form_session = get_active_form_session(session_id, user_id)     │
│ → 找到表單會話，state = COLLECTING                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 收集欄位資料                                             │
│                                                                  │
│ FormManager.collect_field_value(                                │
│   form_session_id="form_session_xyz",                           │
│   field_name="problem_location",                                │
│   value="主臥室"                                                 │
│ )                                                               │
│                                                                  │
│ → 儲存到 collected_data                                         │
│ → current_field_index++                                         │
│ → 返回下一個欄位的問題                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        系統回應：「問題大約什麼時候開始的？」
                              ↓
        ... 繼續收集所有欄位 ...


┌─────────────────────────────────────────────────────────────────┐
│ 第 N 輪對話：租戶完成最後一個欄位                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        POST /v1/chat/vendor
        {
          "session_id": "session_abc",
          "message": "我確認提交",
          "user_role": "tenant"
        }
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 收集最後一個欄位                                         │
│                                                                  │
│ FormManager.collect_field_value(                                │
│   field_name="confirm_submit",                                  │
│   value="confirmed"                                             │
│ )                                                               │
│                                                                  │
│ → 所有欄位收集完成！                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 完成表單                                                 │
│                                                                  │
│ FormManager.complete_form(form_session_id)                      │
│                                                                  │
│ # 2.1 創建 form_submission 記錄                                 │
│ form_submission = FormSubmission.create({                       │
│   form_id: "maintenance_troubleshooting",                       │
│   user_id: "user_123",                                          │
│   vendor_id: 1,                                                 │
│   submitted_data: {                                             │
│     "problem_category": "ac_maintenance",                       │
│     "specific_problem": "ac_not_starting",                      │
│     "urgency_level": "urgent",                                  │
│     "problem_location": "主臥室",                                │
│     "when_started": "today",                                    │
│     "tried_troubleshooting": "yes",                             │
│     "troubleshooting_details": "試過重啟電源和遙控器",           │
│     "detailed_description": "完全沒反應，面板不亮",              │
│     ...                                                         │
│   },                                                            │
│   status: "pending"                                             │
│ })                                                              │
│                                                                  │
│ # 2.2 更新 form_session.state = COMPLETED                       │
│ form_session.update(state='COMPLETED', completed_at=now())      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 檢查是否有 API callback                                  │
│                                                                  │
│ callback = get_form_completion_callback(form_session_id)        │
│                                                                  │
│ → 找到 callback:                                                │
│   {                                                             │
│     callback_type: "api_call",                                  │
│     callback_config: {                                          │
│       endpoint: "maintenance_request",                          │
│       params: {...}                                             │
│     }                                                           │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: 自動調用 API                                             │
│                                                                  │
│ api_handler = get_api_call_handler()                            │
│ api_result = await api_handler.execute_api_call(                │
│   api_config=callback_config,                                   │
│   session_data={                                                │
│     user_id: "user_123",                                        │
│     vendor_id: 1,                                               │
│     session_id: "session_abc"                                   │
│   },                                                            │
│   form_data=form_submission.submitted_data  ← 表單收集的資料    │
│ )                                                               │
│                                                                  │
│ ↓                                                               │
│                                                                  │
│ # API Handler 調用 maintenance_request                          │
│ # (在 services/billing_api.py 中實作)                           │
│                                                                  │
│ async def submit_maintenance_request(form_data, session_data):  │
│   # 4.1 計算優先級                                              │
│   priority = calculate_priority(                                │
│     urgency_level=form_data['urgency_level'],                   │
│     problem_category=form_data['problem_category']              │
│   )  # → P1                                                     │
│                                                                  │
│   # 4.2 生成工單編號                                            │
│   ticket_number = generate_ticket_number()  # → "MT20260122001"│
│                                                                  │
│   # 4.3 創建工單（寫入 form_submissions，更新 status 和 notes）│
│   update_form_submission_as_ticket(                             │
│     form_submission_id=form_submission.id,                      │
│     ticket_number=ticket_number,                                │
│     priority=priority,                                          │
│     status='assigned'  # pending → assigned                    │
│   )                                                             │
│                                                                  │
│   # 4.4 發送通知給維修團隊                                      │
│   notify_maintenance_team({                                     │
│     ticket_number: ticket_number,                               │
│     priority: priority,                                         │
│     problem: form_data['specific_problem'],                     │
│     location: form_data['problem_location'],                    │
│     tenant_phone: form_data['tenant_phone']                     │
│   })                                                            │
│                                                                  │
│   # 4.5 返回結果                                                │
│   return {                                                      │
│     success: true,                                              │
│     ticket_number: ticket_number,                               │
│     priority: priority,                                         │
│     estimated_arrival: "4小時內"                                │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 系統最終回應給租戶                                               │
│                                                                  │
│ {                                                               │
│   "answer": "✅ 維修請求已成功提交！\n\n工單編號：MT20260122001\n優先級：P1（緊急）\n預計到達時間：4小時內\n\n維修人員會先致電您確認時間，請保持手機暢通。",│
│   "form_completed": true,                                       │
│   "api_result": {                                               │
│     "ticket_number": "MT20260122001",                           │
│     "priority": "P1",                                           │
│     "estimated_arrival": "4小時內"                              │
│   }                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘


整個流程完成！🎉
```

---

## 🔑 關鍵實現細節

### 1. SOP Context 儲存位置

**Option A: 使用 Redis/快取（推薦）**
```python
# 儲存
await redis_client.setex(
    key=f"sop_context:{session_id}:{user_id}",
    value=json.dumps(sop_context),
    time=3600  # 1小時過期
)

# 讀取
sop_context_json = await redis_client.get(f"sop_context:{session_id}:{user_id}")
sop_context = json.loads(sop_context_json) if sop_context_json else None
```

**Option B: 使用資料庫表**
```sql
CREATE TABLE sop_followup_contexts (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    sop_item_id INTEGER NOT NULL,
    next_action VARCHAR(50) NOT NULL,
    next_form_id VARCHAR(100),
    next_api_config JSONB,
    trigger_keywords TEXT[],
    followup_prompt TEXT,
    is_triggered BOOLEAN DEFAULT FALSE,
    triggered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '1 hour',

    UNIQUE(session_id, user_id)
);

CREATE INDEX idx_sop_followup_session ON sop_followup_contexts(session_id, user_id)
WHERE is_triggered = FALSE AND expires_at > NOW();
```

**推薦 Option A（Redis）** - 更快，自動過期，不污染主資料庫。

---

### 2. 關鍵詞匹配邏輯

```python
def check_trigger_keywords(user_message: str, trigger_keywords: List[str]) -> bool:
    """
    檢查用戶訊息是否包含觸發關鍵詞

    匹配規則：
    1. 不區分大小寫
    2. 支援部分匹配（"還是不行啊" 會匹配 "還是不行"）
    3. 至少匹配一個關鍵詞即觸發
    """
    user_message_lower = user_message.lower().strip()

    for keyword in trigger_keywords:
        keyword_lower = keyword.lower().strip()
        if keyword_lower in user_message_lower:
            return True

    return False
```

**進階匹配（可選）：**
```python
import re

def check_trigger_keywords_advanced(user_message: str, trigger_keywords: List[str]) -> bool:
    """
    進階匹配：支援正則表達式和同義詞

    範例：
    - "還是不行" 也會匹配 "還是沒用", "還是無效"
    - "試過了" 也會匹配 "試了", "都試了"
    """
    # 定義同義詞群組
    synonyms = {
        "還是不行": ["還是不行", "還是沒用", "還是無效", "還不行", "仍然不行"],
        "試過了": ["試過了", "試了", "都試了", "都試過了", "嘗試過了"],
        "需要維修": ["需要維修", "要維修", "請維修", "幫忙維修", "來修"],
    }

    user_message_lower = user_message.lower().strip()

    for keyword in trigger_keywords:
        # 檢查關鍵詞本身
        if keyword.lower() in user_message_lower:
            return True

        # 檢查同義詞
        if keyword in synonyms:
            for synonym in synonyms[keyword]:
                if synonym.lower() in user_message_lower:
                    return True

    return False
```

---

### 3. Form Completion Callback 儲存

```python
# 在觸發表單時，如果是 form_then_api，儲存 callback

async def save_form_completion_callback(
    form_session_id: int,
    callback_type: str,
    callback_config: dict
):
    """
    儲存表單完成後的 callback 配置

    可以儲存在：
    1. form_sessions.collected_data['_callback']
    2. 獨立的 form_callbacks 表
    3. Redis
    """
    # Option 1: 儲存到 form_sessions.collected_data
    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE form_sessions
            SET collected_data = jsonb_set(
                collected_data,
                '{_callback}',
                %s::jsonb
            )
            WHERE id = %s
        """, (
            json.dumps({
                'type': callback_type,
                'config': callback_config
            }),
            form_session_id
        ))
```

```python
# 在表單完成時，檢查並執行 callback

async def on_form_completed(form_session_id: int):
    # 1. 創建 form_submission
    # ...

    # 2. 檢查是否有 callback
    callback = await get_form_completion_callback(form_session_id)

    if callback and callback['type'] == 'api_call':
        # 3. 執行 API 調用
        api_result = await execute_api_call(
            api_config=callback['config'],
            form_data=form_submission.submitted_data
        )

        # 4. 返回結果
        return {
            'form_completed': True,
            'api_result': api_result
        }
```

---

### 4. 預填表單資料

```python
async def start_form_with_prefill(
    session_id: str,
    user_id: str,
    vendor_id: int,
    form_id: str,
    prefill_data: dict
):
    """
    啟動表單並預填資料

    prefill_data 來自 SOP 的 next_api_config.params:
    {
        "problem_category": "ac_maintenance",
        "specific_problem": "ac_not_starting",
        "urgency_level": "urgent"
    }

    這些欄位會：
    1. 自動填入 collected_data
    2. 跳過這些欄位的詢問（直接進入下一個欄位）
    """
    # 1. 獲取表單定義
    form_schema = await get_form_schema(form_id)

    # 2. 創建表單會話
    form_session = await create_form_session(
        session_id=session_id,
        user_id=user_id,
        vendor_id=vendor_id,
        form_id=form_id,
        collected_data=prefill_data  # ← 預填資料
    )

    # 3. 找到第一個未預填的欄位
    current_field_index = 0
    for idx, field in enumerate(form_schema['fields']):
        field_name = field['field_name']
        if field_name not in prefill_data:
            current_field_index = idx
            break

    # 4. 更新 current_field_index
    await update_form_session(
        form_session_id=form_session.id,
        current_field_index=current_field_index
    )

    # 5. 返回第一個未預填欄位的問題
    next_field = form_schema['fields'][current_field_index]
    return {
        'form_session_id': form_session.id,
        'form_id': form_id,
        'current_field': next_field['field_name'],
        'prompt': next_field['prompt']
    }
```

---

## 🔄 狀態轉移圖

```
SOP Context 狀態:
  created → (用戶說觸發關鍵詞) → triggered → expired

Form Session 狀態:
  (SOP觸發) → COLLECTING → (所有欄位收集完) → COMPLETED

Form Submission 狀態:
  (表單完成) → pending → (API調用成功) → assigned → in_progress → completed
```

---

## ⏱️ 時間軸範例

```
T+0s    租戶: "冷氣壞了"
        → 系統返回 SOP 排查步驟
        → 記錄 SOP context (expires_at: T+3600s)

T+180s  租戶: "試過了，還是不行"
        → 檢測到觸發關鍵詞
        → 標記 SOP context 為 triggered
        → 啟動表單 (state: COLLECTING)
        → 提示: "好的，我來協助您..."

T+200s  租戶: "主臥室"
        → 收集 problem_location
        → 進入下一個欄位

T+220s  租戶: "今天發生"
        → 收集 when_started
        → 進入下一個欄位

...     ... 繼續收集所有欄位 ...

T+350s  租戶: "我確認提交"
        → 所有欄位收集完成
        → 創建 form_submission (status: pending)
        → 更新 form_session (state: COMPLETED)
        → 檢查 callback → 找到 api_call
        → 調用 maintenance_request API
        → 創建工單 MT20260122001
        → 更新 form_submission (status: assigned)
        → 發送通知
        → 返回工單資訊給租戶
```

---

## 📝 實施檢查清單

### 後端修改

- [ ] **chat.py - vendor_chat 函數開頭**
  - 新增：檢查 SOP context
  - 新增：關鍵詞匹配邏輯
  - 新增：觸發表單/API 函數

- [ ] **chat.py - _build_sop_response 函數**
  - 新增：儲存 SOP context 到 Redis/DB

- [ ] **新增函數: save_sop_context_to_session**
- [ ] **新增函數: get_sop_context_from_session**
- [ ] **新增函數: mark_sop_context_as_triggered**
- [ ] **新增函數: trigger_form_from_sop**
- [ ] **新增函數: trigger_api_from_sop**
- [ ] **新增函數: save_form_completion_callback**
- [ ] **新增函數: get_form_completion_callback**

- [ ] **form_manager.py - complete_form**
  - 修改：檢查並執行 API callback

- [ ] **billing_api.py**
  - 實作：submit_maintenance_request 函數

- [ ] **vendor_sop_retriever.py - SQL 查詢**
  - 新增：查詢 next_action 等新欄位

### 資料庫

- [ ] **執行 Migration**: add_sop_next_action_fields.sql
- [ ] **（可選）執行 Migration**: insert_maintenance_sop_examples.sql
- [ ] **（可選）新增表**: sop_followup_contexts

---

**文檔版本**: 1.0
**最後更新**: 2026-01-22
