# P1e-2：23 個 Face 的 `requires_instance_reference` 盤查（**提案，待裁**）

- 日期：2026-08-29｜⚠️ 依業主定案：**依 responsibility 語義裁定，⛔ 不由 `select=api` 推導**
- 現況：宣告數 ＝ **0**（全部 UNKNOWN）

## ⚠️ 盤查中浮現一個必須先裁的語義問題

`requires_instance_reference` 這個名字混了兩件事：

```text
(A) 需要使用者**指出**哪一筆      ——「reference」：bill_ref／contract_ref／estate_ref…
(B) 回答依賴使用者**自己的資料**  ——「instance data」：可由 session 身分決定，不需指認
```

多數面向 (A)(B) 同時成立，但**至少一個面向只成立 (B)**：

```text
subscription_diag  required_slots=[symptom]（不是識別碼）
                   端點 /roles/{role_id}/subscription —— 讀的是**這個使用者**的訂閱
                   ⇒ 需要 instance data，但**不需要** instance reference
```

⚠️ 若把它裁成 REQUIRED 而 gate 的語義是 (A)，
「我的物件為什麼全部下架」這種**沒有指認**的問句會被錯誤抑制。
⇒ **請先裁 (A) 或 (B)**，這決定下面整張表的填法。以下提案採 **(B)** 的讀法。

## 提案（採 (B)：回答是否依賴使用者自己的資料）

### REQUIRED —— 15 個

| Face | 證據（**面向自己的契約**，非 select 推導） |
|---|---|
| `bill_diagnosis`／`billing_anomaly`／`billing_flow`／`billing_invoice` | `required_slots=[bill_ref]` → 必須指認**某一張自己的帳單** |
| `billing_late_fee`／`contract_change`／`contract_closeout`／`contract_diag`／`contract_renew`／`contract_sign`／`account_login` | `required_slots=[contract_ref]` → 指認**自己的合約** |
| `estate_diag` | `required_slots=[estate_ref]` |
| `iot_meter` | `required_slots=[meter_ref]` |
| `account_team` | `required_slots=[member_ref]` → 指認**自己團隊的成員** |
| `subscription_diag` | 端點 `/roles/{role_id}/subscription` → 讀**這個使用者**的訂閱；⚠️ **只成立 (B)** |

⚠️ 這裡引用 `required_slots` 是作為**人工裁定的證據**，
⛔ **不是**主張 runtime 可以用 `bool(required_slots)` 推導——
erratum 01 明文禁止那條 fallback，本提案不改變它。

### NOT_REQUIRED —— 6 個

```text
account_binding／account_register／billing_setup_guide／
contract_create_guide／estate_guide／iot_setup
```

證據：`select=category`、無端點、無 required_slots ⇒ 作答只讀知識庫。
⚠️ 但這是**現行實作**的描述。若產品認為某個引導面向**應該**要看使用者現況
（例如 `estate_guide` 面對「我的物件為什麼全部下架」時），
那它就不是 NOT_REQUIRED 而是**能力缺口**——正是不變量 9 抓 3505/3506 的那一類。
⇒ ⛔ 不得把「現在做不到」寫成「本來就不需要」。

### 需要單獨裁 —— 2 個

```text
presales        無 select、靠 persona 進場、mode=all
                ⇒ 售前對象通常**還沒有**帳號資料 ⇒ 傾向 NOT_REQUIRED，但屬產品定位問題
repair_create   交易面向（execute_endpoint）
                required_slots 五槽含 estate_id ⇒ 需要使用者自己的物件
                但它是**寫入**而非查詢 ⇒ gate 的語義是否涵蓋交易面向，需裁定
```

## ⛔ 本盤查不做的事

```text
⛔ 不寫入任何宣告（population 需業主逐一裁定後才進行）
⛔ 不改 routing、不 enable gate
⛔ 不由 select=api 自動推導——那正是本輪要避免的 fallback
```

## 完成條件

```text
23 個 Face 皆有明示 REQUIRED／NOT_REQUIRED，或明確標記為仍待產品定位；
且 (A)/(B) 的語義選擇已裁定並寫入契約文件。
```
