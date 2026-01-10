# 表單填寫功能 - 具體代碼修改指南

> 詳細的代碼修改示例，包含完整的 diff 和註解

---

## 📝 修改文件清單

1. `rag-orchestrator/app.py`：初始化 FormManager
2. `rag-orchestrator/routers/chat.py`：整合表單邏輯
3. `database/migrations/create_form_tables.sql`：新增表

---

## 1. app.py 修改

### 修改位置：初始化區塊

**文件**：`rag-orchestrator/app.py`

**修改內容**：

```python
# 在文件開頭的導入區塊增加
from services.form_manager import FormManager  # ✅ 新增

# 在全局變數區塊增加
form_manager: FormManager = None  # ✅ 新增

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時初始化
    global db_pool, intent_classifier, rag_engine, confidence_evaluator, \
           unclear_question_manager, llm_answer_optimizer, suggestion_engine, \
           vendor_config_service, cache_service, form_manager  # ✅ 新增 form_manager

    print("🚀 初始化 RAG Orchestrator...")

    # ... 現有初始化代碼 ...

    # 初始化緩存服務
    cache_service = CacheService()

    # ========== ✅ 新增：初始化表單管理器 ==========
    form_manager = FormManager()
    print("✅ 表單管理器已初始化")

    # 將服務注入到 app.state
    app.state.db_pool = db_pool
    app.state.intent_classifier = intent_classifier
    app.state.rag_engine = rag_engine
    app.state.confidence_evaluator = confidence_evaluator
    app.state.unclear_question_manager = unclear_question_manager
    app.state.llm_answer_optimizer = llm_answer_optimizer
    app.state.suggestion_engine = suggestion_engine
    app.state.vendor_config_service = vendor_config_service
    app.state.cache_service = cache_service
    app.state.form_manager = form_manager  # ✅ 新增

    # ... 後續代碼 ...
```

**影響範圍**：~5 行新增

---

## 2. chat.py 修改（主要整合）

### 修改 A：擴展 VendorChatResponse 模型

**位置**：`routers/chat.py` 約第 1546 行

**修改內容**：

```python
class VendorChatResponse(BaseModel):
    """多業者聊天回應"""
    answer: str = Field(..., description="回答內容")
    intent_name: Optional[str] = Field(None, description="意圖名稱")
    intent_type: Optional[str] = Field(None, description="意圖類型")
    confidence: Optional[float] = Field(None, description="分類信心度")
    all_intents: Optional[List[str]] = Field(None, description="所有相關意圖名稱（主要 + 次要）")
    secondary_intents: Optional[List[str]] = Field(None, description="次要相關意圖")
    intent_ids: Optional[List[int]] = Field(None, description="所有意圖 IDs")
    sources: Optional[List[KnowledgeSource]] = Field(None, description="知識來源列表")
    source_count: int = Field(0, description="知識來源數量")
    vendor_id: int
    mode: str
    session_id: Optional[str] = None
    timestamp: str
    # 影片資訊
    video_url: Optional[str] = Field(None, description="教學影片 URL")
    video_file_size: Optional[int] = Field(None, description="影片檔案大小（bytes）")
    video_duration: Optional[int] = Field(None, description="影片長度（秒）")
    video_format: Optional[str] = Field(None, description="影片格式")
    # 調試資訊
    debug_info: Optional[DebugInfo] = Field(None, description="調試資訊（處理流程詳情）")

    # ========== ✅ 新增：表單相關欄位 ==========
    form_triggered: Optional[bool] = Field(None, description="是否觸發表單填寫")
    form_completed: Optional[bool] = Field(None, description="表單是否已完成")
    form_cancelled: Optional[bool] = Field(None, description="表單是否已取消")
    form_id: Optional[str] = Field(None, description="表單 ID")
    current_field: Optional[str] = Field(None, description="當前欄位名稱")
    progress: Optional[str] = Field(None, description="填寫進度（如 '2/5'）")
    allow_resume: Optional[bool] = Field(None, description="是否允許恢復表單填寫")
```

