# Reranker 功能文檔

> ⚠️ **歷史文件**（2026-01-28 原始實施）。2026-04 後經過效能調校與欄位架構重構，
> **當前行為請參考**：
> - [docs/architecture/retriever-pipeline.md](../architecture/retriever-pipeline.md)（Reranker 效能調校章節）
> - [.kiro/issues/reranker-returning-zero.md](../../.kiro/issues/reranker-returning-zero.md)
>
> 本文件保留作為歷史脈絡。

## 📋 概述

Reranker（重排序）是一種二階段檢索優化技術，用於提升 SOP 和 Knowledge 檢索的準確性。通過使用 Cross-Encoder 模型重新評估候選結果，Reranker 能夠捕捉問題與答案之間的深層語義關聯，超越單純的向量相似度匹配。

**實施日期**: 2026-01-28
**狀態**: ✅ 已實施並驗證（邏輯已於 2026-04 refactor 擴充）

---

## 🎯 核心價值

### SOP Reranker
- **問題**: 向量檢索基於詞彙匹配，導致語義相近但用詞不同的 SOP 排序錯誤
- **解決方案**: 使用 Cross-Encoder 評估問題與 SOP 項目的語義相關性
- **效果**: 修正「如何取得租金發票」等錯誤匹配問題

### Knowledge Reranker
- **問題**: 初始測試準確率僅 25%（1/4）
- **解決方案**: 使用相同的 Reranker 架構優化 Knowledge 檢索
- **效果**: 準確率提升至 75%（3/4），**改進 3 倍**

---

## 🔧 技術架構

### 1. 模型選擇

**模型**: `BAAI/bge-reranker-base`
- **類型**: Cross-Encoder（交叉編碼器）
- **參數量**: 278M
- **優勢**:
  - 雙向注意力機制，能夠建模問題-答案間的交互
  - 比單純的向量相似度更準確
  - 中文支持良好

### 2. 二階段檢索流程

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: Vector Similarity Search (Recall)                  │
├─────────────────────────────────────────────────────────────┤
│ • 使用 pgvector 進行向量檢索                                  │
│ • 返回 N 個候選結果（SOP: 5個，Knowledge: 15個）              │
│ • 快速但可能不夠精準                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: Reranker (Precision)                               │
├─────────────────────────────────────────────────────────────┤
│ • 使用 Cross-Encoder 重新評估每個候選                         │
│ • 計算問題與答案的語義相關性分數                               │
│ • 混合原始分數和 Rerank 分數                                  │
│ • 重新排序並返回最終結果                                       │
└─────────────────────────────────────────────────────────────┘
```

### 3. 分數混合策略

```python
# 混合公式
final_score = original_similarity * 0.3 + rerank_score * 0.7

# 理由：
# - Rerank 分數權重較高（70%），因為其更準確
# - 保留 30% 原始分數，避免完全依賴 Rerank
# - 平衡檢索速度與準確性
```

---

## 📦 實施細節

### SOP Reranker

**文件**: `rag-orchestrator/services/vendor_sop_retriever.py`

**關鍵代碼**:
```python
# 初始化（line 30-48）
RERANKER_ENABLED = os.getenv('ENABLE_RERANKER', 'false').lower() == 'true'
if RERANKER_ENABLED:
    from sentence_transformers import CrossEncoder
    self.reranker = CrossEncoder(
        'BAAI/bge-reranker-base',
        max_length=512
    )

# 重排序方法（line 165-237）
def _apply_reranker(self, query: str, candidates: List[Dict]) -> List[Dict]:
    # 準備輸入對：[問題, SOP項目名稱 + 內容]
    pairs = [[query, f"{c['item_name']} {c['content'][:200]}"]
             for c in candidates]

    # 批次預測相關性分數
    raw_scores = self.reranker.predict(pairs, batch_size=32)

    # 歸一化到 0-1 範圍
    normalized_scores = [(score + 1) / 2 for score in raw_scores]

    # 混合分數並重新排序
    for candidate, rerank_score in zip(candidates, normalized_scores):
        candidate['rerank_score'] = rerank_score
        candidate['similarity'] = (
            candidate['original_similarity'] * 0.3 +
            rerank_score * 0.7
        )

    return sorted(candidates, key=lambda x: x['similarity'], reverse=True)
