# 研究記錄：backtest-knowledge-refinement

> 建立時間：2026-03-27T00:00:00Z
> 目的：記錄技術調查、架構決策、相依性分析的過程與結果

## 摘要

### 調查範圍
本次研究範圍涵蓋現有知識完善迴圈系統的架構分析、前端 API 需求識別、資料庫架構完整性檢查，以及非同步執行模式的設計。

### 關鍵發現
- 現有系統已實作完整的 `LoopCoordinator` 狀態機與三層回測架構
- 缺少前端 API 路由層（`routers/loops.py`），需完整設計 RESTful API
- 資料庫架構與需求文件存在部分差異（scenario_ids 欄位、max_iterations 位置）
- 需實作非同步執行模式以避免前端 HTTP 超時問題（50 題：10-15 分鐘，500 題：60-90 分鐘）
- 批量審核功能為關鍵效率提升點，需優先設計

## 研究主題

### 主題 1：現有系統架構分析

**調查問題**：
了解現有 knowledge_completion_loop 模組的實作現狀，識別已完成與待補充的部分。

**研究方法**：
- [x] 現有程式碼分析（coordinator.py, models.py, backtest_client.py）
- [x] 文檔閱讀（GAP_CLASSIFIER_INTEGRATION.md, QUICK_REFERENCE.md）
- [x] 資料庫架構檢查

**發現**：
1. **已完成的核心元件**：
   - `LoopCoordinator`：完整的狀態機實作（13 個狀態）
   - `BacktestFrameworkClient`：三層回測架構的客戶端封裝
   - `GapClassifier`：OpenAI 驅動的智能分類與聚類
   - `SOPGenerator` / `KnowledgeGeneratorClient`：知識生成器
   - `OpenAICostTracker`：成本追蹤與預算控制

2. **缺少的關鍵元件**：
   - **前端 API 路由層**：完全缺失，需從零設計
   - **非同步執行框架**：當前為同步執行，需改造為背景任務
   - **批量審核 API**：僅有單一審核邏輯，缺少批量操作
   - **驗證回測 API**：驗證效果回測功能未實作
   - **暫停/恢復/取消 API**：狀態機已定義但 API 未實作

3. **資料庫架構差異**：
   - `knowledge_completion_loops.scenario_ids`：需求文件規劃為 INTEGER[]，實際可能為 JSONB
   - `knowledge_completion_loops.max_iterations`：需求規劃為獨立欄位，實際可能在 config JSONB 中
   - `knowledge_gap_analysis` 表：需求規劃完整欄位，實際實作程度需驗證

**結論與建議**：
- 優先實作前端 API 路由層，確保迴圈可透過 RESTful API 操作
- 引入背景任務機制（FastAPI BackgroundTasks 或 asyncio.create_task）實現非同步執行
- 資料庫架構需與實際實作對齊，或依需求補充缺失欄位

---

### 主題 2：非同步執行架構設計

**調查問題**：
如何設計非同步執行模式，避免前端 HTTP 請求超時（迭代執行耗時 10-120 分鐘）。

**研究方法**：
- [x] FastAPI 非同步模式調查（BackgroundTasks, asyncio.create_task）
- [x] 長時間任務執行模式研究（Celery, Redis Queue, 內建背景任務）
- [x] 前端輪詢狀態機制設計

**發現**：
1. **FastAPI BackgroundTasks**：
   - 優點：內建支援，無需額外依賴，適合輕量級背景任務
   - 缺點：無法跨請求追蹤進度，API 回應後即斷開連接
   - 適用場景：簡單的後處理任務（日誌寫入、通知發送）

2. **asyncio.create_task**：
   - 優點：可在 FastAPI 中啟動長時間運行的協程，保持任務狀態
   - 缺點：需自行管理任務生命週期、取消機制、錯誤處理
   - 適用場景：長時間運行的迭代任務，配合資料庫狀態追蹤

3. **Celery / Redis Queue**：
   - 優點：生產級分散式任務隊列，支援重試、優先級、監控
   - 缺點：引入額外依賴（Redis、RabbitMQ），增加系統複雜度
   - 適用場景：大規模生產環境，需要跨服務的任務分發

**選擇方案**：
**asyncio.create_task + 資料庫狀態追蹤**

**理由**：
- 現有系統已使用 asyncio（FastAPI 非同步框架），無需額外依賴
- 迴圈狀態已儲存在 `knowledge_completion_loops` 表，天然支援狀態追蹤
- 前端可透過輪詢 `GET /api/v1/loops/{loop_id}` 取得即時進度
- 避免引入 Celery 等重量級依賴，保持架構簡潔

