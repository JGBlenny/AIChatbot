# IoT（智慧設備）J/G 契約（交付 jgb2 端）

> 交付日期：2026-07-04　來源：iot-conversational-facets research.md（jgb2 三路真碼盤查，file:line 齊；台科電=DAE 已確認）
> 消費端一律**存在性驅動**：欄位/端點出現即自動啟用分支，缺失走降級——**不需與 AIChatbot 同步上版**。

## 🔴 J-I0：`/meters` type 過濾錯型別——端點恆回空（阻塞級，一行修復）

| 兩邊 | 值 | 證據 |
|---|---|---|
| 全系統 `iots.type` 實際存值 | 字串 `'power_meter'` | DAE 建檔 DaeJob.php:455；內部查詢 Iot.php:1766；IotController.php:493/1359/1510/1620/1738/1861 全用字串比對 |
| MeterApiController 過濾 | `->where('iots.type', 3)`（註解「type=3 為電表」） | MeterApiController.php:37 |

**後果**：`'power_meter' ≠ 3` → `GET /api/external/v1/meters` **對所有 role 恆回 0 筆**。preview 實測（2026-07-04）：role 37305（DAE 綁定 ×2、活躍業者）與 20151 皆回空，交叉印證。

**修法**：`->where('iots.type', 'power_meter')`。**✅ jgb2 已修復並部署（2026-07-04）：37305 實測回 50 顆電表、欄位齊全、AIChatbot 真資料 e2e 全綠。**

**對 AIChatbot 的影響**：電表排障面向的 grounding 完全依賴此端點——**J-I0 是 IoT 領域唯一的真阻塞**（其餘開發以 stub 照常推進）。修好請通知，我方以 role 37305 立即重驗。

## 🔵 J-I1～I3：缺陷回報（非阻塞，靜態證據）

| # | 缺陷 | 證據 | 影響與建議 |
|---|---|---|---|
| J-I1 | `is_poweron=-1`（未知/從未連線）被 `(bool)` 轉成 **true** | MeterApiController.php:112 | 「從未連線」被消費方判成「供電中」。建議三態露出（-1/0/1）或 null。AIChatbot 端已防護（離線分支優先、離線不引用 is_poweron），修復屬防禦縱深 |
| J-I2 | `Iot::setPowerOn()` 對 DAE 派 `DaeJob('powerOn'/'powerOff')` 為**死路徑** | Iot.php:730-741 vs DaeJob.php:81-383（switch 無此 case） | DAE 實際開關電走 changeMode；此路徑靜默無效——前台若有功能接這條會看似成功實則沒動作 |
| J-I3 | SkyWatch 綁定更新查詢在字串上呼叫 `->where()` | Iot.php:1796（`where('manufacturer', $bindManufacturer->where('is_active', 1))`） | 語法錯置，綁定更新邏輯失效 |
| 觀察級 | Miezo 離線時 power 指令靜默丟棄無回報；Miezo 不寫 `synced_at` | MiezoJob.php:197/266/330；synced_at 僅 DaeJob/SkywatchJob 寫入 | 使用者以為操作成功；對外 API 的 synced_at 對 Miezo 電表恆舊值/NULL（AIChatbot 端措辭已降級處理） |

## 🟡 G 清單：選配（不做照樣上線）

| 項目 | 說明 |
|---|---|
| `/meters` 支援 `keyword`（對 name/estate_name）或 `/meters/{id}` 單筆直查 | AIChatbot 現以「拉全列（≤200）＋client 端過濾」替代——電表數大的業者才有差 |
| `is_poweron` 三態露出 | 同 J-I1，修 bug 即是升級 |

**必要新開 API：無**——J-I0 修復後，`/meters` 現有欄位（is_poweron/balance/available_meter/is_online/synced_at/current_reading/estate_name）已齊未給電判因全部所需。

## 🟠 測試資料請求

**修復 J-I0 後，請確認 role 37305 名下電表可正常回列**（該 role 有 DAE 綁定，應為現成測試素材）；若其 iots 表無資料，請提供任一有 DAE（台科電）電表的 preview role——供 AIChatbot 電表排障 e2e 真資料多輪驗證。

## 消費端承諾

- 全部唯讀：AIChatbot 對 IoT 只消費 GET（meters/iot-manufacturers）；復電/斷電/模式切換/儲值**不代操作**，只判因與指路。發 key 時建議僅授 `meters:read`、`iot-manufacturers:read`。
- 存在性驅動：J-I0 修復前電表排障走降級（引導問句/導客服），不阻斷、不虛構。
- 離線快照語義：`is_online=false` 時所有欄位以「截至最後同步」措辭呈現，不引用 is_poweron 下供電結論（J-I1 防護）。
- 度數/餘額/單價一律引用回傳存值（本為 DAE 鏡像值），不重算。

## 優先序建議

**J-I0（一行）→ 確認 37305 測試資料** 即解鎖 IoT 領域全部驗證；J-I1~I3 依排程；G 選配隨緣。