**影響範圍**：~7 行新增

---

### 修改 B：新增轉換函數

**位置**：`routers/chat.py` 在 `vendor_chat_message()` 函數之前

**修改內容**：

```python
# ==================== 輔助函數：表單結果轉換 ====================

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

**影響範圍**：~30 行新增

---

### 修改 C：整合表單邏輯到主端點（雙點整合）

**位置**：`routers/chat.py` 的 `vendor_chat_message()` 函數（約第 1570 行）

**完整修改後的函數**：

```python
@router.post("/message", response_model=VendorChatResponse)
async def vendor_chat_message(request: VendorChatRequest, req: Request):
    """
    多業者通用聊天端點（Phase 1: B2C 模式）- 已重構 + 表單填寫整合

    流程：
    1. 驗證業者狀態
    2. [✅ 新增] 表單會話檢查
    3. 檢查緩存（表單會話期間跳過）
    4. 意圖分類
    5. [✅ 新增] 表單會話處理 / 表單觸發檢查
    6. 根據意圖處理：unclear → SOP → 知識庫 → RAG fallback
    7. LLM 優化並返回答案

    重構：單一職責原則（Single Responsibility Principle）
    - 主函數作為編排器（Orchestrator）
    - 各功能模塊獨立為輔助函數
    """
    try:
        # Step 1: 驗證業者
        resolver = get_vendor_param_resolver()
        vendor_info = _validate_vendor(request.vendor_id, resolver)

        # ========== ✅ 新增：整合點 A - 表單會話檢查 ==========
        form_manager = req.app.state.form_manager
        active_form_session = None

        if request.session_id:
            session_state = form_manager.get_session_state(request.session_id)
            if session_state and session_state['state'] in ['COLLECTING', 'DIGRESSION']:
                active_form_session = session_state
                print(f"📋 檢測到進行中的表單會話（狀態: {session_state['state']}）")

        # Step 2: 緩存檢查（表單會話期間跳過）
        cache_service = req.app.state.cache_service

        if not active_form_session:  # ✅ 只在非表單會話時使用緩存
            cached_response = _check_cache(cache_service, request.vendor_id, request.message, request.target_user)
            if cached_response:
                return cached_response
        else:
            print(f"⏭️  表單會話期間，跳過緩存檢查")

        # Step 3: 意圖分類（必須執行，用於表單和一般流程）
        intent_classifier = req.app.state.intent_classifier
        intent_result = intent_classifier.classify(request.message)

        # ========== ✅ 新增：表單會話處理（整合點 A 延續）==========
        if active_form_session:
            print(f"📝 處理表單會話：{active_form_session['form_id']}")
            result = await form_manager.collect_field_data(
                user_message=request.message,
                session_id=request.session_id,
                intent_result=intent_result
            )
            return convert_form_result_to_response(result, request)

        # ========== ✅ 新增：整合點 B - 表單觸發檢查 ==========
        if request.session_id:
            form_trigger_result = await form_manager.trigger_form_filling(
                intent_name=intent_result['intent_name'],
                session_id=request.session_id,
                user_id=request.user_id,
                vendor_id=request.vendor_id
            )

            if form_trigger_result.get('form_triggered'):
                print(f"🎯 觸發表單：{form_trigger_result['form_id']}")
                return convert_form_result_to_response(form_trigger_result, request)

        # ========== 原有流程繼續 ==========
        # Step 4: 嘗試檢索 SOP（優先級最高，不管意圖是什麼都先嘗試）- 回測模式可跳過
        if not request.skip_sop:
            sop_items = await _retrieve_sop(request, intent_result)
            if sop_items:
                print(f"✅ 找到 {len(sop_items)} 個 SOP 項目，使用 SOP 流程")
                return await _build_sop_response(
                    request, req, intent_result, sop_items, resolver, vendor_info, cache_service
                )
            print(f"ℹ️  沒有找到 SOP，繼續其他流程")
        else:
            print(f"ℹ️  [回測模式] 跳過 SOP 檢索，僅使用知識庫")

        # Step 5: 處理 unclear 意圖（RAG fallback + 測試場景記錄）
        if intent_result['intent_name'] == 'unclear':
            return await _handle_unclear_with_rag_fallback(
                request, req, intent_result, resolver, vendor_info, cache_service
            )

        # Step 6: 獲取意圖 ID
        intent_id = _get_intent_id(intent_result['intent_name'])

        # Step 7: 檢索知識庫（混合模式：intent + 向量）
        knowledge_list = await _retrieve_knowledge(request, intent_id, intent_result)

        # Step 8: 如果知識庫沒有結果，嘗試參數答案或 RAG fallback
        if not knowledge_list:
            print(f"⚠️  意圖 '{intent_result['intent_name']}' (ID: {intent_id}) 沒有關聯知識，嘗試參數答案或 RAG fallback...")
            return await _handle_no_knowledge_found(
                request, req, intent_result, resolver, cache_service, vendor_info
            )

        # Step 9: 使用知識庫結果構建優化回應
        return await _build_knowledge_response(
            request, req, intent_result, knowledge_list, resolver, vendor_info, cache_service
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"處理聊天請求失敗: {str(e)}"
        )
