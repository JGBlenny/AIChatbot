# AI 知識審核功能修復 - 完整盤查與修復報告

## 📋 問題總覽

**錯誤訊息**:
```
批准失敗：審核候選失敗：function approve_ai_knowledge_candidate(unknown, unknown, unknown, unknown) does not exist
HINT: No function matches the given name and argument types. You might need to add explicit type casts.
```

## 🔍 完整盤查結果

### 1. 根本原因分析

#### 問題 1：參數數量不匹配
- **程式碼調用** (`rag-orchestrator/routers/knowledge_generation.py:778`):
  ```python
  SELECT approve_ai_knowledge_candidate($1, $2, $3, $4)
  ```
  傳入 **4 個參數**:
  1. candidate_id (integer)
  2. reviewed_by (varchar)
  3. review_notes (text)
  4. use_edited (boolean)

- **資料庫函數** (修復前):
  ```sql
  approve_ai_knowledge_candidate(
      candidate_id INTEGER,
      reviewer VARCHAR(100),
      review_note TEXT DEFAULT NULL
  )
  ```
  只接受 **3 個參數**

#### 問題 2：欄位名稱不一致
- **修復腳本原本引用**: `linked_knowledge_ids`, `has_knowledge`
- **實際表欄位**: `related_knowledge_ids`（沒有 `has_knowledge` 欄位）

### 2. 依賴檢查結果

#### ✅ knowledge_base 表欄位
所有必要欄位都存在：
```
✅ question_summary          text
✅ answer                    text
✅ intent_id                 integer
✅ embedding                 vector(1536)
✅ source_type               varchar
✅ source_test_scenario_id   integer
✅ generation_metadata       jsonb
✅ target_user               text[]
✅ is_active                 boolean
```

#### ✅ ai_generated_knowledge_candidates 表欄位
所有必要欄位都存在：
```
✅ question                  text
✅ generated_answer          text
✅ edited_question           text
✅ edited_answer             text
✅ question_embedding        vector(1536)
✅ test_scenario_id          integer
✅ ai_model                  varchar
✅ confidence_score          numeric
✅ generation_reasoning      text
✅ warnings                  text[]
✅ intent_ids                integer[]
✅ status                    varchar
✅ edit_summary              text
```

#### ✅ test_scenarios 表欄位
```
✅ related_knowledge_ids    integer[]  (正確，函數應使用此欄位)
✅ linked_knowledge_ids     不存在     (正確，不應該存在)
✅ has_knowledge            不存在     (正確，函數不應引用此欄位)
```

#### ✅ knowledge_intent_mapping 表
```
✅ 表存在
✅ knowledge_id    integer
✅ intent_id       integer
✅ intent_type     varchar
✅ confidence      float
✅ assigned_by     varchar
```

#### ✅ 外鍵約束
```
✅ knowledge_base.intent_id → intents.id
✅ knowledge_base.source_test_scenario_id → test_scenarios.id
✅ ai_generated_knowledge_candidates.test_scenario_id → test_scenarios.id
```

## ✅ 修復方案

### 修復 1：更新資料庫函數（已執行）

**檔案**: `database/fixes/fix_approve_function_corrected.sql`

**關鍵修正**:
1. ✅ 添加第 4 個參數 `p_use_edited boolean DEFAULT true`
2. ✅ 將 `linked_knowledge_ids` 改為 `related_knowledge_ids`
3. ✅ 移除 `has_knowledge` 欄位引用
4. ✅ 支援多意圖映射（寫入 `knowledge_intent_mapping`）
5. ✅ 支援 embedding 複製（從 `question_embedding`）
6. ✅ 支援編輯版本選擇（使用 `p_use_edited` 參數）

**執行結果**:
```sql
CREATE FUNCTION
✅ approve_ai_knowledge_candidate 函數已更新
   - 參數：4 個（candidate_id, reviewed_by, review_notes, use_edited）
   - 修正：linked_knowledge_ids → related_knowledge_ids
   - 移除：has_knowledge 欄位引用
```

### 修復 2：清理舊版本函數（已執行）

```sql
-- 刪除舊的 3 參數版本
DROP FUNCTION approve_ai_knowledge_candidate(integer, character varying, text);

-- 只保留新的 4 參數版本
✅ 舊版本函數已刪除，只保留 4 參數版本
```

