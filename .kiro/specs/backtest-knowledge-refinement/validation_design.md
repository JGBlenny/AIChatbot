# 設計驗證報告：backtest-knowledge-refinement

> **驗證日期**：2026-03-27T08:00:00Z
> **驗證結果**：✅ **條件通過（CONDITIONAL GO）**
> **設計版本**：1.1（已修正）

---

## 執行摘要

本次設計驗證識別出 **3 個關鍵問題**，已根據使用者決策完成修正：

1. ✅ **資料庫架構不一致**（Critical）→ 已修正
2. ✅ **驗證回測功能定位**（High）→ 已明確為可選功能並設計降級方案
3. ✅ **重複檢測機制缺失**（Medium）→ 已新增完整說明

設計現已達到實作就緒狀態，可進入任務生成階段。

---

## 問題修正記錄

### 問題 1：資料庫架構與需求文件不一致 ✅

**嚴重程度**：🔴 Critical

**修正內容**：

1. **補充 knowledge_completion_loops 表欄位**（design.md:963-988）：
   ```sql
   ALTER TABLE knowledge_completion_loops
   ADD COLUMN IF NOT EXISTS loop_name VARCHAR(200),
   ADD COLUMN IF NOT EXISTS parent_loop_id INTEGER REFERENCES knowledge_completion_loops(id),
   ADD COLUMN IF NOT EXISTS target_pass_rate DECIMAL(5,2) DEFAULT 0.85,
   ADD COLUMN IF NOT EXISTS max_iterations INTEGER DEFAULT 10,
   ADD COLUMN IF NOT EXISTS current_iteration INTEGER DEFAULT 0,
   ADD COLUMN IF NOT EXISTS current_pass_rate DECIMAL(5,2),
   ADD COLUMN IF NOT EXISTS scenario_ids INTEGER[],
   ADD COLUMN IF NOT EXISTS selection_strategy VARCHAR(50),
   ADD COLUMN IF NOT EXISTS difficulty_distribution JSONB,
   ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;
   ```

2. **新增索引優化**：
   - `idx_loops_scenario_ids`：GIN 索引支援陣列查詢
   - `idx_loops_vendor_status`：複合索引加速狀態查詢
   - `idx_loops_parent`：支援批次關聯查詢

3. **新增說明文件**：
   - 明確各欄位用途與對應需求編號
   - 說明 scenario_ids 用於固定測試集（需求 4.5）
   - 說明 parent_loop_id 用於批次關聯（需求 4.4）

**驗證方式**：
- 對照需求文件 requirements.md 第 3.1 節，確保欄位完整性
- 確認所有 API 模型中使用的欄位都已定義

**影響範圍**：
- 資料庫遷移腳本（新增欄位）
- LoopStartResponse 模型（使用 scenario_ids、difficulty_distribution）
- LoopStatusResponse 模型（使用 max_iterations、current_pass_rate）

---

### 問題 2：驗證回測功能標記為「可選」但深度耦合 ✅

**嚴重程度**：🟡 High

**使用者決策**：選擇 **可選功能（延後實作）**

**修正內容**（design.md:1327-1360）：

1. **新增降級方案說明**：
   - 人工審核批准後，知識立即同步到正式庫
   - 知識狀態直接標記為 `approved`（跳過驗證）
   - 迴圈狀態從 `REVIEWING` 直接轉回 `RUNNING`（移除 `VALIDATING` 狀態）
   - 人工決定是否執行下一次完整迭代

2. **明確降級方案影響**：
   - ✅ 核心流程仍完整可用（7 步驟）
   - ✅ 審核後的知識立即生效
   - ⚠️  無法自動標記知識為 `need_improvement`
   - ⚠️  無法執行 Regression 檢測
   - ⚠️  效果驗證依賴完整迭代（耗時較長）

3. **調整狀態機**：
   ```python
   # 降級方案（移除 VALIDATING）
   REVIEWING → RUNNING

   # 完整方案（保留 VALIDATING，未來實作）
   REVIEWING → VALIDATING → RUNNING
   ```

**驗證方式**：
- 確認降級方案不影響核心流程完整性
- 確認前端可清楚提示使用者驗證功能未啟用
- 確認迭代控制邏輯無需修改

**影響範圍**：
- 狀態機實作（移除 VALIDATING 狀態轉換）
- 前端提示訊息（提示執行完整迭代驗證效果）
- API 端點保留（validate API 實作延後）

---

### 問題 3：批量審核 API 缺少重複檢測 ✅

**嚴重程度**：🟡 Medium

**使用者決策**：在 **知識生成時執行重複檢測**

**修正內容**：

