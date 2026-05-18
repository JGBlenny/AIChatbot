# 知識匯入功能 - 完整邏輯分析

## 概述

本文檔詳細分析 **知識匯入功能**（http://localhost:8080/knowledge-import）的完整邏輯，包括前端介面、後端 API、知識提取、向量生成與儲存流程。

**調查日期**: 2025-10-12
**功能狀態**: ⚠️ **部分實作**（前端完整、後端骨架、核心邏輯待整合）

---

## 🏗️ 系統架構

### 整體流程圖

```
┌─────────────────────────────────────────────────────────────────┐
│                          前端 (Vue.js)                           │
│                   KnowledgeImportView.vue                        │
│                                                                  │
│  Step 1: 上傳檔案    Step 2: 預覽      Step 3: 處理中            │
│  Step 4: 完成                                                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ HTTP API Calls
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                      後端 API (FastAPI)                          │
│                    knowledge_import.py                           │
│                                                                  │
│  POST /upload    → 開始匯入作業                                   │
│  GET /jobs/{id}  → 輪詢作業狀態                                   │
│  POST /preview   → 預覽檔案內容（不消耗 token）                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ TODO: 整合知識提取邏輯 ⚠️
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                  知識提取與處理 (Scripts)                         │
│                                                                  │
│  • extract_knowledge_and_tests.py    ← LINE 聊天記錄提取         │
│  • import_excel_to_kb.py             ← Excel 匯入 + 向量生成     │
│  • import_extracted_to_db.py         ← 資料庫匯入                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                    向量生成與儲存                                 │
│                                                                  │
│  OpenAI API                PostgreSQL                           │
│  text-embedding-3-small → knowledge_base.embedding (vector)    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📱 前端實作分析

### 檔案位置
**`knowledge-admin/frontend/src/views/KnowledgeImportView.vue`** (883 行)

### 核心功能

#### 1. 四步驟向導介面

```javascript
data() {
  return {
    currentStep: 1,  // 1=上傳, 2=預覽, 3=處理中, 4=完成
    uploadedFile: null,
    previewData: null,
    jobId: null,
    jobStatus: null,
    pollingInterval: null
  };
}
```

#### 2. 檔案上傳 (Step 1)

**支援功能**:
- 拖放上傳 (Drag & Drop)
- 檔案點擊選擇
- 檔案類型驗證（Excel, PDF, TXT）
- 檔案大小限制（50MB）

**關鍵程式碼**:
```javascript
async uploadFile() {
  const formData = new FormData();
  formData.append('file', this.uploadedFile);
  formData.append('vendor_id', this.selectedVendor);
  formData.append('import_mode', this.importOptions.mode);
  formData.append('enable_deduplication', this.importOptions.deduplication);

  const response = await axios.post(
    `${RAG_API}/knowledge-import/upload`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );

  this.jobId = response.data.job_id;
  this.currentStep = 3;  // 進入處理中階段
  this.startPolling();   // 開始輪詢作業狀態
}
```

#### 3. 檔案預覽 (Step 2)

**功能**:
- 顯示檔案內容預覽
- 展示將要提取的知識數量估計
- 允許調整匯入選項

**匯入選項**:
```javascript
importOptions: {
  mode: 'append',         // append | replace | merge
  deduplication: true,    // 啟用去重
  autoClassify: true      // 自動分類
}
```

#### 4. 處理中 (Step 3) - 輪詢機制

**狀態輪詢**:
```javascript
startPolling() {
  this.pollingInterval = setInterval(async () => {
    const response = await axios.get(
      `${RAG_API}/knowledge-import/jobs/${this.jobId}`
    );
    this.jobStatus = response.data;

    if (response.data.status === 'completed') {
      clearInterval(this.pollingInterval);
      this.currentStep = 4;  // 進入完成階段
    } else if (response.data.status === 'failed') {
      clearInterval(this.pollingInterval);
      this.showError(response.data.error);
    }
  }, 2000);  // 每 2 秒輪詢一次
}
```

**進度顯示**:
- 讀取進度條
- 處理狀態文字
- 已處理 / 總數
- 預估剩餘時間

#### 5. 完成 (Step 4)

**顯示資訊**:
- 成功匯入的知識數量
- 跳過的重複項
- 錯誤項目
- 處理時間
- 操作按鈕（重新匯入、查看知識庫）

---

## 🔧 後端 API 實作分析

### 檔案位置
**`rag-orchestrator/routers/knowledge_import.py`** (306 行)

### API 端點

#### 1. POST `/api/v1/knowledge-import/upload`

**功能**: 開始知識匯入作業

**請求參數**:
```python
class UploadFileRequest:
    file: UploadFile              # 上傳的檔案
    vendor_id: Optional[int]      # 業者 ID
    import_mode: str              # append | replace | merge
    enable_deduplication: bool    # 啟用去重