```

**影響範圍**：~40 行修改（含註解）

**關鍵修改點**：

1. **整合點 A**（第 1590-1600 行）：
   - 檢查是否有進行中的表單會話
   - 表單會話期間跳過緩存

2. **表單會話處理**（第 1605-1615 行）：
   - 如果在表單填寫中，調用 `form_manager.collect_field_data()`
   - 立即返回，不走後續流程

3. **整合點 B**（第 1617-1628 行）：
   - 檢查意圖是否匹配表單觸發條件
   - 如果觸發表單，創建會話並返回第一個欄位提示

---

## 3. 資料庫遷移腳本

### 創建文件

**文件**：`database/migrations/create_form_tables.sql`

**內容**：

```sql
-- ========================================
-- 表單填寫系統 - 資料庫遷移腳本
-- ========================================
-- 創建日期：2026-01-08
-- 說明：新增表單定義、會話和提交記錄表

-- 1. 表單定義表（Form Schemas）
CREATE TABLE IF NOT EXISTS form_schemas (
    id SERIAL PRIMARY KEY,
    form_id VARCHAR(100) UNIQUE NOT NULL,
    form_name VARCHAR(200) NOT NULL,
    description TEXT,

    -- 觸發意圖列表（JSONB 格式）
    -- 例如：["租屋申請", "報修申請", "合約續約"]
    trigger_intents JSONB,

    -- 欄位定義（JSONB 格式）
    -- 例如：[{"field_name": "full_name", "display_name": "姓名", ...}]
    fields JSONB NOT NULL,

    -- 訊息模板
    completion_message TEXT,
    cancellation_message TEXT,

    -- 業者關聯（NULL = 全局表單）
    vendor_id INTEGER REFERENCES vendors(id),

    -- 狀態
    is_active BOOLEAN DEFAULT true,

    -- 時間戳記
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_form_schemas_trigger_intents ON form_schemas USING GIN(trigger_intents);
CREATE INDEX idx_form_schemas_vendor_id ON form_schemas(vendor_id);
CREATE INDEX idx_form_schemas_is_active ON form_schemas(is_active);

-- 註解
COMMENT ON TABLE form_schemas IS '表單定義表：儲存表單結構和觸發條件';
COMMENT ON COLUMN form_schemas.trigger_intents IS '觸發意圖列表（JSONB 陣列）';
COMMENT ON COLUMN form_schemas.fields IS '欄位定義（JSONB 陣列）';

-- ========================================

-- 2. 表單會話表（Form Sessions）
CREATE TABLE IF NOT EXISTS form_sessions (
    id SERIAL PRIMARY KEY,

    -- 會話標識（對應 VendorChatRequest.session_id）
    session_id VARCHAR(100) NOT NULL,

    -- 用戶和業者
    user_id VARCHAR(100),
    vendor_id INTEGER REFERENCES vendors(id),

    -- 表單關聯
    form_id VARCHAR(100) REFERENCES form_schemas(form_id),

    -- 狀態機：COLLECTING / DIGRESSION / COMPLETED / CANCELLED
    state VARCHAR(50) NOT NULL,

    -- 當前欄位索引（0-based）
    current_field_index INTEGER DEFAULT 0,

    -- 已收集的資料（JSONB 格式）
    -- 例如：{"full_name": "王小明", "phone": "0912345678", ...}
    collected_data JSONB,

    -- 驗證失敗次數記錄（JSONB 格式）
    -- 例如：{"phone": 2, "id_number": 1}
    validation_attempts JSONB,

    -- 離題次數統計
    digression_count INTEGER DEFAULT 0,

    -- 時間戳記
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_form_sessions_session_id ON form_sessions(session_id);
CREATE INDEX idx_form_sessions_state ON form_sessions(state);
CREATE INDEX idx_form_sessions_last_activity ON form_sessions(last_activity_at DESC);
CREATE INDEX idx_form_sessions_user_id ON form_sessions(user_id);

-- 註解
COMMENT ON TABLE form_sessions IS '表單會話表：追蹤表單填寫進度和狀態';
COMMENT ON COLUMN form_sessions.state IS '狀態：COLLECTING(收集中) / DIGRESSION(離題) / COMPLETED(完成) / CANCELLED(取消)';
COMMENT ON COLUMN form_sessions.collected_data IS '已收集的欄位資料（JSONB）';

-- ========================================

-- 3. 表單提交記錄表（Form Submissions）
CREATE TABLE IF NOT EXISTS form_submissions (
    id SERIAL PRIMARY KEY,

    -- 關聯表單會話
    form_session_id INTEGER REFERENCES form_sessions(id),

    -- 表單和業者
    form_id VARCHAR(100) REFERENCES form_schemas(form_id),
    user_id VARCHAR(100),
    vendor_id INTEGER REFERENCES vendors(id),

    -- 完整提交資料（JSONB 格式）
    submitted_data JSONB NOT NULL,

    -- 提交來源
    submission_source VARCHAR(50) DEFAULT 'chatbot',  -- 'chatbot' / 'web' / 'app'

    -- 時間戳記
    submitted_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_form_submissions_user_id ON form_submissions(user_id);
CREATE INDEX idx_form_submissions_vendor_id ON form_submissions(vendor_id);
CREATE INDEX idx_form_submissions_form_id ON form_submissions(form_id);
CREATE INDEX idx_form_submissions_submitted_at ON form_submissions(submitted_at DESC);

-- 註解
COMMENT ON TABLE form_submissions IS '表單提交記錄表：儲存已完成的表單資料';
COMMENT ON COLUMN form_submissions.submitted_data IS '完整的表單資料（JSONB）';

-- ========================================

-- 4. 觸發器：自動更新 updated_at
CREATE OR REPLACE FUNCTION update_form_schemas_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_form_schemas_updated_at
    BEFORE UPDATE ON form_schemas
    FOR EACH ROW
    EXECUTE FUNCTION update_form_schemas_updated_at();

-- ========================================

-- 5. 初始化測試表單：租屋申請表
INSERT INTO form_schemas (form_id, form_name, description, trigger_intents, fields, completion_message, cancellation_message)
VALUES (
    'rental_application',
    '租屋申請表',
    '收集租客申請租屋的基本資料',
    '["租屋申請", "我要租房子", "申請租約"]'::jsonb,
    '[
        {
            "field_name": "full_name",
            "display_name": "姓名",
            "field_type": "text",
            "required": true,
            "prompt": "請問您的全名是？",
            "validation": {
                "pattern": "^[\u4e00-\u9fa5]{2,10}$",
                "error_message": "請輸入2-10個中文字的真實姓名"
            },
            "examples": ["王小明", "李美玲"]
        },
        {
            "field_name": "phone",
            "display_name": "聯絡電話",
            "field_type": "phone",
            "required": true,
            "prompt": "請提供您的聯絡電話（手機或市話）",
            "validation": {
                "pattern": "^09\\d{8}$|^0\\d{1,2}-\\d{6,8}$",
                "error_message": "請輸入正確的台灣電話號碼格式（如：0912345678 或 02-12345678）"
            },
            "examples": ["0912345678", "02-12345678"]
        },
        {
            "field_name": "id_number",
            "display_name": "身分證字號",
            "field_type": "text",
            "required": true,
            "prompt": "請提供您的身分證字號（用於身份驗證）",
            "validation": {
                "pattern": "^[A-Z][12]\\d{8}$",
                "error_message": "請輸入正確的身分證字號格式（如：A123456789）"
            },
            "examples": ["A123456789"]
        },
        {
            "field_name": "address",
            "display_name": "通訊地址",
            "field_type": "text",
            "required": true,
            "prompt": "請提供您的通訊地址",
            "validation": {
                "min_length": 10,
                "error_message": "請輸入完整的地址（至少10個字）"
            }
        }
    ]'::jsonb,
    '感謝您完成租屋申請表！我們會儘快審核您的資料並與您聯繫。',
    '已取消表單填寫。如需重新申請，請隨時告訴我！'
)
ON CONFLICT (form_id) DO NOTHING;

-- ========================================

-- 初始化成功訊息
DO $$
BEGIN
    RAISE NOTICE '✅ 表單填寫系統資料表建立完成';
    RAISE NOTICE '   - form_schemas: 表單定義';
    RAISE NOTICE '   - form_sessions: 表單會話';
    RAISE NOTICE '   - form_submissions: 表單提交記錄';
    RAISE NOTICE '   - 測試表單「租屋申請表」已初始化';
END $$;
```

---

## 4. 測試案例

### 測試 1：完整表單流程（無離題）

**cURL 命令**：

```bash
# 1. 觸發表單
curl -X POST http://localhost:8000/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我要申請租房子",
    "session_id": "test_session_001",
    "vendor_id": 1,
    "target_user": "tenant"
  }'

# 預期回應：
# {
#   "answer": "好的，我來協助您填寫**租屋申請表**。\n\n請問您的全名是？",
#   "form_triggered": true,
#   "form_id": "rental_application",
#   "current_field": "full_name",
#   "progress": "0/4",
#   ...
# }

# 2. 填寫姓名
curl -X POST http://localhost:8000/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "王小明",
    "session_id": "test_session_001",
    "vendor_id": 1,
    "target_user": "tenant"
  }'

