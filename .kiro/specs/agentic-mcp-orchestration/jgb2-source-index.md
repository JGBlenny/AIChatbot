# JGB（jgb2）事實來源目錄

> 用途：MCP 架構下，agent 可引用的 JGB 事實住在哪、哪些不可採信、JGB 更新時怎麼同步。
> 盤查日期：2026-09-04
> 盤查基準：`/Users/lenny/jgb/project/jgb/jgb2`，分支 `master`，HEAD `0b9574d3cf`（2026-09-04 11:40:36 +0800），工作樹乾淨（`git status --porcelain` 0 行）。
> 對照 checkout：`/Users/lenny/jgb/project/jgb_1/jgb2`，分支 `preview`，HEAD `62a3cd01c4`（2026-09-03 18:14:28 +0800）。

## 0. 使用紀律

1. **本表列的是「來源在哪」，不是「來源說什麼」。** 引用前一律開檔讀原文。
2. **⛔ 不寫行號。** jgb2 近一年 5,005 筆 commit，行號必漂；引用一律用檔案路徑＋可 grep 的符號。
3. **文件與程式衝突時 ⛔ 不自行選邊。** 本表 C 區（程式即事實）優先於 A/B 區（文件）；衝突要指出反證交回裁決。
4. **D 區（排除清單）的文件不得作為 agent 引用來源**，即使它們內容看起來相關。
5. 本表分類憑據：A 區 13 份、`docs/features/core-features/**`、`docs/feature-config-system.md` 兩份為**逐份精讀**；其餘為**抽讀開頭 30–60 行**分類。抽讀項若要升為引用來源，需先精讀確認。

## 1. 盤查統計（可重跑）

| 項目 | 實數 | 指令 |
|---|---|---|
| jgb2 文件總數 | 183（`docs/` 163 ＋ `ai/` 20） | `find docs ai -name '*.md' \| wc -l` |
| `external/v1` 端點 | 24 支 / 16 個 Controller | `grep -n "Route::" routes/api.php` |
| `agent/v1` 端點 | 18 支 | 同上 |
| `docs/api/` 文件 | 13 份 / 涵蓋 8 個 resource | `find docs/api -name '*.md'` |
| `database/migrations/` | 86 支 | `ls database/migrations/*.php \| wc -l` |
| 近一年動 External controller／routes 的 commit | 93 筆 | 見 §6 缺口 1 |
| 其中同時更新 `docs/api` 的 | 13 筆（**14%**） | 見 §6 缺口 1 |

## 2. 三層同步模型

| 層 | 內容 | 同步方式 | 人工成本 |
|---|---|---|---|
| **L1 執行期自同步** | 狀態／型態的中文標籤 | API 回應自帶 `mapping` 區塊，直接讀 | 零 |
| **L2 建置期機械比對** | 端點清單、回應欄位鍵、權限 resource/action | 對 `routes/api.php` 與 External controller 取指紋，比對本 repo 契約文件 | 一次性建置 |
| **L3 人工守門** | 產品行為規則（滯納金四版本、合約 12 狀態、發票兩模式…） | 知識列記 `source_doc` + `source_commit`，以 jgb2 commit 為觸發重讀 | 持續 |

---

## 3. A 區：對外 API 正本 —— 業者串接的唯一權威來源

**這是 jgb2 唯一一組明確為「業者要串 API 需要什麼」而寫、且維護頻繁的文件。**

### 3.1 文件清單

| 路徑 | 角色 | 對業者的價值 | 模板遵守 |
|---|---|---|---|
| `docs/api/README.md` | 索引 ＋ 開新 resource 的五步 SOP ＋ AI 提示詞範例 | 高 | 不適用 |
| `docs/api/_template.md` | 端點規格文件的固定骨架 | 低（開發模板） | 本身即模板 |
| `docs/api/authentication.md` | API Key 格式／限流／管理指令 | 高 | 不適用（機制敘述文） |
| `docs/api/external-api-permission.md` | 兩層權限模型、`viewer_user_id`、四種主體可讀範圍 | 高 | 不適用（機制敘述文） |
| `docs/api/estates.md` | 物件查詢端點規格 | 高 | 部分（缺「更新紀錄」小節） |
| `docs/api/repairs.md` | 修繕查詢／開立端點規格 | 高 | 遵守 |
| `docs/api/tenants.md` | 租客摘要／註冊狀態 | 高 | 遵守 |
| `docs/api/roles.md` | 團隊成員與權限；文件自述用途為「角色權限確認 grounding」 | 高 | 遵守（另加 grounding 流程章節） |
| `docs/api/meters.md` | 電表查詢；記錄 `is_poweron` 三態語義、`synced_at` 因廠商而異 | 高 | 遵守 |
| `docs/api/recharge-accounts.md` | 固定虛擬帳號 | 高 | 未獨立精讀（端點規格實際位置待查） |
| `docs/api/clients/一方生活.md` | per 業者串接指南（`recharge-accounts`） | 中 | 指南文類，不適用 |
| `docs/api/clients/行銷快手.md` | per 業者串接指南（`estates`） | 中 | 指南文類，不適用 |
| `docs/api/client-guide.md` | **與 `clients/行銷快手.md` 逐位元組相同**（各 14,914 bytes）；`README.md` 的文件結構清單未列它 ⇒ 疑似孤兒舊檔，待裁 | — | — |

