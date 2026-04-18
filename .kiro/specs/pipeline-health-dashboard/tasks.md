# 實作任務：pipeline-health-dashboard

> **建立時間**：2026-04-18T06:40:00Z
> **需求文件**：requirements.md
> **設計文件**：design.md
> **語言**：Traditional Chinese (zh-TW)

---

## 任務概述

本文件定義「Pipeline 健康儀表板」的實作任務。後端在 rag-orchestrator 新增健康檢查服務與 API 端點，前端在 knowledge-admin 新增儀表板頁面。

**任務編號說明**：
- `(P)` 表示可與同層級其他 `(P)` 任務並行執行

---

## 1. Foundation: 後端健康檢查服務

- [x] 1.1 PipelineHealthService — 元件 Checker 實作
  - 建立 `services/pipeline_health_service.py`，實作 PipelineHealthService 類別
  - 實作 7 個 private checker method：`_check_db`, `_check_redis`, `_check_embedding`, `_check_reranker`, `_check_llm`, `_check_vector_search`, `_check_keyword_search`
  - 每個 checker 回傳 ComponentCheckResult（name, status, latency_ms, version, error, is_core, degradation_impact）
  - DB checker：`SELECT 1` + 取 PostgreSQL version
  - Redis checker：PING + 寫入測試
  - Embedding checker：`GET /api/v1/health` 到 embedding-api
  - Reranker checker：`GET /` 到 semantic-model，檢查 model_loaded
  - LLM checker：呼叫 `openai.models.list()`
  - Vector Search checker：生成測試 embedding + 執行一次向量查詢，驗證回傳筆數 > 0
  - Keyword Search checker：用 jieba 分詞 + 執行一次 keyword 查詢，驗證不拋例外
  - 核心元件分類：PostgreSQL / Embedding API / LLM API = core；Redis / Reranker / Vector Search / Keyword Search = non-core
  - 非核心元件附帶 degradation_impact 說明
  - Done：每個 checker 獨立可執行，回傳正確的 ComponentCheckResult 結構
  - _Requirements: 1.1, 1.2, 5.1, 5.2_
  - _Boundary: PipelineHealthService_

- [x] 1.2 PipelineHealthService — 聚合與整體狀態計算
  - 實作 `check_all_components()` 方法：用 `asyncio.gather` 並行執行所有 checker
  - 每個 checker 用 `asyncio.wait_for(timeout=5)` 包裹，逾時標記 unhealthy 並附錯誤訊息「檢查逾時（5 秒）」
  - 方法回傳 PipelineHealthResponse 結構：overall_status, healthy_count, total_count, components, checked_at
  - 整體狀態計算邏輯：全 healthy → healthy；任一核心 unhealthy → unhealthy；核心均正常但非核心有 unhealthy → degraded
  - Done：`check_all_components()` 在 15 秒內回傳完整結果，單一元件逾時不影響其他元件
  - _Depends: 1.1_
  - _Requirements: 1.3, 1.4, 1.5, 5.3_

- [x] 1.3 PipelineHealthService — 端到端測試
  - 實作 `run_e2e_test()` 方法：使用固定測試查詢（如「漏水怎麼處理」，vendor_id=2）
  - 依序執行 4 個 stage：embedding 生成 → vector search → keyword search → reranker
  - 每個 stage 回傳 E2EStageResult（stage, status, latency_ms, error, detail）
  - 任一 stage 失敗則標示失敗階段與錯誤訊息，後續 stage 標記為 skipped
  - 方法回傳 E2ETestResponse 結構：overall_status, test_query, stages, total_latency_ms, tested_at
  - Done：`run_e2e_test()` 在 30 秒內完成，回傳 4 個 stage 的結果
  - _Depends: 1.1_
  - _Requirements: 2.1, 2.2, 2.3_

## 2. Foundation: 後端 API 端點與註冊

