# 表單填寫功能 - 系統衝突分析與整合方案

> 深度盤查現有系統架構，識別重疊、衝突和整合點

---

## 📊 執行摘要

### ✅ 可直接利用的組件
- `session_id` 欄位（無業務邏輯，可直接作為表單會話 ID）
- `conversation_logs` 表（僅用於歷史記錄，與表單會話互不干擾）
- 意圖分類器（可用於表單觸發和離題偵測）
- 資料庫命名空間（無 `form_*` 表，可安全創建）

### ⚠️ 需要處理的衝突
1. **Cache Service（重大衝突）**：緩存機制會繞過表單狀態檢查
2. **流程插入點**：需在特定位置插入表單邏輯
3. **Response 模型擴展**：需增加表單相關欄位

### 🔧 需要修改的文件
- `routers/chat.py`：主要整合點（~20 行新增代碼）
- `app.py`：初始化 FormManager（~5 行）
- Database：新增 3 張表

---

## 🔍 詳細衝突分析

### 1. session_id 使用分析

#### 現狀盤查

**檔案**：`routers/chat.py`

```python
class VendorChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="會話 ID（用於追蹤）")

class VendorChatResponse(BaseModel):
    session_id: Optional[str] = None
```

**實際使用**：
- ✅ 在 Request 中接收
- ✅ 在 Response 中返回
- ❌ **沒有任何讀取或查詢邏輯**
- ❌ 沒有資料庫表關聯

**搜尋結果驗證**：
```bash
grep -r "session_id" rag-orchestrator/routers/*.py | grep -v "request.session_id\|response.session_id"
# 結果：沒有任何業務邏輯使用 session_id
```

#### 結論

**✅ 完全可用，無衝突**

- session_id 目前只是"透傳"欄位
- 可以直接利用作為表單會話的唯一標識
- 不需要重新設計或更名

---

### 2. conversation_logs 表分析

#### 現狀盤查

**檔案**：`database/init/03-create-rag-tables.sql`

```sql
CREATE TABLE IF NOT EXISTS conversation_logs (
    id SERIAL PRIMARY KEY,
    conversation_id UUID DEFAULT gen_random_uuid(),
    user_id VARCHAR(100),
    question TEXT NOT NULL,
    intent_type VARCHAR(50),
    -- ... 其他欄位 ...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**實際使用**：
- 查詢歷史記錄（`GET /conversations`）
- 統計分析（`GET /health` 中的意圖分布、平均信心度）
- 提交反饋（`POST /conversations/{id}/feedback`）
- ❌ **不用於狀態管理或會話追蹤**

#### 結論

**✅ 無衝突**

- `conversation_logs` 用於歷史記錄（read-only 查詢）
- `form_sessions` 用於狀態管理（active tracking）
- 兩者職責完全分離，互不干擾

**建議**：
表單完成後，**可選擇性**記錄到 `conversation_logs` 以便統計分析。

---

### 3. Cache Service 衝突分析（🚨 重大衝突）

#### 現狀盤查

**檔案**：`services/cache_service.py`

```python
def _make_question_key(self, vendor_id: int, question: str, target_user: str, config_version: str):
    question_hash = hashlib.md5(question.lower().strip().encode()).hexdigest()[:16]
    return f"rag:question:{vendor_id}:{target_user}:{config_version}:{question_hash}"

def get_cached_answer(self, vendor_id: int, question: str, target_user: str, config_version: str):
    # 返回完整的 VendorChatResponse（如果緩存命中）
    cached = self.redis_client.get(key)
    if cached:
        return json.loads(cached)  # 直接返回
```

**檔案**：`routers/chat.py` 的 `vendor_chat_message()` 函數

```python
@router.post("/message", response_model=VendorChatResponse)
async def vendor_chat_message(request: VendorChatRequest, req: Request):
    # Step 1: 驗證業者
    resolver = get_vendor_param_resolver()
    vendor_info = _validate_vendor(request.vendor_id, resolver)

    # Step 2: 緩存檢查 ⚠️  在這裡！
    cache_service = req.app.state.cache_service
    cached_response = _check_cache(cache_service, request.vendor_id, request.message, request.target_user)
    if cached_response:
        return cached_response  # 🚨 直接返回，跳過所有後續邏輯

    # Step 3: 意圖分類
    # Step 4: SOP 檢索
    # Step 5: 知識庫檢索
    # ...
