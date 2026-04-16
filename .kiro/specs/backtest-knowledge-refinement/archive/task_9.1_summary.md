# Task 9.1 實作總結：撰寫 API 文檔

> **任務編號**: 9.1
> **實作日期**: 2026-03-27
> **狀態**: ✅ 已完成

## 任務概述

撰寫完整的 API 文檔，定義前端與後端的 API 契約，確保前端正確調用批量審核、迴圈管理等功能。

---

## 驗收標準

- ✅ 完整的 API 端點清單（URL, 方法, 參數, 回應）
- ✅ 請求/回應範例（JSON 格式）
- ✅ 錯誤碼與錯誤訊息清單
- ✅ 使用場景範例（批量審核、非同步執行）

---

## 實作成果

### 1. 迴圈管理 API 文檔

**檔案**: `docs/api/loops_api.md`
**行數**: 約 1000 行

**涵蓋內容**:

#### API 端點（共 10 個）
1. `POST /start` - 啟動新迴圈
2. `POST /{loop_id}/execute-iteration` - 執行迭代
3. `GET /{loop_id}` - 查詢迴圈狀態
4. `POST /{loop_id}/validate` - 驗證效果回測
5. `POST /{loop_id}/complete-batch` - 完成批次
6. `POST /{loop_id}/pause` - 暫停迴圈
7. `POST /{loop_id}/resume` - 恢復迴圈
8. `POST /{loop_id}/cancel` - 取消迴圈
9. `POST /start-next-batch` - 啟動下一批次
10. `GET /` - 列出迴圈（分頁）

#### 資料模型（TypeScript 介面）
- `LoopStartRequest` / `LoopStartResponse`
- `ExecuteIterationRequest` / `ExecuteIterationResponse`
- `LoopStatusResponse`
- `ValidateLoopRequest` / `ValidateLoopResponse`
- `CompleteBatchResponse`

#### 使用場景範例（4 個）
1. 快速驗證（50 題）
2. 標準測試（500 題）
3. 批次處理（第 1 批 50 題 → 第 2 批 50 題）
4. 驗證效果回測（可選功能）

#### 錯誤處理
- 標準錯誤回應格式
- HTTP 狀態碼對應表（200, 201, 202, 400, 404, 409, 422, 500, 503）
- 錯誤碼清單（8 個）

#### 前端整合建議
- 輪詢機制範例（Vue 3 + TypeScript）
- 進度顯示範例（進度條、狀態文字）

---

### 2. 知識審核 API 文檔

**檔案**: `docs/api/loop_knowledge_api.md`
**行數**: 約 950 行

**涵蓋內容**:

#### API 端點（共 3 個）
1. `GET /loop-knowledge/pending` - 查詢待審核知識
2. `POST /loop-knowledge/{knowledge_id}/review` - 單一知識審核
3. `POST /loop-knowledge/batch-review` - 批量知識審核

#### 資料模型（TypeScript 介面）
- `PendingKnowledgeQuery` / `PendingKnowledgeResponse`
- `PendingKnowledgeItem`（包含重複檢測警告）
- `ReviewKnowledgeRequest` / `ReviewKnowledgeResponse`
- `BatchReviewRequest` / `BatchReviewResponse`
- `BatchReviewFailedItem`

#### 使用場景範例（4 個）
1. 查詢並篩選待審核知識
2. 單一審核並修改知識
3. 批量審核無重複警告的知識
4. 處理重複檢測警告

#### 錯誤處理
- 標準錯誤回應格式
- HTTP 狀態碼對應表（200, 400, 404, 500）
- 錯誤碼清單（6 個）

#### 前端整合建議
- 審核中心界面設計（Vue 3 完整範例，約 150 行）
- 包含篩選欄、批量操作工具列、知識列表、分頁功能

---

## 文檔特點

### 1. 完整性
- ✅ 涵蓋所有 API 端點（13 個）
- ✅ 每個端點包含完整的請求/回應範例
- ✅ 所有資料模型使用 TypeScript 介面定義
- ✅ 詳細的欄位說明與驗證規則

### 2. 實用性
- ✅ 提供 8 個真實使用場景範例
- ✅ 包含完整的 curl 命令範例
- ✅ 提供前端整合代碼（Vue 3 + TypeScript）
- ✅ 詳細的錯誤處理說明

### 3. 可讀性
- ✅ 使用 Markdown 格式化
- ✅ 清晰的目錄結構
- ✅ 代碼區塊語法高亮（JSON, TypeScript, bash, vue）
- ✅ 表格化展示（端點清單、錯誤碼、HTTP 狀態碼）

### 4. 準確性
- ✅ 與實際 router 實作一致（從 `routers/loops.py` 和 `routers/loop_knowledge.py` 讀取）
- ✅ 與設計文件對齊（參考 `design.md`）
- ✅ 與需求文件對齊（標註需求覆蓋編號）

---

## 文檔結構

### loops_api.md 結構
```
1. 概述
2. 目錄
3. API 端點清單（表格）
4. 資料模型
   - LoopStartRequest
   - LoopStartResponse
   - ExecuteIterationRequest
   - ExecuteIterationResponse
   - LoopStatusResponse
   - ValidateLoopRequest
   - ValidateLoopResponse
   - CompleteBatchResponse
5. 端點詳細說明（10 個端點）
   - 請求範例
   - 成功回應範例
   - 錯誤回應
   - 功能說明
6. 錯誤處理
   - 標準錯誤回應格式
   - HTTP 狀態碼
   - 錯誤碼清單
7. 使用場景範例（4 個）
8. 前端整合建議
   - 輪詢機制
   - 進度顯示
9. 變更歷史
10. 相關文件
```

