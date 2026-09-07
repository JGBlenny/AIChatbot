# 給 JGB（jgb2）：LINE OA「JGB 房東管家」demo 需要開放／確認的 API（需求總表 v1，2026-09-07）

> 呼叫方：AIChatbot（rag-orchestrator）代表 LINE OA 使用者（代管業務／房東，`role_id=20151` 測試團隊）。demo 性質＝展示對話與 MCP 功能，非上線準確度。**時程（業主 2026-09-08）：demo 先在替身上舉行，本表的 B／B′ 於 demo 後開；替身先照本表形狀實作，JGB 開出來若形狀不同再對。**本表只列**要 JGB 做或答的事**；每條附證據（檔案＋可 grep 符號）。
> 主 session 對帳：scout 原始盤查把③④⑤ LIFF 線需求混入，且把「催繳草稿」誤判為 jgb2 端點；已依業主裁示（③④⑤先不併）分層。⚠️ 修正一項先前結論：jgb2 **有**建物件／建約／建帳單的寫入 API，在內部群組 `agent/v1`，不在 `external/v1`。

## A. 查詢情境：**不需要 JGB 開任何東西**

| 資料 | jgb2 端點 | AIChatbot 已接 |
|---|---|---|
| 帳單清單／明細 | `GET /api/external/v1/bills`、`GET /api/external/v1/bills/{bill_id}` | `services/jgb_system_api.py` `get_bills`／`get_bill` |
| 合約狀態 | `GET /api/external/v1/contracts/status-overview` | `get_contracts` |
| 電錶 | `GET /api/external/v1/meters` | `get_meters` |
| 物件、修繕單、修繕分類 | `GET /estates`、`GET /repairs`、`GET /repairs/categories` | `get_estates`、`get_repairs`、`get_repair_categories` |

agent 路徑對 pm 受眾以 `role_id` 圈定、不驗 `user_id`（`services/agent/tools/jgb2.py` `_audience_of(identity) == "property_manager"`），與現行授權相容。現行組態已打正式站（`JGB_API_BASE_URL=https://www.jgbsmart.com`、`USE_MOCK_JGB_API=false`），`role 20151` 資料即測試資料（516 份「測試物件／DEMO」合約）。

## B. 建立情境（快速建約、歸納謄本建物件、開修繕單、建帳單）：**JGB 要開的是「存取權」，不是新端點**

jgb2 已有內部寫入 API（`routes/api.php` `Route::prefix('agent/v1')->middleware(['internal_api_ip', 'agent_auth', 'internal_api_guard'])`）：

| 動作 | 端點 | 權限 |
|---|---|---|
| 建物件 | `POST /agent/v1/estates` | `_perm create` |
| 從謄本建物件 | `POST /agent/v1/estates/from-transcript` | `create` |
| 建約 | `POST /agent/v1/contracts` | `create` |
| 建帳單 | `POST /agent/v1/bills` | `create` |
| 查（同群組） | `GET /agent/v1/{estates,contracts,bills}[/{id}]`、`GET /agent/v1/whoami` | `read` |
| 開修繕單（external） | `POST /api/external/v1/repairs`（`contract_id` nullable，開單人由 `estates.agent_user` 帶入） | 現行 external key |

**AIChatbot 對 `agent/v1` 命中 0**（正對照 `external/v1` 命中 6）⇒ 若 demo 要演任何「建立」，JGB 需提供：

