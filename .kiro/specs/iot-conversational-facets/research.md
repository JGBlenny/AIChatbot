# 研究記錄：iot-conversational-facets

> 建立時間：2026-07-04
> 目的：jgb2 電表真碼盤查（三路平行）——design 的 ground truth 依據
> 盤查基準：`/Users/lenny/jgb/project/jgb_interrogation/jgb2`；使用者確認＋真碼雙證：**台科電 = DAE**

## 摘要

### 調查範圍
gap-analysis §四的 7 條：未給電決策樹語義、台科電對照與廠商差異、meters/recharge-accounts 參數面、離線判定、舊案過濾（後置）、e2e 真資料前置。

### 關鍵發現
- **台科電 = DAE 確認**（使用者＋`Iot.php:88-101`「台科電雲端儲值系統」）：唯一儲值型電表廠商（`is_topup=1` 寫死，DaeJob.php:463）；Miezo=鳴周（非儲值、遠端開關電）；SkyWatch 是門鎖/攝影機**非電表**。
- **未給電判因語義證實**：`is_poweron` 是**廠商 mode 鏡像**（DAE 四模式 powerOff/powerOn/topUpWithpowerOff/topUpWithpowerOn），**JGB 無「餘額歸零→斷電」程式**——儲值模式下斷電/儲值後復電都是 DAE 電表端行為，系統事後同步得知；**無斷電原因欄位**（無法區分餘額耗盡/手動斷電/模式切換）。
- **「度數不增加/數據不同」三層機制**：①每小時 :35 才同步一次（天然最多 1 小時落差）；②**DAE 帳密失效/未開 API 服務 → login 負快取 1 小時 → 該帳號全部電表停止同步**（Helper.php:4638-4675 註解自證，高頻真因）；③job 失敗不重試。
- **儲值鏈與「儲值了電還沒來」**：租客 topUp（需 enable_topup=1 且 **is_online=1**）→ type=5 儲值帳單（效期 4 天）→ 付款觸發 DaeJob topUp → **DAE webhook 不可靠**（IotReconcileTopup.php:10-31 官方註解：近 30 天 77 筆未回報中 72 筆實已入值）→ 對帳排程每小時＋Slack 告警人工補。
- **recharge-accounts ≠ 電表儲值帳戶**（設計修正）：它是「固定虛擬帳號（銀行 VA）」匯入管理——與電表無直接關聯。IoT 設定引導**不需要 ground 它**。
- **消費端陷阱×2**：①`is_poweron=-1`（未知/從未連線）被 API `(bool)` 轉成 **true**（MeterApiController.php:112，語義失真→J 清單）；②Miezo 不寫 `synced_at`（恆舊值/NULL）。

## 研究主題

### 主題 1：未給電決策樹（R2.2 定案）

builder 決定性語義（全部由現值判，不臆測原因）：

| 現值組合 | 判定 | facts 口徑 |
|---|---|---|
| `is_online=false` | **先判離線**（其他欄位皆為最後同步快照） | 「電表目前離線，以下為截至 {synced_at} 的最後狀態」＋離線分支 |
| online＋`is_poweron=false`＋`enable_topup=true`（儲值模式）＋`balance` 低/0 | 高度可能：儲值餘額耗盡、電表端自動斷電 | 「餘額 {balance} 元/可用 {available_meter} 度——儲值模式下餘額耗盡電表會自動斷電；**儲值入帳後電表端會自動復電**（mode→topUpWithpowerOn 鏡像，Iot.php:969-977）」 |
| online＋poweron=false＋非儲值模式（或餘額充足） | 供電被關閉（手動/模式切換） | 「供電目前為關閉狀態——可於 IoT 裝置頁切換供電模式（強制供電/斷電/儲值）」；**系統無斷電原因紀錄**，不臆測誰關的 |
| online＋poweron=true | 供電正常 | 轉向：跳電/迴路/硬體 → 導廠商；或根本不是這顆表 |

注意：斷電/復電為 **DAE 電表端行為**（repo 只有鏡像證據）——facts 措辭用「電表端會自動…」不稱系統行為。

### 主題 2：離線分支與度數異常（R2.3/R2.4）

- 離線判定：無 synced_at 逾時排程——`is_online` 只在每小時同步/前台觸發當下由廠商 API 結果寫入（DaeJob.php:142-158/241-249；MiezoJob.php:88-165）。
- 離線分支 facts：①最後同步時間（synced_at；**Miezo 無此欄**→措辭降級）；②**DAE 高頻真因：廠商帳號密碼變更/未開 API 服務**（引導至 IoT 裝置頁重新驗證帳密——綁定列 is_active 仍會是 1，別被誤導）；③設備斷網/斷電重啟指引；④仍離線導廠商（台科電）附設備資訊。
- 度數異常 facts：每小時同步一次（1 小時內落差正常）；`current_reading` 為 JGB 側最後同步值；不增加→查 synced_at 是否卡住（帳號失效整批停同步）；度數只引用存值。
- 儲值後電未來：帳單付了但 webhook 未回（官方證實高發）→ 系統每小時對帳自動補認、對不到會告警人工處理——引導稍候或聯繫客服，**不代操作**。

