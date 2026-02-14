# 📌 知識優先級系統

## 概述

知識優先級系統允許管理員標記重要知識，使其在 RAG 檢索時獲得固定的相似度加成，從而提升排名。這有助於確保關鍵知識（如常見問題、重要公告）優先呈現給用戶。

## 系統設計

### 核心機制

- **優先級值**: 0（未啟用）或 1（已啟用）
- **加成方式**: 固定加成 +0.15
- **應用時機**: RAG 檢索時，在相似度計算後應用

### 公式

```sql
boosted_similarity = base_similarity +
  CASE WHEN priority > 0 THEN 0.15 ELSE 0 END
```

其中：
- `base_similarity`: 原始向量相似度（含意圖加成）
- `PRIORITY_BOOST`: 環境變數配置的加成值（預設 0.15）

## 使用方式

### 1. 單筆知識設定優先級

**位置**: http://localhost:8087/knowledge

**操作步驟**:
1. 點擊知識列表中的「編輯」按鈕
2. 在編輯表單中找到「優先級加成」區塊
3. 勾選「啟用優先級加成」checkbox
4. 儲存更改

**效果**:
- ✅ 相似度 +0.15
- ✨ 表格中顯示為「☑」（已啟用）
- ⬜ 表格中顯示為「☐」（未啟用）

### 2. 批量匯入時統一設定優先級

**位置**: http://localhost:8087/knowledge-import

**操作步驟**:
1. 上傳 CSV / Excel 檔案
2. 在 Step 2 勾選「直接加入知識庫（跳過審核）」
3. 勾選「統一啟用優先級」checkbox
4. 確認匯入

**效果**:
- 所有匯入的知識 priority 自動設為 1
- 在 RAG 檢索時自動獲得 +0.15 加成

## 配置參數

### 環境變數

**檔案**: `.env` 或 `docker-compose.yml`

```bash
# 優先級固定加成值（建議範圍：0.10-0.20）
PRIORITY_BOOST=0.15
```

**調整建議**:
- **0.10**: 輕微提升，適合微調排名
- **0.15**: 預設值，平衡排名影響
- **0.20**: 強力提升，確保優先顯示

### 數據庫欄位

**表**: `knowledge_base`

```sql
priority INTEGER DEFAULT 0  -- 0=未啟用，1=已啟用
```

## 效果驗證

### 測試案例

假設有以下知識：

| ID | question | priority | 原始相似度 | 加成後相似度 |
|----|----------|----------|-----------|-------------|
| A  | 客服電話 | 0        | 0.75      | 0.75        |
| B  | 客服專線 | 1        | 0.65      | **0.80**    |

**查詢**: "客服電話"

**排序**:
- **未啟用優先級**: A (0.75) > B (0.65)
- **啟用優先級**: B (0.80) > A (0.75) ✨

### SQL 驗證查詢

```sql
SELECT
    kb.id,
    kb.question_summary,
    kb.priority,
    (1 - (kb.embedding <=> $1::vector)) as raw_similarity,
    (1 - (kb.embedding <=> $1::vector)) +
        CASE WHEN kb.priority > 0 THEN 0.15 ELSE 0 END as boosted_similarity
FROM knowledge_base kb
WHERE kb.question_summary LIKE '%關鍵字%'
ORDER BY boosted_similarity DESC;
```

## 架構演進

### 歷史版本

**v1.0 - 分級制（已廢棄）**:
- priority 範圍: 0-10
- 加成方式: 乘法 `base * (1 + priority * 0.15)`
- 最大加成: 150% (priority=10)

**v2.0 - 開關制（當前版本）**:
- priority 範圍: 0-1
- 加成方式: 加法 `base + (priority > 0 ? 0.15 : 0)`
- 固定加成: +0.15

### 設計理由

**為什麼從分級制改為開關制？**

1. **簡化操作**: Checkbox 比數字輸入更直觀
2. **可預測性**: 固定加成（+0.15）比百分比乘法更容易理解
3. **避免過度調整**: 防止管理員設定過高的 priority 值（如 10）導致排名失真
4. **一致性**: 所有啟用優先級的知識獲得相同的競爭優勢

## API 文檔

### 更新知識優先級

```http
PUT /api/knowledge/{knowledge_id}
Content-Type: application/json

{
  "question_summary": "客服專線是多少",
  "content": "請撥打 02-1234-5678",
  "keywords": ["客服", "電話"],
  "priority": 1  // 0=未啟用，1=已啟用
}
```

