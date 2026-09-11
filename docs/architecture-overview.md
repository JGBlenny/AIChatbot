# AIChatbot 系統架構總覽

> ⚠️ **2026-09-11 舊鏈退役（本輪文件盤查連帶發現，非原七條指定範圍；本檔全篇已過時）**：
> 本文件描述的 `POST /api/v1/message` 整條路由/引擎/表單/SOP 對話鏈**已於
> 2026-09-11 隨 31 個產品模組刪除**（見 `.claude/DECISIONS.md` DSP-046）。
> 現況架構（agentic-MCP，`/mcp` 門面 + `agent.turn`）見
> `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`；本檔保留供理解舊設計脈絡與
> 決策理由，⛔ **新進開發者請勿以本檔為現況入口**——這句話本身与本檔「單一入口」
> 的自我定位矛盾，是本輪盤查中發現、但未修正的文件地圖層級問題，留待下一輪
> 處理文件地圖（`docs/INDEX.md`）指向。
>
> 更新：2026-07-11（＋conversational-repair 落地：引擎交易語義＋修繕交易面向；面向 21＋售前、參數分工定案、計量/額度上線後）
> 讀者：新進開發者、跨 session 的 AI 助理、營運。單一入口——細節見文末文件地圖。
> 數字快照：知識 889 筆（active）／SOP 404 筆／回測題庫 3,909 題（approved）／對話面向 21＋售前。

## 一、系統做什麼

JGB 智慧租賃平台的內嵌 AI 客服。三類使用者、一個端點（`POST /api/v1/message`）：

| 使用者 | 請求形狀 | 回答資源 |
|---|---|---|
| **業者用戶**（管理公司員工，JGB 後台） | `mode=b2b`＋`target_user=property_manager`＋`role_id` | 只走 JGB 系統知識（不走 SOP） |
| **租客**（jgb2 端入口尚未上線，規格已交付） | `mode=b2c`＋`target_user=tenant`＋`vendor_id`＋`user_id`＋`role_id` | SOP＋租客知識＋業者參數＋案場資料＋個資 API |
| **潛在客戶**（售前） | `mode=b2b`＋`target_user=prospect`（無 role_id） | 售前知識（角色級面向） |

## 二、請求的一生（路由順位）

```
POST /api/v1/message
 ├ ① usage middleware：計量 context（token/身分/路徑）＋額度檢查（達限→直接回應，零 LLM 成本）
 ├ ② 進行中會話續跑（表單收集中/對話面向中 → 直接續；面向續跑見補圖通道）
 ├ ②′ trigger_facet_key 直達（選填參數命中 config registry 且 enabled → 跳過意圖辨識直接 seed 面向；未命中→照常管線，防呆不報錯）
 ├ ③ 意圖分類＋檢索（b2b 只撈 JGB 知識；b2c 撈 SOP＋租客知識，比分擇優）
 │   └ Step 0.5 損傷圖改道：is_damage 且信心足 → 不打 SOP 檢索、直接 seed 修繕交易面向（找不到面向配置→降級回原行為）
 ├ ③.5 交易面向 gate：面向宣告 enabled_gate（修繕＝repair_enabled）→ 讀 vendor_configs（缺值預設 true）；false→不進面向、回 gate_disabled 文案＋客服管道參數
 ├ ④ 面向進場判定：top1 知識的 category 掛有「對話規則」→ 進對話引擎（先於表單）
 ├ ⑤ 表單/API 觸發：top1 帶 form_id/action_type 且分數 ≥0.75 → 表單收集或 api_call
 ├ ⑥ 錨點防呆＋相關性把關（reranker 高分錯位 → LLM 判 top1 相關性，不相關次筆晉位）
 ├ ⑦ 直答（含 {{param}} 模板注入業者參數）
 └ ⑧ 全空 → 誠實 fallback（轉客服）
```

## 三、對話面向（conversational facets）——21＋售前

