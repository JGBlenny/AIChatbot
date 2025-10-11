# 🎉 知識庫自動分類系統 - 完整交付

## ✅ 完成日期
2025-10-10

## 📋 系統概述

知識庫自動分類系統是意圖管理系統的擴展，解決了以下核心問題：

### 問題背景
- 有 2 萬筆知識，已經用意圖 A 分類，但後續修改或新增意圖時，原先的分類可能不準確
- 需要一個靈活的系統來：
  1. 自動為新知識分類
  2. 批次重新分類現有知識
  3. 根據條件（信心度、時間等）選擇性重新分類
  4. 控制成本（避免不必要的 OpenAI API 呼叫）

---

## 🎯 核心功能

### Phase 1: 基礎自動分類
✅ 新增知識時自動分配意圖
✅ 記錄分類信心度和時間
✅ 統計分類狀況

### Phase 2: 批次重新分類
✅ 過濾條件支援：
  - 意圖範圍（特定意圖）
  - 信心度條件（< 0.7）
  - 時間範圍（N 天前）
  - 分類來源（auto/manual）
  - 需要重新分類標記
✅ 預覽模式（不實際更新）
✅ 批次大小控制

### Phase 3: 意圖更新時自動處理
✅ 編輯意圖時提供重新分類選項
✅ 三種模式：
  - none: 不重新分類
  - low_confidence: 只重新分類低信心度 (<0.7)
  - all: 重新分類所有相關知識
✅ 顯示重新分類結果

---

## 🏗️ 架構設計

```
知識庫自動分類系統
├── 資料庫層
│   ├── knowledge_base 表擴展
│   │   ├── intent_id (外鍵到 intents)
│   │   ├── intent_confidence (分類信心度)
│   │   ├── intent_assigned_by (auto/manual)
│   │   ├── intent_classified_at (分類時間)
│   │   └── needs_reclassify (是否需要重新分類)
│   └── 索引優化
│
├── 後端服務層 (RAG Orchestrator)
│   ├── KnowledgeClassifier 服務
│   │   ├── classify_single_knowledge() - 分類單一知識
│   │   ├── classify_batch() - 批次分類
│   │   ├── mark_for_reclassify() - 標記需要重新分類
│   │   └── get_classification_stats() - 統計資訊
│   │
│   ├── Knowledge API Router
│   │   ├── POST /api/v1/knowledge/classify - 分類單一知識
│   │   ├── POST /api/v1/knowledge/classify/batch - 批次分類
│   │   ├── POST /api/v1/knowledge/mark-reclassify - 標記重新分類
│   │   ├── GET /api/v1/knowledge/stats - 統計資訊
│   │   └── POST /api/v1/knowledge/reload - 重新載入意圖
│   │
│   └── Intents API 擴展
│       └── PUT /api/v1/intents/{id} - 支援重新分類參數
│
└── 前端界面層
    ├── 知識分類頁面 (KnowledgeReclassifyView.vue)
    │   ├── 統計卡片（總數、已分類、未分類等）
    │   ├── 重新分類設定（過濾條件）
    │   ├── 預覽功能（成本估算）
    │   ├── 批次執行
    │   └── 結果顯示
    │
    └── 意圖管理頁面擴展 (IntentsView.vue)
        └── 編輯意圖時的重新分類選項
```

---

## 🗂️ 檔案清單

### 資料庫遷移
```
/database/migrations/05-add-knowledge-classification-tracking.sql
```

### 後端服務
```
/rag-orchestrator/services/knowledge_classifier.py    (新增)
/rag-orchestrator/routers/knowledge.py                (新增)
/rag-orchestrator/routers/intents.py                  (修改)
/rag-orchestrator/app.py                              (修改)
```

### 前端頁面
```
/knowledge-admin/frontend/src/views/KnowledgeReclassifyView.vue  (新增)
/knowledge-admin/frontend/src/views/IntentsView.vue              (修改)
/knowledge-admin/frontend/src/router.js                          (修改)
/knowledge-admin/frontend/src/App.vue                            (修改)
```

---

## 📖 使用指南

### 1. 查看知識分類統計

訪問：http://localhost:8080/knowledge-reclassify

統計資訊包含：
- 總知識數
- 已分類數量
- 未分類數量
- 需要重新分類數量
- 低信心度數量 (<0.7)
- 平均信心度

### 2. 批次重新分類知識

#### 步驟 1: 設定過濾條件

```
意圖範圍:        可多選特定意圖，或留空表示全部
信心度條件:      全部 / 低信心度 (<0.7) / 自訂閾值
時間範圍:        所有時間 / 7天前 / 30天前 / 90天前
分類來源:        全部 / 僅自動分類 / 僅手動分類
批次大小:        建議 50-200
```

#### 步驟 2: 預覽結果

點擊「🔍 預覽結果」，系統會顯示：
- 符合條件的知識數量
- 預估批次數
- 預估 API 成本
- 預估處理時間

