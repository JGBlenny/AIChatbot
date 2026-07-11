# 實作任務：trigger-vocabulary-debt（觸發語彙還債 P0）

> 建立時間：2026-07-11
> 需求：requirements.md（R1–R4）｜設計：design.md（5 元件、3 決策）｜落差：gap-analysis.md｜研究：research.md
> 標記：`(P)` = 可與同層其他 `(P)` 平行
> 鐵律：TDD（先紅後綠）；**零行為改變**——仲裁邏輯、門檻（0.55/0.6/0.75）、消費邏輯（chat.py:2944-3031）一行不動；
> 計量 fire-and-forget 原則延續——分數是加值，不得危及事件本體（動態 INSERT 陷阱以欄位偵測解）；
> M2（刪欄）破壞性 migration 獨立分檔，**prod 由使用者自行執行**；不碰 embedding 相關欄位與流程（R4.4）。
> 前置已清：R1.5 資料盤點已於 gap-analysis 完成（manual/immediate＝0 筆、觸發詞 0 筆→修復零行為改變）；R2.3 死欄位資料盤點已完成（全為預設值零資訊）。

## 1. 修斷鏈（檢索層欄位透傳）

- [x] 1.1 (P) 透傳實作（TDD 先紅後綠）：unit 先立 `_format_result` 三欄透傳斷言（含 NULL 案例→dict 帶 None）→ 補 `vendor_knowledge_retriever_v2.py` 兩處 SELECT（`_vector_search` L89-106、`_keyword_search` L196-215 各加 `kb.trigger_mode, kb.trigger_keywords, kb.immediate_prompt`）＋ `_format_result`（L297-341）三個 `row.get()` 映射（比照既有分區註解慣例標「觸發配置」區）。
  - 需求：1.1, 1.3
- [x] 1.2 整合驗證（真 DB）：向量與關鍵詞兩條路徑檢索回傳 dict 均含三欄；reranker 啟用下欄位透傳不丟（rerank 路徑一案）。
  - 需求：1.1
- [x] 1.3 回歸驗證：既有 unit/integration 全綠；針對性案例——`trigger_mode` 為 `none`/`auto`/NULL 的表單知識仍直觸發（else 分支不變）、direct_answer／api_call／對話面向分類路由行為不變。
  - 需求：1.3, 1.4, 4.3

## 2. 防回歸不變量（與 1 平行）

- [x] 2.1 (P) 靜態契約測試（新增 unit，離線零 DB）：解析 chat.py 對 best_knowledge 的 `.get('<key>')` 字面量集合（consumed）、`_format_result` return dict key 集合（produced）、兩條 SELECT 欄位集合（selected），斷言 `consumed ⊆ produced` 且 `db_backed(produced) ⊆ selected`（排除 similarity 等計算欄位）；納入既有 unit 套件隨 `make test`/CI 執行。
  - 需求：4.1

## 3. 檢索分數埋點

- [x] 3.1 (P) migration M1（加性、冪等）：`usage_events` 加 `knowledge_score NUMERIC(4,3)`、`sop_score NUMERIC(4,3)`、`decision_case VARCHAR(60)`（`ADD COLUMN IF NOT EXISTS`，沿用 add_vendor_quotas.sql 房式）；dev 套用驗證。
  - 需求：3.4
- [x] 3.2 (P) `set_comparison` hook＋降級偵測（TDD 先紅後綠）：`usage_metering.py` 新增 module-level `set_comparison(knowledge_score, sop_score, decision_case)`——ctx None／已 `_finalized` 靜默略過、decision_case 截斷 [:60]（與 `set_path` 同款）；`_to_row` 前一次性欄位偵測（首寫查 `information_schema.columns` 快取布林，欄位不存在→row 不含三 key、事件照舊完整寫入；偵測失敗視同不存在、下次重試）。unit 矩陣：ctx None 略過／截斷／finalized 略過／欄位不存在時 row 無三 key 且其餘欄位齊全。
  - 需求：3.1, 3.3, 3.5
- [x] 3.3 掛線＋整合驗證（3.1、3.2 完成後）：~~`_build_debug_info` 掛點~~ 實作時修正為 `handle_retrieval` decision 誕生處（L745）經 `_meter_comparison` 無條件埋（debug 閘問題，見 design v1.1）；integration——一次走檢索仲裁的 /message 事件帶三分數且 decision_case 為既有仲裁識別字串；短路路徑（表單續填／快取命中）事件分數欄 NULL；欄位未建之表（rollback M1 後）事件仍完整寫入。
  - 需求：3.1, 3.2, 3.5

## 4. 死欄位清理（1–3 全綠後）

- [x] 4.1 migration M2（破壞性、獨立分檔）＋rollback 檔：依序 `DROP CONSTRAINT check_trigger_form_condition`、`DROP INDEX idx_kb_trigger_form_condition`、`DROP COLUMN` 三欄（各 `IF EXISTS` 冪等）；rollback 依 add_knowledge_form_auto_option.sql 原定義重建（資料不可回復——已雙重確認零資訊內容）；dev 套用後全庫引用終掃（後端/前端/SQL/測試 grep 零引用）＋既有全測試綠。
  - 需求：2.1, 2.2, 2.4

## 5. e2e 與收案

- [x] 5.1 e2e 觸發全流程（G-gated、fixture 自建自清）：建一筆 `trigger_mode='manual'`＋`trigger_keywords` 的表單知識 → 問句命中 → 系統等待確認（不直觸發）→ 回覆關鍵詞 → 表單觸發 → 另案回覆非關鍵詞 → 不觸發；afterEach 清理 fixture 知識。
  - 需求：1.2, 4.2
- [x] 5.2 收案驗證：既有全測試綠＋`make audit` 全綠（含 2.1 新契約測試）；runbook（docs/deployment-runbook.md）增補本案節——部署順序（M1→推程式→煙囪→M2 由使用者執行）、M1/M2/rollback 指令、煙囪步驟（一則真請求→事件帶分數；短路路徑 NULL；manual 知識觸發生效）；semantic-model 免重建註記。
  - 需求：2.5, 4.4, 4.5
  - 收案紀錄（2026-07-11）：unit 744 全綠（含 2.1 契約測試 4 例）；`make audit` 不變量 1/2/4/5/6 綠、
    不變量 3 FAIL＝常駐 rag 容器為舊 image（含本案前既有 stale，非本案引入）——即 runbook §12 的
    「本案生效必須重建」前提，重建屬部署步驟由操作者執行（prod compose 不代操作），部署後 §10 重跑即綠；
    runbook 增補為 §12。

---
掛帳（不阻塞本 spec）：M2 之 prod 執行（使用者操作，runbook 為據）；灰帶占比分析（埋點上線累積後，P2 意圖路由輸入）；admin 觸發配置編輯 UI（範圍外，未來知識管理案）；trigger_mode 值域正規化（設計決策 1——有需要才另案）。