### 主題 3：識別鏈與端點參數面（R2.1/R8.1）

- `GET /meters`：`role_id` 必填＋`estate_id` 選填＋分頁（預設 50/上限 200）；**無 keyword、無單筆直查、無 viewer 圈定**（MeterApiController.php:21-54；viewer 僅 Bill/Payment/Invoice/Contract 四支套用）。
- 回應含 `estate_id`/`estate_name`（estates.title）→ **識別 adapter 設計：拉 role 全列（≤200）後 client 端以 keyword 對 estate_name/name 過濾**，多顆列候選（label：name＋estate_name＋meter_type）；免要求 jgb2 加參數。
- 關聯鏈（跨域備用）：iot ↔ estate（iot_estate）↔ contract（estate_id）——合約→電表可行（Iot.php:163-180）。

### 主題 4：recharge-accounts 定性（設計修正）

銀行固定虛擬帳號的匯入/查詢（tenant_name/email/phone＋bank/account），與電表儲值無關聯鍵（RechargeAccountApiController.php:75-89）。**IoT 設定引導不 ground 此端點**；「儲值單價/餘額」的資料源就是 meters 的 `rate`（DAE 回傳鏡像）與 balance。

### 主題 5：J/G 清單（IoT）

**J 清單（缺陷回報，靜態證據）**：
- J-I1 `is_poweron=-1`（未知）被 `(bool)` 轉 true（MeterApiController.php:112）——消費端會把「從未連線」判成「供電中」。建議三態露出或 null。**消費端防護：is_online=false 時不引用 is_poweron 下結論**（我方 builder 以離線分支優先，天然規避）。
- J-I2 `Iot::setPowerOn()` 對 DAE 派 `DaeJob('powerOn'/'powerOff')` 為死路徑（DaeJob switch 無此 case，Iot.php:730-741 vs DaeJob.php:81-383）——DAE 實際開關電走 changeMode。
- J-I3 SkyWatch 綁定更新查詢在字串上呼叫 `->where()`（Iot.php:1796，語法錯置）。
- （觀察）Miezo 離線時 power 指令靜默丟棄無回報（MiezoJob.php:197/266/330）；Miezo 不寫 synced_at。

**G 清單：趨近於零**——meters 欄位已足主場景。選配候選：meters 支援 keyword/單筆直查（現以 client 端過濾替代，非必要）；is_poweron 三態（同 J-I1）。

### 主題 6：e2e 真資料前置〔待辦〕

preview role 20151 無電表（meters 空）。選項：請 JGB 指一個有 DAE 電表的測試 role／造資料；找不到則 e2e 驗降級態＋整合層 stub 驗分支（誠實標注覆蓋差異）。

### 主題 7：20 舊案過濾（知識工程前置，摘要）

以本次真碼對照：「電錶已安裝要怎麼串接」「儲值單價怎麼設」（單價是 DAE 端設定、JGB 鏡像）→ 口徑更新後轉製；「電錶數據與 JGB 不同」「度數不增加」→ 主題 2 機制轉製（高價值）；「電錶斷線怎麼辦」→ 離線分支；門鎖硬體 6 案 → 單發包（悠遊卡/磁扣屬廠商功能，音量不可調等以廠商文件為準、超出即導廠商）；skywatch 匯入密碼、istaging → 剔除（非現行/範圍外）。逐案存廢表於知識工程任務產出。

## 技術選型

| 決策 | 選擇 | 理由 |
|---|---|---|
| 電表識別 | meters 全列＋client keyword 過濾（estate_name/name）＋候選 | 端點無 keyword 參數；role 電表數 ≤200 可行；零 jgb2 依賴 |
| 電表排障 grounding | select='api' `jgb_meters`＋`meter_ref`（`deterministic_id:false`——識別多為物件名/房號文字） | 沿 member_ref 模式 |
| 設定引導 grounding | select='category'＋**明填 target_user**（account 坑） | 無需 API（recharge-accounts 定性修正） |
| builder 位置 | `iot.py` 平行加 `build_meter_facts`＋`METER_FACE_BUILDERS`；diagnose_iot 零回歸 | 同前三域慣例 |
| formatter 分發 | `jgb_meters` endpoint face 命中 → iot builder | 同 jgb_team_members 模式 |

## 風險登記

| 風險 | 影響 | 緩解 |
|---|---|---|
| is_poweron=-1 失真（J-I1） | 未連線被判供電中 | builder 離線分支優先；J 清單推修 |
| e2e 無真電表資料 | e2e 覆蓋降級 | 請 JGB 指測試 role；stub 補整合覆蓋並標注 |
| 「儲值」錨點與帳務誤吸 | 路由 | 錨點語彙分工＋路由點名測試 |
| Miezo synced_at 恆舊 | facts 誤導 | builder 對 Miezo 略過 synced_at 措辭 |

## 開放問題

1. e2e 真資料 role（請 JGB 提供）。
2. J-I1 三態露出是否由 jgb2 修（消費端已防護，非阻塞）。