#### 步驟 3: 執行重新分類

確認預覽結果後，點擊「🚀 開始重新分類」

處理完成後會顯示：
- 總處理數
- 成功數量
- 失敗數量
- Unclear 數量（無法分類）

### 3. 編輯意圖時重新分類

#### 在意圖管理頁面

1. 點擊意圖的「✏️」編輯按鈕
2. 修改意圖配置（名稱、關鍵字、描述等）
3. 在「🔄 知識庫重新分類」區塊：
   - 勾選「更新後重新分類知識庫」
   - 選擇重新分類模式：
     - **不重新分類**: 保持現狀
     - **只重新分類低信心度**: 只處理 confidence < 0.7 的知識
     - **重新分類所有知識**: 處理此意圖的所有知識（⚠️ 會消耗較多 API）
4. 點擊「💾 儲存」

系統會顯示重新分類結果：
```
✅ 意圖已更新！

📊 重新分類完成:
處理: 123 筆
成功: 118 筆
```

---

## 🔧 API 參考

### 知識分類 API

#### 分類單一知識
```http
POST /api/v1/knowledge/classify
Content-Type: application/json

{
  "knowledge_id": 1,
  "question_summary": "如何退租？",
  "answer": "退租流程說明...",
  "assigned_by": "auto"
}
```

**回應**：
```json
{
  "knowledge_id": 1,
  "classified": true,
  "intent_id": 5,
  "intent_name": "退租流程",
  "intent_type": "knowledge",
  "confidence": 0.85,
  "keywords": ["退租", "解約", "流程"]
}
```

#### 批次分類
```http
POST /api/v1/knowledge/classify/batch
Content-Type: application/json

{
  "filters": {
    "intent_ids": [1, 2],
    "max_confidence": 0.7,
    "older_than_days": 30,
    "needs_reclassify": true
  },
  "batch_size": 100,
  "dry_run": false
}
```

**回應**：
```json
{
  "total_processed": 100,
  "success_count": 95,
  "failed_count": 2,
  "unclear_count": 3,
  "details": [...]
}
```

#### 標記需要重新分類
```http
POST /api/v1/knowledge/mark-reclassify
Content-Type: application/json

{
  "intent_ids": [1, 2, 3],
  "all_knowledge": false
}
```

**回應**：
```json
{
  "success": true,
  "affected_count": 234,
  "message": "已標記 234 筆知識需要重新分類"
}
```

#### 統計資訊
```http
GET /api/v1/knowledge/stats
```

**回應**：
```json
{
  "overall": {
    "total_knowledge": 20000,
    "classified_count": 18500,
    "unclassified_count": 1500,
    "needs_reclassify_count": 234,
    "avg_confidence": 0.82,
    "low_confidence_count": 450
  },
  "by_intent": [
    {
      "id": 1,
      "name": "退租流程",
      "type": "knowledge",
      "knowledge_count": 1200,
      "avg_confidence": 0.85,
      "needs_reclassify_count": 15
    },
    ...
  ]
}
```

### 意圖更新 API 擴展

```http
PUT /api/v1/intents/{id}
Content-Type: application/json

{
  "name": "退租流程",
  "keywords": ["退租", "解約", "搬離", "新關鍵字"],
  "reclassify_knowledge": true,
  "reclassify_mode": "low_confidence"
}
```

**回應**：
```json
{
  "message": "意圖已更新",
  "intent_id": 1,
  "reclassify_result": {
    "mode": "low_confidence",
    "processed": 50,
    "success": 48
  }
}
```

---

## 🧪 測試流程

### 測試 1: 查看知識分類統計

```bash
# 開啟知識分類頁面
open http://localhost:8080/knowledge-reclassify

# 使用 API 查看統計
curl http://localhost:8100/api/v1/knowledge/stats | jq
```

**預期結果**：
- 看到完整的統計卡片
- 按意圖統計表格正確顯示

### 測試 2: 預覽批次分類

在知識分類頁面：
1. 選擇過濾條件（例如：信心度 < 0.7）
2. 點擊「🔍 預覽結果」
3. 確認顯示預估資訊

**預期結果**：
```
符合條件的知識: 450 筆
預估批次數: 5
預估 API 成本: ~$0.90 USD
預估處理時間: ~45 分鐘
```

### 測試 3: 執行批次分類

1. 在預覽後點擊「🚀 開始重新分類」
2. 確認執行
3. 等待處理完成

**預期結果**：
```
✅ 重新分類完成！
成功: 442
失敗: 3
Unclear: 5
```

### 測試 4: 編輯意圖時重新分類

1. 訪問 http://localhost:8080/intents
2. 點擊任一意圖的「✏️」
3. 修改關鍵字（例如：新增一個關鍵字）
4. 勾選「更新後重新分類知識庫」
5. 選擇「只重新分類低信心度」
6. 點擊「💾 儲存」

**預期結果**：
```
✅ 意圖已更新！

📊 重新分類完成:
處理: 15 筆
成功: 14 筆
```

