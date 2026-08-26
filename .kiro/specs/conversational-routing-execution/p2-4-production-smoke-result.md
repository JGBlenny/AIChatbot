# P2.4 real API smoke（**production**：`https://www.jgbsmart.com`）——**六項全數取證**

> 2026-08-26｜業主指示改接 production 實測（preview 的合約端點 500，見 `p2-4-preview-smoke-result.md`）
> ⚠️ **只發唯讀 GET**，未寫入任何資料；容器組態仍指向 preview，本輪以行程內請求直打 production，
> 未變更任何環境設定。
> ⚠️ 本檔**不記錄任何真實個資**——標題、地址、email 一律只記形狀與統計。

## 一、六項結果

| # | 項目 | 結果 |
|---|---|---|
| ① | authentication／authorization | ✅ 無 key → **401**「API Key 未提供」；缺 role_id → **400** |
| ② | user_id／viewer scope 真實行為 | ✅ 見下 |
| ③ | 真實 title／identifier 形狀 | ✅ 見下 |
| ④ | **contract_ids 重查是否真的收斂單筆** | ✅ **total=1、ids 逐位相符** |
| ⑤ | response／error envelope、投影鍵集 | ✅ **41 vs 41，零漂移** |
| ⑥ | timeout／latency | ✅ 初查 361ms／重查 199ms（200 筆頁） |

## 二、④ 最關鍵的那一項：vertical slice 的外部前提**成立**

```text
初查 role_id=20151        → 200，pagination.total = **509**
以 contract_ids 重查      → 200，total = **1**，回傳 id 與請求逐位相符（199ms）
```

⇒ 「初查 N 筆 → 使用者給識別 → 第二次依 request 重查收斂單筆」在**真 production API 上成立**。
這是 v5／v6 vertical slice 最重要、且替身結構上證不到的外部假設。

## 三、⑤ 投影鍵集：**零漂移**

```text
真 API 回傳 41 欄｜我方 EXTERNAL_CONTRACT_FIELDS 宣告 41 欄
真 API 有、我方沒宣告：**無**
我方宣告、真 API 沒有：**無**
```

⇒ M2 那輪逐鍵對照 `formatContract` 的結論，在真 API 上被獨立確認。
（`fixtures.py` 的 33 欄帳單投影未在本輪比對，仍待同法驗證。）

## 四、② viewer scope 的真實行為

```text
user_id=<不存在>          → 200、total=**0**（不是錯誤，是空集合）
viewer_user_id=<不存在>   → **404**「role_id 或 viewer_user_id 不存在」
bills + viewer_user_id    → 同上 404
role_id=<不存在>          → 200、total=0
```

⚠️ 兩種「查不到」在 production 是**不同狀態碼**：
資料層過濾不到 → 200/空；viewer 主體解析不到 → 404。
我方 adapter 目前一律折疊成 `success:False`／空集合——
**能用，但分不出「這個人沒有資料」與「這個人根本不存在」**。GAP-B2 的部分答案。

## 五、③ 真實標題分佈（只記統計）

```text
n=200（單頁）  長度 min/median/max = 3 / 12 / 41
含分隔符（空白・- ・_ ・／）者 = **90/200（45%）**
serial_id                     null = 200/200（**全 null**）
to_user_login_email           null = 99/200（約半數）
early_termination_notice_date null = 200/200（拆表後由衛星表供應，本頁皆空）
```

⚠️ **45% 的標題含分隔符**，直接支持既有的已知問題：
API 的 `keyword` 是整串 `title LIKE`，口語多詞（如「新莊富貴500的14B05」）配不中——
這正是 `get_meters`／`get_estate_status` 改走 client 端 token 化過濾的理由，
現在有了 production 分佈作為佐證，不再只是 e2e 逼出來的印象。

## 六、對 Stage-1 的意義

```text
✅ P2.4 六項全部取證（在 production 上）
❌ **但 P2.5 不能就這樣在 production 上跑**——那會讓真 brain 對線上資料發動完整對話流程，
   已超出「唯讀 smoke」的邊界，需業主另行授權。
⏸ preview 修好後，這六項應在 preview 重跑一次；本輪結果只證明
   **jgb2 的 production 版本**符合契約，不代表 preview 版本符合。
```