| # | JGB 要做 | 為什麼 | 證據 |
|---|---|---|---|
| B1 | **把 AIChatbot 的出口 IP 加進 `internal_api_ip` 白名單**（dev／demo 環境） | 群組第一道 middleware 是 IP 白名單 | `routes/api.php` `internal_api_ip` |
| B2 | **發一組 `agent_auth` 憑證**（`POST /agent/v1/agents` 建 agent、`/agents/{id}/permissions` 給 `create`＋`read`、`/agents/{id}/active` 啟用），並告知 header 形狀 | 第二道 middleware `agent_auth`；權限以 `_perm` 判 | `AgentManageController`、`->defaults('_perm', 'create')` |
| B3 | **`POST /agent/v1/estates/from-transcript` 的請求欄位規格**（謄本 OCR 對映後要送哪些鍵；AIChatbot `POST /ocr-mapping/transcript` 已能產 JGB 欄位對映） | 歸納謄本入庫的最後一段 | `EstateTranscriptWriteController@store`；AIChatbot `routers/ocr_mapping.py`、`DocumentType.transcript` |
| B4 | **`POST /agent/v1/contracts`／`bills` 的欄位規格與必填**（AIChatbot 線②合約 OCR 對映 17 欄已對 `Contract.php`，但寫入契約未定） | 快速建約的最後一段 | `ContractWriteController@store`／`storeBill` |
| B5 | `internal_api_guard` 的限制（每分鐘上限、是否限 dev 環境） | 估 demo 節流 | `internal_api_guard` |

AIChatbot 側對應要做的（不是 JGB 的事，列出以對齊）：agent 寫入工具 `jgb2.action.*`（兌現 `confirm.request` token；子 spec 未立）、`agent/v1` client、對應正本細目。

## B′. 修改情境（業主 2026-09-07 提的 demo 想像：「逾期 → 房東說幫我延 3 天 → MCP 呼叫修改 API」）：**jgb2 目前沒有任何修改帳單的端點，要新開**

jgb2 `bills` 只有 `POST`（建立）與 10 支 `GET`；全檔 19 支 `PATCH` 全是合約狀態流轉（`/extension`、`/confirm`、`/cancelMoveIn`…），沒有帳單到期日／金額的修改端點（查證：`rg -n "Route::(post|put|patch|delete)\('/bills" routes/api.php` 只命中 `POST`；正對照 `Route::get\('/bills` 10 支）。

| # | JGB 要開 | 形狀（建議，欄位由 JGB 定） | 為什麼 |
|---|---|---|---|
| B′1 | **`PATCH /agent/v1/bills/{bill_id}`**：只允許改 `due_date`（延後 N 天由系統算，⛔ 不收模型算好的日期；可選 `note`） | 請求 `{due_date_shift_days: 3, reason: "..."}` 或 `{due_date: "2026-09-08"}`；回應 `{id, due_date_before, due_date_after, updated_at}` | 「延 3 天」情境的唯一缺口；AIChatbot 端會以 `confirm.request` 人確認後才呼叫 |
| B′2 | 同群組的 `agent_auth` 憑證要含 `update` 權限（現行 `_perm` 只見 `read`／`create`） | `POST /agent/v1/agents/{id}/permissions` 加 `update` | 沒有 `update` 權限這支端點打不到 |
| B′3 | 修改要留審計：誰（agent id＋業務 `user_id`）、何時、改前改後 | 回應或 JGB 端 log | 對話改資料必須可追溯，與 AIChatbot 的 `trace_id`／`usage_events` 對得上 |
| B′5（security review 2026-09-08 S-10） | **資源粒度圈定**：`PATCH /agent/v1/bills/{id}` 控制器必須呼叫 `agentCanSee($request, $bill->role_id)`（`Internal/AgentScope.php` 既有樣板），且 demo／線上憑證綁團隊（`isRestricted()`）；請求欄位白名單只收 `due_date`（或 `due_date_shift_days`） | 否則 AIChatbot 持有的 `agent_auth` 權限（整把 key 的 create／update）遠大於發話的房東——confused deputy；現行 `AgentAuth.php` 只擋「有帶 `role_id` 且帶錯」 |
| B′4（候選，等業主定情境） | 其他修改：修繕單狀態／指派（`PATCH /repairs/{id}`）、合約備註（`PATCH /contracts/{id}/metadata` 已有但在 `need_login` 群組，非 agent 可用） | — | 先定 demo 要演哪幾個修改，再開 |

