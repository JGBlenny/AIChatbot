# 11.5 收案：`repair_create` 五槽 wiring census（2026-08-29）

## Completion criterion（業主定案）

> 每個 `required_slots[i]` 都能追到實際 consumer，證明
> 「槽位名稱 → state 取值 → request builder／API payload 使用」一致；
> ⛔ 不能只證明 config 裡有這個名字。

## 資料流（五槽共用）

```text
required_slots[i]
→ state["collected_fields"][slot]                （brain 抽取／prefill／Vision 推斷）
→ _slot_values()                                  {value,source,confirmed} dict 或裸值 → 攤平
→ _execute_transaction(): api_config = {endpoint: execute_endpoint,
                                        params_from_form: execute_params}
→ APICallHandler.execute_api_call()               payload_key ← form_data[來源欄位]
→ JGBSystemAPI.create_repair(**payload)
→ POST /api/external/v1/repairs
缺值時：conversational_engine 在打 API **之前**擋下（`_missing` → 轉追問，不打 API）
```

## 五槽 census

| Slot | Runtime source | Consumer | API key／用途 | Index-sensitive | Verdict |
|---|---|---|---|---|---|
| `estate_id` | prefill（單一租約）／候選選擇（多租約）／brain | `create_repair(estate_id: int)` 必填位置參數 | `estate_id` → POST body | **yes**（`required_slots[0]`） | **CONFIRMED** |
| `category_id` | Vision 推斷經 `resolve_repair_classification` 解出 id／brain | `create_repair(category_id: int)` 必填 | `category_id` → POST body | no（按名稱） | **CONFIRMED** |
| `item_id` | 同上 | `create_repair(item_id: int)` 必填 | `item_id` → POST body | no | **CONFIRMED** |
| `broken_reason` | Vision／brain | `create_repair(broken_reason: str)` 必填 | `broken_reason` → POST body | no | **CONFIRMED** |
| `emergency_status` | Vision `suggested_emergency`／brain | `create_repair(emergency_status: int = 1)` **有預設值** | `emergency_status` → POST body | no | **CONFIRMED**（見下方註記） |

⇒ 五槽皆 identity mapping（`execute_params` 的 key 與來源同名），已與 DB 實際設定對帳一致。

## `emergency_status` 看起來像 contract drift，其實是防護

```text
API 端：create_repair(emergency_status: int = 1) —— 有預設值 ⇒ 技術上 NOT_REQUIRED_BY_CONSUMER
DB 真值：**2＝緊急、1＝非緊急**（jgb_response_formatter 的自家真值對照）
⇒ 若不列入 required_slots，使用者未表態的報修會被**靜默**送成「非緊急」。
   列為 required ＝ 強制取得表態。⛔ 勿因「API 有預設值」就把它從 required 拿掉。
```

## Index sensitivity：只有 `[0]` 有位置語義

```text
以索引讀取（2 處）    `required_slots[0]` —— 候選選擇填槽、決定性識別填槽
按名稱讀取（4 處）    `_has_basic_info`／confirm 缺槽檢查／execute 前把關／清無效識別槽
⇒ **五槽 reorder 不是完全安全的**——把 estate_id 移離首位會改變上述兩處行為。
   已用測試鎖住索引讀取點的數量：新增第三處會紅。
```

## ⚠️ 本輪逐槽稽核抓到的 deterministic defect（已修）

```text
病灶：插點 A（候選選擇輪）一律把使用者選的候選填進 `required_slots[0]`＝estate_id，
      等於假設「候選永遠對應第一個槽位」。對 repair_create 不成立——它有兩種候選：
        ・多租約 → `_estate_candidate`（id＝estate_id）           → 正確
        ・Vision 信心不足 → `_classification_candidates`
          （**id 就是中文名稱字串**，如「冷氣」）                → **錯**
後果：`create_repair(estate_id: int)` 會收到「冷氣」；
      更糟的是單一租約時 estate_id 已被正確 prefill，會被**覆蓋掉**。
修法：候選由**來源端**宣告 `slot`，插點 A 優先採用，未宣告才退回 [0]（向後相容）。
      分類候選宣告 `slot="category"`（顯示槽），⛔ 不是 `category_id`——
      這裡沒有真正的分類編號，填顯示槽會讓 required_slots 仍未齊 ⇒ 引擎繼續追問，
      **失敗方向朝向「再問一次」而不是「把名稱當 id 送進 API」**。

順帶修：插點 A 原本對**任何**面向都呼叫 `_ground_by_api`，但交易面向的
      grounding_scope 只有 `execute_endpoint`／`prefill_api`、**沒有** `endpoint`
      ⇒ 端點為 None，白走一趟失敗降級。改為非 api 面向填完槽即落回主流程。
```

## 三類 guard 皆已落成（19 條 unit，容器內全過）

```text
1. 每槽正控制   填入唯一 sentinel → payload 必須看到同一 sentinel（5 條）
                ＋ payload key 必須是 create_repair 真的接受的參數（簽名對帳，5 條）
2. key mutation `estate_id` 改成 `estate_identifier` → payload key 必須消失
3. drop mutation 四個必填位置參數各自少傳 → `signature.bind` 必須 TypeError（4 條）
                ＋ emergency_status 專測（有預設值，少傳**不**報錯——與上述四槽相反）
回歸鎖  候選必須自帶 slot；引擎必須優先採用候選宣告的 slot
索引鎖  以索引讀 required_slots 的地方維持 2 處，新增會紅
```

## 判定

> **11.5：PARTIALLY CONFIRMED → CONFIRMED。**

五槽全部閉合；全 unit 層 1517 passed / 0 failed。

## 未涵蓋（照實記）

```text
⛔ 未做真實 POST /repairs —— 那會在 production 開單，⛔ 不在唯讀範圍內
   ⇒ 「payload 抵達 API」由簽名對帳＋sentinel 映射證明，**不是**線上證據
⚠️ 測試內的 EXECUTE_PARAMS 是設定副本（本次已與 DB 對帳一致）；
   若日後 DB 改了而測試沒改，簽名對帳仍會抓到多數情況，但不保證全部
```