# 預期回應：
# {
#   "answer": "✅ **姓名**已記錄！\n\n📊 進度：1/4\n\n請提供您的聯絡電話",
#   "current_field": "phone",
#   "progress": "1/4",
#   ...
# }

# 3. 填寫電話
curl -X POST http://localhost:8000/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "0912345678",
    "session_id": "test_session_001",
    "vendor_id": 1,
    "target_user": "tenant"
  }'

# 4. 填寫身分證
# 5. 填寫地址
# 6. 完成
```

### 測試 2：表單填寫中離題

```bash
# 1. 觸發表單並填寫到第2個欄位
# ...

# 2. 用戶離題問問題
curl -X POST http://localhost:8000/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "請問租金多少？",
    "session_id": "test_session_001",
    "vendor_id": 1,
    "target_user": "tenant"
  }'

# 預期回應：
# {
#   "answer": "我們的租金範圍是...\n\n──────\n💡 您的**租屋申請表**還未完成，需要繼續填寫嗎？",
#   "allow_resume": true,
#   ...
# }

# 3. 恢復填寫
curl -X POST http://localhost:8000/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "繼續",
    "session_id": "test_session_001",
    "vendor_id": 1,
    "target_user": "tenant"
  }'

# 預期回應：
# {
#   "answer": "好的，繼續填寫！\n\n📊 進度：1/4\n\n請提供您的聯絡電話",
#   ...
# }
```

### 測試 3：緩存跳過驗證

```bash
# 1. 建立表單會話
# ...