`clients/*.md` 是**串接指南**不是客製端點文件：端點行為對所有客戶一致，指南只是套上該客戶被授權的 resource 與真實 Key。

### 3.2 `_template.md` 骨架（原文小節）

```
# [API 名稱] API
## 端點總覽
## [端點名稱]
### 請求 / ### 路徑參數 / ### Query 參數 / ### Request Body / ### 請求範例
### 回應
## 欄位說明
### [分類名稱] / ### 列舉值
## 注意事項
## 更新紀錄
```

### 3.3 開立新業者 API 規格的五步（`docs/api/README.md` §開發者指南）

1. 建立 Controller，放 `app/Http/Controllers/External/`，回應格式比照 `EstateApiController`（`success` + `data` + `pagination`），用 `$request->attributes->get('external_api_key')` 取認證後的 Key。
2. 註冊 route 於 `routes/api.php` 的 `external/v1` group，**必須加** `->defaults('_resource', ...)` 與 `->defaults('_action', ...)`。
   > 文件原文警語：「⚠️ 如果忘記加，該 route 的權限檢查會被跳過，任何 API Key 都能呼叫」
3. `php artisan external-api-key:run permission-add --key-id=客戶KeyID --resource=新resource --action=read`
4. 複製 `_template.md` 為 `新resource.md` 填規格，更新 README 索引表。
5. 在 `docs/api/clients/` 建 `客戶名.md`，格式參考 `clients/行銷快手.md`。

### 3.4 `external/v1` 完整端點表（24 支）

| Method | Path | Controller@Method |
|---|---|---|
| GET | `/estates` | `External\EstateApiController@index` |
| GET | `/estates/{id}` | `External\EstateApiController@show` |
| GET | `/contracts/status-overview` | `External\ContractApiController@index` |
| GET | `/contracts/{contract_id}/checkin-eligibility` | `External\ContractCheckinApiController@show` |
| GET | `/bills` | `External\BillApiController@index` |
| GET | `/bills/{bill_id}` | `External\BillApiController@show` |
| GET | `/payments` | `External\PaymentApiController@index` |
| GET | `/payment-logs` | `External\PaymentLogApiController@index` |
| GET | `/invoices` | `External\InvoiceApiController@index` |
| GET | `/invoice-logs` | `External\InvoiceLogApiController@index` |
| GET | `/repairs` | `External\RepairApiController@index` |
| GET | `/repairs/{id}` | `External\RepairApiController@show` |
| GET | `/repairs/categories` | `External\RepairApiController@categories` |
| POST | `/repairs` | `External\RepairApiController@store` |
| GET | `/recharge-accounts` | `External\RechargeAccountApiController@index` |
| POST | `/recharge-accounts` | `External\RechargeAccountApiController@store` |
| GET | `/tenants/{user_id}/summary` | `External\TenantApiController@summary` |
| GET | `/tenants/registration-status` | `External\TenantApiController@registrationStatus` |
| GET | `/roles/{role_id}/members` | `External\TeamMemberApiController@members` |
| GET | `/roles/{role_id}/members/{user_id}/permissions` | `External\TeamMemberApiController@permissions` |
| GET | `/roles/{role_id}/subscription` | `External\SubscriptionApiController@show` |
| GET | `/meters` | `External\MeterApiController@index` |
| GET | `/meters/{id}` | `External\MeterApiController@show` |
| GET | `/iot-manufacturers` | `External\IotManufacturerApiController@index` |

### 3.5 認證與兩層權限