```

#### 衝突場景分析

**場景 1：表單填寫中的相同問題**

```
用戶開始填寫「租屋申請表」
  ↓
系統：「請問您的全名是？」
  ↓
用戶：「王小明」
  ↓
系統：「✅ 姓名已記錄！請提供您的聯絡電話」
  ↓
用戶：「請問租金多少？」  ← 離題問題
  ↓
[第一次] 意圖分類 → RAG 檢索 → 返回答案「租金範圍 15,000-25,000 元」
        ↓ 同時緩存這個答案
  ↓
詢問是否繼續填寫？
  ↓
用戶：「請問租金多少？」  ← 再次問相同問題
  ↓
[第二次] 緩存命中 🚨 直接返回「租金範圍 15,000-25,000 元」
        ↓ 跳過表單狀態檢查！
        ↓ 表單會話仍在 DIGRESSION 狀態，但系統沒有處理
```

**問題**：
- 緩存機制會繞過表單狀態檢查
- 用戶無法恢復表單填寫
- 表單會話變成"殭屍會話"（stuck in DIGRESSION）

**場景 2：不同用戶填寫表單時的相同欄位**

```
用戶 A（session_A）填寫表單
  ↓
系統：「請提供您的通訊地址」
  ↓
用戶 A：「台北市大安區復興南路一號」
  ↓
系統：✅ 記錄，繼續下一欄...

---

用戶 B（session_B）開始填寫相同表單
  ↓
系統：「請提供您的通訊地址」
  ↓
用戶 B：「台北市大安區復興南路一號」  ← 與用戶 A 相同
  ↓
🚨 緩存命中（因為 question 相同）？
```

實際上這個場景**問題較小**，因為：
- 緩存 key 包含 `question_hash`（問題的 MD5）
- 但**不包含** `session_id`
- 表單填寫的回應（如「✅ 已記錄」）會緩存，但不影響狀態管理

#### 衝突影響評估

| 影響範圍 | 嚴重程度 | 頻率 | 說明 |
|---------|---------|------|------|
| **表單離題後恢復** | 🔴 高 | 中 | 用戶離題問相同問題，緩存會繞過表單邏輯 |
| **表單欄位收集** | 🟡 低 | 低 | 用戶輸入相同資料（如地址），影響較小 |
| **表單觸發** | 🟢 無 | - | 表單觸發前會先檢查 session，不受影響 |

#### 解決方案

**方案 1：表單會話期間禁用緩存（推薦）**

```python
@router.post("/message", response_model=VendorChatResponse)
async def vendor_chat_message(request: VendorChatRequest, req: Request):
    # Step 1: 驗證業者
    resolver = get_vendor_param_resolver()
    vendor_info = _validate_vendor(request.vendor_id, resolver)

    # ========== 新增：表單會話檢查（在緩存檢查之前）==========
    form_manager = req.app.state.form_manager
    active_form_session = None

    if request.session_id:
        session_state = form_manager.get_session_state(request.session_id)
        if session_state and session_state['state'] in ['COLLECTING', 'DIGRESSION']:
            active_form_session = session_state

    # Step 2: 緩存檢查（表單會話期間跳過）
    cache_service = req.app.state.cache_service

    if not active_form_session:  # ✅ 只在非表單會話時使用緩存
        cached_response = _check_cache(cache_service, request.vendor_id, request.message, request.target_user)
        if cached_response:
            return cached_response

    # ========== 表單邏輯處理 ==========
    if active_form_session:
        intent_result = intent_classifier.classify(request.message)
        result = await form_manager.collect_field_data(
            user_message=request.message,
            session_id=request.session_id,
            intent_result=intent_result
        )
        return convert_form_result_to_response(result, request)

    # ========== 原有流程 ==========
    # Step 3: 意圖分類
    # ...
```

**優點**：
- ✅ 徹底解決緩存繞過問題
- ✅ 保留表單會話的即時性
- ✅ 不影響非表單會話的緩存效能

**缺點**：
- ⚠️ 表單填寫期間，用戶問相同問題會重複查詢 RAG（但這是合理的）

**方案 2：擴展緩存 Key 包含 session_id（不推薦）**

```python
def _make_question_key(self, vendor_id: int, question: str, target_user: str, config_version: str, session_id: Optional[str] = None):
    question_hash = hashlib.md5(question.lower().strip().encode()).hexdigest()[:16]
    if session_id:
        return f"rag:question:{vendor_id}:{target_user}:{config_version}:{session_id}:{question_hash}"
    else:
        return f"rag:question:{vendor_id}:{target_user}:{config_version}:{question_hash}"