**實作細節**：
```python
# API 端點（非同步啟動）
@router.post("/loops/{loop_id}/execute-iteration")
async def execute_iteration(loop_id: int, request: Request):
    coordinator = _get_coordinator(loop_id, request)

    # 立即返回，任務在背景執行
    asyncio.create_task(
        _background_execute_iteration(coordinator, loop_id)
    )

    return {
        "loop_id": loop_id,
        "status": "RUNNING",
        "message": "迭代已在背景執行，請輪詢狀態查看進度"
    }

# 背景執行函數
async def _background_execute_iteration(coordinator, loop_id):
    try:
        # 持續更新狀態到資料庫
        await coordinator.execute_iteration()
    except Exception as e:
        # 錯誤處理，更新狀態為 FAILED
        await coordinator._update_loop_status(LoopStatus.FAILED)
```

**前端輪詢機制**：
```javascript
// 前端輪詢狀態（每 5 秒）
const pollLoopStatus = async (loopId) => {
  const interval = setInterval(async () => {
    const response = await fetch(`/api/v1/loops/${loopId}`);
    const data = await response.json();

    if (data.status === 'REVIEWING' || data.status === 'FAILED') {
      clearInterval(interval);
      // 顯示結果或錯誤
    }

    // 更新進度顯示
    updateProgress(data.current_iteration, data.progress);
  }, 5000);
};
```

**併發控制**：
- 使用資料庫樂觀鎖（`WHERE status = 'RUNNING' AND updated_at = ?`）防止同一 loop 並發執行
- 當檢測到並發執行時，返回 `409 Conflict` 錯誤

---

### 主題 3：批量審核功能設計

**調查問題**：
如何設計高效的批量審核功能，支援一次審核 10-50 個知識項目。

**研究方法**：
- [x] 現有單一審核 API 分析
- [x] 批量操作設計模式研究（部分失敗處理、事務控制、進度回報）
- [x] 前端批量選取 UI/UX 設計

**發現**：
1. **批量操作設計模式**：
   - **全成功或全失敗**（事務模式）：使用資料庫事務確保原子性，一個項目失敗則全部回滾
     - 優點：資料一致性強
     - 缺點：一個項目失敗導致整批失敗，使用者體驗差
   - **部分成功模式**（容錯模式）：逐一處理，記錄失敗項目，繼續處理剩餘項目
     - 優點：最大化成功數量，使用者可重試失敗項目
     - 缺點：需仔細處理部分失敗的狀態管理

2. **選擇方案**：**部分成功模式（容錯模式）**
   - 理由：審核操作通常不需強一致性，部分成功優於全部失敗
   - 失敗項目保持原狀態（pending），可稍後重試
   - 返回詳細的成功/失敗統計與失敗項目清單

3. **批量審核流程**：
   ```
   1. 接收批量審核請求（knowledge_ids: [123, 124, 125, ...], action: 'approve'）
   2. 逐一處理每個項目：
      a. 更新 loop_generated_knowledge 狀態為 approved/rejected
      b. 若為 approve，同步到 knowledge_base/vendor_sop_items
      c. 生成 embedding 向量
      d. 記錄到 loop_execution_logs
   3. 記錄失敗項目（embedding 超時、同步錯誤等）
   4. 返回統計結果：{total: 10, successful: 9, failed: 1, failed_items: [...]}
   ```

4. **前端批量選取設計**：
   - **全選**：選取當前頁面所有項目
   - **篩選後全選**：先篩選（如：無相似度警告），再全選符合條件的項目
   - **Shift 多選**：支援 Shift + 點擊連續選取
   - **確認對話框**：顯示選取數量、知識類型分布、相似度警告統計
   - **進度顯示**：批量處理時顯示進度條（5/15）

**結論與建議**：
- 實作 `POST /api/v1/loop-knowledge/batch-review` API
- 採用部分成功模式，最大化審核效率
- 前端提供友善的批量選取與確認機制

---

### 主題 4：驗證回測功能（可選）

**調查問題**：
驗證效果回測是否為必要功能？如何設計驗證範圍選項？

**研究方法**：
- [x] 需求文件分析（Section 9 標註為可選功能）
- [x] 實務工作流程評估
- [x] Regression 檢測必要性分析

**發現**：
1. **標準工作流程已足夠**：
   ```
   迭代 1 → 審核批准 → 迭代 2（自然驗證知識效果）→ 審核批准 → 迭代 3 → ...
   ```
   - 每次迭代的回測已經驗證知識改善效果
   - 無需額外的驗證步驟

2. **驗證回測的價值場景**：
   - **快速驗證**：審核完立即驗證，無需等待下次迭代
   - **Regression 檢測**：檢查新知識是否影響原本通過的案例
   - **高品質要求**：對知識品質有特別高的要求

3. **驗證範圍選項**：
   - **選項 A（當前）**：只測試失敗案例（快速，無 regression 檢測）
   - **選項 B**：測試所有案例（完整，成本高）
   - **選項 C（建議）**：失敗案例 + 20% 抽樣通過案例（平衡）

