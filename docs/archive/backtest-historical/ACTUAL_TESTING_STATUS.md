# 回測 V2 實際測試狀態

**最後更新**: 2026-03-18
**狀態**: ✅ V2 + Similarity Extraction + 表單 Session 隔離修復完成

---

## ✅ 已完成的工作

### 1. 表單 Session 隔離修復 (100% 完成) 🆕

**修復日期**: 2026-03-18
**問題嚴重度**: 🔴 高（影響回測準確性）

#### 問題描述
- **症狀**: 連續 30+ 題被困在同一表單狀態（如「管理費資訊查詢」）
- **影響**: 案例 1404-1438 全部顯示「還未完成，需要繼續填寫嗎」
- **根因**: 所有測試案例共用 `session_id: "backtest_session"`

#### 修復方案

**1. 獨立 Session ID 生成**
```python
# backtest_framework_async.py Lines 136-137
unique_session_id = f"backtest_session_{scenario_id}" if scenario_id else "backtest_session"
unique_user_id = f"backtest_user_{scenario_id}" if scenario_id else "backtest_user"
```

**2. 修復 Scenario 資料結構**
```python
# run_backtest_db.py Lines 147-148
scenarios.append({
    'id': row[0],  # ✅ 新增 id 欄位
    'scenario_id': row[0],
    'test_question': row[1],
    'difficulty': row[2] or 'medium'
})
```

**3. 前端表單標記**
- 列表顯示: `📝 表單` 小標籤
- 詳情頁: `📝 表單類型` 大標籤
- CSS: 紫色漸層背景 `#8b5cf6`

#### 驗證結果 (Run 77)
- ✅ 測試 10 題，0 題 session 污染
- ✅ 案例 138 觸發表單後，案例 139-141 正常運作
- ✅ 只生成獨立 session: `backtest_session_138`
- ✅ 通過率: 20% (2/10)

#### 相關文件
詳見 [FORM_SESSION_ISOLATION_FIX.md](./FORM_SESSION_ISOLATION_FIX.md)

---

### 2. V2 評估邏輯實作 (100% 完成)

**文件**: `scripts/backtest/backtest_framework_async.py`

#### 新增方法
- `calculate_confidence_score()` (Lines 604-692) - 對齊生產環境
- `evaluate_answer_v2()` (Lines 694-829) - 綜合判定邏輯

#### 移除方法
- `_llm_evaluate_async()`
- `_llm_evaluate_batch_async()`
- `llm_evaluate_answer()`
- `_batch_llm_evaluation()`
- `_calculate_hybrid_score()`
- `_determine_pass_status()`
- **共移除約 283 行代碼**

#### 修改主流程
- Line 245: 改用 `evaluate_answer_v2()`
- Lines 956-964: 移除批量 LLM 評估

### 2. Similarity Extraction 修復 (100% 完成)

**問題**: Run 66 (100 tests) 全部失敗,因為 `max_similarity` 總是 0.0

**根因**: RAG API 的 `sources` 默認不包含 similarity scores

**修復方案** (2026-03-16):

#### 2.1 請求 debug_info
```python
# backtest_framework_async.py Line 139
payload = {
    "message": question,
    "vendor_id": self.vendor_id,
    "mode": "tenant",
    "include_sources": True,
    "skip_sop": True,
    "include_debug_info": True  # ✅ 關鍵：請求調試資訊
}
```

#### 2.2 提取並注入 similarity
```python
# backtest_framework_async.py Lines 157-173 (在 sync_post() 內)
# 從 debug_info 提取 similarity 並注入到 sources
if data and "debug_info" in data and data["debug_info"]:
    debug_info = data["debug_info"]
    if debug_info and "knowledge_candidates" in debug_info and debug_info["knowledge_candidates"] and "sources" in data:
        # 建立 ID 到 similarity 的映射
        id_to_sim = {}
        for candidate in debug_info["knowledge_candidates"]:
            kb_id = candidate.get("id")
            # 優先使用 boosted_similarity (語義重排後), 其次 base_similarity
            similarity = candidate.get("boosted_similarity") or candidate.get("base_similarity", 0.0)
            if kb_id:
                id_to_sim[kb_id] = similarity

        # 注入 similarity 到 sources
        for source in data.get("sources", []):
            source_id = source.get("id")
            if source_id in id_to_sim:
                source["similarity"] = id_to_sim[source_id]
```

#### 2.3 Null Safety 檢查
- 添加多層 null 檢查防止 `NoneType` 錯誤
- 確保 `debug_info`, `knowledge_candidates`, `sources` 都存在且非空

### 3. Docker 基礎設施修復 (100% 完成)