- **認證**：Header `X-API-Key`（或 query `?api_key=`）。Key 格式 `jgb_` + 32 碼，SHA256 儲存，**只在建立時顯示一次**。實作 `App\Http\Middleware\ExternalApiAuth`。
- **Layer 1 — 這把 Key 能呼叫什麼**：`external_api_key_permissions`（`resource`:`action`，對應 route 的 `_resource`/`_action` defaults）＋ `external_api_key_whitelists`（限定能碰哪些 `user`／`role`）。`is_root` 的 Key **略過全部檢查**。
- **Layer 2 — 業者團隊內某成員實際看得到什麼**：帶 `viewer_user_id` 觸發，由 `App\Support\VisibleScope::resolve()` 依既有職權規則（owner／agent／biglandlord／tenant）自動圈定，**不可手動設定**。
  **⚠️ 只有 `bills`、`contracts/status-overview`、`payments`、`invoices` 四個端點支援圈定**；其餘 20 支帶了也不生效。
- **發放流程**：只有 artisan CLI，**沒有後台介面、沒有業者自助申請**。
  `App\Console\Commands\ExternalApiKeyCommand`，signature `external-api-key:run {action}`，動作：`generate|list|show|deactivate|activate|whitelist-add|whitelist-remove|whitelist-list|permission-add|permission-remove|permission-list`。

---

## 4. B 區：產品行為正本 —— 「這個狀態代表什麼」的來源

| 路徑 | 主題 | 備註 |
|---|---|---|
| `docs/contract-status-logic.md` | 合約 12 狀態 ＋ `status`／`bit_status` 雙欄機制 | 自帶版本與驗證日期 |
| `docs/invoice-issuance-specification.md` | 發票開立兩模式（到帳後／預約開立） | 自稱「規格文件」 |
| `docs/deposit-interest-feature.md` | 押金設算息計算規則 | |
| `docs/joerich-features.md` | 富喬系（`JOERICH_BIND_ROLE_IDS`）客製功能總覽 | 回答「我這功能為什麼跟別人不一樣」 |
| `docs/features/core-features/README.md` | 核心模組總索引 | 正本 |
| `docs/features/core-features/bill-management/README.md` | 帳單管理 | 單檔正本 |
| `docs/features/core-features/invoice-management/README.md` | 發票管理 | 單檔正本 |
| `docs/features/core-features/contract-signing/README.md` | 合約簽署 | 單檔正本 |
| `docs/features/core-features/early-termination/README.md` | 提前解約 | 單檔正本 |
| `docs/features/core-features/move-in-out/README.md` | 點交／點退 | 單檔正本 |
| `docs/features/core-features/late-fee/OVERVIEW.md` | 滯納金總覽 | **正本**（`late-fee/README.md` 只是索引） |
| `docs/features/core-features/late-fee/versions/VERSION_COMPARISON.md` | 滯納金四版本比較矩陣 | 附屬 |
| `docs/features/core-features/late-fee/versions/{joerich,nthurc,tonesang}/README.md` | 各業者版滯納金 | 附屬 |
| `docs/features/core-features/late-fee/core/GUIDE.md` | 通用版計算指南 | 附屬 |
| `docs/features/core-features/contract-renewal/README.md` | 續約導航頁 | 正本（**內容主體在下一列**） |
| `docs/features/core-features/contract-renewal/RENEWAL_INVESTIGATION_REPORT.md` | 續約調查報告 | README 標為主要內容來源，**實質正本** |
| `docs/features/core-features/contract-renewal/{DATABASE,SERVICE_LAYER,API_REFERENCE,NOTIFICATION_SYSTEM,RENEWAL_CODE_INDEX}.md` | 續約各切面 | 附屬 |
| `docs/features/client-customizations/{joerich,nthurc,tonesang}/README.md` | 三大客製客戶專屬規則 | |
| `docs/tenant-info-update/TENANT_INFO_UPDATE_README.md` | 租客資料變更機制（含 XXTEA 加密） | 同目錄其餘為一次性測試報告 |
| `docs/BOTBONNIE_INTEGRATION.md` | LINE Bot 串接機制 | 文件自記已知 bug |
| `docs/franchise-profit-share/franchise-profit-share-spec.md` | 加盟分潤匯出規則 | 同目錄其餘 6 份為一次性報告 |
| `docs/social-housing/*.md`（4 份） | 社宅表單欄位對應 | PM 版可讀性較高 |

**⚠️ 這批文件多數自帶四欄位**：`📅 最後更新` / `📝 版本` / `✅ 驗證狀態` / `📍 最後驗證日期`。
L3 同步就靠這四欄位 ＋ jgb2 commit 觸發。核對：`grep -rl "最後驗證日期" docs`