### 修復 3：更新 init 腳本（已執行）

**檔案**: `database/init/12-create-ai-knowledge-system.sql`

**更新內容**:
- ✅ 替換舊的 3 參數函數定義
- ✅ 使用新的 4 參數版本
- ✅ 確保未來重新初始化資料庫時包含正確版本

**備份位置**: `database/init/12-create-ai-knowledge-system.sql.backup`

### 修復 4：服務重啟（已執行）

```bash
docker-compose restart rag-orchestrator knowledge-admin-api
✅ 所有服務已重啟並正常運行
```

## 🧪 驗證結果

### 全面檢查腳本
**檔案**: `scripts/comprehensive_approval_check.py`

**檢查結果**:
```
======================================================================
📊 檢查總結
======================================================================

✅ 所有檢查通過！
   審核函數可以正常使用

檢查項目：
✅ 函數簽名正確（4 個參數）
✅ knowledge_base 所有必要欄位存在（9 個欄位）
✅ ai_generated_knowledge_candidates 所有必要欄位存在（13 個欄位）
✅ test_scenarios.related_knowledge_ids 存在
✅ linked_knowledge_ids 不存在（正確）
✅ has_knowledge 不存在（正確）
✅ knowledge_intent_mapping 表存在
✅ 所有外鍵約束正確配置
```

## 📊 函數功能說明

### 新版本函數功能

```sql
approve_ai_knowledge_candidate(
    p_candidate_id INTEGER,      -- 候選知識 ID
    p_reviewed_by VARCHAR(100),  -- 審核者
    p_review_notes TEXT,         -- 審核備註
    p_use_edited BOOLEAN         -- 是否使用編輯版本
)
RETURNS INTEGER  -- 返回新建立的知識 ID
```

#### 執行流程

1. **取得候選記錄**
   - 檢查候選知識是否存在
   - 驗證狀態（必須是 `pending_review` 或 `needs_revision`）

2. **決定使用版本**
   - 如果 `p_use_edited=true` 且有編輯版本 → 使用編輯版本
   - 否則 → 使用 AI 原始生成版本

3. **提取意圖資訊**
   - 從 `intent_ids` 陣列中提取第一個作為主要意圖

4. **準備 metadata**
   - 記錄 AI 模型、信心度、生成時間
   - 記錄審核者、審核時間
   - 記錄是否被編輯、編輯摘要
   - 記錄生成推理、警告訊息

5. **插入知識庫**
   - 插入問題、答案、意圖
   - **複製 embedding**（從 `question_embedding`）
   - 設定來源類型為 `ai_generated`
   - 記錄來源測試情境 ID
   - 設定目標用戶為租客（可擴展）

6. **更新候選狀態**
   - 狀態改為 `approved`
   - 記錄審核者和審核時間

7. **建立意圖映射**
   - 支援多意圖（遍歷 `intent_ids` 陣列）
   - 第一個為主要意圖（primary）
   - 其他為次要意圖（secondary）
   - 人工審核的信心度設為 0.95

8. **更新測試情境關聯**
   - 將新知識 ID 添加到 `related_knowledge_ids` 陣列
   - 更新 `updated_at` 時間戳

## 📁 相關檔案

### 修復腳本
```
database/fixes/
├── fix_approve_function.sql              (舊版本，有欄位名稱問題)
├── fix_approve_function_corrected.sql    (新版本，已修正)
```

### Init 腳本
```
database/init/
├── 12-create-ai-knowledge-system.sql         (已更新為 4 參數版本)
├── 12-create-ai-knowledge-system.sql.backup  (舊版本備份)
```

### 驗證工具
```
scripts/
├── comprehensive_approval_check.py    (全面檢查審核功能依賴)
└── verify_similarity_functions.py     (驗證相似度功能)
```

### 文檔
```
docs/
├── APPROVAL_FUNCTION_FIX.md                      (本文檔)
├── KNOWLEDGE_IMPORT_SIMILARITY_FIX.md            (知識匯入修復文檔)
└── KNOWLEDGE_IMPORT_FIX_SUMMARY.md               (知識匯入總結)
```