### 批量匯入（含優先級）

```http
POST /api/v1/knowledge-import/upload
Content-Type: multipart/form-data

file: @/path/to/knowledge.csv
skip_review: true
default_priority: 1  // 統一設定為 1
```

## 最佳實踐

### 適合啟用優先級的知識

- ✅ **常見問題（FAQ）**: 客服電話、營業時間、繳費方式
- ✅ **重要公告**: 系統維護通知、政策變更
- ✅ **高頻查詢**: 根據日誌分析，用戶最常詢問的問題
- ✅ **業務核心**: 關鍵業務流程、必須知曉的規則

### 不建議啟用優先級的知識

- ❌ **專業術語**: 僅特定情況使用，不需優先展示
- ❌ **例外情況**: 罕見案例，語意匹配度已足夠
- ❌ **過時資訊**: 即將淘汰的知識

### 優先級比例建議

建議啟用優先級的知識比例：**10-20%**

- 過少（<5%）: 優先級效果不明顯
- 適中（10-20%）: 平衡用戶體驗與檢索準確度
- 過多（>30%）: 失去優先級的意義，所有知識都被提升

## 監控與調整

### 監控指標

1. **優先級知識命中率**:
   ```sql
   SELECT
       COUNT(*) FILTER (WHERE priority > 0) as priority_count,
       COUNT(*) as total_count,
       ROUND(100.0 * COUNT(*) FILTER (WHERE priority > 0) / COUNT(*), 2) as priority_rate
   FROM knowledge_base;
   ```

2. **優先級知識檢索比例**:
   透過 RAG 日誌分析，統計優先級知識在結果中的佔比

### 調整策略

**如果優先級知識過少命中**:
- 增加 `PRIORITY_BOOST` 值（如 0.15 → 0.20）
- 擴大優先級知識範圍

**如果優先級知識過度命中**:
- 降低 `PRIORITY_BOOST` 值（如 0.15 → 0.10）
- 縮小優先級知識範圍，僅保留最關鍵的

## 相關配置

### RAG 引擎配置

**檔案**: `rag-orchestrator/services/rag_engine.py`

```python
self.priority_boost = float(os.getenv("PRIORITY_BOOST", "0.15"))
```

**檔案**: `docker-compose.yml`

```yaml
rag-orchestrator:
  environment:
    PRIORITY_BOOST: ${PRIORITY_BOOST:-0.15}
```

## 測試與驗證

### 測試腳本

完整的測試驗證已實現，位於：
- `/tmp/test_rag_priority_boost.py` - RAG 加成效果驗證
- `/tmp/test_priority_api.sh` - API 功能測試

### 測試結果

所有測試通過 ✅:
- ✅ 數據庫 priority 值正確設定
- ✅ RAG 公式正確應用 +0.15 加成
- ✅ 前端 API 完整支持 priority 欄位
- ✅ 批量匯入統一優先級功能正常

## 故障排除

### 問題 1: 優先級未生效

**症狀**: 設定 priority=1 但檢索排名未改變

**排查步驟**:
1. 確認環境變數 `PRIORITY_BOOST` 已設定
2. 重啟 `rag-orchestrator` 服務
3. 檢查 SQL 查詢是否包含 priority 欄位

**解決方案**:
```bash
docker-compose restart rag-orchestrator
```

### 問題 2: 批量匯入優先級未設定

**症狀**: 勾選「統一啟用優先級」但匯入後 priority=0

**排查步驟**:
1. 確認前端傳送 `default_priority=1`
2. 檢查後端 `knowledge_import_service.py` 是否接收參數
3. 驗證數據庫 INSERT 語句使用 `default_priority`

**解決方案**:
更新後端代碼，確保參數正確傳遞（已修復）

## 版本歷史

- **2025-11-17**: v2.0 - 從分級制改為開關制，添加批量匯入優先級功能
- **2025-11-16**: v1.0 - 初始版本，支援 0-10 分級制（已廢棄）

## 參考資料

- [RAG 引擎實現](../../rag-orchestrator/services/rag_engine.py#L117)
- [知識管理 API](../../knowledge-admin/backend/app.py#L73)
- [知識匯入服務](../../rag-orchestrator/services/knowledge_import_service.py#L1157)
- [環境變數配置](../../.env.example#L75)