**結論與建議**：
- **建議**：將驗證回測功能標記為「可選功能」，優先實作核心迭代流程
- 如需實作，採用選項 C（失敗 + 抽樣），配置參數為 `validation_scope: "failed_plus_sample"`, `sample_pass_rate: 0.2`
- 實作時使用 `LoopConfig.validation_scope` 參數控制行為

---

## 技術選型

### 選型 1：非同步執行框架

**候選方案**：

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|---------|
| FastAPI BackgroundTasks | 內建、無額外依賴、簡單 | 無法追蹤進度、無跨請求狀態 | 輕量級後處理任務 |
| asyncio.create_task | 保持任務狀態、配合資料庫追蹤、無額外依賴 | 需自行管理生命週期 | 長時間任務 + 狀態追蹤 |
| Celery / Redis Queue | 生產級、分散式、監控完善 | 引入額外依賴、增加複雜度 | 大規模生產環境 |

**評估標準**：
- 實作複雜度
- 系統依賴
- 狀態追蹤能力
- 現有架構對齊

**最終選擇**：asyncio.create_task + 資料庫狀態追蹤

**理由**：
- 現有系統已使用 FastAPI 非同步框架，天然支援 asyncio
- 迴圈狀態已儲存於資料庫，無需額外狀態管理服務
- 避免引入 Celery/Redis Queue 等重量級依賴
- 前端輪詢模式簡單可靠

### 選型 2：批量操作錯誤處理策略

**候選方案**：

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|---------|
| 全成功或全失敗（事務） | 資料一致性強 | 一個失敗全部失敗 | 金融交易、強一致性需求 |
| 部分成功（容錯） | 最大化成功數量、可重試失敗項目 | 需管理部分失敗狀態 | 批量審核、匯入操作 |

**最終選擇**：部分成功（容錯模式）

**理由**：
- 審核操作不需強一致性
- 部分失敗優於全部失敗，提升使用者體驗
- 失敗項目可稍後重試

---

## 相依性分析

### 外部 API 與服務

| 服務名稱 | 版本 | 用途 | 文件連結 | 注意事項 |
|---------|------|------|---------|---------|
| OpenAI API | gpt-4o-mini | 知識缺口分類、聚類、知識生成 | https://platform.openai.com/docs | 速率限制：3,500 req/min，需實作成本追蹤 |
| PostgreSQL pgvector | 0.5+ | 向量相似度搜尋、重複知識檢測 | https://github.com/pgvector/pgvector | 需建立 IVFFlat 索引加速搜尋 |
| FastAPI | 0.100+ | RESTful API 框架 | https://fastapi.tiangolo.com | 內建支援 asyncio、BackgroundTasks |

### 函式庫與套件

| 套件名稱 | 版本 | 用途 | 授權 | 風險評估 |
|---------|------|------|------|---------|
| asyncio | Python 標準庫 | 非同步任務執行 | PSF | 無風險 |
| asyncpg | - | PostgreSQL 非同步驅動 | Apache 2.0 | 已使用，無風險 |
| psycopg2 | - | PostgreSQL 同步驅動 | LGPL | 已使用，無風險 |
| openai | 1.x | OpenAI API 客戶端 | MIT | 已使用，無風險 |

---

## 現有程式碼分析

### 相關模式與慣例

**檔案位置**：
- `rag-orchestrator/services/knowledge_completion_loop/coordinator.py` - 核心協調器
- `rag-orchestrator/services/knowledge_completion_loop/models.py` - 狀態機與資料模型
- `rag-orchestrator/routers/knowledge_generation.py` - 現有知識生成 API（參考模式）

**發現的模式**：
1. **API 路由層**：使用 FastAPI Router，命名為 `router`，使用 Pydantic BaseModel 定義請求/回應
2. **資料庫存取**：透過 `request.app.state.db_pool` 取得連接池
3. **錯誤處理**：使用 `HTTPException` 統一回報錯誤
4. **狀態機管理**：使用 Enum 定義狀態，`_update_loop_status()` 方法更新狀態
5. **事件日誌**：所有關鍵操作記錄到 `loop_execution_logs` 表

**整合點**：
- 新增 `rag-orchestrator/routers/loops.py` 路由檔案
- 在 `app.py` 中註冊路由：`app.include_router(loops.router, prefix="/api/v1/loops", tags=["loops"])`
- 使用現有的 `LoopCoordinator` 類別，透過工廠函數初始化

---

## 效能考量

### 效能基準

| 指標 | 目標值 | 測試方法 | 備註 |
|------|--------|---------|------|
| API 回應時間 | < 1 秒 | 非同步啟動，立即返回 | 實際執行在背景進行 |
| 迭代執行時間 | 50 題: 10-15 分鐘<br>500 題: 60-90 分鐘 | 實際回測耗時 | 依 OpenAI API 速率限制 |
| 批量審核 10 項 | < 5 秒 | 不含 embedding 生成 | 逐一處理，無並發 |
| 批量審核 50 項 | < 20 秒 | 不含 embedding 生成 | 逐一處理，無並發 |