**⚠️ 沒有任何一份文件是從「業者在後台怎麼操作」寫的**（見 §5 的否定結論與正對照組）。B 區最接近的是業務語言的狀態機與規則，不是逐步點擊教學。

### 4.1 jgb2 自己的客服知識庫方法論（同題不同版本，值得對照）

`ai/chatbot/01.客服 LLM AI ChatBot 知識庫設計指南.md`、`ai/chatbot/01-1.知識單元格式.md`、`ai/chatbot/01-1-1.知識單元範例.md`、`ai/chatbot/01-2.指南中的 code 是什麼.md`、`ai/chatbot/01-3.是否可用 JS:TS 技術棧.md`

---

## 5. C 區：程式即事實 —— 優先於文件

### 5.1 執行期自描述：9 支 controller 回應自帶 `mapping`

`app/Http/Controllers/External/` 底下有 `getMapping()` 的：`BillApiController`、`ContractApiController`、`InvoiceApiController`、`PaymentApiController`、`RepairApiController`、`EstateApiController`、`MeterApiController`、`IotManufacturerApiController`、`SubscriptionApiController`。

例：`BillApiController::getMapping()` 回 `status`（6 值）／`invoice_status`（3 值）／`type`（6 值）三張中文對照表。
`SubscriptionApiController::getMapping()` 回 `plan_type`：`trial=試用`／`basic=基本`／`advance=進階`。

**⇒ L1 同步：agent 一律讀回應的 `mapping`，⛔ 不得自行維護標籤表。**

核對：`grep -rln "getMapping" app/Http/Controllers/External/`

### 5.2 列舉常數（散在 Model，非集中）

| 主題 | 位置 | 符號 |
|---|---|---|
| 合約狀態位元 | `app/Contract.php` | `CONTRACT_READY`(1) … `CONTRACT_HISTORY_DONE`(2048)，共 12 個 |
| 合約付款方式 | `app/Contract.php` | `PAYMENT_METHOD_VENDOR`／`_CASH`／`_RECHARGE_ACCOUNT` |
| 合約種類 | `app/Contract.php` | `GENERAL_HOUSING`(1)／`SOCIAL_HOUSING`(2) |
| 帳單狀態 | `app/Bill.php` | `BILL_PREPARE`(1)／`BILL_READY`(2)／`BILL_PAYED`(8)／`BILL_COMPLETE`(16)／`BILL_PREPARE_TO_READY`(32)／`BILL_EXPIRED`(64) |
| 帳單型態 | `app/Bill.php` | `BILL_TYPE_RENT`(1) … `BILL_TYPE_DEPOSITRATE`(6) |
| 帳單類別 | `app/Bill.php` | `CATEGORY_PROPERTY_OPERATION`(1) … `CATEGORY_DEPOSIT`(6)　**⚠️ `getMapping()` 未含此欄的標籤表** |
| 發票狀態 | `app/Bill.php` | `INVOICE_STATUS`（陣列常數） |
| 角色／業態 | `config/role.php`、`config/character.php` | config 陣列，非 const |

**⚠️ `app/Const.php` 不是 enum 檔**，只是 model→table 名對照與時間常數。

近一年常數實際改動：`app/Contract.php` 9 次、`app/Bill.php` 5 次（約每月一次）。

### 5.3 `agent/v1` —— jgb2 已有的 AI agent 專用 API 面

與 `external/v1` 是**完全獨立的兩套認證與權限模型，⛔ 不共用權限表**。

| | `external/v1` | `agent/v1` |
|---|---|---|
| 認證 middleware | `ExternalApiAuth`（`X-API-Key`） | `AgentAuth`（SSH ed25519 簽章） |
| 身分表 | `external_api_keys` | `agent_identities`（`App\AgentIdentity`：`label`,`fingerprint`,`pubkey`,`permissions`,`is_active`） |
| 權限 | `_resource`/`_action` 對權限表 | `permissions` JSON：`read`／`create`／`codebase`／`manage` |
| 網路 | 公網 | `InternalApiIp` IP 白名單，讀 `.env` 的 `INTERNAL_API_ALLOWED_IPS`；**未設定時全部 403（inert）** |

18 支端點：`whoami`／`estates`(2)／`contracts`(2)／`bills`(2)／`teams`／`POST estates`／`POST contracts`／`POST bills`／`code/tree`／`code/file`／`code/grep`／`agents`(2)／`agents/{id}/permissions`／`agents/{id}/active`。

