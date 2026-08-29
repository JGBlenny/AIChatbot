# P1e-2：23 個 Face requirement 全量複核與 population（2026-08-29，**已凍結**）

判準＝業主裁定③ 的 **(B)** 定義：

> This Face is applicable only when correctly fulfilling the user's intent
> depends on user-specific or instance-specific runtime data.

⛔ **這四條捷徑一律不得作為依據**（它們只是 execution shape）：

```text
select=api → REQUIRED ／ 有 required_slots → REQUIRED ／
有 endpoint → REQUIRED ／ 名字像 diagnosis → REQUIRED
```

⇒ 證據一律取自 **Face 自己宣告的責任**（persona 開頭句與 scope 規則）。
⚠️ **NOT_REQUIRED 也要有正面證據**——⛔ 不重演 knowledge general 那個坑
（「沒看到 instance evidence」≠ NOT_REQUIRED）。

## REQUIRED（16）

| Face | 責任證據（引自其 persona 宣告） |
|---|---|
| `contract_diag` | 「查詢與診斷**自己的某一份合約**的狀態與資訊」 |
| `estate_diag` | 「查**特定物件**的現況」 |
| `subscription_diag` | 「**需要查該帳號實際訂閱狀態**」 |
| `repair_create` | 「**物件由租約帶入**」⇒ 須讀該租客租約 |
| `bill_diagnosis` | 「**這筆**帳單為什麼發不出去／取消不了…」 |
| `billing_late_fee` | 「**這份合約/這筆帳單**的滯納金怎麼算」 |
| `billing_anomaly` | 「金額不對/帳單沒出現/租客看不到帳單」 |
| `billing_flow` | 「租客說繳了但錢沒進來/帳單狀態沒動」 |
| `billing_invoice` | 「發票**開了沒**」＝實值 |
| `contract_change` | 能不能改／能不能轉歷史刪除 → 取決於該合約狀態 |
| `contract_closeout` | 把**這份**退租流程走完 |
| `contract_renew` | 「**可否**系統續約」→ 取決於該合約 |
| `contract_sign` | 簽署卡關排查 → 該合約／該租客 |
| `account_login` | 「租客登不進去/登入後看不到資料」→ 須查該租客綁定與合約 |
| `account_team` | 「某成員看不到某帳單/合約/物件」→ 須查該成員權限 |
| `iot_meter` | 「租客沒電/電表離線/度數怪怪的」→ 該顆電表 |

## NOT_REQUIRED（6）——**皆有正面證據**

```text
account_register       責任明文「**當事人（租客）不在系統內**」⇒ 根本沒有可讀的個體資料
billing_setup_guide    責任明文「**本面向不查帳單 API**」
contract_create_guide  責任明文「**本面向不查合約 API**」
estate_guide           責任＝建立／編輯／刊登等**操作方法**（產品知識）
iot_setup              責任＝串接／單價／密碼規則等**設定方法**（產品知識）
presales               售前對象是**潛在客戶**，尚無帳號 ⇒ 無 user-specific runtime data
```

## UNKNOWN（1）——⛔ 刻意不寫入

```text
account_binding 「換綁手機/信箱、帳號資料修改、**帳號合併**」
  ・「分流」看似產品知識，但**帳號合併的可行性取決於那兩個帳號的狀態**
  ・且它**沒有**像 billing_setup_guide／contract_create_guide 那樣的「不查 API」明文
  ⇒ 責任定義本身不足以判 ⇒ 維持 UNKNOWN，⛔ 不靠名字或 endpoint 猜
```

## 反例矩陣（防止把 execution shape 當 responsibility）

```text
✅ 名字像排障、但 NOT_REQUIRED     account_register（當事人不在系統內）
✅ 無查詢 API、但 REQUIRED         repair_create（物件由租約帶入）
⚠️ 「有 API 但責任是 general」     本批**沒有**實例 —— 該格為空
   ⛔ 空格不代表不可能，更⛔ 不得反推成「有 API 就是 REQUIRED」
```

## ⚠️ Population **不改 routing**（已用測試鎖住）

```text
`gate_active()` 是最外層守衛：`INSTANCE_REFERENCE_GATE` 未設 ⇒ false
⇒ `_instance_gate_decision` 回 None ⇒ `_instance_hint_suppressed` 恆 False
⇒ 宣告寫入前後 routing **逐位元相同**

且 C∧D 兩層未被摺疊：16 個宣告 true 之中，
只有 `bill_diagnosis` 同時落在 `LEVEL_A_INSTANCE_GATE_SCOPE`
⇒ 其餘 15 個**不會**因為宣告而被納管。擴大納管需要另一個授權決定。
```

## 兩軸首次完整

```text
Knowledge applicability   instance 34（deterministic）／general 0／unknown 839
Face requirement          required 16／not_required 6／unknown 1
```

⇒ 交叉判定已可對**真實宣告過的配對**產生結果（3503 × billing_invoice → ELIGIBLE，有測試）。

## 下一步（不在本刀）

```text
76 筆 INSTANCE_PROPOSAL 的確認
742 筆 general review queue
⏸ gate authorization／3.4 維持 PAUSED
```
