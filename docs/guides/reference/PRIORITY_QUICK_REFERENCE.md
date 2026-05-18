# 📌 知識優先級 - 快速參考

> 5 分鐘快速上手知識優先級系統

## 什麼是知識優先級？

知識優先級讓重要知識在 RAG 檢索時獲得 **固定 +0.15 相似度加成**，提升排名優先顯示給用戶。

## 快速使用

### 方式 1: 單筆設定（已存在的知識）

1. 前往 http://localhost:8087/knowledge
2. 點擊知識的「編輯」按鈕
3. 勾選「啟用優先級加成」✅
4. 儲存

**效果**: 該知識在檢索時相似度 +0.15

### 方式 2: 批量匯入時統一設定

1. 前往 http://localhost:8087/knowledge-import
2. 上傳 CSV / Excel 檔案
3. Step 2: 勾選「直接加入知識庫（跳過審核）」
4. 勾選「統一啟用優先級」✨
5. 確認匯入

**效果**: 所有匯入的知識 priority=1，自動獲得 +0.15 加成

## 表格圖示

| 圖示 | 意義 | priority 值 |
|------|------|------------|
| ☑    | 已啟用優先級 | 1 |
| ☐    | 未啟用優先級 | 0 |

## 適用場景

### ✅ 建議啟用

- 常見問題（FAQ）
- 客服聯絡方式
- 重要公告
- 高頻查詢問題
- 關鍵業務流程

### ❌ 不建議啟用

- 專業術語
- 罕見案例
- 過時資訊
- 例外情況

## 配置調整

### 調整加成值

**檔案**: `.env`

```bash
# 預設 0.15，建議範圍 0.10-0.20
PRIORITY_BOOST=0.15
```

**調整後**:
```bash
docker-compose restart rag-orchestrator
```

### 推薦比例

啟用優先級的知識建議佔總知識的 **10-20%**

## 效果示例

### 案例：查詢「客服電話」

**無優先級**:
```
1. 如何聯絡客服 (0.75)
2. 客服專線是多少 (0.65)  ← 最相關但排第2
```

**啟用優先級**:
```
1. 客服專線是多少 (0.80) ← +0.15 加成，提升至第1
2. 如何聯絡客服 (0.75)
```

## 驗證查詢

檢查優先級知識比例：

```sql
SELECT
    COUNT(*) FILTER (WHERE priority > 0) as priority_count,
    COUNT(*) as total_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE priority > 0) / COUNT(*), 2) || '%' as priority_rate
FROM knowledge_base;
```

## 故障排除

### 問題：優先級未生效

**解決**:
```bash
# 1. 檢查環境變數
cat .env | grep PRIORITY_BOOST

# 2. 重啟服務
docker-compose restart rag-orchestrator
```

### 問題：批量匯入後 priority=0

**原因**: 未勾選「統一啟用優先級」checkbox

**解決**: 重新匯入並勾選選項，或手動編輯知識啟用優先級

## API 使用

### 更新單筆知識優先級

```bash
curl -X PUT "http://localhost:8000/api/knowledge/10" \
  -H "Content-Type: application/json" \
  -d '{
    "question_summary": "客服專線是多少",
    "content": "請撥打 02-1234-5678",
    "keywords": ["客服", "電話"],
    "priority": 1
  }'
```

### 批量匯入（含優先級）

```bash
curl -X POST "http://localhost:8100/api/v1/knowledge-import/upload" \
  -F "file=@knowledge.csv" \
  -F "skip_review=true" \
  -F "default_priority=1"
```

## 更多資訊

- 📖 [完整文檔](../../archive/2025-Q4/features/PRIORITY_SYSTEM.md)
- 📝 [變更日誌](../../archive/backtest-historical/CHANGELOG.md)
- 🏗️ [系統架構](../../README.md)

---

**提示**: 優先級系統於 2025-11-17 重構，從分級制改為開關制，更簡單易用！