```

**回應**:
```json
{
  "job_id": "uuid-string",
  "status": "processing",
  "message": "知識匯入作業已開始"
}
```

**實作狀態**: ⚠️ **骨架實作**

```python
@router.post("/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    vendor_id: Optional[int] = Form(None),
    import_mode: str = Form("append"),
    enable_deduplication: bool = Form(True),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    # 1. 儲存上傳的檔案到臨時目錄
    job_id = str(uuid.uuid4())
    file_path = save_uploaded_file(file, job_id)

    # 2. 建立作業記錄（儲存到資料庫或記憶體）
    job_record = {
        "job_id": job_id,
        "status": "processing",
        "file_name": file.filename,
        "vendor_id": vendor_id,
        "import_mode": import_mode,
        "created_at": datetime.now()
    }

    # 3. 使用背景任務處理
    background_tasks.add_task(
        process_import_job,
        job_id=job_id,
        file_path=file_path,
        vendor_id=vendor_id,
        import_mode=import_mode,
        enable_deduplication=enable_deduplication
    )

    return {"job_id": job_id, "status": "processing"}
```

**第 100 行重要註解**:
```python
# TODO: 整合 extract_knowledge_and_tests.py 的邏輯
```

#### 2. GET `/api/v1/knowledge-import/jobs/{job_id}`

**功能**: 查詢作業狀態（用於前端輪詢）

**回應**:
```json
{
  "job_id": "uuid",
  "status": "processing | completed | failed",
  "progress": {
    "current": 45,
    "total": 100,
    "percentage": 45
  },
  "result": {
    "imported": 80,
    "skipped": 15,
    "errors": 5
  },
  "error": null,
  "created_at": "2025-10-12T10:30:00Z",
  "completed_at": null
}
```

#### 3. POST `/api/v1/knowledge-import/preview`

**功能**: 預覽檔案內容（不實際匯入，不消耗 OpenAI token）

**實作狀態**: ⚠️ **未實作**

```python
@router.post("/preview")
async def preview_knowledge_file(file: UploadFile = File(...)):
    # TODO: 實作檔案預覽邏輯
    #   - 讀取檔案前幾行
    #   - 估計知識條目數量
    #   - 檢查格式是否正確
    pass
```

#### 4. GET `/api/v1/knowledge-import/jobs`

**功能**: 列出匯入歷史記錄

#### 5. DELETE `/api/v1/knowledge-import/jobs/{job_id}`

**功能**: 刪除作業記錄

---

## 🤖 知識提取邏輯分析

### 1. LINE 聊天記錄提取

**檔案**: `/Users/lenny/jgb/AIChatbot/scripts/knowledge_extraction/extract_knowledge_and_tests.py` (339 行)

#### 核心流程

```python
class LineKnowledgeExtractor:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

    def process_all_files(self, file_paths: List[str]):
        """處理所有 LINE 聊天記錄"""
        for file_path in file_paths:
            # 1. 解析 LINE 聊天記錄
            messages = self.parse_line_chat(file_path)

            # 2. 使用 LLM 提取問答對和測試情境
            qa_pairs, test_scenarios = self.extract_qa_pairs_and_tests(
                messages,
                source_file=os.path.basename(file_path)
            )

            # 3. 儲存為 Excel
            self.save_to_excel(qa_pairs, test_scenarios, output_dir)
```

#### LLM 提取提示詞

```python
system_prompt = """你是一個專業的客服知識庫分析師。分析 LINE 對話記錄，提取：

1. **問答對（QA Pairs）**：提取客服回答的問題和答案
   - 問題要通用化（移除具體租客姓名、房號等）
   - 答案要完整且實用
   - 識別問題類型（帳務/合約/服務/設施）
   - 判斷對象（房東/租客/管理師）

2. **測試情境（Test Scenarios）**：提取可以作為測試的真實問題
   - 保留問題的原始表達方式
   - 記錄預期答案的關鍵要點
   - 分類測試場景

請以 JSON 格式輸出：
{
  "qa_pairs": [
    {
      "title": "問題標題",
      "category": "帳務問題|合約問題|服務問題|設施問題",
      "question_summary": "問題摘要",
      "answer": "完整答案",
      "audience": "房東|租客|管理師",
      "keywords": ["關鍵字1", "關鍵字2"]
    }
  ],
  "test_scenarios": [...]
}
"""
```

#### 批次處理

```python
def extract_qa_pairs_and_tests(
    self,
    messages: List[Dict],
    source_file: str,
    batch_size: int = 50
):
    """將訊息分批處理，避免超出 token 限制"""
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i+batch_size]
        batch_text = self._format_messages_for_llm(batch)

        # 呼叫 LLM 提取
        extracted = self._call_llm_extract(batch_text, source_file)

        qa_pairs.extend(extracted['qa_pairs'])
        test_scenarios.extend(extracted['test_scenarios'])

        # 避免 API rate limit
        time.sleep(1)
