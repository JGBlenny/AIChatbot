# 知識完善迴圈 - 執行指南

## 重要提醒
**不要重複創建腳本！所有需要的腳本已經存在於代碼庫中。**

---

## 現有腳本位置

### 1. 主執行腳本
```
/app/services/knowledge_completion_loop/run_first_loop.py
```

**用途**: 執行知識完善迴圈的第一輪（50題回測 + AI生成知識）

**功能**:
- 執行 50 題回測
- 分析知識缺口
- 使用 GapClassifier 智能分類和聚類
- 生成知識（一般知識 + SOP）
- 結果存入 `loop_generated_knowledge` 表等待審核

### 2. 清理審核資料腳本
```
/tmp/clear_pending_knowledge.py
```

**用途**: 清理所有待審核的知識資料

---

## 標準執行流程

### 步驟 1: 清理舊的待審核資料（如需要）

```bash
docker cp /tmp/clear_pending_knowledge.py aichatbot-rag-orchestrator:/tmp/
docker exec -e DB_HOST=postgres aichatbot-rag-orchestrator python3 /tmp/clear_pending_knowledge.py
```

### 步驟 2: 執行知識完善迴圈

#### Vendor 1 (預設)
```bash
docker exec aichatbot-rag-orchestrator bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"
```

#### Vendor 2
```bash
docker exec -e VENDOR_ID=2 aichatbot-rag-orchestrator bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"
```

#### 其他 Vendor
```bash
docker exec -e VENDOR_ID=<vendor_id> aichatbot-rag-orchestrator bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"
```

#### 後台執行（推薦）
```bash
docker exec -e VENDOR_ID=2 aichatbot-rag-orchestrator bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py" 2>&1 | tee /tmp/vendor2_backtest.log &
```

### 步驟 3: 監控執行進度

```bash
# 查看日誌
tail -f /tmp/vendor2_backtest.log

# 或查看最後 50 行
tail -50 /tmp/vendor2_backtest.log
```

### 步驟 4: 查看生成的知識

#### 透過 API 查詢
```bash
curl -s http://localhost:8100/api/v1/loop-knowledge/pending | python3 -m json.tool
```

#### 透過前端審核
訪問: http://localhost:3000/review
切換到「迴圈知識審核」tab

---

## 環境變數配置

### 必需環境變數
- `OPENAI_API_KEY`: OpenAI API 金鑰（容器內已設定）

### 可選環境變數
- `VENDOR_ID`: 業者 ID（預設: 1）
- `DB_HOST`: 資料庫主機（預設: postgres）
- `DB_PORT`: 資料庫端口（預設: 5432）
- `DB_NAME`: 資料庫名稱（預設: aichatbot_admin）
- `DB_USER`: 資料庫使用者（預設: aichatbot）
- `DB_PASSWORD`: 資料庫密碼（預設: aichatbot_password）
- `RAG_API_URL`: RAG API 基礎 URL（預設: http://localhost:8100）

---

## 迴圈配置參數

在 `run_first_loop.py` 中的配置（第 81-86 行）：

```python
config = LoopConfig(
    batch_size=50,              # 每批次測試題數
    target_pass_rate=0.85,      # 目標通過率 85%
    max_iterations=10,          # 最大迭代次數
    action_type_mode="ai_assisted",  # AI 輔助判斷回應類型
)
```

---

## 重要資料表

### 1. `loop_generated_knowledge`
存放 AI 生成的待審核知識

**欄位**:
- `id`: 知識 ID
- `loop_id`: 迴圈 ID
- `iteration`: 迭代次數
- `question`: 問題
- `answer`: 答案
- `knowledge_type`: 知識類型（null=一般知識, 'sop'=SOP）
- `status`: 狀態（'pending'=待審核, 'approved'=已通過, 'rejected'=已拒絕）
- `sop_config`: SOP 配置（JSON）

### 2. `knowledge_completion_loops`
存放迴圈執行記錄

### 3. `vendor_sop_items`
存放已審核通過的 SOP

---

## 常見問題排查

### Q1: 執行時出現 `'GapClassifier' object has no attribute 'select_representative_gaps'`

**原因**: coordinator.py 中調用了不存在的方法

