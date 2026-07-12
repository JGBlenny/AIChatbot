# 修繕租約清單契約（交付 jgb2 端，J 清單第 6 條）

> 交付日期：2026-07-12　來源：conversational-repair research.md 決策 1（G1）＋ jgb2 真碼盤查（file:line 齊）
> 盤查基準：jgb2 **master（7edb3b4）與 preview（ceacecb，2026-07-10）雙分支皆驗**——本文所有斷言兩分支一致成立（status-overview 本體、修繕全套、emergency_status 缺陷）；`room_number` 兩分支皆缺，R1 對兩邊都成立。行號以 master 為準；preview 因疊有各面向 G 擴充（診斷欄位等），對應段落行號有偏移、語義不變。
> 消費端**存在性驅動**：欄位出現即自動啟用 grounded 分支，缺失走降級——**不需與 AIChatbot 同步上版**。
> 定位：**E1 真 API 上線 gate 的最後一塊**。修繕建單 `POST /repairs` jgb2 已上線、AIChatbot 真分支已接妥；全鏈只剩「租客名下租約清單」一項。

## 結論先行：不需要新端點

原 J 清單第 6 條立案時假設「jgb2 尚無租客視角的租約清單端點」（G1 缺口）。真碼盤查推翻此假設：

**`GET /api/external/v1/contracts/status-overview`**（`ContractApiController@index`，routes/api.php:40）已具備所需能力：

- `role_id` 必填＋`user_id` 選填 → `where('to_user_id', user_id)`（ContractApiController.php:43-45）＝「某業者名下、某租客的合約」，正是雙證語義
- 內建 `active=1 AND is_newest=1` 過濾（:39-41）
- 回傳含 `id / status / bit_status / estate_id / title / city / district / address / date_start / date_end` 等欄位

AIChatbot 需要的五欄對照：

| AIChatbot 契約欄位 | status-overview 對應 | 現況 |
|---|---|---|
| `contract_id` | `id` | ✅ 已有 |
| `estate_id` | `estate_id` | ✅ 已有 |
| `estate_title` | `title` | ✅ 已有 |
| `display_address` | `city`＋`district`＋`address` 消費端拼接 | ✅ 已有 |
| `room` | `room_number` | ❌ **缺，唯一需求** |

## 需求清單（jgb2 端）

| # | 項目 | 建議做法 | 用途 |
|---|---|---|---|
| R1 | **status-overview 回應補 `room_number`** | `contracts.room_number`（VARCHAR 20, nullable）已在表上；select 清單（ContractApiController.php:30-37）與 `formatContract()`（:90-118）各補一行即可 | 修繕報修預填時向租客顯示「哪一間」（多租約候選選單的辨識欄）；nullable 消費端自行容錯 |
| R2 | **路徑/欄位正式命名確認** | 確認 `status-overview` 為此用途的正式接口、`room_number` 為正式欄名——AIChatbot 對接後改名會斷（沿 G-A1 教訓） | 防守 |
| R3 | （搭車建議）status-overview 補掛權限點 | 即帳號 J 清單 **J4**：routes/api.php:40 缺 `->defaults('_resource','contracts')->defaults('_action','read')`；本次動同一支端點，順手補兩行 | 修同授權範圍內的跨資源越權（root key 不受影響） |

**R1 是唯一阻塞項**；R2 回個話即可；R3 非阻塞、純搭車。

## J 級缺陷回報：`emergency_status` 語義兩層打架（真碼證據）

jgb2 內部行為一致以 **2=緊急、1=非緊急** 為真值：

- 寫入路徑：`RepairController.php:966`——`is_urgent==='true' ? EMERGENCY_STATUS(2) : EMERGENCY_NON_STATUS(1)`
- 讀取判斷 ×3：`RepairController.php:533, :1742`、`UserController.php:1246`——`is_urgent = (emergency_status === EMERGENCY_STATUS)`，:533 註解明載「緊急：true」
- `RepairService.php:115-116`：1→非緊急、2→緊急
- 常數命名本身（`EMERGENCY_STATUS`＝緊急＝2）也與上述一致

但兩處**註記層反了**：

| 位置 | 內容 | 問題 |
|---|---|---|
| `app/Repair.php:48-49` | `EMERGENCY_NON_STATUS = 1; // 緊急`、`EMERGENCY_STATUS = 2; // 非緊急` | 註解與常數名/全部行為用法相反 |
| `External/RepairApiController.php:462-463` | 對外 `mapping` 標 1=緊急、2=非緊急 | 跟著錯誤註解走，**對外契約層與 DB 真值反轉** |

影響：外部消費端（含 AIChatbot）依對外 mapping 實作，送單與顯示的緊急語義會與管理師後台相反——租客報「緊急」、後台顯示「非緊急」，優先序反轉。AIChatbot 端已同步排定修正（見下節）。建議 jgb2 修 :462-463 的 mapping 與 :48-49 註解（DB 值不動，純註記層，無資料遷移）。修正時請回個話，雙側對齊後才切真 API。