```

#### 輸出格式

**生成兩個 Excel 檔案**:
1. `knowledge_base_extracted.xlsx` - 提取的知識庫
2. `test_scenarios.xlsx` - 測試情境

---

### 2. Excel 匯入與向量生成

**檔案**: `/Users/lenny/jgb/AIChatbot/scripts/knowledge_extraction/import_excel_to_kb.py` (357 行)

#### 核心流程

```python
class ExcelKnowledgeImporter:
    async def import_to_database(
        self,
        knowledge_list: List[Dict],
        vendor_id: int = None,
        batch_generate_questions: bool = True
    ):
        """匯入知識到資料庫"""

        for knowledge in knowledge_list:
            # 1. 生成問題摘要（使用 LLM）
            question_summary = self.generate_question_summary(
                knowledge['answer'],
                knowledge['category']
            )

            # 2. 檢查是否已存在（去重）
            exists = await self.conn.fetchval("""
                SELECT COUNT(*) FROM knowledge_base
                WHERE question_summary = $1 AND answer = $2
            """, question_summary, knowledge['answer'])

            if exists > 0:
                continue  # 跳過重複項

            # 3. 生成向量嵌入 ⭐ 核心步驟
            embedding_response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=f"{question_summary} {knowledge['answer'][:200]}"
            )
            embedding = embedding_response.data[0].embedding

            # 4. 插入資料庫
            await self.conn.execute("""
                INSERT INTO knowledge_base (
                    intent_id,
                    vendor_id,
                    title,
                    category,
                    question_summary,
                    answer,
                    audience,
                    keywords,
                    source_file,
                    source_date,
                    embedding,    ← 向量欄位
                    scope,
                    priority,
                    created_at,
                    updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """, ...)
```

#### 向量生成細節

**使用的 OpenAI 模型**:
- `text-embedding-3-small` (1536 維)

**嵌入文字格式**:
```python
input_text = f"{question_summary} {knowledge['answer'][:200]}"
# 範例: "如何退租？ 退租流程如下：1. 提前一個月告知 2. 填寫退租..."
```

**向量儲存**:
- 資料表: `knowledge_base`
- 欄位: `embedding` (type: `vector(1536)`)
- 用途: 語意相似度搜尋

---

## 🔍 向量檢索邏輯分析

### 檔案位置
**`rag-orchestrator/services/rag_engine.py`** (413 行)

### 核心搜尋邏輯

```python
class RAGEngine:
    async def search(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.6,
        intent_ids: Optional[List[int]] = None,
        primary_intent_id: Optional[int] = None,
        allowed_audiences: Optional[List[str]] = None
    ) -> List[Dict]:
        """搜尋相關知識"""

        # 1. 將問題轉換為向量
        query_embedding = await self._get_embedding(query)

        # 2. 向量相似度搜尋
        results = await conn.fetch("""
            SELECT
                id,
                title,
                answer as content,
                category,
                audience,
                keywords,
                1 - (embedding <=> $1::vector) as base_similarity
            FROM knowledge_base
            WHERE embedding IS NOT NULL
                AND (1 - (embedding <=> $1::vector)) >= $2
                AND (audience IS NULL OR audience = ANY($4::text[]))
            ORDER BY embedding <=> $1::vector
            LIMIT $3
        """, vector_str, similarity_threshold, limit, allowed_audiences)

        return search_results
