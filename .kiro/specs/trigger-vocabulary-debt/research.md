# 研究記錄：trigger-vocabulary-debt

> 建立時間：2026-07-11
> 目的：記錄設計階段的調查與決策。深度盤查已於 gap-analysis.md 完成（三路對碼＋DB 實查），本文件補設計層級的實碼細節與決策收斂。
> 發現流程：light discovery（既有系統擴充、無新外部依賴）

## 摘要

### 調查範圍
- 檢索層 row→dict 映射的實際結構（`_format_result`）
- 計量層 hook 慣例與事件寫入機制（`set_path`／`_to_row`／`_write_event`）
- 三個設計待決事項的收斂（trigger_mode 值域、分數欄位、不變量形態）

### 關鍵發現
- **`_format_result`（vendor_knowledge_retriever_v2.py:297-341）是欄位透傳的唯一閘口**：向量與關鍵詞兩條 SQL 的 row 都經此函式組 dict——補欄位＝2 處 SELECT＋此處 3 個 key，與 gap-analysis 判斷一致。
- **計量 hook 有現成房式**：`set_path(processing_path, answer_source)`（usage_metering.py:158-165）——contextvar 取 ctx、None 靜默略過、值截斷（[:60]/[:40]）。`set_comparison` 依同款設計。
- **⚠️ 動態 INSERT 的降級陷阱**：`_write_event`（usage_metering.py:215-219）按 `row.keys()` 動態組 INSERT——若 `_to_row` 加了分數 key 而 DB 欄位未建，**整筆事件寫入失敗**（不只丟分數），比降級更糟。R3.5 需以「欄位存在偵測」解，不能靠 try/except 混過。
- **DB 值分佈**（gap-analysis §0）：manual/immediate＝0 筆、觸發詞＝0 筆——修復零行為改變；死欄位零資訊內容——DROP 安全（程式面＋資料面雙確認）。

## 現有程式碼分析

### 模式 1：檢索結果 dict 契約
**位置**：`vendor_knowledge_retriever_v2.py:297-341`（`_format_result`）
- row→dict 明列 key（非 `dict(row)` 全收）——**這正是斷鏈成因**：SELECT 有欄也要映射才透傳，兩層都要補
- 分數欄位有註解分區慣例（`─── 分數欄位 ───`），新增觸發配置欄位比照分區註記
- reranker（base_retriever.py `_apply_semantic_reranker`）只 update 分數 key，不重建 dict——透傳安全

### 模式 2：計量 hook 與事件寫入
**位置**：`usage_metering.py:142-219`
- hook 房式：module-level 函式、`_ctx.get()` 取 contextvar、`ctx is None → return`（非計量路徑靜默）、字串值截斷
- `_to_row` 明列事件欄位 → `_write_event` 動態組 INSERT＋`ON CONFLICT (request_id) DO NOTHING`
- 中央賦值點前例：`_um_set_path` 於 chat.py `_build_debug_info`（L1523-1524）內呼叫，各終局路徑必經；comparison_metadata 已流至同一函式——落點零新增

### 模式 3：migration 房式
- 加欄：`ADD COLUMN IF NOT EXISTS`（add_vendor_quotas.sql 前例）
- 建欄檔含 CHECK 約束與索引（add_knowledge_form_auto_option.sql:24/68）——刪欄需連帶 DROP CONSTRAINT/INDEX
- fixes/ 目錄放 gitignore 的 prod 修復檔；migrations/ 進版控——刪欄 migration 屬後者（機制變更非資料修復）

## 技術選型（三個待決事項收斂）

### 選型 1：trigger_mode 值域處理（none=983 筆 vs 消費語彙 auto/manual/immediate）

| 方案 | 優點 | 缺點 |
|---|---|---|
| A. 不動資料、文件化寬鬆 else（**選定**） | 零行為改變（R1.4）、零資料風險 | 值域語義靠文件維持 |
| B. 資料正規化 none→auto＋CHECK 約束 | 值域乾淨 | 改 983 筆無行為收益；CHECK 增加匯入路徑破壞面；超出 P0 最小範圍 |

**理由**：`none`/`auto`/NULL 在 chat.py:2948 的 `if trigger_mode in ['manual','immediate']` 全落 else＝直觸發，行為等價。值域正規化留待未來有需要時另案。

### 選型 2：分數欄位與降級機制

**欄位**：`knowledge_score NUMERIC(4,3)`、`sop_score NUMERIC(4,3)`、`decision_case VARCHAR(60)`——獨立欄非 JSONB（R3.4 灰帶一句 SQL 直查）；NUMERIC(4,3) 覆蓋 similarity ∈ [0,1]；decision_case 沿用仲裁碼既有識別字串（如 `sop_cancelled_by_user`），[:60] 截斷與 processing_path 同款。

**降級（R3.5）**：

| 方案 | 評估 |
|---|---|
| A. 啟動/首寫時偵測欄位存在，快取布林，存在才於 `_to_row` 加 key（**選定**） | 乾淨；欄位未建時事件照舊寫入（無分數），零損失 |
| B. try/except 失敗後重組不含分數的 row 重寫 | 每筆失敗雙倍寫入嘗試；混濁 |
| C. env flag 手動開關 | 部署多一步人為環節，易漏 |

### 選型 3：不變量形態（R4.1）

| 方案 | 評估 |
|---|---|
| A. 靜態 unit 斷言（**選定為主**）：解析 chat.py 對 best_knowledge 的 `.get('...')` key 集合，比對 retriever SELECT＋`_format_result` key 集合，斷言 ⊆ | 離線可跑、無 DB、CI 天然覆蓋；納入既有 unit 套件即等效納入 make audit 的測試閘 |
| B. 執行期檢查：建含全配置的測試知識走真實檢索斷言 key 齊全 | 已由 R4.2 e2e 實質覆蓋，不重複建 |

## 風險登記

| 風險 | 類型 | 影響 | 機率 | 緩解策略 | 狀態 |
|---|---|---|---|---|---|
| 動態 INSERT 因新 key 無欄而整筆失敗 | 技術 | 高（事件遺失） | 高（若未處理） | 選型 2A 欄位偵測 | 已緩解（設計內建） |
| e2e 需 manual+keywords 測試知識（DB 現無此資料） | 技術 | 低 | 確定 | fixture 自建自清，沿用 G-gated e2e 慣例 | 已緩解 |
| 刪欄 migration 誤在 prod 自動執行 | 操作 | 中 | 低 | 破壞性 migration 獨立分檔＋runbook 明示由使用者執行（既定紀律） | 已緩解 |
| admin 後台無觸發配置編輯 UI，修復後配置僅能 SQL/匯入設定 | 產品 | 低 | 確定 | 記為已知限制（範圍外）；未來知識管理案補 UI | 開放（範圍外） |

## 開放問題

（無——三個設計待決事項均已於本文件收斂。）

## 時間軸

| 日期 | 活動 | 結果 |
|---|---|---|
| 2026-07-10 | 架構評估盤查＋獨立查核 | 14 條斷言 CONFIRMED，P0 立案依據 |
| 2026-07-11 | gap-analysis 三路盤查＋DB 實查 | 修復零行為改變；DROP 雙重安全；埋點落點確定 |
| 2026-07-11 | light discovery（本文件） | 實碼細節補齊、三決策收斂、發現動態 INSERT 陷阱 |
