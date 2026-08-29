# H6 control-flow audit：「需要個別資料」是否必然等於「要進多輪」

- 日期：2026-08-29｜性質：**deterministic design audit**，讀控制流＋契約＋少量唯讀實測
- ⛔ 射程外（本輪不碰）：nomination coverage／production rate／gate authorization／
  classifier／0.75 threshold／knowledge quality
- ⇒ 本檔**不能**回答「多少使用者會遇到」，只回答
  **「現行架構在什麼條件下會多問一輪，以及那一輪是否真有資訊增益」**

## 結論

> **H6 的 redundancy 假設在數字型識別碼上 REFUTED。**
> 使用者原句已含可抽取的識別碼時，引擎在 **LLM 之前**就決定性填槽並直接 grounding，
> **單輪答完，不會再問一次**。

## 一、Entry input preservation：有 pre-LLM 的決定性填槽

`conversational_engine.prepare` 在呼叫 brain **之前**：

```python
required = gscope.get("required_slots") or []
slot = required[0] if required else None
_ident = _extract_identifier(user_message) if slot else None
if select=="api" and gscope.get("deterministic_id", True) and slot \
   and _ident is not None and _ident != _prev_ident:
    state["collected_fields"][slot] = _ident
    r = await self._ground_by_api(...)      # 先搜後提交：命中才留，查無回滾
    if r["kind"] == "converge": → 直接回答
```

`_extract_identifier`：整句純數字（2–15 位）→ 直接回；否則抽句中第一個 id-like token（≥4 位）；
抓不到回 `None`（純文字名稱交 brain）。

⇒ **`required_slots[0]` 被當成「完成 grounding 的必要資料」，不是「進 Face 後固定要問的題目」。**
這同時回答了任務 11.5 的核心疑問（見文末）。

## 二、Grounding prerequisite：逐 Face 契約盤點

| 類別 | Faces | 快速路徑 |
|---|---|---|
| `api` ＋ `deterministic_id` 預設 true | account_login, bill_diagnosis, billing_anomaly, billing_flow, billing_invoice, billing_late_fee, contract_change, contract_closeout, contract_diag, contract_renew, contract_sign（11 個） | ✅ 有 |
| `api` ＋ **`deterministic_id=false`** | account_team（member_ref）、estate_diag（estate_ref）、iot_meter（meter_ref） | ❌ 關閉（主槽為名字型，數字非其值——刻意，避免把資源編號誤填） |
| `select=category`（無 grounding） | account_binding, account_register, billing_setup_guide, contract_create_guide, estate_guide, iot_setup（6 個） | — 無槽位，追問不是為了識別碼 |
| 交易型 | repair_create（5 個必填槽） | — 另一種形狀 |

## 三、First-question policy：唯讀實測（production API，唯讀）

```text
「合約 89557 現在狀態？」
  → **單輪**答完：名稱／狀態／期間／月租，無任何追問
「幫我查合約 89557 什麼時候到期」
  → **單輪**答完：到期日 2026/11/13
⇒ 識別碼已在原句 ⇒ 不再問。**REDUNDANT_CLARIFICATION 未發生。**
```

對照組（識別碼型別不同或未提名）：

```text
「帳單 716317 的收據金額是多少」
  → 進 billing_anomaly，識別碼**有被使用**，但 API 查無
  → 回「查無對應的資料，請再確認識別資訊」
  ⇒ 這是 **CAPABILITY／資料歸屬**問題（該帳單不屬本 role），
    **不是** redundancy——它沒有要求使用者重講一次剛講過的號碼。
「文山路那間現在還有人在住嗎」  → **未進任何面向**，direct_answer 查無
「3樓的電表度數現在是多少」     → **未進任何面向**，direct_answer 查無
  ⇒ 這兩筆是 **nomination coverage** 問題，屬本輪射程外。
```

## 四、分類結果

```text
DIRECT_GROUNDING_POSSIBLE   11 個 api 面向（數字型識別）——已在 contract 路徑實測確認
CLARIFICATION_REQUIRED       6 個 category 面向（無 grounding，追問非為識別碼）
                             ＋ repair_create（交易型，5 槽）
UNKNOWN                      3 個 deterministic_id=false 面向
                             （estate_diag／iot_meter／account_team）
                             ⚠️ 本輪**測不到**：那些問句根本沒被提名進面向，
                                所以無從觀察它們的第一個問題
REDUNDANT_CLARIFICATION      **0 筆**——未發現任何「已給識別碼卻再問一次」
CAPABILITY_MISSING           未在本輪射程內判定
```

## 五、對任務 11.5 `required_slots` 的直接回答

> **問**：`required_slots` 只是「完成 grounding 的必要資料」，還是被錯拿成「進 Face 後固定要問的問題」？
>
> **答**：是前者。證據＝ pre-LLM 快速路徑把 `required_slots[0]` 從**使用者原句**填入後
> 直接 grounding，完全不經追問。若它被當成「固定要問的題目」，這條路徑不會存在。

⚠️ 但 11.5 仍有未答的部分：本輪只驗了 `required_slots[0]`。
`repair_create` 的 5 個槽、以及「是否索取了面向實際不需要的欄位」尚未逐槽比對 API consumer。

## 六、這輪**不能**推論的事

```text
⛔ 不得說「架構沒有多餘追問」——只驗了數字型識別碼那條路徑
⛔ 不得說「estate_diag／iot_meter 沒問題」——它們根本沒被提名，UNKNOWN
⛔ 不得由此對 production 分布做任何宣稱
```

## 七、H6 的處置

```text
H6（instance 是否必然等於多輪）→ 在數字型識別碼上 **REFUTED**，該分支收掉。
剩餘開口：名字型識別（estate/meter/member）在**能被提名之後**是否仍會多問一輪——
         這個問題被 nomination coverage 擋在前面，須等上游解決才測得到。
```
