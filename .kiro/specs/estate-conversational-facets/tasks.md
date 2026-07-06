# 實作任務：estate-conversational-facets（物件管理領域對話面向擴充）

> 建立時間：2026-07-04
> 需求：requirements.md（R1–R8）｜設計：design.md（含 validate-design 三修正）｜落差：gap-analysis.md｜研究：research.md（定案 9 項）
> 標記：`(P)` = 可與同層其他 `(P)` 平行；`- [ ]*` = 可延後（外部條件 gated）
> ⚠️ 範圍變更（使用者裁定 2026-07-04）：**批次上傳整條移除不處理**——脈絡/persona 改導客服、J-E1 撤除、3431/3357 不動、R2.5 作廢、e2e 批次案改地址案。
> 鐵律：TDD（先紅後綠）；面向字面只准出現在資料列與 `services/jgb/` 領域檔；合約 6＋帳務 5＋帳號 4＋IoT 2 面向/售前/form_fill 零回歸；狀態機口徑一律**兩軸模型**（status 位元×is_open，research 定案 #1）；status 轉譯用程式不用 LLM；**個資紅線：address/full_address/經緯度不出口**（facts 只用 title/display_address/serial_id）；「查不到」口徑走 sentinel（不斷言已刪除）；不代操作（建立/編輯/刊登/刪除只指路）；UI 路徑以 research 為準（店舖 `/p/`、通知中心）

## 1. wrapper＋estates.py builder 底座（先做）

- [x] 1.1 `jgb_system_api.get_estates`＋`get_estate_detail` client wrapper（TDD）：index 拉頁 ≤200＋client 端 token 化過濾（title｜display_address 拼接、去分隔符 AND、int 容錯 str()、純數字先 id 直配——get_meters 同款）；**過濾後空集回 sentinel `[{"found": False, "keyword": kw}]`**（引擎 0-row 短路對策，design Issue 1）；`get_estate_detail` 單物件正規化單元素 list＋**空/None id 回 success:False 優雅降級**；registry 掛 **`jgb_estate_status`**/`jgb_estate_detail` 兩鍵＋mock 同步（⚠️ `jgb_estates` 為修繕報修表單現役鍵不可改——新鍵策略，見 design 偏差註記）。
  - 需求：4.1, 8.1
- [x] 1.2 `services/jgb/estates.py` 新領域檔：`ESTATE_FACE_BUILDERS`＋`build_estate_status_facts`——sentinel 優先（「刊登清單中找不到『{kw}』：先確認名稱；若無誤代表目前非刊登中——不得斷言已刪除」）；status 位元→中文轉譯（1/2/4/8，未知值原樣標注）；建約決策樹（detail.contract_required_fields：all_filled=False 列缺欄 label／True＋status=2 可建約／status≠2 建約前提為刊登中）；facts 只出 title/display_address/serial_id；`jgb_response_formatter` 加 `jgb_estates` face 分發；face=None 恆等（零回歸慣例）。
  - 需求：4.2, 4.3, 2.4
- [x] 1.3 單元測試（先紅後綠）：builder 矩陣（sentinel／四狀態轉譯／未知位元值／缺欄列舉／all_filled×status 組合）；**個資負斷言**（facts 串不含 address/full_address/經緯度值）；wrapper 過濾矩陣（token 命中/查無 sentinel/int 容錯/純數字 id 直配/detail 空 id 降級）；face=None 恆等；**status 位元互斥性真資料驗證**（preview DISTINCT status，組合值出現即回設計覆核——design Issue 3）。
  - 需求：4.3, 8.1

## 2. 面向資料四件套（migrations）

- [x] 2.1 (P) `add_estate_facet_categories.sql`：2 子分類（`物件操作引導`/`物件現況診斷`，parent_value='物件管理'，冪等）；**重用既有母列 id 61 不新建不修改**；整合驗證 `_domain_faces` 含兩面向。
  - 需求：1.1
- [x] 2.2 (P) `seed_estate_facet_system_context.sql`：系統脈絡 3 列——母薄層 ≤180 字（兩軸狀態機一句話版＋領域邊界出口）；子 `物件操作引導`（狀態×可做操作對照、批次機制鏈：11 必填欄/10MB/額度/通知中心結果/停「處理中」逾時導客服不教重傳、地址雙層、店舖 `/p/` 入口、儲存行為提醒）；子 `物件現況診斷`（status 轉譯表、建約決策樹、查不到弱信號紅線）；長度預算自檢 ≤4500。
  - 需求：1.3, 1.5, 2.3, 2.6, 3.1, 3.3
