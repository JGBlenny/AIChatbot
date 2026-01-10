# 表單填寫功能整合計畫

## 📌 目標

在現有聊天系統上擴展**表單填寫對話**功能，避免建立全新路線，最大化利用現有架構。

---

## 🔍 現有架構盤查

### ✅ 可重用的組件

| 組件 | 位置 | 用途 |
|------|------|------|
| **session_id** | `VendorChatRequest.session_id` | 追蹤對話會話 |
| **user_id** | `VendorChatRequest.user_id` | 識別用戶 |
| **conversation_logs** | `database/init/03-create-rag-tables.sql` | 記錄對話歷史 |
| **意圖分類器** | `app_state.intent_classifier` | 偵測用戶意圖（可用於離題偵測） |
| **vendor_id** | `VendorChatRequest.vendor_id` | 業者識別（表單可按業者定義） |

### ❌ 需要新增的組件

1. **會話狀態表**（`form_sessions`）：追蹤表單填寫進度
2. **表單定義表**（`form_schemas`）：儲存表單結構
3. **表單提交表**（`form_submissions`）：儲存已完成的表單
4. **FormManager 服務**：管理表單生命週期
5. **離題偵測器**：判斷用戶是否離題

---

## 🏗️ 整合方案

### 方案 A：最小侵入式整合（推薦）

**核心思想**：在現有 `/api/v1/message` 端點上擴展，不新增獨立端點。

#### 1. 資料庫擴展

新增 3 張表（最小必要集合）：

```sql
-- 1. 表單定義表
CREATE TABLE form_schemas (
    id SERIAL PRIMARY KEY,
    form_id VARCHAR(100) UNIQUE NOT NULL,
    form_name VARCHAR(200) NOT NULL,
    trigger_intents JSONB,  -- 觸發意圖列表，例如：["租屋申請", "報修申請"]
    fields JSONB NOT NULL,  -- 欄位定義（JSON格式）
    vendor_id INTEGER REFERENCES vendors(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. 表單會話表（擴展現有 session_id 機制）
CREATE TABLE form_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,  -- 沿用現有 session_id
    user_id VARCHAR(100),
    vendor_id INTEGER,
    form_id VARCHAR(100) REFERENCES form_schemas(form_id),
    state VARCHAR(50) NOT NULL,  -- COLLECTING / DIGRESSION / COMPLETED / CANCELLED
    current_field_index INTEGER DEFAULT 0,
    collected_data JSONB,  -- 已收集的資料
    started_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW()
);

-- 3. 表單提交記錄表
CREATE TABLE form_submissions (
    id SERIAL PRIMARY KEY,
    form_session_id INTEGER REFERENCES form_sessions(id),
    user_id VARCHAR(100),
    vendor_id INTEGER,
    submitted_data JSONB NOT NULL,
    submitted_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. API 流程整合

**現有流程**：
```
POST /api/v1/message
  ↓
意圖分類 → SOP檢索 → 知識庫檢索 → LLM優化 → 返回答案
```

**整合後流程**：
```
POST /api/v1/message
  ↓
檢查是否有進行中的表單會話？
  ├─ 是 → 表單收集流程（FormManager.collect_field_data）
  │         ├─ 偵測離題？
  │         │   ├─ 是 → 處理離題 → 詢問是否繼續
  │         │   └─ 否 → 驗證資料 → 儲存 → 下一欄位
  │         └─ 完成？ → 儲存提交記錄 → 返回完成訊息
  │
  └─ 否 → 意圖分類
            ├─ 匹配表單觸發意圖？
            │   ├─ 是 → 創建表單會話 → 開始收集第一個欄位
            │   └─ 否 → [原有流程] SOP → 知識庫 → LLM
            └─ 返回答案