---

## 💡 最佳實踐

### 1. 分類策略

**新增知識**：
- 自動分類（系統會自動處理）
- 信心度 > 0.7 才分配意圖
- 低於 0.7 的標記為需要重新分類

**批次重新分類**：
- 定期（每週）檢查低信心度知識
- 意圖大幅修改後，重新分類該意圖的所有知識
- 使用預覽模式確認影響範圍

**意圖更新**：
- 小幅調整（新增1-2個關鍵字）：使用「低信心度」模式
- 大幅修改（改變描述或多個關鍵字）：使用「全部」模式
- 不確定時：使用「標記重新分類」，稍後批次處理

### 2. 成本控制

**估算公式**：
```
API 成本 ≈ 知識數量 × $0.002 USD
處理時間 ≈ 知識數量 / 10 分鐘
```

**節省成本**：
- 使用過濾條件只處理必要的知識
- 定期清理需要重新分類的標記
- 批次大小設為 100-200（平衡速度和穩定性）

### 3. 信心度管理

**信心度分級**：
- **0.8 - 1.0**: 高信心度，可靠分類
- **0.7 - 0.8**: 中等信心度，可接受
- **< 0.7**: 低信心度，需要檢視

**處理策略**：
- 高信心度：保持不動
- 中等信心度：定期檢視（每月）
- 低信心度：立即處理或標記重新分類

---

## 📊 系統監控

### 關鍵指標

**分類完整度**：
```
分類率 = 已分類數量 / 總知識數量 × 100%
目標: > 95%
```

**分類品質**：
```
高品質率 = (信心度 > 0.8 的數量) / 已分類數量 × 100%
目標: > 80%
```

**需維護數量**：
```
維護率 = 需要重新分類數量 / 總知識數量 × 100%
目標: < 5%
```

### 監控查詢

```sql
-- 查看分類統計
SELECT
    COUNT(*) as total,
    COUNT(intent_id) as classified,
    COUNT(CASE WHEN intent_confidence < 0.7 THEN 1 END) as low_confidence,
    COUNT(CASE WHEN needs_reclassify THEN 1 END) as needs_reclassify,
    AVG(intent_confidence) as avg_confidence
FROM knowledge_base;

-- 查看各意圖的知識分布
SELECT
    i.name,
    COUNT(kb.id) as knowledge_count,
    AVG(kb.intent_confidence) as avg_confidence
FROM intents i
LEFT JOIN knowledge_base kb ON i.id = kb.intent_id
WHERE i.is_enabled = true
GROUP BY i.id, i.name
ORDER BY knowledge_count DESC;
```

---

## 🚨 故障排除

### 問題 1: 分類速度慢

**原因**: 批次大小過大或網路延遲
**解決**:
- 減少批次大小（50-100）
- 檢查 OpenAI API 連線狀態

### 問題 2: 分類結果不準確

**原因**: 意圖配置不佳或關鍵字不足
**解決**:
- 檢視意圖的關鍵字和描述
- 增加更具體的關鍵字
- 調整信心度閾值

### 問題 3: API 成本過高

**原因**: 重複分類或批次範圍過大
**解決**:
- 使用過濾條件精確控制範圍
- 使用預覽模式確認影響
- 避免對同一批知識重複執行

---

## 🎓 進階功能

### 自訂分類邏輯

如需修改分類邏輯，編輯：
```python
# /rag-orchestrator/services/knowledge_classifier.py

class KnowledgeClassifier:
    def classify_single_knowledge(self, ...):
        # 修改分類邏輯
        pass
```

### 批次處理優化

如需處理超大批次（>10000），建議：
1. 使用 Celery 後台任務
2. 實作進度追蹤
3. 支援暫停/恢復

### 自動維護排程

建議設定定期任務：
```bash
# 每週日凌晨 2 點處理低信心度知識
0 2 * * 0 curl -X POST http://localhost:8100/api/v1/knowledge/classify/batch \
  -H "Content-Type: application/json" \
  -d '{"filters": {"max_confidence": 0.7}, "batch_size": 100}'
```

---

## ✅ 驗證清單

部署後請確認：

- [x] 資料庫遷移成功執行
- [x] 知識分類頁面可訪問
- [x] 統計資訊正確顯示
- [x] 預覽功能正常
- [x] 批次分類可執行
- [x] 意圖編輯時重新分類選項顯示
- [x] API 端點正常回應
- [x] 前端容器正常運行
- [x] 後端容器正常運行

---

## 📚 相關文檔

- [意圖管理系統總覽](/docs/INTENT_MANAGEMENT_COMPLETE.md)
- [Phase B 完整報告](/docs/intent_management_phase_b_complete.md)
- [前端使用指南](/docs/frontend_usage_guide.md)

---

**交付狀態**: ✅ 完整實作
**系統版本**: 2.0.0
**完成度**: 100%

🎉 **知識庫自動分類系統已完整實作並可立即使用！**
