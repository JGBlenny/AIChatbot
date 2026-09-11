# JGB API 整合模組

> ⚠️ **2026-09-11 舊鏈退役對碼**：本檔原本描述的「表單填寫觸發 API」流程
> （`form_manager` 收集資訊 → `call_api` → `api_call_handler` →
> `jgb_response_formatter` 分派）**已隨舊 REST 對話鏈刪除**——`api_call_handler.py`／
> `jgb_response_formatter.py` 都已不存在。目前的呼叫路徑改為 `/mcp` 的
> `agent.turn`／`jgb2.query.*` 工具直接呼叫本目錄模組，見下方「現況架構」。
> `jgb/contracts.py`、`jgb/bills.py`、`jgb/estates.py`、`jgb/iot.py`、
> `jgb/repairs.py` **五個模組皆已建成**（原表格中的「待建」已完成，見下方檔案職責）。

## 現況架構

```
使用者訊息（經 X-JGB-Identity 帶身分）
  → /mcp 的 agent.turn 或 jgb2.query.* 工具（services/agent/tools/jgb2.py）
  → JGBSystemAPI（jgb_system_api.py；mock / real 切換，經 transport.py 的 Transport 契約）
  → 依 domain 呼叫對應模組的 face-builder / format_*_response（jgb/contracts.py、
    jgb/bills.py、jgb/estates.py、jgb/iot.py、jgb/repairs.py 等）
  → 產出 facts 文字，交由 agent runtime 組進最終答覆（經 Output Verifier 逐句驗引用）
```

契約細節見 `docs/api/mcp-facade.md` §7.1（`agent.turn`）與
`rag-orchestrator/services/agent/tools/jgb2.py`（各 `jgb2.query.*` 工具的身分閘與
候選列表邏輯）。

## 檔案職責

| 檔案 | 職責 | 不應做的事 |
|---|---|---|
| `jgb_system_api.py` | JGB API client，mock/real 切換，只負責打 API 拿資料 | 不做業務邏輯判斷、不做回應格式化 |
| `transport.py` | HTTP transport 契約（`Transport` Protocol），mock 與 real 共用同一份呼叫端契約 | 不做業務判斷 |
| `jgb/contracts.py` | 合約業務邏輯判斷 + 回應格式化（`format_contract_response`、`check_can_*`） | 不打 API、不處理其他模組 |
| `jgb/bills.py` | 帳單診斷引擎 + 面向 fact-builder（B01–B04、P04 等） | 同上 |
| `jgb/repairs.py` | 修繕業務邏輯判斷 + 回應格式化 | 同上 |
| `jgb/iot.py` | 電表/IoT 業務邏輯判斷 + 回應格式化 | 同上 |
| `jgb/estates.py` | 物件業務邏輯判斷 + 回應格式化 | 同上 |
| `jgb/accounts.py` | 帳戶面向 fact-builder | 同上 |
| `services/agent/tools/jgb2.py` | `/mcp` 的 `jgb2.query.*` 工具入口：身分閘、候選列表、逐模組分派 | 不寫 JGB 專屬業務判斷（那是各 `jgb/*.py` 的事） |

## 每個模組的標準結構（以 contracts.py 為例）

```python
# 1. 常數定義
class ContractBit:       # bit_status bitmask 常數
class ContractStatus:    # status 當前階段常數

# 2. 狀態工具函式
has_bit()                # 檢查 bitmask
decode_bit_status()      # 拆解為標籤列表
get_current_stage()      # 判斷當前階段（人可讀）

# 3. 操作條件判斷（對應 JGB 系統的 can* 方法）
check_can_invite()       # → { can_do, operation, blockers }
check_can_move_in()
check_can_move_out()
check_can_early_termination()
check_can_renew()

# 4. 回應格式化（產出客戶理解的自然語言）
format_contract_response()  # 主入口，根據用戶問題 + API 資料產出回應
```

## 回應格式化原則

### 不要
- 列出所有操作的 ✅❌ 清單（像診斷報告）
- 直接 dump JSON 或 raw data
- 用工程師語言（bit_status、bitmask 等）

### 要
- 只回答用戶問的問題
- 用客戶理解的自然語言
- 說明原因和建議的下一步操作
- 一次只回應一筆匹配的資料（用戶輸入的 ID 或標題過濾）

### 範例