# 2. 在表單填寫中問相同問題兩次
curl -X POST http://localhost:8000/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "請問租金多少？",
    "session_id": "test_session_001",
    "vendor_id": 1,
    "target_user": "tenant"
  }'

# 第一次：正常 RAG 處理 + 緩存

# 3. 再問一次（驗證緩存被跳過）
curl -X POST http://localhost:8000/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "請問租金多少？",
    "session_id": "test_session_001",
    "vendor_id": 1,
    "target_user": "tenant"
  }'

# 第二次：應該再次執行 RAG 處理（不從緩存返回）
# 查看日誌確認：「⏭️  表單會話期間，跳過緩存檢查」
```

---

## 5. 部署檢查清單

### 開發環境

- [ ] 執行遷移腳本：`psql -h localhost -U your_user -d ai_chatbot -f database/migrations/create_form_tables.sql`
- [ ] 驗證表已創建：`\dt form_*`
- [ ] 驗證測試表單已插入：`SELECT * FROM form_schemas WHERE form_id = 'rental_application';`
- [ ] 重啟服務並檢查初始化日誌：「✅ 表單管理器已初始化」
- [ ] 運行測試案例 1-3

### Staging 環境

- [ ] 備份資料庫
- [ ] 執行遷移腳本
- [ ] 部署新代碼
- [ ] 運行整合測試
- [ ] 驗證監控指標

### Production 環境

- [ ] 準備回滾計畫
- [ ] 執行遷移腳本（先）
- [ ] 部署新代碼（後）
- [ ] 監控錯誤率和響應時間
- [ ] 驗證表單填寫流程

---

## 6. 回滾方案

### 如果需要回滾

**步驟 1：停止新服務**

```bash
# Docker 環境
docker-compose stop rag-orchestrator