## 回應信封形狀（消費端解析依據）

`status-overview` 真實回應為扁平頂層（`successResponse` 用 `array_merge`，ContractApiController.php:146-151）：

```json
{
  "success": true,
  "mapping": { "bit_status": { "...": "12 碼中文對照" } },
  "data": [ { "id": 123, "status": 8, "room_number": "3F-1", "...": "..." } ],
  "pagination": { "current_page": 1, "per_page": 50, "total": 2, "total_pages": 1, "has_more": false }
}
```

消費端讀 `resp["data"]` 與 `resp["pagination"]`。回應內建的 `mapping` 僅供人讀；AI 端狀態集合判準一律以 `app/Contract.php:38-49` 為準，不依 `mapping` 做程式分支（防兩份對照表漂移——`emergency_status` 缺陷正是前車之鑑）。

## 消費端行為（AIChatbot 自理，jgb2 不需配合）

- **有效租約過濾在消費端做**：以回應中的 `status` 過濾，jgb2 不需加參數。修繕情境納入 `status ∈ {8, 16, 32, 64, 256}`：
  - 8 SIGNED／32 MOVE_IN_DONE：執行中，當然可報修
  - 16 MOVE_IN（點交送出）：點交檢查正是報修高發點，納入
  - 64 MOVE_OUT（點退送出）：尚未搬離，納入
  - 256 EARLY_TERMINATION（提前解約進行中）：仍居住，納入
  - 排除：1/2/4（簽約前）、128 MOVE_OUT_DONE（已搬離）、512/1024/2048（已解約/歷史）
  - 狀態語義依 `app/Contract.php:38-49`（12 狀態 ground-truth）；此集合為 AI 端產品判準，日後調整不需 jgb2 改版
- **display_address 拼接**：`city + district + address`；`room_number` 為 null 時省略房號行，不擋流程
- **0 筆／API 失敗**：一律誠實降級「請與管理師確認租約狀態」，不阻斷對話、不虛構
- **分頁**：租客名下有效租約為個位數量級，預設 `per_page=50` 足夠，消費端只讀第一頁
- **個資只讀不吐**：status-overview 連帶回傳 `to_user_phone / to_user_email / rent / deposit_amount` 等欄位，AIChatbot 僅消費上表五欄語義，其餘不進回話（沿帳號面向雙層防護慣例）

## E1 全鏈現況（對照）

| 環節 | jgb2 端 | AIChatbot 端 |
|---|---|---|
| 租約清單（本文件） | R1 補 `room_number` | `get_tenant_contracts` real 分支待實作：呼叫 status-overview → 五欄映射＋狀態過濾（現為 `NotImplementedError` 占位，jgb_system_api.py:769-771） |
| 修繕分類/項目 | ✅ `GET /repairs/categories` 已上線 | ✅ 真分支已接 |
| 修繕建單 | ✅ `POST /repairs` 已上線（RepairApiController@store:152，參數驗證與我方 `create_repair` 送出欄位逐一對齊，`contract_id` nullable 相容） | ✅ 真分支已接（jgb_system_api.py:399-412）；⚠️ `emergency_status` 語義沿用了 jgb2 對外 mapping 的反轉值（formatter/mock/預設值），切真 API 前需按 DB 真值（2=緊急）修正 |
| 切換機制 | — | `USE_MOCK_JGB_API=false`＋`JGB_API_KEY`（X-API-Key header） |

R1 交付後：AIChatbot 補 real 分支＋修正 `emergency_status` 語義 → E1 gate 可關 → 修繕對話式流程與 LINE 端到端具備上線條件。

## 分支落差提醒（E1/prod 切換的前置確認）

jgb2 的慣例是 API 修改先落 preview、完整功能以 master 為主。2026-07-12 雙分支比對，**AIChatbot 已對接的以下能力目前是 preview-only、尚未併入 master**：

- `GET /bills/{bill_id}`（帳單詳情，帳務面向已對接）
- `GET /tenants/registration-status`（G-A1，帳號面向已對接）
- `GET /roles/{role_id}/members`、`.../members/{user_id}/permissions`（G-A2）
- `GET /meters/{id}`（電表）
- `external_viewer` middleware（Layer 2 viewer 圈定）
- status-overview 的診斷欄位擴充（滯納金/違約金設定、簽約時間點、`to_user_login_email`）

若 prod 部署基準為 master，上述端點/欄位在 prod 均不存在——AIChatbot 各面向會走存在性降級（不炸、但 grounded 能力全關）。**E1 切真 API 前需確認：這批 preview 擴充已併 master 隨版上線，或 prod 部署包含 preview 內容。** R1（room_number）建議直接同批處理。

## 優先序建議

R1 一行欄位擴充即解鎖 E1（修繕真 API 上線 gate、LINE 端到端前置），投入極小、槓桿最大；建議隨下次 preview 部署帶上。