```

**缺點**：
- ❌ 緩存碎片化（每個 session 都有獨立緩存）
- ❌ 緩存命中率大幅下降
- ❌ Redis 記憶體浪費

---

### 4. 資料庫結構衝突分析

#### 現狀盤查

**現有表**（與表單相關的命名空間檢查）：

```bash
grep -r "CREATE TABLE" database --include="*.sql" | grep -E "session|form|conversation"
```

**結果**：
- `conversation_logs`：對話記錄（歷史）
- **無** `form_*` 開頭的表
- **無** `*_session*` 表

#### 結論

**✅ 無命名衝突**

可以安全創建：
- `form_schemas`
- `form_sessions`
- `form_submissions`

---

### 5. 意圖處理流程分析

#### 現狀盤查

**檔案**：`routers/chat.py` 的 `vendor_chat_message()` 函數

```python
@router.post("/message")
async def vendor_chat_message(request: VendorChatRequest, req: Request):
    # Step 1: 驗證業者
    resolver = get_vendor_param_resolver()
    vendor_info = _validate_vendor(request.vendor_id, resolver)

    # Step 2: 緩存檢查
    cache_service = req.app.state.cache_service
    cached_response = _check_cache(...)
    if cached_response:
        return cached_response

    # Step 3: 意圖分類
    intent_classifier = req.app.state.intent_classifier
    intent_result = intent_classifier.classify(request.message)

    # Step 4: SOP 檢索（優先級最高）
    if not request.skip_sop:
        sop_items = await _retrieve_sop(request, intent_result)
        if sop_items:
            return await _build_sop_response(...)

    # Step 5: unclear 意圖處理
    if intent_result['intent_name'] == 'unclear':
        return await _handle_unclear_with_rag_fallback(...)

    # Step 6: 獲取意圖 ID
    intent_id = _get_intent_id(intent_result['intent_name'])

    # Step 7: 檢索知識庫
    knowledge_list = await _retrieve_knowledge(...)

    # Step 8: 找不到知識，參數答案或兜底
    if not knowledge_list:
        return await _handle_no_knowledge_found(...)

    # Step 9: 使用知識庫結果構建回應
    return await _build_knowledge_response(...)
```

#### 表單整合點分析

**整合點 A：在緩存檢查之後，意圖分類之前**

```python
# Step 2: 緩存檢查
...

# ========== 整合點 A：表單會話檢查 ==========
if request.session_id:
    session_state = form_manager.get_session_state(request.session_id)
    if session_state and session_state['state'] in ['COLLECTING', 'DIGRESSION']:
        # 用戶正在填寫表單 → 走表單流程
        intent_result = intent_classifier.classify(request.message)
        result = await form_manager.collect_field_data(...)
        return convert_form_result_to_response(result, request)

# Step 3: 意圖分類
...
```

**優點**：
- ✅ 優先檢查表單會話，避免不必要的 RAG 處理
- ✅ 表單填寫期間不受緩存影響

**整合點 B：在意圖分類之後，SOP 檢索之前**

```python
# Step 3: 意圖分類
intent_result = intent_classifier.classify(request.message)

# ========== 整合點 B：表單觸發檢查 ==========
if request.session_id:
    form_trigger_result = await form_manager.trigger_form_filling(
        intent_name=intent_result['intent_name'],
        session_id=request.session_id,
        user_id=request.user_id,
        vendor_id=request.vendor_id
    )
    if form_trigger_result.get('form_triggered'):
        return convert_form_result_to_response(form_trigger_result, request)