```

#### 3. 程式碼修改點

**檔案：`rag-orchestrator/routers/chat.py`**

```python
# 在 vendor_chat_message() 函數開頭增加表單檢查
@router.post("/message", response_model=VendorChatResponse)
async def vendor_chat_message(request: VendorChatRequest, req: Request):
    try:
        # ========== 新增：表單會話檢查 ==========
        form_manager = req.app.state.form_manager  # 新增到 app_state

        # 1. 檢查是否有進行中的表單會話
        if request.session_id:
            session_state = form_manager.get_session_state(request.session_id)

            if session_state and session_state['state'] in ['COLLECTING', 'DIGRESSION']:
                # 用戶正在填寫表單 → 走表單收集流程
                intent_result = intent_classifier.classify(request.message)

                result = await form_manager.collect_field_data(
                    user_message=request.message,
                    session_id=request.session_id,
                    intent_result=intent_result
                )

                # 將表單結果轉換為 VendorChatResponse 格式
                return convert_form_result_to_response(result, request)

        # ========== 原有流程 ==========
        # Step 1: 驗證業者
        resolver = get_vendor_param_resolver()
        vendor_info = _validate_vendor(request.vendor_id, resolver)

        # Step 2: 緩存檢查
        ...

        # Step 3: 意圖分類
        intent_result = intent_classifier.classify(request.message)

        # ========== 新增：表單觸發檢查 ==========
        # 檢查意圖是否匹配表單觸發條件
        if request.session_id:
            form_trigger_result = await form_manager.trigger_form_filling(
                intent_name=intent_result['intent_name'],
                session_id=request.session_id,
                user_id=request.user_id,
                vendor_id=request.vendor_id
            )

            if form_trigger_result.get('form_triggered'):
                # 表單已觸發 → 返回第一個欄位提示
                return convert_form_result_to_response(form_trigger_result, request)

        # ========== 原有流程繼續 ==========
        # Step 4: SOP 檢索
        ...
```

#### 4. 服務初始化

**檔案：`rag-orchestrator/app.py`**

```python
from services.form_manager import FormManager

# 在 lifespan 函數中初始化
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... 現有初始化 ...

    # 新增：表單管理器
    app.state.form_manager = FormManager()
    print("✅ 表單管理器已初始化")

    yield

    # 清理（如有需要）
```

---

### 方案 B：獨立端點（不推薦，但保留選項）

**新增獨立端點**：`POST /api/v1/forms/message`

```python
@router.post("/forms/message")
async def form_message(request: FormChatRequest, req: Request):
    """
    表單專用對話端點

    與一般聊天隔離，專注於表單填寫流程
    """
    form_manager = req.app.state.form_manager
    # ... 表單處理邏輯 ...
```

**缺點**：
- 需要前端判斷何時切換端點
- 增加維護複雜度
- 用戶體驗不連貫（表單填寫與一般對話割裂）

---

## 📊 對比分析

| 項目 | 方案 A（整合） | 方案 B（獨立） |
|------|--------------|--------------|
| **侵入性** | 低（在現有端點擴展） | 中（新增端點） |
| **維護成本** | 低（統一流程） | 中（雙軌維護） |
| **用戶體驗** | 好（無縫切換） | 中（需手動切換） |
| **測試複雜度** | 中（需測試整合邏輯） | 低（獨立測試） |
| **推薦度** | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## 🚀 實施步驟（方案 A）

### Phase 1：資料庫準備（1天）

- [ ] 創建 `migrations/create_form_tables.sql`
- [ ] 執行遷移腳本
- [ ] 插入測試表單定義（租屋申請表）

```sql
-- migrations/create_form_tables.sql
-- 完整 SQL 參考 FORM_FILLING_DIALOG_DESIGN.md
```

### Phase 2：核心服務開發（2-3天）

- [ ] 實作 `services/form_manager.py`（已完成草稿）
- [ ] 實作 `services/form_validator.py`（已完成草稿）
- [ ] 實作 `services/digression_detector.py`（已完成草稿）
- [ ] 編寫單元測試

### Phase 3：API 整合（1-2天）

- [ ] 修改 `routers/chat.py` 的 `vendor_chat_message()` 函數
- [ ] 新增 `convert_form_result_to_response()` 轉換函數
- [ ] 在 `app.py` 初始化 FormManager
- [ ] 整合測試（Postman / cURL）

### Phase 4：前端適配（1-2天）

- [ ] 前端檢測表單狀態（`response.form_triggered`）
- [ ] 顯示進度條（`response.progress`）
- [ ] 處理離題提示（`response.allow_resume`）
- [ ] 顯示完成訊息（`response.form_completed`）

### Phase 5：測試與優化（1-2天）

- [ ] 端到端測試（完整流程）
- [ ] 離題場景測試
- [ ] 驗證失敗測試
- [ ] 性能測試（會話狀態查詢）
- [ ] 清理過期會話（定時任務）

---

## 📝 轉換函數範例

```python
def convert_form_result_to_response(
    form_result: Dict,
    request: VendorChatRequest
) -> VendorChatResponse:
    """
    將表單處理結果轉換為標準 VendorChatResponse

    Args:
        form_result: FormManager 返回的結果
        request: 原始請求

    Returns:
        VendorChatResponse 實例
    """
    return VendorChatResponse(
        answer=form_result['answer'],
        intent_name=form_result.get('intent_name', '表單填寫'),
        intent_type='form_filling',
        confidence=1.0,  # 表單流程固定高置信度
        sources=None,
        source_count=0,
        vendor_id=request.vendor_id,
        mode=request.mode,
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat(),
        # 表單專屬欄位
        form_triggered=form_result.get('form_triggered', False),
        form_completed=form_result.get('form_completed', False),
        form_cancelled=form_result.get('form_cancelled', False),
        form_id=form_result.get('form_id'),
        current_field=form_result.get('current_field'),
        progress=form_result.get('progress'),
        allow_resume=form_result.get('allow_resume', False)
    )