`Internal\CodeQueryController` 的 `tree`／`file`／`grep` 讓 agent 唯讀查 prod 原始碼，三道邊界：realpath 須在 `base_path()` 內、須命中 `config('jgb.internal_code_roots')`、不得命中 `config('jgb.internal_code_deny')`。

---

## 6. 缺口登記（實查，附正對照組）

| # | 缺口 | 證據 | 影響 |
|---|---|---|---|
| 1 | **`docs/api/` 與程式同步率 14%** | 近一年動 External controller／`routes/api.php` 的 93 筆 commit 中，只有 13 筆同時改 `docs/api`。`docs/api` 最後異動 2026-07-04；External controller 2026-07-27；`routes/api.php` 2026-09-03 | 文件覆蓋 8 resource，實際 24 端點 |
| 2 | **訂閱方案有端點、零文件** | `GET /roles/{role_id}/subscription` 存在且有 `plan_type` mapping；`docs/api/` 無 `subscription.md`；`docs/features/core-features/subscription-system/` 底下**只有 `.DS_Store`**。全文搜「訂閱\|subscription」無任何一份以它為主題（**正對照組**：同法搜「滯納金」命中 31 份） | 業者問「我是什麼方案／進階多了什麼」答不出來 |
| 3 | **業者 API 的四張權限表無 migration** | `external_api_keys`／`external_api_key_permissions`／`external_api_key_whitelists`／`external_api_logs` 在 `database/migrations/` 內容全文搜尋零命中（**正對照組**：同法搜 `recharge_account` 命中 3 支 migration） | schema 不在版控，開新業者時權限欄位真相只能問線上 DB |
| 4 | **AIChatbot 不認得帳單 `category`** | `BillApiController` 回應帶 `category`，但 `getMapping()` 無其標籤表；本 repo `rag-orchestrator/services/jgb/` 全目錄搜 `屋主直收\|屋主提領\|備用金\|CATEGORY_DEPOSIT` 零命中（**正對照組**：同目錄 `bit_status` 命中 26 次） | 「屋主直收帳單是什麼」答不出來 |
| 5 | **`client-guide.md` 是孤兒重複檔** | 與 `clients/行銷快手.md` 逐位元組相同（各 14,914 bytes）；README 文件結構清單未列它 | 待裁：刪除或標示廢止 |
| 6 | **`feature-config-system.md` 文件分裂** | `docs/feature-config-system.md`（2026-03-12，自標 v1.1）vs `docs/features/_architecture/feature-config-system.md`（2026-03-14，自標 v1.0.0）。日期較新者版本號較小，內容卻多了 `allow_role_settings`、`batchSetConfig()`。兩份互不引用，無廢止聲明 | 待裁 |
| 7 | **本 repo 硬表與 `mapping` 重複** | `rag-orchestrator/services/jgb_response_formatter.py` 已讀 `api_result.get("mapping", {})`，但 `rag-orchestrator/services/jgb/bills.py` 又硬寫 `STATUS_LABELS` | 兩個來源，遲早分歧 |
| 8 | **無任何自動同步機制** | 全 repo 搜尋無腳本／CI 讀 jgb2 repo 或呼叫 jgb2 API 更新本地文件／知識；知識列無 `source_doc`／`source_version` 欄位 | 現況全靠人工一次性快照 |

---

## 7. D 區：排除清單 —— ⛔ 不得作為 agent 引用來源