# Step 4: SOP 檢索
...
```

**優點**：
- ✅ 利用意圖分類結果觸發表單
- ✅ 與現有流程無縫整合

#### 推薦整合方案

**雙點整合**：

```python
@router.post("/message")
async def vendor_chat_message(request: VendorChatRequest, req: Request):
    # Step 1: 驗證業者
    resolver = get_vendor_param_resolver()
    vendor_info = _validate_vendor(request.vendor_id, resolver)

    # ========== 整合點 A：表單會話檢查 ==========
    form_manager = req.app.state.form_manager
    active_form_session = None

    if request.session_id:
        session_state = form_manager.get_session_state(request.session_id)
        if session_state and session_state['state'] in ['COLLECTING', 'DIGRESSION']:
            active_form_session = session_state

    # Step 2: 緩存檢查（表單會話期間跳過）
    cache_service = req.app.state.cache_service
    if not active_form_session:
        cached_response = _check_cache(...)
        if cached_response:
            return cached_response

    # Step 3: 意圖分類（必須執行，用於表單和一般流程）
    intent_classifier = req.app.state.intent_classifier
    intent_result = intent_classifier.classify(request.message)

    # ========== 表單會話處理（整合點 A 延續）==========
    if active_form_session:
        result = await form_manager.collect_field_data(
            user_message=request.message,
            session_id=request.session_id,
            intent_result=intent_result
        )
        return convert_form_result_to_response(result, request)

    # ========== 整合點 B：表單觸發檢查 ==========
    if request.session_id:
        form_trigger_result = await form_manager.trigger_form_filling(
            intent_name=intent_result['intent_name'],
            session_id=request.session_id,
            user_id=request.user_id,
            vendor_id=request.vendor_id
        )
        if form_trigger_result.get('form_triggered'):
            return convert_form_result_to_response(form_trigger_result, request)

    # ========== 原有流程繼續 ==========
    # Step 4: SOP 檢索
    if not request.skip_sop:
        sop_items = await _retrieve_sop(request, intent_result)
        if sop_items:
            return await _build_sop_response(...)

    # ... 後續流程
```

---

### 6. VendorChatResponse 模型擴展

#### 現狀盤查

**檔案**：`routers/chat.py`

```python
class VendorChatResponse(BaseModel):
    answer: str
    intent_name: Optional[str] = None
    confidence: Optional[float] = None
    sources: Optional[List[KnowledgeSource]] = None
    source_count: int = 0
    vendor_id: int
    mode: str
    session_id: Optional[str] = None
    timestamp: str
    video_url: Optional[str] = None
    debug_info: Optional[DebugInfo] = None
```

#### 需要擴展的欄位

```python
class VendorChatResponse(BaseModel):
    # ... 現有欄位 ...

    # ========== 新增：表單相關欄位 ==========
    form_triggered: Optional[bool] = Field(None, description="是否觸發表單填寫")
    form_completed: Optional[bool] = Field(None, description="表單是否已完成")
    form_cancelled: Optional[bool] = Field(None, description="表單是否已取消")
    form_id: Optional[str] = Field(None, description="表單 ID")
    current_field: Optional[str] = Field(None, description="當前欄位名稱")
    progress: Optional[str] = Field(None, description="填寫進度（如 '2/5'）")
    allow_resume: Optional[bool] = Field(None, description="是否允許恢復表單填寫")
```

---

## 🎯 整合方案總結

### 修改清單

| 文件 | 修改內容 | 行數估計 | 複雜度 |
|------|---------|---------|--------|
| `database/migrations/create_form_tables.sql` | 新增 3 張表 | ~100 行 | 低 |
| `services/form_manager.py` | 表單管理器（已完成草稿） | ~600 行 | 中 |
| `services/form_validator.py` | 欄位驗證器（已完成草稿） | ~200 行 | 低 |
| `services/digression_detector.py` | 離題偵測器（已完成草稿） | ~150 行 | 低 |
| `routers/chat.py` | 整合表單邏輯（雙點插入） | ~30 行新增 | 低 |
| `routers/chat.py` | 擴展 VendorChatResponse | ~7 行新增 | 低 |
| `routers/chat.py` | 新增轉換函數 | ~20 行新增 | 低 |
| `app.py` | 初始化 FormManager | ~5 行新增 | 低 |

**總計**：~60 行代碼修改（不含新服務），風險可控。

---

### 實施順序

#### Phase 1：資料庫準備（不影響現有服務）
1. 創建遷移腳本 `migrations/create_form_tables.sql`
2. 執行遷移
3. 插入測試表單定義

#### Phase 2：服務開發（獨立模組）
1. 完善 `form_manager.py`
2. 完善 `form_validator.py`
3. 完善 `digression_detector.py`
4. 編寫單元測試

#### Phase 3：API 整合（修改現有文件）
1. 修改 `app.py`：初始化 FormManager
2. 修改 `routers/chat.py`：
   - 擴展 `VendorChatResponse` 模型
   - 新增 `convert_form_result_to_response()` 函數
   - 在 `vendor_chat_message()` 插入表單邏輯（雙點整合）
3. 測試整合

#### Phase 4：前端適配
1. 檢測表單狀態（`response.form_triggered`）
2. 顯示進度條（`response.progress`）
3. 處理離題提示（`response.allow_resume`）

---

## 🔒 風險評估與緩解

### 風險 1：緩存繞過表單邏輯

**風險等級**：🔴 高

**緩解方案**：
- 表單會話期間禁用緩存（方案 1）
- 在緩存檢查前增加表單會話檢查

**驗證方法**：
```bash
# 測試場景：表單填寫中問相同問題兩次
curl -X POST /api/v1/message -d '{
  "message": "請問租金多少？",
  "session_id": "test_session_123",
  "vendor_id": 1
}'