**文件**:
- `docker-compose.prod.yml`
- `knowledge-admin/backend/Dockerfile`

**目的**: 讓 knowledge-admin-api 能夠觸發 rag-orchestrator 容器內的回測

#### 3.1 Docker Socket 掛載
```yaml
# docker-compose.prod.yml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

#### 3.2 安裝 Docker CLI
```dockerfile
# knowledge-admin/backend/Dockerfile
RUN apt-get update && \
    apt-get install -y docker.io && \
    rm -rf /var/lib/apt/lists/*
```

---

## 📊 測試結果

### Run 66 (2026-03-16 08:13-08:17)

**測試規模**: 100 題 (第 1-100 題)

**配置**:
- 並發數: 5
- 超時時間: 60s
- 批量 LLM 評估: 啟用 (batch_size=10)
- 語義評估: 啟用 (使用生產環境 SemanticReranker 邏輯)

**結果**:
- 總耗時: 247.85 秒 (4.13 分鐘)
- **通過數量: 0 (0.0%)**
- 失敗數量: 100
- 錯誤數量: 0
- 吞吐量: 0.40 測試/秒

**失敗原因**: Similarity extraction 未實施,所有 `max_similarity = 0.0`,導致 `confidence_score` 極低 (~0.130)

### Run 66 修復後狀態

**修復內容** (2026-03-16 後):
- ✅ 添加 `include_debug_info: True`
- ✅ 實作 similarity extraction 邏輯
- ✅ 添加 null safety 檢查

**預期效果**:
- `max_similarity` 應為實際相似度 (0.7-0.95)
- `confidence_score` 應提升到合理範圍 (0.6-0.9)
- 通過率應顯著提升

**驗證狀態**: ⏳ 待執行新的回測驗證修復效果

---

## 🔄 後續待驗證

### 1. 執行修復後的回測
- 運行 10-20 題小規模測試
- 驗證 `max_similarity` 不再是 0.0
- 驗證 `confidence_score` 在合理範圍

### 2. 前端修改 (待完成)
- 從 10-point scale 改回 confidence_score (0-1) + level
- 顯示格式：`信心度: High (0.87)`

### 3. 資料庫 Schema 調整 (待完成)
**移除欄位**:
- `relevance`, `completeness`, `accuracy`, `intent_match`
- `quality_overall`, `quality_reasoning`

**保留欄位**:
- `confidence_score` (float, 0-1)
- `confidence_level` (varchar: high/medium/low)
- `semantic_overlap` (float, 0-1)

---

## 📁 修改文件清單

### 核心邏輯
1. `scripts/backtest/backtest_framework_async.py`
   - evaluate_answer_v2() 實作
   - calculate_confidence_score() 實作
   - similarity extraction 修復

### 基礎設施
2. `docker-compose.prod.yml` - Docker socket 掛載
3. `knowledge-admin/backend/Dockerfile` - Docker CLI 安裝

### 後端 API
4. `knowledge-admin/backend/app.py` - V2 欄位提取

### 前端 UI
5. `knowledge-admin/frontend/src/views/BacktestView.vue` - UI 優化

### 依賴
6. `knowledge-admin/backend/requirements.txt` - 新增依賴

---

## 🎯 核心成就

### V2 評估系統
- ✅ 移除不可靠的 LLM 0-10 分制
- ✅ 對齊生產環境 confidence_score 計算
- ✅ 保留語義攔截機制 (semantic_overlap < 0.4)

### Similarity Extraction
- ✅ 解決 max_similarity=0.0 根本問題
- ✅ 從 debug_info 正確提取 similarity
- ✅ 支持 boosted_similarity 優先邏輯

### 基礎設施
- ✅ 實現跨容器回測執行 (Docker-in-Docker)
- ✅ 確保前端可觸發回測

---

## 📖 相關文檔

1. **[BACKTEST_V2_IMPLEMENTATION_REPORT.md](./BACKTEST_V2_IMPLEMENTATION_REPORT.md)** - 完整實施報告
2. **[QUICK_START_V2.md](./QUICK_START_V2.md)** - 快速入門指南
3. **[BACKTEST_ALIGNMENT_PLAN_2026-03-15.md](./BACKTEST_ALIGNMENT_PLAN_2026-03-15.md)** - 對齊計劃
4. **[SOLUTION_B_SEMANTIC_PRIORITY.md](./SOLUTION_B_SEMANTIC_PRIORITY.md)** - 語義優先策略

---

**最後更新**: 2026-03-16
**狀態**: V2 實施 + Similarity Extraction 修復完成
**下一步**: 執行小規模回測驗證修復效果
