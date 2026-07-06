# AIChatbot 系統架構總覽

> 更新：2026-07-06（面向 21＋售前、參數分工定案、計量/額度上線後）
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
 ├ ② 進行中會話續跑（表單收集中/對話面向中 → 直接續）
 ├ ③ 意圖分類＋檢索（b2b 只撈 JGB 知識；b2c 撈 SOP＋租客知識，比分擇優）
 ├ ④ 面向進場判定：top1 知識的 category 掛有「對話規則」→ 進對話引擎（先於表單）
 ├ ⑤ 表單/API 觸發：top1 帶 form_id/action_type 且分數 ≥0.75 → 表單收集或 api_call
 ├ ⑥ 錨點防呆＋相關性把關（reranker 高分錯位 → LLM 判 top1 相關性，不相關次筆晉位）
 ├ ⑦ 直答（含 {{param}} 模板注入業者參數）
 └ ⑧ 全空 → 誠實 fallback（轉客服）
```

## 三、對話面向（conversational facets）——21＋售前

**機制**：面向＝`knowledge_base` 中 `category='對話規則'` 的一筆設定資料（persona prompt＋topic_scope＋grounding_scope），**新增面向＝加一筆資料零改程式**。進場靠「top1 知識的 category → 規則」；收斂兩型：`select=api`（識別→候選→查現值→formatter 決定性 facts→LLM 組話）與 `select=category`（輕引導，撈該分類知識作答）。

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
| `vendor_sop_items` | 各業者客服標準回覆（租客問業者） | per-vendor | 後台 | b2c 檢索（b2b 不走） |
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

## 八、文件地圖

| 文件 | 用途 |
|---|---|
| `docs/deployment-runbook.md` | **統一部署聖經**（33 migrations→匯入→重建→煙囪→稽核） |
| `docs/jgb2-tenant-chat-integration.md` | 租客端串接規格（給 jgb2 工程） |
| `scripts/audit/check_invariants.sh` | 不變量稽核（維護準則在腳本頭） |
| `scripts/audit/reports/` | 盤查報告與可重放批次（知識盤查/業者SOP盤查/修正批次/lookup 錨點） |
| `scripts/usage/` | 計量治理 SQL（被遺忘權/內部重標/保留期清理） |
| `.kiro/specs/`（不進版控） | 各功能 spec 開發史（requirements/design/tasks/research） |
| `CLAUDE.md` | AI 助理工作流（kiro spec 流程與開發鐵則） |
