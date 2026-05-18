# 知識庫表單觸發模式實現文檔

**版本**: 1.0
**日期**: 2026-02-03
**狀態**: ✅ 已完成
**作者**: AI Chatbot Development Team

---

## 📋 目錄

1. [概述](#概述)
2. [背景與問題](#背景與問題)
3. [系統架構](#系統架構)
4. [觸發模式說明](#觸發模式說明)
5. [實現細節](#實現細節)
6. [資料庫設計](#資料庫設計)
7. [測試案例](#測試案例)
8. [最佳實踐](#最佳實踐)
9. [故障排除](#故障排除)

---

## 概述

### 功能目標

實現知識庫與 SOP 系統的表單觸發模式統一，支援以下三種觸發模式：

- ✅ **Manual（排查型）**：顯示內容 → 等待用戶關鍵詞確認 → 觸發表單
- ✅ **Immediate（行動型）**：顯示內容 → 立即詢問確認 → 等待關鍵詞 → 觸發表單
- ✅ **Auto（自動型）**：顯示內容 → 自動觸發表單

### 核心特性

1. **統一架構**：知識庫使用 SOP 的觸發處理邏輯
2. **內存備援**：Redis 未啟用時使用內存存儲 context
3. **避免重複**：表單完成後不重複顯示知識內容
4. **關鍵詞配置**：預設觸發關鍵詞為 `['是', '要']`
5. **測試友好**：提供完整的測試知識庫項目

---

## 背景與問題

### 業務需求

在包租代管業務中，知識庫項目需要支援與 SOP 相同的表單觸發模式：

**場景 1：排查型（Manual）**
```
用戶：「我想租房子」
AI：（顯示租房流程說明）

    💡 需要安排處理嗎？
    • 回覆「是」或「要」→ 立即填寫表單
    • 回覆「不用」→ 繼續為您解答其他問題

用戶：「是」
AI：（觸發租房申請表單）
```

**場景 2：行動型（Immediate）**
```
用戶：「我要退租」
AI：（顯示退租流程說明）
    是否需要協助您填寫退租申請表？

用戶：「要」
AI：（觸發退租表單）
```

**場景 3：自動型（Auto）**
```
用戶：「我想租房子」
AI：（顯示租房流程說明）
    （自動觸發租房申請表單，無需確認）
```

### 遇到的問題

#### 問題 1：知識庫不支援 Manual/Immediate 模式

**現象**：
```python
# routers/chat.py:1540-1545
elif trigger_mode in ['manual', 'immediate']:
    print(f"   ⚠️ trigger_mode={trigger_mode} 暫不支援，降級為 direct_answer")
    return _build_simple_answer(...)
```

**影響**：
- 知識庫只支援 auto 模式（直接觸發）
- Manual 和 Immediate 模式被降級為純知識問答
- 無法實現「詢問確認 → 觸發表單」的流程

#### 問題 2：缺少內存備援機制

**現象**：
```
⚠️ Redis 未啟用，跳過 SOP Context 存儲
```

**影響**：
- 用戶第一次問「我想租房子」→ 顯示內容 + 提示
- 用戶回覆「是」→ 系統無法識別這是確認，當作新問題處理

#### 問題 3：SQL 查詢缺少欄位

**現象**：
context 中的 trigger_keywords 為空陣列

**原因**：
`vendor_knowledge_retriever.py` 的 SQL 查詢未選取 `trigger_keywords` 和 `trigger_mode` 欄位

#### 問題 4：表單完成後重複顯示知識內容

**現象**：
```
用戶：「是」
AI：✅ 表單填寫完成！

（又顯示一次租房流程說明）
```

**原因**：
表單設定 `on_complete_action='show_knowledge'`，但用戶在觸發表單時已經看過知識內容了。

---

## 系統架構

### 整體架構

```
用戶問題
    ↓
檢索知識庫
    ↓
檢查 action_type 和 trigger_mode
    ↓
    ├─ action_type = 'direct_answer' ────→ 直接返回答案
    │
    ├─ action_type = 'form_fill'
    │       ↓
    │   trigger_mode 是什麼？
    │       ├─ NULL ──────→ 直接觸發表單（舊行為，保持兼容）
    │       ├─ 'auto' ────→ 直接觸發表單
    │       ├─ 'manual' ──→ 使用 SOP Orchestrator 處理
    │       └─ 'immediate' → 使用 SOP Orchestrator 處理
    │
    └─ action_type = 'api_call' ──────→ 調用 API
```

### SOP Orchestrator 處理流程

```
SOP Orchestrator
    ↓
檢查是否有待處理 context
    ├─ 有 context
    │   ↓
    │   檢查用戶訊息是否匹配關鍵詞
    │       ├─ 匹配 → 刪除 context，返回 triggered
    │       └─ 不匹配 → 保持等待，返回提示
    │
    └─ 無 context
        ↓
        首次觸發
            ├─ auto 模式 → 返回 execute_immediately
            ├─ manual 模式 → 儲存 context，返回等待回應（帶關鍵詞提示）
            └─ immediate 模式 → 儲存 context，返回等待回應（帶詢問提示）
```

### Context 存儲機制

```
Context 存儲
    ├─ Redis 啟用
    │   └─ 使用 Redis 存儲（TTL: 600 秒）
    │
    └─ Redis 未啟用
        └─ 使用內存字典存儲（TTL: 600 秒）
            └─ 結構：{session_id: {data: {...}, expires_at: timestamp}}
```

---

## 觸發模式說明

### 模式對比表

| 模式 | trigger_mode | 行為 | 適用場景 | 預設關鍵詞 |
|-----|-------------|------|---------|-----------|
| **直接回答** | NULL | 純知識問答，不觸發表單 | 一般 FAQ | - |
| **自動型** | `auto` | 顯示內容後自動觸發表單 | 明確的表單需求 | - |
| **排查型** | `manual` | 顯示內容 → 等待關鍵詞 → 觸發表單 | 需要確認的操作 | `['是', '要']` |
| **行動型** | `immediate` | 顯示內容 → 立即詢問 → 等待關鍵詞 → 觸發表單 | 緊急或重要操作 | `['是', '要']` |

### Manual 模式詳解

**配置範例**：
```json
{
  "question_summary": "我想租房子",
  "answer": "📋 **租房申請流程說明**\n\n...",
  "action_type": "form_fill",
  "trigger_mode": "manual",
  "form_id": "rental_inquiry",
  "trigger_keywords": ["是", "要", "好"]
}
```

**對話流程**：
```
用戶：「我想租房子」
↓
系統：檢索知識庫 → ID 1264 (trigger_mode=manual)
↓
系統：將知識項目轉為 SOP 格式，調用 SOPOrchestrator.handle_knowledge_trigger()
↓
系統：首次觸發 → 儲存 context（session_id, knowledge_id, trigger_keywords）
↓
返回：知識內容 + 關鍵詞提示
    「📋 租房申請流程說明...

     💡 需要安排處理嗎？
     • 回覆「是」或「要」→ 立即填寫表單
     • 回覆「不用」→ 繼續為您解答其他問題」

用戶：「是」
↓
系統：檢測到 context → 匹配關鍵詞成功
↓
系統：刪除 context，返回 triggered
↓
系統：觸發表單 → form_manager.trigger_form_by_knowledge()
```

### Immediate 模式詳解

**配置範例**：
```json
{
  "question_summary": "我要退租",
  "answer": "📋 **退租申請流程**\n\n...",
  "action_type": "form_fill",
  "trigger_mode": "immediate",
  "form_id": "rental_inquiry",
  "trigger_keywords": ["是", "要"],
  "immediate_prompt": "是否需要協助您填寫退租申請表？"
}
```

**對話流程**：
```
用戶：「我要退租」
↓
系統：檢索知識庫 → ID 1269 (trigger_mode=immediate)
↓
系統：將知識項目轉為 SOP 格式，調用 SOPOrchestrator.handle_knowledge_trigger()
↓
系統：首次觸發 → 儲存 context
↓
返回：知識內容 + immediate_prompt
    「📋 退租申請流程...

     是否需要協助您填寫退租申請表？」

用戶：「要」
↓
系統：檢測到 context → 匹配關鍵詞成功
↓
系統：刪除 context，返回 triggered
↓
系統：觸發表單
```

---

## 實現細節

### 1. 路由層處理（chat.py）

**位置**：`/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/chat.py:1540-1590`

**變更前**：
```python
elif trigger_mode in ['manual', 'immediate']:
    print(f"   ⚠️ trigger_mode={trigger_mode} 暫不支援，降級為 direct_answer")
    return _build_simple_answer(...)
```

**變更後**：
```python
elif trigger_mode in ['manual', 'immediate']:
    # 排查型/行動型：使用 SOP Orchestrator 處理關鍵詞匹配
    print(f"   ✅ 使用 SOP Orchestrator 處理 trigger_mode={trigger_mode}")

    # 將知識庫項目轉換為 SOP 格式
    knowledge_as_sop = {
        'id': best_knowledge['id'],
        'item_name': best_knowledge.get('question_summary', ''),
        'content': best_knowledge.get('answer', ''),
        'trigger_mode': trigger_mode,
        'next_action': 'form_fill',
        'next_form_id': form_id,
        'next_api_config': None,
        'trigger_keywords': best_knowledge.get('trigger_keywords', []),
        'immediate_prompt': best_knowledge.get('immediate_prompt', ''),
        'followup_prompt': None
    }

    # 使用 SOP Orchestrator 處理
    sop_orchestrator = req.app.state.sop_orchestrator
    result = await sop_orchestrator.handle_knowledge_trigger(
        knowledge_item=knowledge_as_sop,
        user_message=request.message,
        session_id=request.session_id,
        user_id=request.user_id,
        vendor_id=request.vendor_id
    )

    # 根據結果返回
    if result.get('action') == 'triggered':
        # 觸發表單
        form_manager = req.app.state.form_manager
        form_result = await form_manager.trigger_form_by_knowledge(
            knowledge_id=best_knowledge['id'],
            form_id=form_id,
            session_id=request.session_id,
            user_id=request.user_id,
            vendor_id=request.vendor_id,
            trigger_question=request.message
        )
        return _convert_form_result_to_response(form_result, request)
    else:
        # 返回等待狀態的回應
        return VendorChatResponse(
            answer=result.get('response', best_knowledge.get('answer', '')),
            vendor_id=request.vendor_id,
            mode=request.mode,
            session_id=request.session_id,
            timestamp=datetime.utcnow().isoformat(),
            source_count=0
        )
```

### 2. SOP Orchestrator 新增方法

**位置**：`/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/sop_orchestrator.py:567-636`

**新增方法**：
```python
async def handle_knowledge_trigger(
    self,
    knowledge_item: Dict,
    user_message: str,
    session_id: str,
    user_id: str,
    vendor_id: int
) -> Dict:
    """
    處理知識庫項目的觸發（支援 manual 和 immediate 模式）

    Args:
        knowledge_item: 知識庫項目（已轉換為 SOP 格式）
        user_message: 用戶訊息
        session_id: 會話 ID
        user_id: 用戶 ID
        vendor_id: 業者 ID

    Returns:
        處理結果 {'action': 'triggered'/'wait_for_confirmation', 'response': str}
    """
    print(f"🎯 [Knowledge Trigger] 處理知識庫觸發 ID={knowledge_item.get('id')}, mode={knowledge_item.get('trigger_mode')}")

    # 檢查是否有待處理的 context
    existing_context = self.trigger_handler.get_context(session_id)

    if existing_context:
        # 有待處理的 context，檢查關鍵詞匹配
        print(f"   📖 檢測到待處理 context: knowledge_id={existing_context.get('sop_id')}")

        trigger_keywords = existing_context.get('trigger_keywords', [])
        matched, matched_keyword = self.keyword_matcher.match(user_message, trigger_keywords)

        if matched:
            print(f"   ✅ 關鍵詞匹配成功: {matched_keyword}")
            # 刪除 context
            self.trigger_handler.delete_context(session_id)
            return {
                'action': 'triggered',
                'response': '',
                'matched_keyword': matched_keyword
            }
        else:
            print(f"   ❌ 關鍵詞未匹配，保持等待")
            return {
                'action': 'wait_for_keywords',
                'response': '請告訴我您是否需要協助？'
            }
    else:
        # 沒有 context，首次觸發
        result = self.trigger_handler.handle(
            sop_item=knowledge_item,
            user_message=user_message,
            session_id=session_id,
            user_id=user_id,
            vendor_id=vendor_id
        )

        if result.get('action') == 'execute_immediately':
            # auto 模式：直接觸發
            return {
                'action': 'triggered',
                'response': result.get('response', '')
            }
        else:
            # manual/immediate 模式：返回等待回應
            return {
                'action': 'wait_for_confirmation',
                'response': result.get('response', '')
            }
```

### 3. 內存備援機制

**位置**：`/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/sop_trigger_handler.py`

**初始化內存存儲**（Line 76）：
```python
def __init__(self, redis_client = None):
    self.redis_client = redis_client or self._get_redis_client()

    # 內存存儲（當 Redis 未啟用時使用）
    self._memory_store = {}

    # 配置參數
    self.context_ttl = {
        TriggerMode.MANUAL: int(os.getenv("SOP_MANUAL_TTL", "600")),
        TriggerMode.IMMEDIATE: int(os.getenv("SOP_IMMEDIATE_TTL", "600")),
    }
```

**儲存 Context**（Line 424-431）：
```python
def _save_context(self, context_key: str, context_data: Dict, ttl: int) -> bool:
    """儲存 SOP 觸發 context（支援 Redis 或內存）"""

    # 如果 Redis 被禁用，使用內存存儲
    if self.redis_client is None:
        self._memory_store[context_key] = {
            'data': context_data,
            'expires_at': datetime.now().timestamp() + ttl
        }
        print(f"   💾 SOP Context 已儲存到內存: {context_key} (TTL: {ttl}s)")
        return True

    # ... Redis 存儲邏輯 ...
```

**讀取 Context**（Line 460-477）：
```python
def get_context(self, session_id: str) -> Optional[Dict]:
    """取得 SOP 觸發 context（支援 Redis 或內存）"""
    context_key = f"sop_trigger:{session_id}"

    # 如果 Redis 被禁用，使用內存存儲
    if self.redis_client is None:
        stored = self._memory_store.get(context_key)
        if stored:
            # 檢查是否過期
            if datetime.now().timestamp() > stored['expires_at']:
                # 已過期，刪除
                del self._memory_store[context_key]
                print(f"   ⚠️  SOP Context 已過期: {context_key}")
                return None

            context = stored['data']
            print(f"   📖 讀取內存 SOP Context: {context_key}")
            print(f"      狀態: {context.get('state')}")
            return context
        else:
            print(f"   ⚠️  無內存 SOP Context: {context_key}")
            return None

    # ... Redis 讀取邏輯 ...
```

**刪除 Context**（Line 509-513）：
```python
def delete_context(self, session_id: str) -> bool:
    """刪除 SOP 觸發 context（支援 Redis 或內存）"""
    context_key = f"sop_trigger:{session_id}"

    # 如果 Redis 被禁用，從內存刪除
    if self.redis_client is None:
        if context_key in self._memory_store:
            del self._memory_store[context_key]
            print(f"   🗑️  內存 SOP Context 已刪除: {context_key}")
        return True

    # ... Redis 刪除邏輯 ...
```

### 4. SQL 查詢欄位補充

**位置**：`/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/vendor_knowledge_retriever.py`

**第一處**（Line 115-117）：
```sql
kb.trigger_mode,
kb.trigger_keywords,
kb.immediate_prompt,
```

**第二處**（Line 382-384）：
```sql
kb.trigger_mode,
kb.trigger_keywords,
kb.immediate_prompt,
```

### 5. 避免重複顯示知識內容

**位置**：`/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/form_manager.py`

**添加觸發來源檢查**（Line 801-808）：
```python
# 5. 格式化完成訊息
# ⚠️ 如果表單由知識庫觸發，用戶已看過知識內容，不再重複顯示
triggered_by_knowledge = session_state.get('knowledge_id') is not None
completion_message = await self._format_completion_message(
    on_complete_action=on_complete_action,
    knowledge_answer=knowledge_answer,
    api_result=api_result,
    triggered_by_knowledge=triggered_by_knowledge
)
```

**修改格式化邏輯**（Line 853-873）：
```python
async def _format_completion_message(
    self,
    on_complete_action: str,
    knowledge_answer: Optional[str],
    api_result: Optional[Dict],
    triggered_by_knowledge: bool = False
) -> str:
    """格式化表單完成訊息

    Args:
        triggered_by_knowledge: 表單是否由知識庫觸發（用戶已看過知識內容）
    """
    # 情況 1: 只顯示知識答案
    if on_complete_action == 'show_knowledge':
        # ⚠️ 如果表單由知識庫觸發，用戶已看過知識內容，不再重複顯示
        if triggered_by_knowledge:
            return "✅ **表單填寫完成！**\n\n感謝您完成表單！我們會儘快與您聯繫。"
        elif knowledge_answer:
            return f"✅ **表單填寫完成！**\n\n{knowledge_answer}"
        else:
            return "✅ **表單填寫完成！**\n\n感謝您完成表單！我們會儘快處理您的資料。"
```

### 6. 預設關鍵詞配置

**Manual 模式預設**（Line 216）：
```python
trigger_keywords = sop_item.get('trigger_keywords') or ['是', '要']
```

**Immediate 模式預設**（Line 270）：
```python
trigger_keywords = sop_item.get('trigger_keywords', ['是', '要'])
```

---

## 資料庫設計

### knowledge_base 表結構

```sql
-- 觸發模式欄位
trigger_mode VARCHAR(20) CHECK (
    trigger_mode IS NULL OR
    trigger_mode IN ('manual', 'immediate', 'auto')
);

-- 觸發關鍵詞（陣列）
trigger_keywords TEXT[];

-- 行動型提示訊息
immediate_prompt TEXT;

-- 行為類型
action_type VARCHAR(50) DEFAULT 'direct_answer' CHECK (
    action_type IN ('direct_answer', 'form_fill', 'api_call')
);

-- 表單 ID（當 action_type='form_fill' 時必填）
form_id VARCHAR(100);
```

### 約束說明

#### trigger_mode 約束
```sql
CHECK (
    trigger_mode IS NULL OR
    trigger_mode IN ('manual', 'immediate', 'auto')
)
```

**注意**：沒有 'none' 選項。純知識問答使用 `trigger_mode = NULL`。

#### action_type 約束
```sql
CHECK (
    action_type IN ('direct_answer', 'form_fill', 'api_call')
)
```

### 配置範例

**範例 1：Manual 模式**
```sql
INSERT INTO knowledge_base (
    question_summary,
    answer,
    vendor_id,
    scope,
    priority,
    trigger_mode,
    action_type,
    form_id,
    trigger_keywords,
    business_types,
    created_at,
    updated_at
) VALUES (
    '我想租房子',
    '📋 **租房申請流程說明**...',
    1,
    'customized',
    500,
    'manual',
    'form_fill',
    'rental_inquiry',
    ARRAY['是', '要'],
    ARRAY['property_management'],
    NOW(),
    NOW()
);
```

**範例 2：Immediate 模式**
```sql
INSERT INTO knowledge_base (
    question_summary,
    answer,
    vendor_id,
    scope,
    priority,
    trigger_mode,
    action_type,
    form_id,
    trigger_keywords,
    immediate_prompt,
    business_types,
    created_at,
    updated_at
) VALUES (
    '我要退租',
    '📋 **退租申請流程**...',
    2,
    'customized',
    500,
    'immediate',
    'form_fill',
    'rental_inquiry',
    ARRAY['是', '要'],
    '是否需要協助您填寫退租申請表？',
    ARRAY['property_management'],
    NOW(),
    NOW()
);
```

**範例 3：Direct Answer（純知識）**
```sql
INSERT INTO knowledge_base (
    question_summary,
    answer,
    vendor_id,
    scope,
    priority,
    trigger_mode,
    action_type,
    form_id,
    trigger_keywords,
    business_types,
    created_at,
    updated_at
) VALUES (
    '合約問題',
    '📋 **租賃合約說明**...',
    2,
    'customized',
    400,
    NULL,  -- NULL 表示純知識問答
    'direct_answer',
    NULL,
    NULL,
    ARRAY['property_management'],
    NOW(),
    NOW()
);
```

---

## 測試案例

### 測試知識庫項目

系統已建立以下測試知識（Vendor 2 / VENDOR_B / 信義包租代管）：

| ID | 問題摘要 | 觸發模式 | 行為類型 | 表單 ID | 關鍵詞 |
|----|---------|---------|---------|---------|--------|
| 1264 | 我想租房子 | manual | form_fill | rental_inquiry | ['是', '要'] |
| 1269 | 我要退租 | immediate | form_fill | rental_inquiry | ['是', '要'] |
| 1294 | 我想報修 | manual | form_fill | rental_inquiry | ['是', '要', '好'] |
| 1295 | 合約問題 | NULL | direct_answer | NULL | NULL |

### 測試場景

#### 測試 1：Manual 模式

**測試知識**：ID 1264「我想租房子」

**測試步驟**：
```
1. 訪問 http://localhost:8087/#/vendor-b/chat
2. 輸入：「我想租房子」
   預期：顯示租房流程 + 關鍵詞提示

3. 輸入：「是」
   預期：觸發表單

4. 完成表單
   預期：只顯示「✅ 表單填寫完成！」，不重複顯示租房流程
```

**驗證點**：
- [ ] 首次問題返回知識內容
- [ ] 顯示關鍵詞提示：「• 回覆「是」或「要」→ 立即填寫表單」
- [ ] 回覆「是」後成功觸發表單
- [ ] 表單完成後不重複顯示知識內容
- [ ] 回覆「不用」後繼續對話（不觸發表單）

#### 測試 2：Immediate 模式

**測試知識**：ID 1269「我要退租」

**測試步驟**：
```
1. 訪問 http://localhost:8087/#/vendor-b/chat
2. 輸入：「我要退租」
   預期：顯示退租流程 + immediate_prompt

3. 輸入：「要」
   預期：觸發表單

4. 完成表單
   預期：只顯示「✅ 表單填寫完成！」
```

**驗證點**：
- [ ] 首次問題返回知識內容
- [ ] 顯示 immediate_prompt：「是否需要協助您填寫退租申請表？」
- [ ] 回覆「要」後成功觸發表單
- [ ] 表單完成後不重複顯示知識內容

#### 測試 3：Direct Answer

**測試知識**：ID 1295「合約問題」

**測試步驟**：
```
1. 輸入：「合約問題」
   預期：直接顯示合約說明，不觸發表單
```

**驗證點**：
- [ ] 返回完整合約說明
- [ ] 不出現任何表單相關提示
- [ ] 對話可以繼續進行

#### 測試 4：Context 過期

**測試步驟**：
```
1. 輸入：「我想租房子」
   預期：顯示內容 + 提示

2. 等待 10 分鐘以上（TTL: 600 秒）

3. 輸入：「是」
   預期：系統當作新問題處理（context 已過期）
```

**驗證點**：
- [ ] Context TTL 正確運作
- [ ] 過期後不會觸發表單
- [ ] 日誌顯示「SOP Context 已過期」

#### 測試 5：內存備援機制

**前置條件**：確認 `CACHE_ENABLED=false`

**測試步驟**：
```
1. 輸入：「我想租房子」
   檢查日誌：應顯示「💾 SOP Context 已儲存到內存」

2. 輸入：「是」
   檢查日誌：應顯示「📖 讀取內存 SOP Context」
   預期：成功觸發表單
```

**驗證點**：
- [ ] Redis 未啟用時使用內存存儲
- [ ] 內存存儲可以正確讀取和刪除
- [ ] TTL 機制正常運作

---

## 最佳實踐

### 1. 選擇正確的觸發模式

| 場景 | 推薦模式 | 理由 |
|-----|---------|------|
| 一般 FAQ | NULL (direct_answer) | 純資訊查詢，無需表單 |
| 明確的表單需求 | auto | 用戶意圖明確，直接觸發 |
| 需要確認的操作 | manual | 給用戶選擇權 |
| 緊急或重要操作 | immediate | 明確詢問，減少誤觸發 |

### 2. 關鍵詞配置建議

**推薦關鍵詞**：
- 肯定：`['是', '要', '好', '需要', '可以']`
- 否定：`['不用', '不要', '不需要', '取消']`（系統自動識別，無需配置）

**避免使用**：
- 太短的詞（如「好」單獨使用）
- 歧義詞（如「對」、「嗯」）

### 3. immediate_prompt 撰寫建議

**好的範例**：
```
是否需要協助您填寫退租申請表？
```

**不好的範例**：
```
要不要填表？  // 太隨便
您是否希望系統為您啟動退租申請表單填寫流程？  // 太冗長
```

### 4. 知識內容撰寫

**結構化內容**：
```markdown
📋 **標題**

1. 第一點說明
2. 第二點說明
3. 第三點說明

注意事項：
• 注意事項 1
• 注意事項 2
```

**避免**：
- 過長的段落
- 缺少結構
- 沒有明確的行動指引

### 5. 測試檢查清單

在部署前確認：
- [ ] 所有 trigger_mode 都有對應的測試案例
- [ ] 關鍵詞匹配正確
- [ ] Context 存儲和讀取正常
- [ ] 表單完成後不重複顯示內容
- [ ] 日誌記錄完整

---

## 故障排除

### 問題 1：關鍵詞無法匹配

**現象**：
```
用戶：「是」
系統：（當作新問題處理）
```

**可能原因**：
1. Context 未正確存儲
2. Context 已過期（超過 TTL）
3. session_id 不一致

**排查步驟**：
```bash
# 1. 檢查日誌
docker-compose logs rag-orchestrator | grep "SOP Context"

# 2. 檢查 Redis
docker-compose exec redis redis-cli
> keys sop_trigger:*

# 3. 檢查內存存儲（如果 Redis 未啟用）
# 日誌應顯示：「💾 SOP Context 已儲存到內存」
```

**解決方案**：
```python
# 確認 session_id 一致
# 確認 TTL 未過期（預設 600 秒）
# 確認內存存儲機制運作正常
```

### 問題 2：表單完成後重複顯示知識內容

**現象**：
```
✅ 表單填寫完成！

📋 租房申請流程說明...  // 重複了
```

**原因**：
表單的 `on_complete_action='show_knowledge'` 且未檢查 `triggered_by_knowledge`

**解決方案**：
```python
# form_manager.py
triggered_by_knowledge = session_state.get('knowledge_id') is not None
if triggered_by_knowledge:
    return "✅ 表單填寫完成！"
```

### 問題 3：知識庫查詢缺少欄位

**現象**：
context 中的 trigger_keywords 為空

**原因**：
SQL 查詢未選取 `trigger_keywords`, `trigger_mode`, `immediate_prompt` 欄位

**解決方案**：
```python
# vendor_knowledge_retriever.py
# 確認 SQL 包含以下欄位：
"""
kb.trigger_mode,
kb.trigger_keywords,
kb.immediate_prompt,
"""
```

### 問題 4：Redis 未啟用導致 Context 丟失

**現象**：
```
⚠️ Redis 未啟用，跳過 SOP Context 存儲
```

**解決方案**：
已實現內存備援機制，無需修復。確認日誌顯示：
```
💾 SOP Context 已儲存到內存
```

### 問題 5：Constraint 違反錯誤

**現象**：
```sql
ERROR: new row for relation "knowledge_base" violates check constraint "check_kb_trigger_mode"
```

**原因**：
使用了不允許的 trigger_mode 值（如 'none'）

**解決方案**：
```sql
-- 正確的值：
trigger_mode = NULL        -- 純知識問答
trigger_mode = 'manual'    -- 排查型
trigger_mode = 'immediate' -- 行動型
trigger_mode = 'auto'      -- 自動型

-- 錯誤的值：
trigger_mode = 'none'      -- ❌ 不允許
```

---

## 相關文檔

- [SOP 系統完整指南](../guides/features/SOP_GUIDE.md)
- [知識庫動作系統設計](../design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
- [表單管理系統](./FORM_MANAGEMENT_SYSTEM.md)
- [SOP 觸發模式 UI 更新](sop/implementation/SOP_TRIGGER_MODE_UI_UPDATE_2026-02-03.md)

---

## 變更歷史

| 日期 | 版本 | 說明 |
|------|------|------|
| 2026-02-03 | 1.0 | 初始版本，實現知識庫表單觸發模式 |

---

**文檔維護**: AI Chatbot Development Team
**最後審查**: 2026-02-03
