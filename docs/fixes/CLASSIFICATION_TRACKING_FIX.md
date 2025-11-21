# 知識庫分類追蹤功能修復 - 完整盤查與修復報告

## 📋 問題總覽

**錯誤訊息**:
```
載入統計失敗：獲取統計失敗：column "needs_reclassify" does not exist
LINE 6: COUNT(CASE WHEN needs_reclassify THEN 1 ...
```

**影響功能**:
- 意圖分配頁面（KnowledgeReclassifyView）的統計資訊載入失敗
- 批次分類功能無法使用 needs_reclassify 過濾條件
- 無法標記和追蹤需要重新分類的知識

## 🔍 完整盤查結果

### 1. 根本原因分析

#### 問題：缺少分類追蹤欄位

knowledge_base 表缺少以下兩個欄位：
- `intent_classified_at` (TIMESTAMP) - 最後分類時間
- `needs_reclassify` (BOOLEAN) - 是否需要重新分類

#### 程式碼引用位置

**`rag-orchestrator/services/knowledge_classifier.py`**:
- **Line 74**: 分類時設置 `needs_reclassify = false`
  ```python
  needs_reclassify = false
  ```
- **Line 278-279**: 批次分類過濾條件
  ```python
  if filters.get('needs_reclassify'):
      where_clauses.append("needs_reclassify = true")
  ```
- **Line 460**: 整體統計查詢
  ```python
  COUNT(CASE WHEN needs_reclassify THEN 1 END) as needs_reclassify_count,
  ```
- **Line 476**: 按意圖統計查詢
  ```python
  COUNT(CASE WHEN kb.needs_reclassify THEN 1 END) as needs_reclassify_count
  ```

**`rag-orchestrator/routers/knowledge.py`**:
- **Line 45**: API 文檔中的過濾條件範例
- **Line 185-199**: 統計 API endpoint

#### 歷史原因

這些欄位定義在歸檔的 migration 腳本中：
- `docs/archive/database_migrations/05-add-knowledge-classification-tracking.sql`

該檔案在 archive 目錄，說明是歷史 migration，但從未應用到生產資料庫。

### 2. 資料庫結構檢查

#### ❌ 修復前的 knowledge_base 表

缺少欄位：
- `intent_classified_at`
- `needs_reclassify`

已有欄位：
- `intent_id` - 意圖 ID（但缺少分類時間追蹤）
- `intent_confidence` - 分類信心度
- `intent_assigned_by` - 分配方式（auto/manual）

#### ✅ 修復後的 knowledge_base 表

新增欄位：
```sql
intent_classified_at  TIMESTAMP           -- 最後分類時間
needs_reclassify      BOOLEAN DEFAULT false  -- 是否需要重新分類
```

新增索引：
```sql
idx_kb_needs_reclassify    -- 部分索引（needs_reclassify = true）
idx_kb_intent_confidence   -- 信心度索引
```

### 3. 影響範圍分析

**直接影響**:
- ✅ 意圖分配頁面統計載入（當前報錯）
- ✅ 批次分類的過濾功能
- ✅ 標記需要重新分類功能
- ✅ 分類時間追蹤

**相關 API**:
- `GET /api/v1/knowledge/stats` - 獲取分類統計
- `POST /api/v1/knowledge/classify/batch` - 批次分類（使用 needs_reclassify 過濾）
- `POST /api/v1/knowledge/mark-reclassify` - 標記需要重新分類

## ✅ 修復方案

### 修復 1：創建修復腳本（已執行）

**檔案**: `database/fixes/add_knowledge_classification_tracking.sql`

**關鍵修正**:
1. ✅ 添加 `intent_classified_at` 欄位
2. ✅ 添加 `needs_reclassify` 欄位（預設值 false）
3. ✅ 建立部分索引 `idx_kb_needs_reclassify`（只索引 needs_reclassify=true）
4. ✅ 建立 `idx_kb_intent_confidence` 索引
5. ✅ 為已有 intent_id 的知識初始化 intent_classified_at

**執行結果**:
```sql
ALTER TABLE
CREATE INDEX
CREATE INDEX
UPDATE 12

✅ 知識庫分類追蹤欄位已建立
   total_knowledge: 13
   classified_count: 12
   unclassified_count: 1
   needs_reclassify_count: 0
```

### 修復 2：更新 Init 腳本（已完成）