1. **新增流程 4：知識生成時的重複檢測**（design.md:1212-1280）：
   - 完整的序列圖（Mermaid）
   - 檢測時機：知識生成時（`KnowledgeGenerator.generate_knowledge_batch()` 方法內）
   - 檢測範圍：knowledge_base、vendor_sop_items、loop_generated_knowledge
   - 相似度閾值定義：
     ```python
     SIMILARITY_THRESHOLDS = {
         "duplicate": 0.95,    # 幾乎完全相同，建議拒絕
         "similar": 0.85,      # 高度相似，建議人工判斷
         "related": 0.75       # 相關知識，僅供參考
     }
     ```

2. **性能優化策略**：
   - 使用 pgvector IVFFlat 索引加速搜尋
   - 限制搜尋範圍：只搜尋相同 vendor_id 的知識
   - 限制返回數量：LIMIT 3（只顯示前 3 個最相似的）
   - 批量生成時可並發執行檢測

3. **前端審核介面調整說明**：
   - 在待審核知識列表中顯示警告圖標
   - 點擊知識項目時顯示相似知識詳情
   - 提供重複警告文字：「⚠️ 檢測到 1 個高度相似的知識（相似度 93%）」

4. **更新 API 模型**（design.md:365-383）：
   ```python
   class PendingKnowledgeItem(BaseModel):
       ...
       similar_knowledge: Optional[Dict] = Field(
           None,
           description="重複檢測結果，格式：{detected: bool, items: [...]}"
       )
       duplication_warning: Optional[str] = Field(
           None,
           description="重複警告文字"
       )
   ```

**驗證方式**：
- 確認 similar_knowledge 欄位格式與需求文件一致（requirements.md:178-191）
- 確認檢測邏輯可在實作階段補充細節
- 確認性能優化策略合理

**影響範圍**：
- KnowledgeGenerator 實作（新增重複檢測邏輯）
- PendingKnowledgeItem 模型（新增 duplication_warning 欄位）
- 前端審核介面（顯示重複警告）

---

## 設計優勢確認

經驗證，設計保持以下優勢：

### 優勢 1：清晰的分層架構與責任劃分 ✅
- 路由層、服務層、資料層責任明確
- 每個元件單一職責，可獨立測試
- 符合專案 steering 文件定義的架構模式

### 優勢 2：完整的 API 契約定義與 Pydantic 模型驗證 ✅
- 所有 API 端點都有對應的 Request/Response 模型
- 使用 Pydantic Field 定義驗證規則
- 明確標註 Optional 欄位，避免歧義

---

## 最終評估

### GO / NO-GO 決策：✅ **GO（通過）**

**理由**：
1. ✅ 所有 Critical 問題已修正
2. ✅ 設計決策明確（驗證回測延後、重複檢測在生成時執行）
3. ✅ 降級方案完整，不影響核心流程
4. ✅ 資料庫架構與需求文件一致

### 下一步行動

**立即執行**：
```bash
/kiro:spec-tasks backtest-knowledge-refinement -y
```

**後續步驟**：
1. 生成實作任務（自動批准）
2. 開始實作核心 API 端點
3. 實作知識生成與重複檢測邏輯
4. 前端整合與測試

---

## 驗證檢查清單

- [x] 資料庫架構與需求文件一致
- [x] 所有 API 模型定義完整
- [x] 驗證回測功能定位明確
- [x] 降級方案設計完整
- [x] 重複檢測機制說明清楚
- [x] 性能優化策略合理
- [x] 前端整合需求明確
- [x] 設計文件更新時間戳
- [x] spec.json 階段更新為 design-validated

---

## 修正文件清單

1. **design.md**：
   - 資料庫架構補充（knowledge_completion_loops 表完整欄位）
   - 決策 4 調整（驗證回測降級方案）
   - 流程 4 新增（重複檢測機制）
   - PendingKnowledgeItem 模型更新

2. **spec.json**：
   - updated_at: 2026-03-27T08:00:00Z
   - phase: design-validated

3. **validation_design.md**（本文件）：
   - 完整的驗證報告與修正記錄

---

## 備註

**重要提醒**：
- 驗證回測功能已保留 API 端點定義（POST /api/v1/loops/{loop_id}/validate）
- 實作階段優先實作核心流程，驗證回測可在後續迭代補充
- 重複檢測機制在實作階段需與 embedding_utils.py 整合
- 前端整合需與 Vue.js 開發團隊同步 API 契約

**成本估算**（基於修正後的設計）：
- 單次迭代成本：~$0.03（50 題，40 題失敗）
- 包含重複檢測：額外 +$0.005（embedding 生成 + 向量搜尋）
- 完整迴圈成本（10 次迭代）：~$0.35-$0.50

**實作優先級**（建議順序）：
1. 資料庫遷移（補充欠缺欄位）
2. LoopRouter 核心 API（啟動、執行迭代、查詢狀態）
3. LoopKnowledgeRouter 審核 API（查詢、單一審核、批量審核）
4. ScenarioSelector 測試情境選取（分層隨機抽樣）
5. KnowledgeGenerator 重複檢測整合
6. 前端整合與測試

---

**驗證完成**：設計已達實作就緒狀態 ✅