**機制**：面向＝`knowledge_base` 中 `category='對話規則'` 的一筆設定資料（persona prompt＋topic_scope＋grounding_scope），**新增面向＝加一筆資料零改程式**。進場靠「top1 知識的 category → 規則」；收斂兩型：`select=api`（識別→候選→查現值→formatter 決定性 facts→LLM 組話）與 `select=category`（輕引導，撈該分類知識作答）。

**面向分兩型——診斷（唯讀）／交易（寫入）**：
- **診斷面向**（既有）：收斂動作是查詢現值並回答，唯讀。
- **交易面向**（conversational-repair 落地，修繕為首個）：`grounding_scope` 宣告 `execute_endpoint` 即為交易面向——收斂動作是**執行寫入**（如 create_repair）。引擎零硬編面向字樣、全配置驅動：面向啟動時依 `prefill_api` 預填槽位（租約→物件、Vision→分類，確認型槽位不開口問）；brain 收齊必填槽位（含推斷槽）後回 `action='confirm'` 組摘要＋三顆確認 quick reply（confirm_submit/confirm_edit/confirm_cancel）；**收齊≠送出**——同意判定在引擎層（決定性，非 brain）才 execute；成功回執（單號取 `execute_result_path`）、`executed=True` 冪等（同意詞不重複建單）；失敗誠實告知＋重試，絕不假裝成功；brain 失敗降級一般流程、絕不建單。下一個交易面向（退租等）＝加配置與 seeds、引擎零改動（目標）。**完整邏輯（進場三路/prefill/confirm gate/execute/降級矩陣/配置鍵全表）見 `docs/architecture/facet-architecture.md`「交易面向」章節。**

| 領域 | 面向（select=api 診斷型） | 面向（category 輕引導） |
|---|---|---|
| 合約 | 合約異動、狀態判斷、簽署排障、續約、退租收尾 | 建約引導 |
| 帳務 | 繳費金流排障、帳單異常、**條件診斷：帳單**、發票、滯納金 | 帳單設定引導 |
| 帳號 | 登入排障、團隊成員權限 | 註冊驗證排障、帳號綁定異動 |
| 物件 | 物件現況診斷 | 物件操作引導 |
| IoT | 電表排障 | IoT設定引導 |
| 售前 | —（角色級 mode=all，prospect 進場） | — |

**設計鐵則**：機械判定用程式不用 LLM（狀態解碼/可否操作由 `services/jgb/*.py` 的 FACE_BUILDERS 決定性算，LLM 只照 facts 組話）；識別鏈「無編號→物件名→候選選序號」；個資紅線（完整地址/經緯度不出口）；金額只引存值禁重算。

## 四、資料體系分工（2026-07-06 定案）

| 體系 | 內容 | 粒度 | 維護動線 | 消費端 |
|---|---|---|---|---|
| `knowledge_base` | 系統知識＋面向規則＋系統脈絡＋錨點 | 全域/受眾 | 人工閘門＋import 工具 | 檢索/面向/模板 |
| `vendor_sop_items` | 各業者客服標準回覆（租客問業者）；**修繕子集已停用**（vendor 2/4 各 75 條 `next_form_id='jgb_repair_create'`，is_active=false 可逆——b2c 修繕改走交易面向；vendor 2 其餘 250 條非修繕 SOP 不動） | per-vendor | 後台 | b2c 檢索（b2b 不走） |
| `vendor_configs` | **通用單值參數**（電話/LINE/營業時間/繳費日） | per-vendor | 後台 | `{{param}}` 模板注入 |
| `lookup_tables` | **案場級/清單級**（各棟管理費/包裹/水電/廠商） | per-vendor per-key | Excel 統一匯入（拒收「範例：」列） | lookup 錨點（api_call） |
| jgb 外部 API | 個人現況資料（帳單/合約/電表） | per-user | jgb2 | 面向/表單，雙證制（role_id＋user_id） |

## 五、計量與額度（usage-metering／quota-management）