AIChatbot 側對應：`jgb2.action.bill_due_extend`（`{payload, confirmation_token}` → `{receipt}`，design 元件 3 形狀，子 spec `agent-write-tools` 未立）＋ `agent/v1` client。

## C. 待 JGB 確認（不擋 demo；③④⑤ LIFF 線用，業主裁先不併）

| # | 問題 | 證據 |
|---|---|---|
| C1 | **`emergency_status` 值域已對碼（2026-09-08，jgb2 三處用法一致）：DB 真值 2＝緊急、1＝非緊急**——內部寫入 `RepairController` `is_urgent==='true' ? EMERGENCY_STATUS : EMERGENCY_NON_STATUS`、急件判斷 `=== EMERGENCY_STATUS`（`RepairController`×2、`UserController`）；line-bot「急迫送 2」與 AIChatbot 註解皆正確。**⚠️ C1′（請 JGB 修）**：`app/Repair.php` 常數註解（`EMERGENCY_NON_STATUS = 1; // 緊急`）與 External API 列舉標籤（`RepairApiController` enum map `1 => '緊急', 2 => '非緊急'`）**與真值相反**，外部呼叫者照標籤送會送反；External `@store` 缺值預設 `EMERGENCY_NON_STATUS`（=1，非緊急）正確 | jgb2 `rg -n "EMERGENCY_STATUS" app/Http/Controllers/RepairController.php app/Http/Controllers/UserController.php`；`rg -n "=> '緊急'" app/Http/Controllers/External/RepairApiController.php` |
| C2 | ~~`is_urgent` 是否實裝~~ **已對碼：實裝**，`is_urgent` 直接等於 `emergency_status` 值（依 C1：要急件送 `is_urgent=2`） | jgb2 `RepairApiController@index` `where('emergency_status', (int) is_urgent)` |
| C3 | `GET /bills` 無入帳日（只有 `pay_at`）；要不要補 `accounting_date` | jgb2 盤查：`BillApiController@formatBill` 無 `accounting_date`（確認沒有） |
| C4 | ~~`broken_photos` 上限~~ **已對碼：`nullable|array|max:10`**（10 張） | jgb2 `RepairApiController@store` validation |

## D. 不是 JGB 的事（避免誤送）

催繳草稿（`dunning_draft`）是 line-bot 對 AIChatbot 的要求（回模板＋語氣等級），⛔ 不是 jgb2 端點。

## 查證指令

```bash
rg -n "prefix\('agent/v1'\)|internal_api_ip|agent_auth|_perm', 'create'" /Users/chenqinghuang/dev/work/jgb2/dev1/routes/api.php
rg -rn "agent/v1" rag-orchestrator --glob '!**/tests/**'          # 應零命中
rg -rn "external/v1" rag-orchestrator --glob '!**/tests/**' -l    # 正對照：≥6 檔
rg -n "class DocumentType" -A 4 rag-orchestrator/services/ocr_mapping/models.py
rg -n "api\.get_(bills|contracts|meters)\(" rag-orchestrator/services/agent/tools/jgb2.py
```


## E. jgb2 盤查（2026-09-08；業主原則「開 API 前先盤查 jgb2 有無此規格」；checkout `~/dev/work/jgb2/dev1`）

> 業主 2026-09-08（R6）：標「沒有」的項目（B′1 PATCH、B′2 `update`、B′6 冪等）由業主親自與 JGB 溝通、**預設會有**；AIChatbot 端照本表形狀先做替身，⛔ 不為其缺席另設計繞路。