### 瓶頸分析
- **OpenAI API 速率限制**：3,500 req/min，大規模回測需控制並發數
- **Embedding 生成**：每個知識需調用 embedding API，批量審核時可能延遲
- **資料庫向量搜尋**：重複知識檢測需搜尋大量向量，需使用 IVFFlat 索引加速

---

## 安全性考量

### 威脅模型
- **未授權存取**：Loop 操作需驗證業者身份（vendor_id）
- **併發衝突**：同一 loop 並發執行導致狀態混亂
- **資源耗盡**：惡意大量請求導致 OpenAI API 成本爆炸

### 緩解措施
- **業者隔離**：所有 API 需驗證 vendor_id，確保只能操作自己的 loop
- **併發控制**：使用資料庫樂觀鎖防止並發執行
- **預算控制**：使用 `OpenAICostTracker` 追蹤成本，超過預算自動停止
- **速率限制**：在 API Gateway 層實作速率限制（如：每分鐘 60 次請求）

---

## 風險登記

| 風險 | 類型 | 影響 | 機率 | 緩解策略 | 狀態 |
|------|------|------|------|---------|------|
| OpenAI API 速率限制導致回測失敗 | 技術 | 高 | 中 | 實作重試機制（tenacity），控制並發數 | 開放 |
| 非同步任務執行失敗無法追蹤 | 技術 | 中 | 低 | 所有狀態記錄到資料庫，前端輪詢狀態 | 開放 |
| 批量審核部分失敗導致狀態不一致 | 技術 | 中 | 中 | 採用部分成功模式，記錄失敗項目供重試 | 開放 |
| 資料庫架構與需求文件不匹配 | 商業 | 高 | 高 | 優先驗證實際架構，必要時補充欄位 | 開放 |
| 驗證回測功能實作複雜度高但使用頻率低 | 時程 | 低 | 中 | 標記為可選功能，優先實作核心流程 | 已緩解 |

---

## 開放問題

### 問題 1：資料庫架構需補充欄位

**描述**：
需求文件規劃的 `knowledge_completion_loops.scenario_ids` 欄位（INTEGER[]）在實際資料庫中可能不存在或為 JSONB 格式。

**影響範圍**：
- 固定測試集功能（Section 4.5）
- 批次間避免重複選取功能

**可能解法**：
- 解法 A：補充 `scenario_ids INTEGER[]` 欄位到資料庫
- 解法 B：使用現有 JSONB 欄位儲存，調整查詢邏輯
- 解法 C：保持現狀，使用 `total_scenarios` 整數欄位（功能受限）

**決策狀態**：待決定（需驗證實際資料庫架構）

### 問題 2：load_loop() 方法實作優先級

**描述**：
當前 `LoopCoordinator` 無法載入已存在的 loop 並繼續執行下一次迭代（Section 10.6.1）。

**影響範圍**：
- 跨 session 迭代續接
- 腳本 `run_next_iteration.sh` 無法使用

**可能解法**：
- 解法 A：實作 `load_loop(loop_id)` 方法，從資料庫載入狀態
- 解法 B：前端透過 API 執行迭代，無需命令列腳本

**決策狀態**：已決定 - 優先實作解法 A（高優先級）

---

## 時間軸

| 日期 | 活動 | 結果 | 後續行動 |
|------|------|------|---------|
| 2026-03-27 | 研究啟動、現有系統分析 | 識別核心元件與缺失部分 | 設計 API 路由層 |
| 2026-03-27 | 非同步執行架構設計 | 選擇 asyncio.create_task 方案 | 實作背景任務執行框架 |
| 2026-03-27 | 批量審核功能設計 | 選擇部分成功模式 | 設計 batch-review API |

---

## 參考資源

### 官方文件
- FastAPI 非同步任務：https://fastapi.tiangolo.com/tutorial/background-tasks/
- OpenAI API 文件：https://platform.openai.com/docs/api-reference
- pgvector 文件：https://github.com/pgvector/pgvector

### 技術文章
- Python asyncio 最佳實踐：https://docs.python.org/3/library/asyncio.html
- RESTful API 設計指南：https://restfulapi.net/

### 專案內部文件
- `docs/backtest/QUICK_REFERENCE.md` - 回測快速參考
- `docs/backtest/GAP_CLASSIFIER_INTEGRATION.md` - 缺口分類器整合文檔
- `.kiro/specs/backtest-knowledge-refinement/requirements.md` - 完整需求規格

---

*本文件持續更新，記錄設計階段的所有重要調查與決策過程。*