- **計量**：每請求一筆 `usage_events`（身分×路徑×token×估算成本；不存原文），middleware＋contextvar 歸集、fire-and-forget；內部流量（回測/迴圈/probe 前綴）標記排除。後台「使用量統計」頁＋`/api/usage/*`。
- **額度**：`vendor_quotas` 每業者月訊息額度（opt-in）——快到額度寄警示信（每月一次）；達限 middleware 直接回應（零 LLM 成本，業者見加值引導/租客見中性文案）；加值即恢復。**多輪 N 輪＝扣 N 則**。

## 六、品質三層

| 層 | 是什麼 | 怎麼跑 |
|---|---|---|
| unit（709） | 邏輯正確性，毫秒級離線 | `make test-unit`（容器內 pytest，CI 同款） |
| 系統回測 | 行為品質：迴圈凍結題集＋多輪模擬器＋v3 六級評審＋金標斷言，按受眾分庫（租客/業者/售前） | 8087 後台「迴圈管理」；**驗收鐵則：改引擎行為以系統路徑實跑收案** |
| 不變量稽核 | 配置/部署一致性（面向接管/evaluation 形狀/容器同步/計量健全/額度一致） | `make audit`；修一類 bug＝加一條不變量 |

基準快照（2026-07-06）：業者庫 68.3%（範疇內 85.4%）／租客庫 52%（首條基準）。

## 七、已知債總表（活文件，處理後劃掉）

- **業者資料就緒**：vendor 1 零 SOP；vendor 3 configs 假值（@example/123456789）；vendor 2 lookup 客服類疑似拷貝污染待重匯——**租客端上線硬前置**
- **租客個資查詢進場**：問法錨點/persona 皆業者視角，「我繳了沒」落 fallback——租客端開放前另案補
- 管理費 generic 知識（#3117）排名壓過 lookup 實值錨點（灰帶翻面家族）
- 回測殘族：通則個案化 ~6 題（需進場分流設計）；J 清單 3 條待 jgb2 名稱檢索端點
- 次優先斷言補盤（刊登必填/邀請上限/方案額度）；lookup 細節粗化（服務時間 7 筆/繳費帳戶——業者補 configs 完整值可復原）
- **conversational-repair 上線 gate 與後續**：
  - E1 真 API 為上線 gate——現以 `USE_MOCK_JGB_API` 驗流程，`get_tenant_contracts` 真端點列 J 清單待 jgb2 交付
  - vendor 4 缺 `service_hotline`（gate 關閉時的客服管道文案會落空）——業者補 configs
  - 下一個交易面向（退租等）＝加配置與 seeds 驗證「引擎零改動」目標成立
  - SOP 其餘 404 條全面退役／遷移為另案（本案僅停用修繕子集）
  - 上線 30 天 P50/P90 實測（目標 P50≤4／P90≤6 含岔題），未達標觸發設計覆核

## 八、文件地圖

| 文件 | 用途 |
|---|---|
| `docs/deployment-runbook.md` | **統一部署聖經**（33 migrations→匯入→重建→煙囪→稽核） |
| `docs/jgb2-chat-integration.md` | jgb2 串接規格正式版：b2b/b2c/prospect 三形狀契約 |
| `scripts/audit/check_invariants.sh` | 不變量稽核（維護準則在腳本頭） |
| `scripts/audit/reports/` | 盤查報告與可重放批次（知識盤查/業者SOP盤查/修正批次/lookup 錨點） |
| `scripts/usage/` | 計量治理 SQL（被遺忘權/內部重標/保留期清理） |
| `.kiro/specs/`（不進版控） | 各功能 spec 開發史（requirements/design/tasks/research） |
| `docs/architecture/facet-architecture.md` | 面向化系統脈絡＋**交易面向完整邏輯**（conversational-repair：進場三路/prefill/confirm gate/execute/配置鍵全表） |
| `docs/api/conversational-api.md` | 對話式 API 契約（含 `trigger_facet_key` 直達參數、confirm gate `quick_replies`） |
| `docs/architecture/`＋`docs/INDEX.md` | 深度文檔（完整對話架構/Retriever Pipeline/DB Schema）與任務導向索引 |
| `CLAUDE.md` | AI 助理工作流（kiro spec 流程與開發鐵則） |