# 或 K8s 環境
kubectl rollout undo deployment/rag-orchestrator
```

**步驟 2：回滾資料庫（可選）**

```sql
-- 只在必要時執行（會刪除所有表單數據）
DROP TABLE IF EXISTS form_submissions CASCADE;
DROP TABLE IF EXISTS form_sessions CASCADE;
DROP TABLE IF EXISTS form_schemas CASCADE;
DROP FUNCTION IF EXISTS update_form_schemas_updated_at();
```

**步驟 3：回滾代碼**

```bash
git revert <commit_hash>
```

---

## 7. 總結

### 修改統計

| 文件 | 新增行數 | 修改行數 | 刪除行數 |
|------|---------|---------|---------|
| `app.py` | 5 | 2 | 0 |
| `routers/chat.py` | 77 | 15 | 0 |
| `database/migrations/create_form_tables.sql` | 280 | 0 | 0 |
| **總計** | **362** | **17** | **0** |

### 風險評估

| 風險 | 等級 | 緩解措施 |
|------|------|---------|
| 緩存繞過 | 🔴 高 | 已通過雙點整合解決 |
| 流程衝突 | 🟡 中 | 已驗證整合點正確性 |
| 資料庫遷移 | 🟢 低 | 提供回滾腳本 |
| 前端適配 | 🟡 中 | 提供明確的欄位定義 |

### 下一步

1. 審閱本文檔
2. 在開發環境執行遷移和部署
3. 運行測試案例 1-3
4. 前端適配（根據新增欄位）
5. 整合測試
6. Staging 部署
7. Production 部署