| 路徑 | 排除理由 |
|---|---|
| `docs/1-architecture.md`、`2-backend.md`、`3-frontend.md`、`4-database.md`、`5-api-routes.md`、`6-models.md`、`7-business-logic.md`、`8-deployment.md`、`9-development.md` | 全部 RD 視角。用「後台\|點擊\|按鈕\|畫面\|操作步驟」掃這 9 份 **0 命中**（**正對照組**：同組關鍵字在 `docs/help-assistant/`、`docs/ops/report-compression-playbook.md` 有命中）。`5-api-routes.md` 講的是 Laravel 路由架構，**不是** `docs/api/` 那種對外規格；`7-business-logic.md` 講「程式碼怎麼判斷」不是「業者按什麼」 |
| `docs/help-assistant/**`（17 份） | 是 jgb2 平台**內建浮動教學按鈕 widget** 的開發文件，不是 AI 客服。`ROADMAP.md` 自述 Phase 1 尚待實作 |
| `docs/feature-config*`（8 份）、`docs/features/_architecture/**`（4 份） | 內部工程。`docs/feature-config-development-guide.md` 自述「讀者：Claude（AI 助手），協助 RD 操作」 |
| `docs/refactoring/**`（6 份）、`docs/customer-service-modularization/**`（11 份） | 重構過程紀錄 |
| `docs/plans/**`（4 份）、`docs/superpowers/**`（7 份）、`docs/diy-contract-pdf-upload-precheck-plan.md`、`docs/deposit-interest-refactoring-plan.md` | 單一工單的設計／修復計畫 |
| `docs/*-audit.md`（`bills-all-active-performance-audit`、`bills-search-performance-audit`）、`docs/VERIFICATION_REPORT.md`、`docs/ARCHITECTURE_ENHANCEMENT_SUMMARY.md`、`docs/DOCUMENTATION_ROADMAP.md`、`docs/README.md` | 一次性報告／meta 文件 |
| `docs/adr/**`（4 份）、`docs/architecture/HELPER_VS_SERVICE.md`、`docs/services/README.md`、`docs/ops/report-compression-playbook.md` | 內部工程決策與維運 |
| `docs/balance-invoice-group/**`（6 份）、`docs/community-balance-invoice/**`（3 份）、`docs/recruitment_pages/**`（3 份）、`docs/bills/**`（2 份）、`docs/franchise-profit-share/` 除 spec 外 6 份、`docs/tenant-info-update/` 除 README 外 4 份 | 一次性紀錄／已移除功能 |
| `ai/docs/**`（12 份）、`ai/agents/**`（2 份）、`ai/instructions.md`、`ai/cc-sdd.claude.md` | jgb2 RD 團隊給 coding agent 的開發規範，與客服無關 |

---

## 8. 同步作業程序（觸發式，非週期式）

**觸發點是 jgb2 的 commit，不是日曆。**以下 `<上次同步的 commit>` 記在本檔 §9。

```bash
cd /Users/lenny/jgb/project/jgb/jgb2
git fetch origin && git checkout master && git pull

# 1) 端點是否增減
git diff <上次同步的 commit>..HEAD -- routes/api.php

# 2) 回應欄位／mapping 是否變動
git diff <上次同步的 commit>..HEAD -- app/Http/Controllers/External/

# 3) 列舉常數是否變動（B 區知識的判準）
git diff <上次同步的 commit>..HEAD -- app/Contract.php app/Bill.php | grep -E '^[+-].*const [A-Z_]+'

# 4) A 區／B 區來源文件是否變動
git diff --stat <上次同步的 commit>..HEAD -- docs/api docs/features/core-features \
    docs/contract-status-logic.md docs/invoice-issuance-specification.md \
    docs/joerich-features.md docs/deposit-interest-feature.md

# 5) 權限表 schema 是否終於進了 migration（缺口 3 的解除條件）
grep -rl "external_api_key" database/migrations/
```

任一項有輸出 ⇒ 對應處置：

| 變動 | 處置 |
|---|---|
| 1／2 有輸出 | 更新本 repo `docs/api/*-api-contract.md`，重跑 L2 比對 |
| 3 有輸出 | 檢查是否為 agent 已引用的語義；若標籤變動且該 controller 有 `getMapping()`，L1 自動吸收，⛔ 不需改碼 |
| 4 有輸出 | 重讀該份文件，比對已匯入知識列，決定改寫或退休 |
| 5 有輸出 | 缺口 3 解除，權限規格可改為從 migration 機械抽取 |

---

## 9. 同步狀態

| 項目 | 值 |
|---|---|
| 上次同步的 jgb2 commit | `0b9574d3cf`（2026-09-04 11:40:36 +0800，master） |
| 上次同步日期 | 2026-09-04 |
| 未解缺口 | §6 全部 8 項 |

---

## 10. 待裁

1. **MCP 工具面掛哪邊**：只掛 `external/v1`（現況、公網可達、業者同權限）／加掛 `agent/v1`（多 codebase 查詢，但要開 IP 白名單）／兩套分屬不同工具圈。
2. **L2 契約漂移偵測要不要進 CI**：成本落在解析 16 支手組陣列的 External controller（**它們不用 API Resource class**，正對照組：`app/Modules/CustomerService/*/Resources/` 確實有 Resource 類，證明專案有此慣例只是 External 沒用）。
3. **缺口 5、6 的文件分裂**：刪除孤兒檔／標示廢止／保留不動。
4. **缺口 2 的訂閱文件**：要不要向 jgb2 團隊要求補 `docs/api/subscription.md` 與 `core-features/subscription-system/README.md`。
