# 回測系統快速開始指南

> 本指南幫助您快速上手 AIChatbot 回測系統與知識完善迴圈

**最後更新**：2026-03-27

---

## 📚 目錄

1. [系統概述](#系統概述)
2. [快速執行回測](#快速執行回測)
3. [知識完善迴圈](#知識完善迴圈)
4. [核心概念](#核心概念)
5. [進階主題](#進階主題)
6. [常見問題](#常見問題)

---

## 系統概述

### 什麼是回測系統？

回測系統用於驗證 RAG 知識庫的回答品質，透過測試情境（test scenarios）批量測試 AI 客服的回答準確度。

### 核心功能

1. **回測執行** - 批量測試 AI 回答品質
2. **知識完善迴圈** - 自動發現知識缺口並生成新知識
3. **評估指標** - confidence_score、semantic_overlap 等指標
4. **測試覆蓋率分析** - 多維度測試覆蓋率統計

---

## 快速執行回測

### 前置需求

1. **環境設定**
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

2. **Docker 容器運行中**
   ```bash
   docker ps | grep aichatbot-rag-orchestrator
   ```

### 執行步驟

#### 方法 1：50 題快速驗證（推薦新手）

```bash
# 從專案根目錄執行
./scripts/testing/run_50_verification.sh
```

**特點**：
- 測試 50 題
- 執行時間：約 10-15 分鐘
- 適用於快速驗證知識庫變更

#### 方法 2：500 題標準驗證

```bash
./scripts/testing/run_500_verification.sh
```

**特點**：
- 測試 500 題
- 執行時間：約 60-90 分鐘
- 適用於標準測試覆蓋率

#### 方法 3：3000 題完整驗證

```bash
./scripts/testing/run_3000_verification.sh
```

**特點**：
- 測試 3000 題
- 執行時間：約 90-120 分鐘
- 適用於全面評估知識庫品質

### 查看結果

```bash
# 查詢最新的 Loop ID
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c \
  "SELECT id FROM knowledge_completion_loops ORDER BY id DESC LIMIT 1;"

# 查看迴圈執行結果
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT * FROM knowledge_completion_loops ORDER BY id DESC LIMIT 1;"
```

---

## 知識完善迴圈

### 什麼是知識完善迴圈？

知識完善迴圈是一個自動化流程，透過回測發現知識缺口，使用 AI 生成新知識，經人工審核後補充到知識庫。

### 完整流程（8 步驟）

```
1. 執行回測
   ↓
2. 分析失敗案例
   ↓
3. AI 智能分類（OpenAI）
   ↓
4. 按類別分離
   ↓
5. 分別聚類
   ↓
6. 生成知識（SOP/一般知識）
   ↓
7. 人工審核
   ↓
8. 驗證改善效果
```

### 執行迴圈

```bash
# 進入 rag-orchestrator 容器
docker exec -it aichatbot-rag-orchestrator bash

# 執行知識完善迴圈
cd /app
python3 services/knowledge_completion_loop/run_first_loop.py
```

### 審核生成的知識

1. **登入管理後台**
   - URL: `http://localhost:8087`

2. **審核知識**
   - 進入「審核中心」
   - 查看待審核知識
   - 批准或拒絕生成的知識

3. **執行下一次迭代**
   - 批准知識後，系統會自動同步到正式知識庫
   - 執行新的回測驗證改善效果

---

## 核心概念

### 1. 評估指標

#### confidence_score (0-1)

**計算公式**：
```
confidence_score =
  max_similarity * 0.7 +      // 最高相似度（70% 權重）
  (result_count / 5) * 0.2 +  // 結果數量（20% 權重）
  keyword_match_rate * 0.1    // 關鍵字匹配（10% 權重）
```

**等級判定**：
- **0.85+**: 高信心度 - 答案很可能正確且完整
- **0.70-0.84**: 中信心度 - 答案基本正確，可能不完整
- **0.60-0.69**: 低信心度 - 答案相關性弱，需人工檢查
- **< 0.60**: 極低信心度 - 答案很可能不正確

#### semantic_overlap (0-1)

**用途**：檢測答非所問

**閾值**：
- **< 0.4**: 答非所問（直接失敗）
- **0.4-0.6**: 弱相關（需配合 confidence_score 判斷）
- **> 0.6**: 強相關

### 2. 通過標準

測試案例通過需滿足以下條件之一：

```python
# 第 1 層：基礎檢查
if answer == "" or "沒有找到資訊" in answer:
    → 失敗

# 第 2 層：語義攔截
elif semantic_overlap < 0.4:
    → 失敗（答非所問）

# 第 3 層：綜合判定
elif confidence_score >= 0.85:
    → 通過
elif confidence_score >= 0.70 and semantic_overlap >= 0.5:
    → 通過
elif confidence_score >= 0.60 and semantic_overlap >= 0.6:
    → 通過
else:
    → 失敗
```

### 3. 知識類型

系統支援三種知識類型：

1. **sop_knowledge** - SOP 流程知識（操作步驟）
2. **form_fill** - 表單填寫知識
3. **system_config** - 系統配置知識

---

## 進階主題

### 自定義測試規模

```bash
# 設定環境變數
export VENDOR_ID=2
export BATCH_SIZE=100
export LOOP_NAME="自定義回測"

# 執行回測
docker exec -e VENDOR_ID=$VENDOR_ID \
  -e BATCH_SIZE=$BATCH_SIZE \
  -e LOOP_NAME="$LOOP_NAME" \
  aichatbot-rag-orchestrator \
  python3 /app/services/knowledge_completion_loop/run_first_loop.py
```

### 查看執行日誌

```bash
# 查看迴圈執行日誌
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT * FROM loop_execution_logs WHERE loop_id = <loop_id> ORDER BY created_at DESC;"
```

### 查看生成的知識

```bash
# 查看待審核知識
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT * FROM loop_generated_knowledge WHERE loop_id = <loop_id> AND status = 'pending';"
```

---

## 常見問題

### Q1: 為什麼我的回測全部失敗？

**可能原因**：
1. 知識庫為空或內容不足
2. 測試問題與知識庫內容不匹配
3. API 服務未正常運行

**解決方案**：
1. 檢查知識庫是否有內容
2. 查看測試問題是否合理
3. 確認 RAG API 正常運行（`http://localhost:8100/health`）

### Q2: 如何提高通過率？

**建議**：
1. **補充知識庫** - 增加相關知識內容
2. **豐富測試場景** - 確保測試問題有對應知識
3. **優化答案品質** - 確保知識內容包含問題關鍵字
4. **移除錯誤知識** - 刪除答非所問的知識

### Q3: 知識完善迴圈需要多長時間？

**時間估算**：
- 50 題：約 10-15 分鐘
- 500 題：約 60-90 分鐘
- 3000 題：約 90-120 分鐘

**影響因素**：
- 測試數量
- 知識生成數量
- OpenAI API 回應速度

### Q4: 如何停止正在執行的迴圈？

```bash
# 找到容器內的 Python 進程
docker exec aichatbot-rag-orchestrator ps aux | grep run_first_loop

# 停止進程
docker exec aichatbot-rag-orchestrator kill <PID>
```

### Q5: 生成的知識品質如何保證？

**品質保證機制**：
1. **AI 分類** - OpenAI GPT-4o 智能分類知識類型
2. **聚類去重** - 相似問題聚類避免重複知識
3. **人工審核** - 所有生成知識需人工批准
4. **驗證回測** - 批准後重新測試驗證效果

---

## 相關文檔

- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - 回測系統快速參考
- [KNOWLEDGE_COMPLETION_LOOP_GUIDE.md](./KNOWLEDGE_COMPLETION_LOOP_GUIDE.md) - 知識完善迴圈詳細指南
- [IMPLEMENTATION_GAPS.md](./IMPLEMENTATION_GAPS.md) - 實作缺口與待辦事項

---

## 技術支援

如遇到問題，請查看：

1. **執行日誌**
   ```bash
   docker logs aichatbot-rag-orchestrator
   ```

2. **資料庫狀態**
   ```bash
   docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin
   ```

3. **API 健康檢查**
   ```bash
   curl http://localhost:8100/health
   ```

---

**維護者**：AIChatbot Team
**最後更新**：2026-03-27