```

### 相似度計算

**PostgreSQL 向量操作符**:
- `<=>` : 餘弦距離（Cosine Distance）
- `1 - (embedding <=> query)` : 餘弦相似度（範圍 0-1）

**過濾條件**:
1. `embedding IS NOT NULL` - 必須有向量
2. `similarity >= threshold` - 相似度超過閾值（預設 0.6）
3. `audience = ANY(allowed_audiences)` - Business Scope 過濾

### Embedding API 呼叫

```python
async def _get_embedding(self, text: str) -> Optional[List[float]]:
    """呼叫 Embedding API 將文字轉換為向量"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            self.embedding_api_url,  # http://embedding-api:5000/api/v1/embeddings
            json={"text": text}
        )
        data = response.json()
        return data.get('embedding')
```

---

## 📊 資料庫 Schema

### knowledge_base 表結構

```sql
CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    intent_id INTEGER REFERENCES intents(id),
    vendor_id INTEGER REFERENCES vendors(id),
    title VARCHAR(255),
    category VARCHAR(100),
    question_summary TEXT,
    answer TEXT,
    audience VARCHAR(50),              -- 房東/租客/管理師
    keywords TEXT[],
    source_file VARCHAR(255),
    source_date DATE,
    embedding vector(1536),            ⭐ 向量欄位
    scope VARCHAR(50),                 -- global/vendor
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 向量索引（提升檢索效能）
CREATE INDEX idx_knowledge_embedding ON knowledge_base
USING ivfflat (embedding vector_cosine_ops);
```

### knowledge_import_jobs 表（建議新增）

```sql
CREATE TABLE knowledge_import_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id INTEGER REFERENCES vendors(id),
    file_name VARCHAR(255),
    file_path VARCHAR(500),
    status VARCHAR(50),                -- processing/completed/failed
    import_mode VARCHAR(50),           -- append/replace/merge
    enable_deduplication BOOLEAN,

    -- 進度追蹤
    total_items INTEGER,
    processed_items INTEGER,
    imported_count INTEGER,
    skipped_count INTEGER,
    error_count INTEGER,

    -- 時間戳
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- 錯誤資訊
    error_message TEXT
);
```

---

## 🔧 整合方案建議

### 問題分析

**當前狀態**:
1. ✅ 前端介面完整（4 步驟向導、檔案上傳、輪詢機制）
2. ⚠️ 後端 API 是骨架實作（TODO 註解表示需整合）
3. ✅ 知識提取腳本存在但是獨立的命令行工具
4. ❌ 前後端未整合

**核心問題**:
- `knowledge_import.py:100` 有 TODO 註解要整合 `extract_knowledge_and_tests.py`
- 但 `extract_knowledge_and_tests.py` 是設計用於處理 LINE 聊天記錄的腳本
- 前端上傳的可能是 Excel、PDF 或 TXT 檔案，不一定是 LINE 格式

### 建議整合方案

#### 方案 A: 重構為通用匯入服務

**步驟**:

1. **建立統一的知識匯入服務**

```python
# rag-orchestrator/services/knowledge_import_service.py

class KnowledgeImportService:
    """統一的知識匯入服務"""

    async def process_import_job(
        self,
        job_id: str,
        file_path: str,
        file_type: str,  # 'excel' | 'pdf' | 'txt' | 'line_chat'
        vendor_id: Optional[int],
        import_mode: str,
        enable_deduplication: bool
    ):
        """處理知識匯入作業"""

        # 1. 根據檔案類型選擇解析器
        if file_type == 'excel':
            parser = ExcelKnowledgeParser()
        elif file_type == 'line_chat':
            parser = LineKnowledgeParser()
        elif file_type == 'pdf':
            parser = PDFKnowledgeParser()
        else:
            parser = TextKnowledgeParser()

        # 2. 解析檔案
        knowledge_list = await parser.parse(file_path)

        # 3. LLM 處理（問題生成、分類等）
        processed = await self.process_with_llm(knowledge_list)

        # 4. 生成向量
        embedded = await self.generate_embeddings(processed)

        # 5. 去重（如果啟用）
        if enable_deduplication:
            embedded = await self.deduplicate(embedded)

        # 6. 匯入資料庫
        result = await self.import_to_database(
            embedded,
            vendor_id=vendor_id,
            import_mode=import_mode
        )

        # 7. 更新作業狀態
        await self.update_job_status(job_id, 'completed', result)
```

2. **實作各種檔案解析器**

```python
class ExcelKnowledgeParser:
    async def parse(self, file_path: str) -> List[Dict]:
        """解析 Excel 檔案"""
        df = pd.read_excel(file_path)
        # 解析邏輯...
        return knowledge_list

class LineKnowledgeParser:
    """重用 extract_knowledge_and_tests.py 的邏輯"""
    async def parse(self, file_path: str) -> List[Dict]:
        extractor = LineKnowledgeExtractor()
        messages = extractor.parse_line_chat(file_path)
        qa_pairs, _ = extractor.extract_qa_pairs_and_tests(messages, file_path)
        return qa_pairs

class PDFKnowledgeParser:
    async def parse(self, file_path: str) -> List[Dict]:
        """解析 PDF 檔案（使用 PyPDF2 或 pdfplumber）"""
        # PDF 解析邏輯...
        pass
```

3. **更新後端 API**

```python
# knowledge_import.py

@router.post("/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    vendor_id: Optional[int] = Form(None),
    import_mode: str = Form("append"),
    enable_deduplication: bool = Form(True),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    # 1. 儲存檔案
    job_id = str(uuid.uuid4())
    file_path = await save_uploaded_file(file, job_id)

    # 2. 偵測檔案類型
    file_type = detect_file_type(file.filename, file.content_type)

    # 3. 建立作業記錄
    await create_import_job(
        job_id=job_id,
        vendor_id=vendor_id,
        file_name=file.filename,
        file_path=file_path,
        import_mode=import_mode
    )

    # 4. 啟動背景處理
    service = KnowledgeImportService(db_pool=request.app.state.db_pool)
    background_tasks.add_task(
        service.process_import_job,
        job_id=job_id,
        file_path=file_path,
        file_type=file_type,
        vendor_id=vendor_id,
        import_mode=import_mode,
        enable_deduplication=enable_deduplication
    )

    return {"job_id": job_id, "status": "processing"}
```

4. **實作作業狀態追蹤**

```python
# 使用 Redis 或 PostgreSQL 儲存作業狀態

async def update_job_progress(job_id: str, current: int, total: int):
    """更新作業進度"""
    await redis.hset(f"import_job:{job_id}", {
        "current": current,
        "total": total,
        "percentage": int(current / total * 100),
        "updated_at": datetime.now().isoformat()
    })

async def get_job_status(job_id: str) -> Dict:
    """取得作業狀態（供前端輪詢）"""
    job_data = await redis.hgetall(f"import_job:{job_id}")
    return job_data
```

#### 方案 B: 簡化版 - 僅支援 Excel

**適用場景**: 如果只需要支援 Excel 檔案匯入

**步驟**:
1. 直接整合 `import_excel_to_kb.py` 的邏輯到 `knowledge_import.py`
2. 移除 LINE 聊天記錄相關功能
3. 簡化檔案類型判斷

---

## 🎯 完整資料流程

### 標準匯入流程

```
┌──────────────────────────────────────────────────────────────┐
│ 1. 使用者上傳檔案                                              │
│    → 前端: KnowledgeImportView.vue                            │
│    → File: customer_qa.xlsx (50 條 QA)                       │
└────────────┬─────────────────────────────────────────────────┘
             │
             │ HTTP POST /knowledge-import/upload
             ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. 後端接收檔案並建立作業                                       │
│    → API: knowledge_import.py                                │
│    → 生成 job_id: "a1b2c3d4-..."                             │
│    → 儲存檔案到臨時目錄                                         │
│    → 返回 job_id 給前端                                       │
└────────────┬─────────────────────────────────────────────────┘
             │
             │ 啟動背景任務
             ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. 背景處理 - 檔案解析                                         │
│    → 讀取 Excel: 50 行資料                                    │
│    → 解析欄位: 問題、答案、分類、對象                           │
│    → 過濾無效資料: 剩餘 45 條                                  │
└────────────┬─────────────────────────────────────────────────┘
             │
             │ 更新進度: 10%
             ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. LLM 處理 - 問題生成                                         │
│    → 對每條答案生成問題摘要                                     │
│    → OpenAI API: gpt-4o-mini                                 │
│    → 生成 45 個問題摘要                                        │
└────────────┬─────────────────────────────────────────────────┘
             │
             │ 更新進度: 40%
             ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. 向量生成                                                   │
│    → OpenAI Embeddings API                                   │
│    → Model: text-embedding-3-small                           │
│    → 為每個 QA 生成 1536 維向量                               │
│    → 生成 45 個向量                                           │
└────────────┬─────────────────────────────────────────────────┘
             │
             │ 更新進度: 70%
             ↓
┌──────────────────────────────────────────────────────────────┐
│ 6. 去重檢查（如果啟用）                                         │
│    → 查詢資料庫是否存在相同的 question + answer                 │
│    → 跳過 5 條重複項                                          │
│    → 剩餘 40 條待匯入                                         │
└────────────┬─────────────────────────────────────────────────┘
             │
             │ 更新進度: 85%
             ↓
┌──────────────────────────────────────────────────────────────┐
│ 7. 資料庫匯入                                                 │
│    → INSERT INTO knowledge_base                              │
│    → 批次插入 40 條知識                                        │
│    → 包含 title, category, answer, audience, keywords,       │
│             embedding, vendor_id                             │
└────────────┬─────────────────────────────────────────────────┘
             │
             │ 更新進度: 100%
             ↓
┌──────────────────────────────────────────────────────────────┐
│ 8. 作業完成                                                   │
│    → 更新作業狀態: completed                                  │
│    → 記錄結果:                                                │
│      - imported: 40                                          │
│      - skipped: 5 (重複)                                     │
│      - errors: 0                                             │
│    → 清理臨時檔案                                             │
└────────────┬─────────────────────────────────────────────────┘
             │
             │ 前端輪詢取得結果
             ↓
┌──────────────────────────────────────────────────────────────┐
│ 9. 前端顯示完成結果                                            │
│    → Step 4: 完成頁面                                         │
│    → 顯示匯入統計                                             │
│    → 提供操作按鈕（重新匯入、查看知識庫）                       │
└──────────────────────────────────────────────────────────────┘
```

### 輪詢機制時序圖

```
前端                   後端 API                背景任務
 │                      │                       │
 │  POST /upload        │                       │
 ├─────────────────────>│                       │
 │                      │  啟動背景任務           │
 │                      ├──────────────────────>│
 │  {job_id: "a1b2"}    │                       │
 │<─────────────────────┤                       │
 │                      │                       │ 開始處理...
 │  GET /jobs/a1b2      │                       │
 ├─────────────────────>│  查詢 Redis/DB        │
 │                      ├──────────────────────>│
 │  {status: "processing", progress: 10%}      │
 │<─────────────────────┤                       │
 │                      │                       │
 │  (等待 2 秒)          │                       │
 │                      │                       │
 │  GET /jobs/a1b2      │                       │
 ├─────────────────────>│                       │
 │  {status: "processing", progress: 40%}      │
 │<─────────────────────┤                       │
 │                      │                       │
 │  (等待 2 秒)          │                       │
 │                      │                       │ 處理完成
 │  GET /jobs/a1b2      │                       │
 ├─────────────────────>│                       │
 │  {status: "completed", result: {...}}       │
 │<─────────────────────┤                       │
 │                      │                       │
 │  停止輪詢             │                       │
 │  顯示完成頁面         │                       │
```

---

## 🔒 Business Scope 整合

### Audience 過濾機制

**知識匯入時**:
```python
# 匯入時指定對象（audience）
knowledge = {
    "question_summary": "如何退租？",
    "answer": "退租流程說明...",
    "audience": "租客",  # 或 "房東", "管理師", "general"
    ...
}
```

**檢索時**:
```python
# 根據 user_role 決定 business_scope
user_role = "customer"  # 或 "staff"
business_scope = "external" if user_role == "customer" else "internal"

# 根據 business_scope 取得允許的 audiences
allowed_audiences = BUSINESS_SCOPE_AUDIENCE_MAPPING[business_scope]['allowed_audiences']
# external: ['租客', '房東', 'tenant', 'general', ...]
# internal: ['管理師', '系統管理員', 'general', ...]

# 檢索時過濾
results = await rag_engine.search(
    query="如何退租？",
    allowed_audiences=allowed_audiences
)
```

---

## 📈 效能考量

### 1. OpenAI API 成本

**每次匯入 100 條知識的成本估算**:

| 項目 | 模型 | 用量 | 單價 | 成本 |
|------|------|------|------|------|
| 問題生成 | gpt-4o-mini | 100 * 200 tokens | $0.15/1M input | $0.003 |
| 向量生成 | text-embedding-3-small | 100 * 50 tokens | $0.02/1M tokens | $0.0001 |
| **總計** | | | | **$0.0031** |

**優化建議**:
- 批次處理：一次處理多個項目
- 快取機制：相同內容不重複生成向量
- 去重在前：先去重再生成向量，避免浪費

### 2. 資料庫向量檢索效能

**索引優化**:
```sql
-- 使用 IVFFlat 索引（pgvector extension）
CREATE INDEX idx_knowledge_embedding ON knowledge_base
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- lists 參數根據資料量調整

-- 對於 10,000 條知識：lists = 100
-- 對於 100,000 條知識：lists = 200
-- 對於 1,000,000 條知識：lists = 500
```

**查詢優化**:
- 設定合理的 `similarity_threshold`（避免返回過多結果）
- 限制 `limit` 數量（預設 5 條）
- 使用意圖過濾減少檢索範圍

### 3. 背景任務處理

**當前實作**: FastAPI BackgroundTasks（適用於輕量任務）

**建議升級**:
- **Celery** - 適合大量背景任務
- **RQ (Redis Queue)** - 輕量級任務佇列
- **AWS SQS + Lambda** - 雲端方案

**範例**: Celery 整合

```python
# celery_app.py
from celery import Celery

celery_app = Celery(
    'knowledge_import',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

@celery_app.task
def process_import_job(job_id, file_path, ...):
    """使用 Celery 處理匯入作業"""
    service = KnowledgeImportService()
    return service.process_import_job(job_id, file_path, ...)
```

---

## 🧪 測試建議

### 1. 單元測試

```python
# tests/test_knowledge_import.py

async def test_excel_parser():
    """測試 Excel 解析器"""
    parser = ExcelKnowledgeParser()
    result = await parser.parse("test_data/sample.xlsx")

    assert len(result) > 0
    assert 'question_summary' in result[0]
    assert 'answer' in result[0]

async def test_embedding_generation():
    """測試向量生成"""
    service = KnowledgeImportService()
    text = "如何退租？退租需要提前一個月通知..."

    embedding = await service.generate_embedding(text)

    assert len(embedding) == 1536
    assert all(isinstance(x, float) for x in embedding)

async def test_deduplication():
    """測試去重功能"""
    service = KnowledgeImportService()

    # 新增一條知識
    knowledge = {
        "question_summary": "測試問題",
        "answer": "測試答案"
    }
    await service.import_to_database([knowledge])

    # 嘗試新增相同的知識（應該被跳過）
    result = await service.deduplicate([knowledge])
    assert len(result) == 0
```

### 2. 整合測試

```python
async def test_full_import_workflow():
    """測試完整匯入流程"""
    # 1. 上傳檔案
    response = await client.post(
        "/api/v1/knowledge-import/upload",
        files={"file": open("test_data/sample.xlsx", "rb")},
        data={"vendor_id": 1, "import_mode": "append"}
    )

    job_id = response.json()["job_id"]

    # 2. 輪詢作業狀態
    for _ in range(30):  # 最多等待 60 秒
        response = await client.get(f"/api/v1/knowledge-import/jobs/{job_id}")
        status = response.json()["status"]

        if status == "completed":
            break

        await asyncio.sleep(2)

    # 3. 驗證結果
    assert status == "completed"
    result = response.json()["result"]
    assert result["imported"] > 0
```

### 3. 效能測試

```python
async def test_large_file_import():
    """測試大檔案匯入效能"""
    # 生成包含 1000 條知識的測試檔案
    test_file = generate_test_excel(num_rows=1000)

    start_time = time.time()

    response = await client.post(
        "/api/v1/knowledge-import/upload",
        files={"file": test_file}
    )

    # 等待完成
    job_id = response.json()["job_id"]
    await wait_for_job_completion(job_id)

    elapsed_time = time.time() - start_time

    # 驗證效能（應在 5 分鐘內完成）
    assert elapsed_time < 300
```

---

## 🚨 錯誤處理

### 常見錯誤情境

#### 1. 檔案格式錯誤

```python
class InvalidFileFormatError(Exception):
    """檔案格式錯誤"""
    pass

async def validate_file(file: UploadFile):
    """驗證檔案格式"""
    # 檢查副檔名
    if not file.filename.endswith(('.xlsx', '.xls', '.txt', '.pdf')):
        raise InvalidFileFormatError(
            f"不支援的檔案格式: {file.filename}. "
            "支援的格式: Excel (.xlsx, .xls), TXT (.txt), PDF (.pdf)"
        )

    # 檢查檔案大小（50MB 限制）
    if file.size > 50 * 1024 * 1024:
        raise InvalidFileFormatError("檔案大小超過 50MB 限制")

    # 檢查檔案內容（簡單驗證）
    content = await file.read(1024)
    await file.seek(0)  # 重置檔案指針

    if not content:
        raise InvalidFileFormatError("檔案為空")
```

#### 2. OpenAI API 錯誤

```python
async def generate_embedding_with_retry(text: str, max_retries: int = 3):
    """生成向量（含重試機制）"""
    for attempt in range(max_retries):
        try:
            response = openai.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding

        except openai.RateLimitError:
            # Rate limit - 等待後重試
            wait_time = 2 ** attempt  # 指數退避
            await asyncio.sleep(wait_time)

        except openai.APIError as e:
            # API 錯誤
            if attempt == max_retries - 1:
                raise Exception(f"OpenAI API 錯誤: {e}")
            await asyncio.sleep(1)

    raise Exception("生成向量失敗：超過最大重試次數")
```

#### 3. 資料庫錯誤

```python
async def import_knowledge_with_transaction(
    knowledge_list: List[Dict],
    conn: asyncpg.Connection
):
    """使用事務匯入知識（確保原子性）"""
    async with conn.transaction():
        try:
            for knowledge in knowledge_list:
                await conn.execute("""
                    INSERT INTO knowledge_base (...)
                    VALUES (...)
                """, ...)

        except asyncpg.UniqueViolationError:
            # 處理重複鍵錯誤
            print(f"知識已存在，跳過: {knowledge['question_summary']}")

        except Exception as e:
            # 其他錯誤：回滾事務
            print(f"匯入失敗，回滾事務: {e}")
            raise
```

---

## 📝 待辦事項與改進建議

### 🔴 高優先級（核心功能）

1. **實作完整的知識匯入服務**
   - [ ] 建立 `KnowledgeImportService` 類別
   - [ ] 整合檔案解析器（Excel, PDF, TXT）
   - [ ] 整合向量生成邏輯
   - [ ] 實作去重機制
   - [ ] 實作進度追蹤

2. **完成後端 API**
   - [ ] 實作 `POST /upload` 完整邏輯
   - [ ] 實作 `GET /jobs/{id}` 狀態查詢
   - [ ] 實作 `POST /preview` 檔案預覽
   - [ ] 建立作業狀態儲存（Redis 或 PostgreSQL）

3. **資料庫 Schema**
   - [ ] 建立 `knowledge_import_jobs` 表
   - [ ] 建立向量索引優化查詢效能
   - [ ] 建立必要的外鍵約束

### 🟡 中優先級（使用者體驗）

4. **前端優化**
   - [ ] 實作檔案預覽功能（Step 2）
   - [ ] 改進進度顯示（顯示當前處理階段）
   - [ ] 增加錯誤詳情展示
   - [ ] 支援取消匯入作業

5. **錯誤處理**
   - [ ] 統一錯誤回應格式
   - [ ] 實作重試機制
   - [ ] 記錄詳細錯誤日誌
   - [ ] 提供錯誤修正建議

### 🟢 低優先級（進階功能）

6. **效能優化**
   - [ ] 升級到 Celery 進行背景處理
   - [ ] 實作批次處理優化
   - [ ] 增加向量生成快取
   - [ ] 資料庫連接池優化

7. **功能擴展**
   - [ ] 支援更多檔案格式（JSON, CSV, Word）
   - [ ] 支援從 URL 匯入
   - [ ] 支援 API 匯入（Webhook）
   - [ ] 匯入排程功能
   - [ ] 匯入模板下載

8. **監控與分析**
   - [ ] 匯入統計儀表板
   - [ ] API 成本追蹤
   - [ ] 效能監控
   - [ ] 匯入歷史分析

---

## 🔗 相關文件連結

### 程式碼檔案

- **前端**: `knowledge-admin/frontend/src/views/KnowledgeImportView.vue` (883 行)
- **後端 API**: `rag-orchestrator/routers/knowledge_import.py` (306 行)
- **知識提取**: `scripts/knowledge_extraction/extract_knowledge_and_tests.py` (339 行)
- **Excel 匯入**: `scripts/knowledge_extraction/import_excel_to_kb.py` (357 行)
- **RAG 引擎**: `rag-orchestrator/services/rag_engine.py` (413 行)
- **Business Scope 工具**: `rag-orchestrator/services/business_scope_utils.py`

### 相關文件

- [Business Scope 重構總結](BUSINESS_SCOPE_REFACTORING_SUMMARY.md)
- [Business Scope 詳細說明](../architecture/BUSINESS_SCOPE_REFACTORING.md)
- [認證與業務範圍整合](../2025-Q4/architecture/AUTH_AND_BUSINESS_SCOPE.md)

---

## 📊 總結

### 現狀評估

| 模組 | 狀態 | 完整度 | 備註 |
|------|------|--------|------|
| 前端介面 | ✅ 完成 | 100% | 4 步驟向導完整實作 |
| 後端 API 骨架 | ⚠️ 部分完成 | 40% | 端點存在但核心邏輯待實作 |
| 檔案解析器 | ⚠️ 部分完成 | 30% | LINE/Excel 解析器存在但未整合 |
| 向量生成 | ✅ 完成 | 100% | 已有完整實作範例 |
| 資料庫匯入 | ✅ 完成 | 100% | 已有完整實作範例 |
| 進度追蹤 | ❌ 未實作 | 0% | 需要建立作業狀態管理機制 |
| 錯誤處理 | ⚠️ 基本實作 | 30% | 需要更完善的錯誤處理 |

### 核心問題

1. **前後端未整合**: 前端已完成，但後端只有骨架，兩者未連接
2. **知識提取邏輯獨立**: `extract_knowledge_and_tests.py` 是獨立的命令行工具，未整合到 API
3. **作業狀態管理缺失**: 沒有實作作業狀態的持久化儲存和查詢機制
4. **檔案類型支援不明確**: 前端支援多種格式，但後端只有 LINE 格式的解析器

### 建議下一步

**Phase 1: 核心整合（1-2 週）**
1. 建立 `KnowledgeImportService` 統一服務
2. 實作 Excel 檔案解析器
3. 整合向量生成邏輯
4. 實作作業狀態管理（使用 Redis 或 PostgreSQL）
5. 連接前後端，完成基本匯入流程

**Phase 2: 功能完善（1 週）**
6. 實作去重機制
7. 完善錯誤處理
8. 增加檔案預覽功能
9. 優化進度顯示

**Phase 3: 效能與擴展（1 週）**
10. 升級到 Celery 或其他任務佇列
11. 優化資料庫向量索引
12. 增加更多檔案格式支援
13. 實作監控與統計

---

**文檔版本**: v1.0
**最後更新**: 2025-10-12
**作者**: Claude Code
**狀態**: ✅ 完整調查完成

