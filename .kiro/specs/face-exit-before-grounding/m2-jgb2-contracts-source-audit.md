# M2：`contracts` 替身對照 jgb2 原始碼（source audit）

> 2026-08-25｜零外部呼叫｜來源：
> `jgb2/app/Http/Controllers/External/ContractApiController.php`（本機 checkout `project/jgb_1/jgb2`）

## 0. 結論

> **替身有三處與 production 不一致，已修；其中一處會直接影響 v5 的收斂結果。**

## 1. 逐條對照

| 項目 | production（原始碼） | 替身（修正前） | 處置 |
|---|---|---|---|
| `role_id` | 必填，缺 → 400（:23-25） | 同 | ✅ 一致 |
| 恆定 where | `active=1` ＋ **`is_newest=1`**（:51-52） | **無** | ✅ 已補 |
| `contract_ids` | `array_map('intval', explode(','))` → `whereIn('id')`（:67-70） | 只收純數字 token | ✅ 改為照抄 `intval` 前綴語義 |
| `keyword` | 跳脫 `%_` 後 **`title LIKE '%kw%'`**（:72-75） | title **或 address** | ⚠️ **過度寬鬆 → 已修為只比 title** |
| 排序 | `orderBy('id','desc')`（:77） | 依 fixture 宣告序 | ✅ 已明確排序 |
| `total_pages` | total=0 時為 **0**（:83） | 恆 1 | ✅ 已修 |
| `has_more` | `page < total_pages`（:99） | 恆 False | ✅ 已修 |
| 投影 | `formatContract()` 逐鍵（:107-157） | 少 6 鍵 | ✅ 已補 `contract_inviting_at`／`_expire_at`／`_sign_at`／`contract_finish_sign_at`／`to_user_login_email`／`is_newest` |
| `mapping` | `bit_status` 12 項（:163-181） | 同 | ✅ 一致 |

## 2. 那個會影響結論的差異

```text
keyword：production 只比 title，替身首版連 address 一起比
```

⇒ 若 adapter 以地址片段重查，production **查無**、替身**查到**——
這正是「替身比真 API 寬鬆，於是測試綠得比現實容易」的典型。已修，並補上具名測試
（`("信義路五段", [])`）把它鎖住。

⚠️ **v5 的單筆收斂不受此影響**：該次重查走的是 `contract_ids=678`（精確 id），
不是 keyword。但在修正之前，我們無權宣稱 keyword 路徑已被驗證。

## 3. 保真度聲明更新

`contract_fixtures.py` 開頭原本標「**未**重新閱讀 jgb2 原始碼核對」，
現已改為「**已對照** `formatContract()` 逐鍵與 `index()` 的 where 條件」。

⚠️ 仍**未**涵蓋：認證／權限（`external_api_key`、`user_data` 圈定）、
`user_id` 篩選、延遲與錯誤碼、真實資料的標題格式分佈——那些屬 real API smoke。