- [x] 2.3 (P) `seed_estate_facet_configs.sql`：對話 config 2 筆（persona_role `pm_estate_guide`/`pm_estate_diag` 專屬鍵）——引導面向 select='category'＋**明填 target_user='property_manager'**；persona 分流清單（單筆？批次？編輯刊登？狀態功能？對外顯示/店舖？）＋**問句已含明確主題直接收斂**（IoT 先例）＋不代操作/刪除三擋/通知中心口徑紅線＋跨域 switch 規則（合約/IoT/帳號/VR 導廠商/資料異動導客服）；診斷面向 select='api' endpoint=jgb_estate_status＋required_slots=[estate_ref]＋**deterministic_id:false**＋result_mapping（label：title/display_address/status 轉譯欄，candidate_cap 8，refine keyword）＋**secondary_call jgb_estate_detail(id={row.id}) attach detail**＋查不到紅線 answer_rules。
  - 需求：1.2, 1.6, 1.7, 2.1, 2.2, 2.7, 3.4, 4.1, 5.3
- [x] 2.4 整合測試：兩面向 config_for_category 進場；三層脈絡疊加正確（不含他域層與售前）；診斷面向 identify→client 過濾→候選→單筆＋detail attach→facts；**sentinel 案**（查無物件→非刊登中口徑、不出通用「查無資料」句）；引導面向 category 收斂（target_user 明填生效）；跨域 switch；零引擎修改驗證。
  - 需求：1.2, 1.3, 1.4, 4.1, 4.2, 5.3, 8.2

## 3. 知識工程（2 完成後可與 4 交錯；含人工確認閘門）

- [x] 3.1 (P) 既有知識複核補標表：28+ 筆逐筆（3428-3434/3505-3507/3862/3894/3895/3456…）——**兩軸口徑複核**（單軸描述改寫，3428 優先）、3505-3507 掛 `物件現況診斷`、3433 VR 改導 istaging/客服口徑、未標旗補 categories；產 facet-backfill-review.md → 人工閘門 → `backfill_estate_knowledge_facet_categories.sql`。
  - 需求：6.1, 6.2, 5.2
- [x] 3.2 (P) 新知識批次＋錨點產製：新知識（批次失敗原因集與通知中心、停「處理中」處置、刪除三擋、地址雙層、店舖入口與 URL、儲存行為）＋**單發三筆**（報表匯出、進階搜尋、點交點退快找）＋錨點（引導面向操作強詞；**診斷面向個案型三句**——design Issue 2；皆避「物件」裸詞）；question 短關鍵字、answer 先述情境、business_types=system_provider；批次檔 → 人工閘門 → 匯入。
  - 需求：5.1, 6.1, 6.3, 6.4, 2.5
- [x] 3.3 進場路由回歸擴物件案：`test_facet_entry_routing_req.py` 擴——錨點進對話＋單發不進＋**最小對比對**（「這份合約的物件地址錯了」→合約域 vs「物件要改對外顯示地址」→本域）＋三組誤吸邊界（綁電表→IoT、經理人→帳號、建約/點交→合約）；紅→調→綠。
  - 需求：7.1, 7.2, 7.3

## 4. 全流程＋端到端

- [x] 4.1 整合測試（真 DB＋stub 參數感知）：引導面向分流→收斂（批次失敗→通知中心 facts）；診斷全流程（識別→候選→status/缺欄 facts 各一案＋sentinel 案）；mock handler endpoint 感知（secondary 回 detail、G5 先例）；跨域 switch 雙向。
  - 需求：2.1, 2.2, 2.5, 3.1, 4.2, 8.2
- [x] 4.2 e2e（真 LLM＋真 jgb2 preview）：①引導：地址雙層多輪（「完整地址/對外頁」token 斷言）＋儲存行為冷問；②診斷：真物件識別→候選→現況 facts（真資料 role 待選——37305 或 20151 名下刊登中物件）；③**查不到→打錯字更正流程**（sentinel 口徑 token「非刊登中」＋負斷言不含「已刪除」）；④誤吸最小對比對負斷言；⑤不代操作/個資負斷言（回答不含完整地址）。斷言模式沿「逐輪推進＋全輪累計＋機制 token＋紅線負斷言」。
  - 需求：2.2, 3.1, 4.2, 4.3, 7.2, 8.3

## 5. 回歸＋部署＋契約

- [x] 5.1 回歸：合約 6／帳務 5／帳號 4／IoT 2 面向、售前、form_fill 全綠（unit＋integration＋e2e 全套）；進場路由五域全案例綠。
  - 需求：8.4
- [ ] 5.2 部署執行（併入統一部署 runbook）：migrations 4 支追加 → 知識匯入（閘門後）＋補標 → reranker semantic model 重建 → 清快取 → 煙囪驗證（2 面向各一句＋單發對照）。
  - 需求：6.4, 8.4
- [x] 5.3 (P) J/G 契約文件（estate-api-contract.md 交 jgb2）：**J-E1**（EstateBatchJob tries=1 無失敗通知——停「處理中」體驗缺陷，附 file:line 與建議 failed() handler）；**G-E1**（estates API 放寬 is_open 過濾參數化或露出刊登軸——現況診斷弱信號升級正面判定）；消費端承諾（唯讀/個資不出口/存在性驅動）。
  - 需求：4.1, 5.1