**檔案**: `database/init/13-add-knowledge-classification-tracking.sql`

**更新內容**:
- ✅ 創建新的 init 腳本（編號 13）
- ✅ 包含欄位定義、索引、註釋
- ✅ 初始化現有資料的 intent_classified_at
- ✅ 確保未來重新初始化資料庫時包含這些欄位

**設計考慮**:
- 使用獨立的 init 腳本，保持功能模組化
- 按照數字編號順序，確保在 knowledge_base 表創建後執行

### 修復 3：服務重啟（已執行）

```bash
docker-compose restart rag-orchestrator
✅ 服務已重啟並正常運行
```

### 修復 4：創建驗證工具（已完成）

**檔案**: `scripts/verify_classification_tracking.py`

**檢查項目**:
- ✅ 資料庫欄位存在且類型正確
- ✅ 索引已創建
- ✅ 資料完整性（已分類知識有分類時間戳）
- ✅ 統計 API 正常工作

## 🧪 驗證結果

### 全面檢查結果

```
======================================================================
📊 檢查總結
======================================================================
資料庫欄位                ✅ 通過
索引                   ✅ 通過
資料完整性                ✅ 通過
統計 API               ✅ 通過
======================================================================

✅ 所有檢查通過！分類追蹤功能可以正常使用
```

### 統計 API 測試

**請求**: `GET http://localhost:8100/api/v1/knowledge/stats`

**回應**:
```json
{
  "overall": {
    "total_knowledge": 13,
    "classified_count": 12,
    "unclassified_count": 1,
    "needs_reclassify_count": 0,
    "avg_confidence": null,
    "low_confidence_count": 0
  },
  "by_intent": [
    {
      "id": 1,
      "name": "帳務查詢",
      "knowledge_count": 4,
      "needs_reclassify_count": 0
    },
    ...
  ]
}
```

✅ API 成功返回統計資訊，包含 `needs_reclassify_count`

### 資料完整性驗證

```sql
總知識數:           13
已分類知識數:       12
缺少分類時間戳:     0    ← 所有已分類知識都有 intent_classified_at
需要重新分類:       0    ← 所有知識的 needs_reclassify = false
```

## 📊 功能說明

### 新增欄位用途

#### 1. intent_classified_at (TIMESTAMP)

**用途**: 記錄知識最後一次被分類的時間

**使用場景**:
- 追蹤知識的分類歷史
- 批次分類時過濾「N 天前分類的知識」
- 統計分類效率和覆蓋率

**更新時機**:
- 調用 `classify_single_knowledge()` 時自動設置為當前時間
- 批次分類 `classify_batch()` 時更新
- 人工分配意圖時更新

#### 2. needs_reclassify (BOOLEAN)

**用途**: 標記知識是否需要重新分類

**使用場景**:
- 意圖定義更新後，標記相關知識需要重新分類
- 批次分類時只處理需要重新分類的知識
- 統計待處理的知識數量

**標記方式**:
```python
# 標記特定意圖的所有知識
classifier.mark_for_reclassify(intent_ids=[1, 2, 3])

# 標記所有知識
classifier.mark_for_reclassify(all_knowledge=True)
```

**清除方式**:
- 分類成功後自動設置為 `false`

### 索引優化

#### idx_kb_needs_reclassify (部分索引)

```sql
CREATE INDEX idx_kb_needs_reclassify ON knowledge_base(needs_reclassify)
WHERE needs_reclassify = true;
```

**優化原理**:
- 只索引 `needs_reclassify = true` 的記錄
- 減少索引大小（大部分知識不需要重新分類）
- 提高過濾查詢效率

**適用查詢**:
```sql
SELECT * FROM knowledge_base WHERE needs_reclassify = true;
```

#### idx_kb_intent_confidence

```sql
CREATE INDEX idx_kb_intent_confidence ON knowledge_base(intent_confidence);
```

**適用查詢**:
```sql
-- 查詢低信心度知識
SELECT * FROM knowledge_base WHERE intent_confidence < 0.7;

-- 統計平均信心度
SELECT AVG(intent_confidence) FROM knowledge_base;
```

## 🎯 使用指南

### 1. 獲取分類統計

```python
# Python (使用 API)
import requests
stats = requests.get('http://localhost:8100/api/v1/knowledge/stats').json()

print(f"總知識數: {stats['overall']['total_knowledge']}")
print(f"需要重新分類: {stats['overall']['needs_reclassify_count']}")
```