用戶問「合約 678 為什麼不能點退」：
```
您好，合約「信義區套房A」目前為執行中狀態
（合約期間 2026/01/01 ~ 2026/12/31）。

目前無法發送點退，因為合約到期日為 2026/12/31，
系統規定需在到期前 30 天（2026/12/01）起才可操作點退。

如需提前結束合約，可以使用「提前解約」功能。
```

用戶問「合約 678 可以續約嗎」：
```
您好，合約「信義區套房A」目前為執行中狀態，可以進行續約。

合約期間為 2026/01/01 ~ 2026/12/31，
建議在到期前安排續約事宜。
```

## JGB API 回應格式

遵循 JGB client-guide（`jgb2/docs/api/client-guide.md`）：

```json
{
  "success": true,
  "mapping": { "bit_status_flags": { "1": "已建立", ... } },
  "data": [ { ... } ],
  "pagination": { "current_page": 1, "per_page": 50, ... }
}
```

- 認證：`X-API-Key` header
- Base URL：`https://www.jgbsmart.com`
- 路徑前綴：`/api/external/v1/`
- 錯誤格式：`{ "success": false, "error": { "code": 401, "message": "..." } }`

## 合約 API 需求欄位

JGB 合約 API 需回傳以下欄位供判斷引擎使用：

| 欄位 | 類型 | 用途 |
|---|---|---|
| id | integer | 識別 |
| title | string | 物件名稱，顯示用 |
| status | integer | 當前階段（會被覆寫） |
| bit_status | integer | 狀態 bitmask（累加），核心判斷依據 |
| active | integer | 合約是否啟用 |
| is_history | integer | 是否已標記歷史 |
| is_history_done | integer | 是否歷史完成 |
| date_start | integer | 合約起始日（YYYYMMDD） |
| date_end | integer | 合約結束日（YYYYMMDD） |
| rent | number | 月租金 |
| allow_early_termination | boolean | 是否允許提前終止 |
| early_termination_days | integer | 提前終止需提前天數 |
| to_user_connect | boolean | 租客是否已綁定 JGB |
| is_tenant_registered | boolean | 是否為註冊租客 |
| to_user_phone | string | 租客電話 |
| to_user_email | string | 租客 Email |
| father_id | integer | 續約來源合約 ID |
| property_purpose_key | integer | 用途（1=住宅, 2=社會住宅） |
| early_termination_wish_date_end | string | 提前解約期望結束日 |

## 合約 bit_status 對照表

| 值 | 常數 | 說明 |
|---|---|---|
| 1 | READY | 已建立 |
| 2 | INVITING | 已發送簽約邀請 |
| 4 | INVITING_NEXT | 租客已簽名 |
| 8 | SIGNED | 雙方簽名完成 |
| 16 | MOVE_IN | 已發送點交 |
| 32 | MOVE_IN_DONE | 租客同意點交 |
| 64 | MOVE_OUT | 已發送點退 |
| 128 | MOVE_OUT_DONE | 租客同意點退 |
| 256 | EARLY_TERMINATION | 提前解約中 |
| 512 | EARLY_TERMINATION_DONE | 提前解約確認 |
| 1024 | HISTORY | 歷史合約 |
| 2048 | HISTORY_DONE | 歷史完成 |

bit_status 是 bitmask，一個執行中且已點交的合約：`1+2+4+8+16+32 = 63`

## Mock 切換

- `USE_MOCK_JGB_API=true`（預設）：使用 jgb_system_api.py 內的假資料
- `USE_MOCK_JGB_API=false` + `JGB_API_KEY=xxx`：打真實 JGB API

## 新增模組流程（⚠️ 2026-09-11 對碼：分派點已改為 `jgb2.py`，非舊鏈的 `jgb_response_formatter.py`）

以新增一個 jgb domain 模組為例（比照 `jgb/bills.py` 的既有作法）：

1. 建立 `jgb/{domain}.py`，定義狀態常數 + 判斷邏輯 + `format_*_response()` 或
   face-builder（比照 `jgb/bills.py`／`jgb/contracts.py` 的既有寫法）
2. 在 `services/agent/tools/jgb2.py` 加入對應的 `jgb2.query.*` 工具（身分閘＋候選
   列表邏輯，比照既有的 `query_bills`／`query_contracts`）
3. 更新 `jgb_system_api.py` 的 mock 資料對齊實際欄位
4. 測試：`rag-orchestrator/tests/unit/agent/`／`tests/integration/agent/` 加對應
   測試，或用 `/mcp` 實打 `jgb2.query.*` 確認回應品質
5. 更新此 README
