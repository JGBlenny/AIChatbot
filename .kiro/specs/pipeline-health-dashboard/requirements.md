# Requirements Document

## Introduction

本功能在 knowledge-admin 系統設定層新增「Pipeline 健康儀表板」頁面，提供 RAG pipeline 各階段元件的即時健康狀態檢視。管理者在發現回答異常時，可透過此頁面快速定位是哪個環節出問題（如 Embedding 服務不可用、Reranker 超時、DB 斷線等），而不需逐一檢查容器日誌。

## Boundary Context

- **In scope**：RAG pipeline 各元件的即時健康檢查、狀態顯示、延遲量測、版本資訊；端到端 pipeline 驗證（送出測試查詢驗證完整流程）
- **Out of scope**：歷史趨勢圖表、告警通知推送、閾值或環境變數的線上修改、效能 profiling、日誌搜尋
- **Adjacent expectations**：各元件（Embedding API、Semantic Model、PostgreSQL、Redis）需提供可檢測的健康端點或連線測試方式；前端沿用現有 knowledge-admin 的導航結構與 UI 元件風格

## Requirements

### Requirement 1：元件健康檢查端點

**Objective:** As a 系統管理者, I want 透過單一 API 端點取得所有 pipeline 元件的健康狀態, so that 不需逐一登入容器即可掌握系統全貌

#### Acceptance Criteria

1. When 管理者呼叫健康檢查端點, the pipeline-health API shall 回傳所有受檢元件的狀態，每個元件包含：名稱、狀態（healthy / unhealthy / degraded）、回應延遲（毫秒）、版本或模型資訊（若可取得）、錯誤訊息（若異常）
2. The pipeline-health API shall 檢查以下元件：PostgreSQL 資料庫、Redis 快取、Embedding API、Semantic Reranker、LLM API（OpenAI）、Vector Search（實際執行向量查詢）、Keyword Search（實際執行關鍵字查詢）
3. When 任一元件檢查逾時或拋出例外, the pipeline-health API shall 將該元件標記為 unhealthy 並附上錯誤訊息，不影響其他元件的檢查結果
4. The pipeline-health API shall 在 15 秒內完成所有元件檢查並回傳結果
5. The pipeline-health API shall 回傳一個整體狀態欄位：所有元件 healthy 時為 healthy；有任一元件 unhealthy 時為 unhealthy；所有核心元件正常但非核心元件異常時為 degraded

### Requirement 2：端到端 Pipeline 驗證

**Objective:** As a 系統管理者, I want 透過一鍵端到端測試驗證完整 RAG pipeline 是否正常運作, so that 能確認各元件不只單獨存活，而是串接後也能正確回答

#### Acceptance Criteria

1. When 管理者觸發端到端驗證, the pipeline-health API shall 使用預設測試查詢執行完整 RAG pipeline（embedding → vector search → reranker → 回傳結果），並回報各階段是否成功及耗時
2. When 端到端驗證的任一階段失敗, the pipeline-health API shall 標示失敗的階段名稱與錯誤訊息
3. The pipeline-health API shall 在 30 秒內完成端到端驗證

### Requirement 3：健康儀表板頁面

**Objective:** As a 系統管理者, I want 在管理後台的系統設定層看到各元件的健康狀態, so that 能一眼判斷系統是否正常運作

#### Acceptance Criteria

1. The 健康儀表板頁面 shall 顯示在系統設定層的導航中，位於現有項目（快取管理、管理員管理、角色管理）之間
2. When 頁面載入時, the 健康儀表板 shall 自動執行一次元件健康檢查並顯示結果
3. The 健康儀表板 shall 以卡片或列表形式顯示每個元件的名稱、狀態圖示（綠色 healthy / 紅色 unhealthy / 黃色 degraded）、回應延遲、版本資訊
4. When 有元件狀態為 unhealthy, the 健康儀表板 shall 將該元件的錯誤訊息以醒目方式顯示
5. The 健康儀表板 shall 在頂部顯示整體狀態摘要（整體 healthy/unhealthy/degraded + 正常元件數 / 總元件數）

### Requirement 4：手動重新檢查與端到端測試

**Objective:** As a 系統管理者, I want 手動重新執行健康檢查和端到端測試, so that 在排除問題後能即時確認系統恢復

#### Acceptance Criteria

1. When 管理者點擊「重新檢查」按鈕, the 健康儀表板 shall 重新執行所有元件健康檢查並更新顯示結果
2. While 健康檢查正在執行中, the 健康儀表板 shall 顯示載入狀態並禁用重新檢查按鈕
3. When 管理者點擊「端到端測試」按鈕, the 健康儀表板 shall 觸發端到端 pipeline 驗證並顯示各階段的通過/失敗狀態與耗時
4. While 端到端測試正在執行中, the 健康儀表板 shall 顯示測試進度

### Requirement 5：降級狀態辨識

**Objective:** As a 系統管理者, I want 區分核心元件與非核心元件的異常影響, so that 能判斷系統是完全不可用還是部分功能受影響

#### Acceptance Criteria

1. The pipeline-health API shall 將 PostgreSQL、Embedding API、LLM API 歸類為核心元件（任一不可用則系統無法正常回答）
2. The pipeline-health API shall 將 Redis、Semantic Reranker 歸類為非核心元件（不可用時系統可降級運作但回答品質可能下降）
3. When 非核心元件不可用但核心元件正常時, the 健康儀表板 shall 顯示整體狀態為 degraded 並標示降級影響說明（例如：「Reranker 不可用，回答排序品質可能下降」）

### Requirement 6：存取權限控制

**Objective:** As a 系統管理者, I want 健康儀表板僅限有權限的管理者存取, so that 系統內部資訊不會外洩

#### Acceptance Criteria

1. The pipeline-health API shall 要求有效的管理者身份驗證才能存取
2. The 健康儀表板頁面 shall 僅對具有系統設定權限的管理者顯示導航入口