```sql
-- SQL (直接查詢)
SELECT
    COUNT(*) as total_knowledge,
    COUNT(intent_id) as classified_count,
    COUNT(*) - COUNT(intent_id) as unclassified_count,
    COUNT(CASE WHEN needs_reclassify THEN 1 END) as needs_reclassify_count
FROM knowledge_base;
```

### 2. 標記需要重新分類

```python
# 意圖更新後，標記相關知識需要重新分類
response = requests.post('http://localhost:8100/api/v1/knowledge/mark-reclassify', json={
    "intent_ids": [1, 2],  # 意圖 ID 列表
    "all_knowledge": False
})

# 標記所有知識
response = requests.post('http://localhost:8100/api/v1/knowledge/mark-reclassify', json={
    "all_knowledge": True
})
```

### 3. 批次分類（只處理需要重新分類的）

```python
response = requests.post('http://localhost:8100/api/v1/knowledge/classify/batch', json={
    "filters": {
        "needs_reclassify": True  # 只處理標記為需要重新分類的
    },
    "batch_size": 100,
    "dry_run": False
})
```

### 4. 查詢需要重新分類的知識

```sql
-- 查詢所有需要重新分類的知識
SELECT id, question_summary, intent_id, needs_reclassify
FROM knowledge_base
WHERE needs_reclassify = true;

-- 查詢特定意圖的需要重新分類的知識
SELECT kb.id, kb.question_summary, i.name as intent_name
FROM knowledge_base kb
LEFT JOIN intents i ON kb.intent_id = i.id
WHERE kb.needs_reclassify = true
  AND kb.intent_id = 1;
```

## 📁 相關檔案

### 修復腳本
```
database/fixes/
└── add_knowledge_classification_tracking.sql  (修復腳本)
```

### Init 腳本
```
database/init/
├── 02-create-knowledge-base.sql               (knowledge_base 主表)
├── 12-create-ai-knowledge-system.sql          (AI 知識系統)
└── 13-add-knowledge-classification-tracking.sql  (新增：分類追蹤)
```

### 驗證工具
```
scripts/
└── verify_classification_tracking.py          (全面驗證腳本)
```

### 文檔
```
docs/
├── CLASSIFICATION_TRACKING_FIX.md             (本文檔)
└── archive/
    └── database_migrations/
        └── 05-add-knowledge-classification-tracking.sql  (歷史 migration)
```

### 相關程式碼
```
rag-orchestrator/
├── services/
│   └── knowledge_classifier.py                (分類服務，4 處引用)
└── routers/
    └── knowledge.py                           (分類 API)
```

## 🔄 未來維護

### 監控建議

定期檢查分類追蹤功能狀態：
```bash
python3 scripts/verify_classification_tracking.py
```

### 如果需要添加新功能

修改順序：
1. 更新 `database/init/13-add-knowledge-classification-tracking.sql`（init 腳本）
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
❌ 缺少 intent_classified_at 欄位
❌ 缺少 needs_reclassify 欄位
❌ 意圖分配頁面統計載入失敗
❌ 無法追蹤分類時間
❌ 無法標記需要重新分類的知識
❌ 批次分類無法使用 needs_reclassify 過濾
```

### 修復後 ✅

```
✅ intent_classified_at 欄位已添加
✅ needs_reclassify 欄位已添加
✅ 部分索引優化查詢效率
✅ 意圖分配頁面正常顯示統計
✅ 可以追蹤每個知識的分類時間
✅ 可以標記和追蹤需要重新分類的知識
✅ 批次分類支援完整過濾條件
✅ Init 腳本已更新
✅ 所有依賴檢查通過
✅ 服務正常運行
```

### 核心改進

1. **功能完整性**: 從缺少分類追蹤升級為完整的分類管理系統
2. **資料追溯性**: 記錄分類時間，便於審計和優化
3. **重分類管理**: 支援標記和批次處理需要重新分類的知識
4. **查詢效率**: 部分索引優化，減少索引大小和查詢時間
5. **可維護性**: Init 腳本與程式碼保持一致

---

**修復完成時間**: 2025-01-15
**測試狀態**: ✅ 通過
**生產就緒**: ✅ 是

分類追蹤功能現在可以完整運作，意圖分配頁面的統計功能已恢復正常！