```

**注意**：需要擴展 `VendorChatResponse` 模型，增加表單相關欄位。

---

## 🎯 關鍵決策點

### Q1：表單填寫時，離題處理是否需要完整的 RAG 流程？

**建議**：需要，但簡化版。

- 如果用戶問問題（digression_type="question"），應該調用原有的 RAG 流程回答問題
- 回答後，詢問是否繼續填寫表單
- 實作方式：在 `_handle_digression()` 中調用 `_build_rag_response()`

```python
async def _handle_digression(
    self,
    user_message: str,
    session_state: Dict,
    form_schema: Dict,
    digression_type: str,
    req: Request  # 新增：用於訪問 RAG 引擎
) -> Dict:
    if digression_type == "question":
        # 調用原有的 RAG 流程回答問題
        from routers.chat import _build_rag_response
        rag_answer = await _build_rag_response(...)

        return {
            "answer": f"{rag_answer['answer']}\n\n──────\n💡 您的表單還未完成，需要繼續填寫嗎？",
            "state": FormState.DIGRESSION
        }
```

### Q2：session_id 如何生成？

**建議**：前端生成 UUID，後端驗證。

```javascript
// 前端生成
const sessionId = `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
```

### Q3：表單超時如何處理？

**建議**：定時清理過期會話（30分鐘無活動）。

```python
# 在 app.py 中新增定時任務（使用 APScheduler 或 Celery）
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=10)
def cleanup_expired_sessions():
    form_manager.cleanup_expired_sessions(timeout_minutes=30)

scheduler.start()
```

---

## 🔒 安全性考量

1. **敏感資料加密**
   - `collected_data` 中的身分證、電話等應加密儲存
   - 使用 `pgcrypto` 擴展或應用層加密

2. **會話劫持防護**
   - `session_id` 應包含用戶 IP 或設備指紋驗證
   - 定期輪換 session_id

3. **資料存取控制**
   - 只允許表單創建者訪問自己的會話
   - 業者只能訪問自己的表單定義

---

## 📈 監控與日誌

### 關鍵指標

```python
# 在 FormManager 中增加指標記錄
import time

class FormManager:
    def __init__(self):
        self.metrics = {
            'forms_triggered': 0,
            'forms_completed': 0,
            'forms_cancelled': 0,
            'digression_count': 0,
            'average_completion_time': 0
        }

    async def collect_field_data(self, ...):
        start_time = time.time()

        # ... 處理邏輯 ...

        # 記錄完成時間
        if result.get('form_completed'):
            self.metrics['forms_completed'] += 1
            elapsed = time.time() - start_time
            self.metrics['average_completion_time'] = \
                (self.metrics['average_completion_time'] + elapsed) / 2
```

### 日誌範例

```python
# 在關鍵步驟增加結構化日誌
import logging

logger = logging.getLogger(__name__)

logger.info(
    "表單觸發",
    extra={
        'form_id': form_id,
        'session_id': session_id,
        'user_id': user_id,
        'vendor_id': vendor_id
    }
)
```

---

## 🎓 總結

**推薦方案**：方案 A（最小侵入式整合）

**理由**：
1. ✅ 利用現有 `session_id` 機制，無需重新設計
2. ✅ 用戶體驗連貫（表單填寫與一般對話無縫切換）
3. ✅ 維護成本低（統一端點，統一流程）
4. ✅ 離題處理可複用現有 RAG 流程

**關鍵整合點**：
- 在 `/api/v1/message` 端點開頭增加表單會話檢查
- 意圖分類後增加表單觸發檢查
- 離題處理時調用原有 RAG 流程

**預估時間**：7-10 天（含測試和前端適配）