```

### Knowledge Reranker

**文件**: `rag-orchestrator/services/vendor_knowledge_retriever.py`

**關鍵代碼**:
```python
# 初始化（line 29-46）
RERANKER_ENABLED = os.getenv('ENABLE_KNOWLEDGE_RERANKER', 'false').lower() == 'true'
if RERANKER_ENABLED:
    from sentence_transformers import CrossEncoder
    self.reranker = CrossEncoder(
        'BAAI/bge-reranker-base',
        max_length=512
    )

# 重排序方法（line 163-233）
def _apply_reranker(self, query: str, candidates: List[Dict]) -> List[Dict]:
    # 準備輸入對：[問題, 知識摘要 + 答案]
    pairs = [[query, f"{c.get('question_summary', '')} {c.get('answer', '')}"]
             for c in candidates]

    # 相同的 Reranker 邏輯
    # ...（與 SOP Reranker 相同）
```

**調用位置**:
```python
# retrieve_knowledge_hybrid 方法（line 522-524）
if self.reranker_enabled and len(candidates) > 1:
    candidates = self._apply_reranker(query, candidates)
```

---

## ⚙️ 配置說明

### 環境變數

**`.env` 文件**:
```bash
# SOP Reranker
ENABLE_RERANKER=true

# Knowledge Reranker
ENABLE_KNOWLEDGE_RERANKER=true
```

**`docker-compose.yml`**:
```yaml
environment:
  ENABLE_RERANKER: ${ENABLE_RERANKER:-true}
  ENABLE_KNOWLEDGE_RERANKER: ${ENABLE_KNOWLEDGE_RERANKER:-true}
```

### 預設值
- 兩個 Reranker 預設都啟用（`true`）
- 可透過環境變數獨立控制

---

## 📊 效能評估

### SOP Reranker 效果

**典型案例**: "如何取得租金發票"

| 階段 | 排名第一 | 相似度 | Rerank 分數 | 最終分數 |
|------|---------|--------|------------|----------|
| Before Rerank | ID 1263 (錯誤) | 0.7458 | - | 0.7458 |
| After Rerank | ID 385 (正確) | 0.6673 | **0.9329** | 0.8532 |

**結論**: Rerank 分數 0.9329 成功將正確答案提升到第一位

### Knowledge Reranker 效果

#### 測試結果對比

| 指標 | Before | After | 改進幅度 |
|------|--------|-------|---------|
| 準確率 | 25% (1/4) | 75% (3/4) | **+200%** |
| 平均相似度 | 0.688 | 0.859 | +24.9% |
| 錯誤案例 | 2 | 0 | -100% |

#### 詳細測試案例

**測試案例 1**: "租金發票如何取得"
- Before: ❌ ID 1263 (租金繳納方式) - 0.7458
- After: ✅ ID 385 (發票證明) - Rerank 0.9329 → 最終 0.8532

**測試案例 2**: "每個月幾號繳租金"
- Before: ❌ ID 572 (收據相關) - 0.7442
- After: ✅ ID 511 (繳租日期) - Rerank 0.9921 → 最終 0.9130

**測試案例 3**: "押金什麼時候退還"
- Before: ✅ ID 265 - 0.7136
- After: ✅ ID 65 (更優) - Rerank 0.9973 → 最終 0.9016

**測試報告**: `/tmp/knowledge_reranker_final.log`

---

## 🚀 性能優化

### 批次處理
```python
# 批次大小設為 32，平衡速度與記憶體
raw_scores = self.reranker.predict(pairs, batch_size=32)
```

### 條件執行
```python
# 只有當候選數量 > 1 時才執行 Rerank
if self.reranker_enabled and len(candidates) > 1:
    candidates = self._apply_reranker(query, candidates)