- [x] 2.1 system_health router
  - 建立 `routers/system_health.py`，定義兩個端點：
    - `GET /api/v1/system/pipeline-health` → 呼叫 `PipelineHealthService.check_all_components()`
    - `POST /api/v1/system/pipeline-e2e-test` → 呼叫 `PipelineHealthService.run_e2e_test()`
  - 定義 Pydantic response models：PipelineHealthResponse、E2ETestResponse、ComponentCheckResult、E2EStageResult
  - 兩個端點都加上管理者認證（沿用既有 auth dependency）
  - 在 `app.py` 中 `include_router(system_health.router)`
  - 在 `config/api.js` 新增 `pipelineHealth` 和 `pipelineE2ETest` 端點定義
  - Done：兩個端點可用 curl 呼叫並回傳正確 JSON 格式；無 token 時回 401
  - _Depends: 1.2, 1.3_
  - _Requirements: 1.1, 1.5, 2.1, 6.1_
  - _Boundary: system_health router_

## 3. Core: 前端健康儀表板頁面

- [x] 3.1 PipelineHealthView.vue — 頁面結構與元件狀態顯示
  - 建立 Vue Options API 頁面 `views/PipelineHealthView.vue`
  - `mounted()` 自動呼叫 `GET /rag-api/v1/system/pipeline-health`
  - 頂部：整體狀態摘要卡片（大圖示 ✅/❌/⚠️ + 「X/Y 元件正常」+ overall_status 文字）
  - 中間：元件狀態 grid，每個元件一張卡片，顯示名稱、狀態 emoji、延遲（ms）、版本資訊
  - unhealthy 元件的錯誤訊息以紅色醒目顯示
  - degraded 元件顯示降級影響說明
  - CSS class：`status-healthy`（綠色）/ `status-unhealthy`（紅色）/ `status-degraded`（黃色）
  - Done：頁面載入時自動顯示所有元件健康狀態卡片，unhealthy 元件有紅色錯誤提示
  - _Depends: 2.1_
  - _Requirements: 3.2, 3.3, 3.4, 3.5, 5.3_
  - _Boundary: PipelineHealthView_

- [x] 3.2 PipelineHealthView.vue — 操作按鈕與端到端測試
  - 「重新檢查」按鈕：重新呼叫健康檢查 API 並更新結果
  - 「端到端測試」按鈕：呼叫 `POST /rag-api/v1/system/pipeline-e2e-test`
  - 端到端測試結果區域：各階段名稱、通過/失敗狀態、耗時列表
  - 操作中顯示 loading 狀態並禁用按鈕
  - Done：兩個按鈕均可操作，loading 狀態正確切換，端到端測試結果正確顯示
  - _Depends: 3.1_
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

## 4. Integration: 路由與導航整合

- [x] 4.1 前端路由與導航
  - `router.js` 新增 `/pipeline-health` 路由，meta 設定 `requiresAuth: true`
  - `App.vue` 系統設定層導航加入「系統健康」項目，位於快取管理之後
  - 導航項目僅對具有系統設定權限的管理者顯示
  - Done：登入後可從系統設定層導航進入健康儀表板頁面，無權限時看不到入口
  - _Depends: 3.1_
  - _Requirements: 3.1, 6.2_

## 5. Validation: 測試

- [ ] 5.1 (P) 後端單元測試
  - 測試 PipelineHealthService.check_all_components()：mock 各元件回傳，驗證 ComponentCheckResult 結構
  - 測試逾時隔離：mock 某元件 sleep 超過 5 秒，驗證其他元件結果不受影響
  - 測試整體狀態計算：全 healthy → healthy；核心 unhealthy → unhealthy；僅非核心 unhealthy → degraded
  - 測試 run_e2e_test()：mock 各 stage 回傳，驗證 E2EStageResult 結構
  - Done：所有單元測試通過
  - _Depends: 1.2, 1.3_
  - _Requirements: 1.1, 1.3, 1.5, 2.1, 5.1, 5.2, 5.3_
  - _Boundary: PipelineHealthService_

- [ ] 5.2 (P) 後端整合測試
  - `GET /api/v1/system/pipeline-health`：驗證回傳 JSON 格式、HTTP 200、包含所有 7 個元件
  - `POST /api/v1/system/pipeline-e2e-test`：驗證回傳 4 個 stage 結果
  - 認證測試：無 token 時回 401
  - Done：所有 API 整合測試通過
  - _Depends: 2.1_
  - _Requirements: 1.1, 1.2, 2.1, 6.1_
  - _Boundary: system_health router_