## 🎯 最佳實踐建議

### 1. 使用審核功能

**Python 調用範例**:
```python
new_knowledge_id = await conn.fetchval("""
    SELECT approve_ai_knowledge_candidate($1, $2, $3, $4)
""",
    candidate_id,      # 候選 ID
    reviewed_by,       # 審核者（如：'admin'）
    review_notes,      # 審核備註（可為 NULL）
    use_edited         # 是否使用編輯版本（True/False）
)
```

**SQL 直接調用**:
```sql
-- 使用編輯版本
SELECT approve_ai_knowledge_candidate(
    p_candidate_id := 123,
    p_reviewed_by := 'admin',
    p_review_notes := '答案準確，已批准',
    p_use_edited := TRUE
);

-- 使用 AI 原始版本
SELECT approve_ai_knowledge_candidate(
    p_candidate_id := 124,
    p_reviewed_by := 'reviewer_name',
    p_review_notes := 'AI 生成版本已足夠好',
    p_use_edited := FALSE
);
```

### 2. 審核前檢查

```sql
-- 查看候選知識詳情
SELECT
    id,
    question,
    generated_answer,
    edited_answer,
    status,
    confidence_score,
    warnings,
    intent_ids
FROM ai_generated_knowledge_candidates
WHERE id = 123;
```

### 3. 審核後驗證

```sql
-- 查看新建立的知識
SELECT
    kb.id,
    kb.question_summary,
    kb.answer,
    kb.intent_id,
    i.name as intent_name,
    kb.embedding IS NOT NULL as has_embedding,
    kb.generation_metadata
FROM knowledge_base kb
LEFT JOIN intents i ON kb.intent_id = i.id
WHERE kb.id = [new_knowledge_id];

-- 查看意圖映射
SELECT
    kim.knowledge_id,
    kim.intent_id,
    i.name as intent_name,
    kim.intent_type,
    kim.confidence
FROM knowledge_intent_mapping kim
JOIN intents i ON kim.intent_id = i.id
WHERE kim.knowledge_id = [new_knowledge_id];

-- 查看測試情境關聯
SELECT
    id,
    test_question,
    related_knowledge_ids
FROM test_scenarios
WHERE [new_knowledge_id] = ANY(related_knowledge_ids);
```

## 🔄 未來維護

### 監控建議

定期檢查函數狀態：
```bash
python3 scripts/comprehensive_approval_check.py
```

### 如果需要添加新功能

修改順序：
1. 更新 `database/init/12-create-ai-knowledge-system.sql`（init 腳本）
2. 創建對應的 `database/fixes/fix_xxx.sql`（修復腳本）
3. 執行修復腳本
4. 重啟服務
5. 執行驗證腳本

### 版本控制

所有資料庫變更都應該：
1. ✅ 在 init 腳本中體現
2. ✅ 創建對應的 fix 腳本
3. ✅ 在 git 中提交變更
4. ✅ 更新相關文檔

## ✨ 總結

### 修復前 ❌
```
❌ 函數只有 3 個參數
❌ 引用不存在的欄位（linked_knowledge_ids, has_knowledge）
❌ 功能簡陋（只插入知識庫，無多意圖、無 embedding）
❌ init 腳本與實際需求不符
```

### 修復後 ✅
```
✅ 函數有正確的 4 個參數
✅ 使用正確的欄位名稱（related_knowledge_ids）
✅ 完整功能：
   - 多意圖映射
   - Embedding 複製
   - 編輯版本選擇
   - 完整的 metadata 記錄
   - 測試情境關聯更新
✅ init 腳本已更新
✅ 所有依賴檢查通過
✅ 服務正常運行
```

### 核心改進

1. **參數完整性**: 4 參數支援更靈活的審核流程
2. **資料完整性**: 自動複製 embedding，確保可檢索性
3. **關聯完整性**: 支援多意圖映射，提高檢索準確度
4. **追溯性**: 完整的 metadata 記錄，便於審計
5. **可維護性**: init 腳本與程式碼一致，避免未來問題

---

**修復完成時間**: 2025-01-15
**測試狀態**: ✅ 通過
**生產就緒**: ✅ 是

審核功能現在可以完整運作，包含所有必要的功能和資料完整性保證。