# 第二次（緩存應被跳過）
curl -X POST /api/v1/message -d '{
  "message": "請問租金多少？",
  "session_id": "test_session_123",
  "vendor_id": 1
}'
```

### 風險 2：表單會話超時導致殭屍會話

**風險等級**：🟡 中

**緩解方案**：
- 定時清理過期會話（30 分鐘無活動）
- 使用 APScheduler 或 Celery

**實施**：
```python
# app.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=10)
def cleanup_expired_sessions():
    form_manager.cleanup_expired_sessions(timeout_minutes=30)

scheduler.start()
```

### 風險 3：前端未正確處理表單狀態

**風險等級**：🟡 中

**緩解方案**：
- 後端返回明確的表單狀態欄位
- 前端根據 `form_triggered`, `form_completed`, `allow_resume` 調整 UI

**驗證方法**：
- 整合測試（Cypress / Playwright）
- 手動測試流程

---

## 📋 整合檢查清單

### 開發階段

- [ ] 資料庫遷移腳本已創建
- [ ] 遷移腳本已在開發環境測試
- [ ] FormManager 已實作並通過單元測試
- [ ] FormValidator 已實作並通過單元測試
- [ ] DigressionDetector 已實作並通過單元測試
- [ ] `app.py` 已初始化 FormManager
- [ ] `VendorChatResponse` 已擴展表單欄位
- [ ] `convert_form_result_to_response()` 已實作
- [ ] `vendor_chat_message()` 已整合表單邏輯（雙點）
- [ ] 緩存繞過問題已驗證解決

### 測試階段

- [ ] 單元測試：FormManager 的所有方法
- [ ] 單元測試：FormValidator 的驗證邏輯
- [ ] 單元測試：DigressionDetector 的偵測策略
- [ ] 整合測試：完整表單填寫流程（無離題）
- [ ] 整合測試：表單填寫中離題並恢復
- [ ] 整合測試：表單填寫中明確退出
- [ ] 整合測試：驗證失敗重試流程
- [ ] 整合測試：表單超時自動清理
- [ ] 性能測試：會話狀態查詢效能
- [ ] 緩存測試：表單會話期間緩存被正確跳過

### 部署階段

- [ ] 資料庫遷移已在 Staging 環境執行
- [ ] 服務已在 Staging 環境部署並測試
- [ ] 前端已適配表單狀態顯示
- [ ] 監控指標已配置（完成率、離題率、平均耗時）
- [ ] 日誌已配置（結構化日誌）
- [ ] 定時清理任務已啟動
- [ ] 回退方案已準備（資料庫回滾腳本）

---

## 🎓 結論

### 可行性評估

**✅ 高度可行**

- 核心組件（session_id）可直接利用
- 資料庫無命名衝突
- 主要衝突（緩存）有明確解決方案
- 代碼修改量小（~60 行）

### 預估時間

| 階段 | 時間 | 責任 |
|------|------|------|
| 資料庫準備 | 0.5 天 | 後端工程師 |
| 服務開發 | 2-3 天 | 後端工程師 |
| API 整合 | 1-2 天 | 後端工程師 |
| 測試 | 1-2 天 | QA / 後端工程師 |
| 前端適配 | 1-2 天 | 前端工程師 |
| **總計** | **6-10 天** | - |

### 關鍵成功因素

1. ✅ 緩存繞過問題的正確處理（方案 1）
2. ✅ 雙點整合方案的精確實施
3. ✅ 完整的測試覆蓋（特別是離題場景）
4. ✅ 前端與後端的狀態同步

### 下一步行動

1. **審閱本文檔**：確認分析結論和整合方案
2. **決策點**：選擇緩存處理方案（推薦方案 1）
3. **資料庫遷移**：創建並測試遷移腳本
4. **開始開發**：按照 Phase 1-4 順序實施