**解決方案**: 已修復（coordinator.py:912），使用 `get_clusters_for_generation()` 方法

**驗證**:
```bash
docker exec aichatbot-rag-orchestrator grep -n "get_clusters_for_generation" /app/services/knowledge_completion_loop/coordinator.py
```

應該看到第 912 行使用此方法。

### Q2: Vue 前端顯示 `this.$set is not a function`

**原因**: Vue 3 不支援 `$set` 方法

**解決方案**: 已修復，使用直接屬性賦值

**文件**: `LoopKnowledgeReviewTab.vue`

### Q3: 如何確認容器內的腳本是最新的？

```bash
# 如果修改了本地文件，需要重新部署
docker cp /Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop/coordinator.py \
  aichatbot-rag-orchestrator:/app/services/knowledge_completion_loop/coordinator.py
```

---

## 工作流程圖

```
1. 啟動迴圈
   ↓
2. 執行回測（50題）
   ↓
3. 分析知識缺口
   ↓
4. GapClassifier 智能分類
   - SOP 知識
   - API 查詢（不生成）
   - 表單填寫
   - 系統配置
   ↓
5. 聚類合併相似問題
   ↓
6. 路由分發
   ↓
7a. 生成一般知識 ──┐
7b. 生成 SOP ───────┤
   ↓                │
8. 存入 loop_generated_knowledge（status='pending'）
   ↓
9. 前端人工審核
   ↓
10. 審核通過後同步到對應表
    - 一般知識 → knowledge_base
    - SOP → vendor_sop_items
```

---

## API 端點

### 查看待審核知識
```
GET /api/v1/loop-knowledge/pending
```

### 查看單筆知識
```
GET /api/v1/loop-knowledge/{knowledge_id}
```

### 審核知識
```
POST /api/v1/loop-knowledge/{knowledge_id}/review
```

**Request Body**:
```json
{
  "action": "approve",  // 或 "reject"
  "question": "修改後的問題",
  "answer": "修改後的答案",
  "keywords": ["關鍵字1", "關鍵字2"],
  "vendor_id": 1,
  "category_id": 1,
  "group_id": 1
}
```

---

## 前端審核介面

### 路徑
```
/review
```

### Tab
- **迴圈知識審核**: 審核 AI 生成的一般知識和 SOP

### 預填邏輯
- SOP 的 `vendor_id`, `category_id`, `group_id` 會從 `sop_config` 自動預填
- 用戶只需確認或修改

---

## 重要修復記錄

### 2026-03-24
1. ✅ 修復 GapClassifier 方法名稱錯誤
   - 文件: `coordinator.py:912`
   - 從 `select_representative_gaps()` 改為 `get_clusters_for_generation()`

2. ✅ 修復 Vue 3 兼容性問題
   - 文件: `LoopKnowledgeReviewTab.vue`
   - 移除 `this.$set()` 和 `this.$delete()`，改用直接賦值

3. ✅ 修復 trigger_mode 資料庫約束
   - 文件: `knowledge_generation.py`
   - 添加 'keyword' → 'auto' 映射

---

## 執行檢查清單

執行前確認：

- [ ] 容器正在運行
- [ ] OPENAI_API_KEY 已設定
- [ ] 資料庫連接正常
- [ ] 前端已部署最新版本
- [ ] coordinator.py 已修復（使用 get_clusters_for_generation）

執行後檢查：

- [ ] 回測通過率
- [ ] 生成的知識數量
- [ ] 前端可以看到待審核項目
- [ ] SOP 欄位是否正確預填

---

## 快速參考命令

```bash
# 清理待審核資料
docker exec -e DB_HOST=postgres aichatbot-rag-orchestrator python3 /tmp/clear_pending_knowledge.py

# 執行 vendor 1 回測
docker exec aichatbot-rag-orchestrator bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"

# 執行 vendor 2 回測（後台）
docker exec -e VENDOR_ID=2 aichatbot-rag-orchestrator bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py" 2>&1 | tee /tmp/vendor2_backtest.log &

# 查看待審核知識
curl -s http://localhost:8100/api/v1/loop-knowledge/pending | python3 -m json.tool

# 查看日誌
tail -f /tmp/vendor2_backtest.log
```
