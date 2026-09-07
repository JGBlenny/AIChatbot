# 給 JGB（jgb2）：LINE OA「JGB 房東管家」demo 需要開放／確認的 API（需求總表 v1，2026-09-07）

> 呼叫方：AIChatbot（rag-orchestrator）代表 LINE OA 使用者（代管業務／房東，`role_id=20151` 測試團隊）。demo 性質＝展示對話與 MCP 功能，非上線準確度。本表只列**要 JGB 做或答的事**；每條附證據（檔案＋可 grep 符號）。
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
| B′4（候選，等業主定情境） | 其他修改：修繕單狀態／指派（`PATCH /repairs/{id}`）、合約備註（`PATCH /contracts/{id}/metadata` 已有但在 `need_login` 群組，非 agent 可用） | — | 先定 demo 要演哪幾個修改，再開 |

AIChatbot 側對應：`jgb2.action.bill_due_extend`（`{payload, confirmation_token}` → `{receipt}`，design 元件 3 形狀，子 spec `agent-write-tools` 未立）＋ `agent/v1` client。

## C. 待 JGB 確認（不擋 demo；③④⑤ LIFF 線用，業主裁先不併）

| # | 問題 | 證據 |
|---|---|---|
| C1 | `emergency_status` 值域：AIChatbot 註解「2=緊急、1=非緊急（對齊 jgb2 DB）」，舊表單相反；缺值預設 2 | `image_recognition_service.py` `suggested_emergency`；jgb2 `Repair::EMERGENCY_NON_STATUS` |
| C2 | `GET /repairs?is_urgent=1` 是否實裝 | `RepairApiController` 接收 `is_urgent` |
| C3 | `GET /bills` 無入帳日（只有 `pay_at`）；要不要補 `accounting_date` | `docs/api/jgb_external_api_spec.md` §2.1 |
| C4 | `POST /repairs` `broken_photos` 上限（LINE 端全部照片） | `RepairApiController@store` |

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