| 需求 | jgb2 現況 | 證據（檔案＋符號） | 形狀差異／對替身的修正 |
|---|---|---|---|
| B1 IP 白名單 | 已有 | `app/Http/Middleware/InternalApiIp.php` `allowlist()`，讀 `config('jgb.internal_api_allowed_ips')`，支援 CIDR，不分環境 | — |
| B2 `agent_auth` | 已有 | `app/Http/Middleware/AgentAuth.php`：header `X-Agent-Key`／`X-Agent-Sig`／`X-Agent-Ts`／`X-Agent-Nonce`（簽章制）；`AgentManageController@store/@setPermissions/@setActive` | 真 client 要做簽章（demo 後切片）；**權限值域 `PERMS = ['read','create','codebase','manage']`，⛔ 無 `update`** |
| B3 from-transcript 欄位 | 已有 | `EstateTranscriptWriteController@store`：必填 `role_id`／`title`，可選 `fields`／`building_registration_transcript`；`ALLOWED_FIELDS` 白名單、省略不補值 | 替身 `create_estate` 欄位對齊白名單 |
| B4 contracts／bills 建立欄位 | 已有 | `ContractWriteController@store` validator；`@storeBill`：必填 `contract_id`、可選 `count`；**帳單到期日欄位＝`date_expire`** | 替身 `PATCH` 已用 `date_expire`（對上） |
| B5 `internal_api_guard` | 已有 | `InternalApiQueryGuard@handle`：`config('jgb.internal_api.max_concurrent', 4)`、slot TTL 30 s；限 `agent/v1`＋`internal/v1` | demo 併發 ≤4 |
| B′1 帳單修改端點 | **沒有** | `routes/api.php` 無 PATCH／PUT／DELETE `/bills`（正對照 GET 命中 3 支；POST 建立 1 支） | JGB 新開 `PATCH /agent/v1/bills/{id}`，只收 `date_expire`（或 `date_expire_shift_days`） |
| B′2 `update` 權限 | **沒有** | `app/AgentIdentity.php` `const PERMS` 四值 | JGB 加 `update` |
| B′3 審計 | 部分 | `InternalApiQueryGuard` 只在失敗／慢／429 記 `laravel.log`，不記 body；無 audit 表 | JGB 至少回 receipt（`id`、改前改後、`updated_at`）；AIChatbot 端以 `trace_id`／`pending_id` 對 |
| B′5 資源圈定 | 部分（樣板已有、需控制器呼叫） | `Internal/AgentScope.php` `agentCanSee()`／`applyAgentScope()`；`AgentAuth` `isRestricted()` | 新端點必須呼叫 `agentCanSee($request, $bill->role_id)` |
| **冪等** | **沒有** | `agent/v1` POST 路由無 `Idempotency-Key` 讀取、無 unique 約束 ⇒ 重送會重複建 | **B′6（新）**：請 JGB 支援 `Idempotency-Key` header（同 key 回同 receipt）；未支援前 AIChatbot 端以 Runtime 狀態 receipt 擋重送，網路層重試風險記帳本 |
| C1 值域 | 已對碼（DB 真值 2＝緊急）；**C1′ 標籤反了請 JGB 修** | 見 §C C1 | 替身沿用 2＝緊急 |
| C2 `is_urgent` | 已有 | `RepairApiController@index` | — |
| C3 入帳日 | 沒有 | `BillApiController@formatBill` 無 `accounting_date` | 待裁要不要補 |
| C4 照片上限 | 已有：10 | `RepairApiController@store` `max:10` | line-bot 上傳 ≤10 |

查證：`rg -n "allowlist\(\)" app/Http/Middleware/InternalApiIp.php`；`rg -n "X-Agent-Key" app/Http/Middleware/AgentAuth.php`；`rg -n "const PERMS" app/AgentIdentity.php`；`rg -n "storeBill\(|date_expire" app/Http/Controllers/Internal/ContractWriteController.php`；`rg "Route::(patch|put|delete)\(" routes/api.php | grep bills`（應 0，正對照 `Route::get\(.*bills` ≥3）；`rg -n "Idempotency" routes/api.php app/Http/Middleware`（應 0）。