### loop_knowledge_api.md 結構
```
1. 概述
2. 目錄
3. API 端點清單（表格）
4. 資料模型
   - PendingKnowledgeQuery
   - PendingKnowledgeItem
   - PendingKnowledgeResponse
   - ReviewKnowledgeRequest
   - ReviewKnowledgeResponse
   - BatchReviewRequest
   - BatchReviewFailedItem
   - BatchReviewResponse
5. 端點詳細說明（3 個端點）
   - 請求範例
   - 成功回應範例
   - 錯誤回應
   - 功能說明
6. 錯誤處理
   - 標準錯誤回應格式
   - HTTP 狀態碼
   - 錯誤碼清單
7. 使用場景範例（4 個）
8. 前端整合建議
   - 審核中心界面設計（完整 Vue 3 範例）
9. 變更歷史
10. 相關文件
```

---

## 關鍵特性

### 1. 迴圈管理 API 關鍵特性

#### 非同步執行機制
- 預設使用非同步模式（`async_mode: true`）
- 返回 `execution_task_id` 供前端輪詢
- 建議輪詢頻率：每 5 秒

#### 進度追蹤
- `progress.phase`：backtest/analyzing/classifying/generating/reviewing/validating
- `progress.percentage`：0-100
- `progress.message`：詳細進度說明

#### 狀態機
```
pending → running → reviewing → validating → running （繼續迭代）
pending → running → completed （達成目標）
pending → running → failed （執行失敗）
running → paused （暫停）
paused → running （恢復）
running → cancelled （取消）
```

#### 固定測試集保證
- 啟動迴圈時選取固定的 `scenario_ids`
- 所有迭代使用相同的測試集
- 確保結果可比較性

#### 批次關聯功能
- 透過 `parent_loop_id` 關聯批次
- 自動排除父迴圈已使用的測試情境
- 避免批次間重複選取

---

### 2. 知識審核 API 關鍵特性

#### 重複檢測警告
- `similar_knowledge.detected`：是否檢測到重複
- `similar_knowledge.items`：相似知識列表（ID, 來源表, 相似度）
- `duplication_warning`：警告文字（如「檢測到 1 個高度相似的知識（相似度 93%）」）

#### 批量審核效能
- 支援 1-100 個項目的批量操作
- **部分成功模式**：一個失敗不影響其他項目
- 預期耗時：
  - 10 個項目：< 5 秒
  - 50 個項目：< 20 秒
  - 100 個項目：< 40 秒

#### 立即同步機制
- 批准後立即同步到正式庫（`knowledge_base` / `vendor_sop_items`）
- 自動生成 embedding 向量
- 更新來源追蹤欄位（`source_loop_id`, `source_loop_knowledge_id`）

#### 審核流程
```
待審核 (pending) → 批准 (approve) → 同步 (synced) → 正式庫生效
                  → 拒絕 (reject) → 不同步
```

---

## 前端整合要點

### 迴圈管理前端整合

1. **啟動迴圈**
   - 表單驗證：batch_size (1-3000), max_iterations (1-50), target_pass_rate (0.0-1.0)
   - 顯示選取策略與難度分布

2. **執行迭代**
   - 預設非同步模式
   - 啟動後立即開始輪詢狀態

3. **輪詢狀態**
   - 每 5 秒調用 `GET /loops/{loop_id}`
   - 顯示進度條與階段資訊
   - 狀態變為 `reviewing` 時停止輪詢，跳轉審核中心

4. **暫停/恢復/取消**
   - 提供按鈕供用戶操作
   - 顯示確認對話框

---

### 知識審核前端整合

1. **查詢待審核知識**
   - 篩選條件：迴圈、類型、狀態
   - 支援分頁（limit + offset）

2. **篩選後全選**
   - 前端邏輯：過濾無重複警告的項目
   - 提取 knowledge_ids 列表

3. **批量審核**
   - 顯示已選取數量
   - 批量批准/拒絕按鈕
   - 顯示處理進度（`successful / total`）
   - 顯示結果摘要對話框（成功/失敗統計、失敗項目列表、重試按鈕）

4. **重複檢測警告**
   - 顯示警告圖標
   - 顯示相似知識列表
   - 提供批准/拒絕建議

---

## 相關文件

1. **設計文件**: `.kiro/specs/backtest-knowledge-refinement/design.md`
   - 架構設計
   - 元件介面定義
   - 資料流程圖

2. **需求文件**: `.kiro/specs/backtest-knowledge-refinement/requirements.md`
   - 功能需求
   - 資料模型定義
   - 驗收標準

3. **路由實作**:
   - `rag-orchestrator/routers/loops.py`
   - `rag-orchestrator/routers/loop_knowledge.py`

---

## 後續任務

- **9.2**: 前端批量選取功能需求定義
- **9.3**: 前端迴圈管理界面需求定義

---

## 總結

✅ 已完成兩份詳細的 API 文檔（共約 1950 行），涵蓋所有 API 端點、資料模型、使用場景與前端整合建議。文檔與實際實作完全一致，可直接供前端開發團隊使用。

**核心價值**：
- 明確的 API 契約定義
- 完整的使用範例
- 詳細的錯誤處理說明
- 實用的前端整合代碼

**文檔品質**：
- 完整性：✅（所有端點、所有模型）
- 準確性：✅（與實作一致）
- 可讀性：✅（清晰結構、代碼高亮）
- 實用性：✅（真實場景、可執行範例）