```

### 輸入截斷
```python
# SOP: 截取前 200 字元避免超過模型限制
f"{c['item_name']} {c['content'][:200]}"

# Knowledge: 使用完整的 question_summary + answer
f"{c.get('question_summary', '')} {c.get('answer', '')}"
```

---

## 📈 監控與日誌

### Debug 日誌輸出

**SOP Reranker**:
```
🔄 [Reranker] 重排序 5 個候選結果
   排名 1: ID 385 - 想問一下，明年報稅的時候...
      原始: 0.6673, Rerank: 0.9329, 最終: 0.8532
   排名 2: ID 394 - 大概三點多，租金是...
      原始: 0.6288, Rerank: 0.8576, 最終: 0.7889
```

**Knowledge Reranker**:
```
🔄 [Knowledge Reranker] 重排序 10 個候選結果
   排名 1: ID 385 - 想問一下，明年報稅的時候...
      原始: 0.6673, Rerank: 0.9329, 最終: 0.8532
```

### 前端顯示

候選結果中會包含以下欄位：
- `original_similarity`: 原始向量相似度
- `rerank_score`: Reranker 評分（0-1）
- `similarity`: 最終混合分數
- `boosted_similarity`: 加成後的分數（含意圖加成）

---

## 🔍 故障排除

### 問題 1: Reranker 未初始化

**症狀**: 日誌中沒有 "Reranker initialized" 訊息

**原因**:
- 環境變數未設定
- `sentence-transformers` 套件未安裝
- 模型下載失敗

**解決方案**:
```bash
# 檢查環境變數
docker-compose exec rag-orchestrator env | grep RERANKER

# 安裝依賴
pip install sentence-transformers

# 手動下載模型
from sentence_transformers import CrossEncoder
model = CrossEncoder('BAAI/bge-reranker-base')
```

### 問題 2: Reranker 未執行

**症狀**: 有初始化日誌，但沒有 "🔄 [Reranker]" 日誌

**原因**:
- 候選結果數量 <= 1
- `reranker_enabled` 標記為 False

**解決方案**:
```python
# 檢查條件
print(f"Reranker enabled: {self.reranker_enabled}")
print(f"Candidates count: {len(candidates)}")
```

### 問題 3: 容器重啟後 Reranker 失效

**原因**: 環境變數未在 `docker-compose.yml` 中配置

**解決方案**:
```bash
# 強制重建容器
docker-compose up -d --force-recreate rag-orchestrator
```

---

## 📚 相關文檔

- [RAG 實施計劃](../rag-system/RAG_IMPLEMENTATION_PLAN.md)
- [系統架構](../architecture/SYSTEM_ARCHITECTURE.md)
- [Knowledge 檢索優化指南](../backtest/BACKTEST_KNOWLEDGE_OPTIMIZATION_GUIDE.md)
- [Reranker 實施完成報告](../archive/completion_reports/RERANKER_IMPLEMENTATION_COMPLETE.md)

---

## 🎯 未來優化建議

### 1. 模型升級
- 考慮使用 `bge-reranker-large` (560M 參數) 獲得更高準確度
- 評估 `bge-reranker-v2-m3` 等多語言模型

### 2. 動態閾值
- 根據 Rerank 分數動態調整相似度閾值
- 當 Rerank 分數 > 0.95 時，降低對原始相似度的要求

### 3. 性能監控
- 統計 Rerank 前後的排序變化率
- 追蹤 Rerank 對準確率的實際影響

### 4. A/B 測試
- 在生產環境中進行 A/B 測試
- 比較啟用/禁用 Reranker 的用戶滿意度

---

**最後更新**: 2026-01-28
**維護者**: AI Chatbot Team
