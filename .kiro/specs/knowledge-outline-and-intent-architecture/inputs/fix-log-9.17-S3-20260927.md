# Plan 9.17 S3a 修正紀錄（`jgb/E/payment-gateway-fees`）

> 允許集合 `scratchpad/p917-s3-allowed.json`＝`["jgb/E/payment-gateway-fees"]`。基準＝`scratchpad/p917-s3-backup/runs/`（改前 drafts-D／E）。句序一律為**備份側**句序。verifier 判定：過／不過／待核。

## 修正表

| 細目 id | 欄位 | 句序 | 動作 | 依據 | verifier |
|---|---|---|---|---|---|
| `jgb/E/payment-gateway-fees` | sentences | 0 | 改 | 依據 #1 | 過 |
| `jgb/E/payment-gateway-fees` | sentences | 2 | 新增句 | 依據 #1 | 過 |
| `jgb/E/payment-gateway-fees` | sources | | 改 | 依據 #1 | 過 |
| `jgb/E/payment-gateway-fees` | title | | 改 | 依據 #1 | 過 |

（sentences #2 新增句一列涵蓋在備份側句序 2 位置插入的兩句：藍新提款費用、藍新交易手續費依據。第一次核：新句 [3] 原寫「這份說明沒有列出，需要洽客服確認」不過（流程註記、引導無據）⇒ 依 D1 修一次，改為開通畫面條款原文並補來源 `code:src/pages/users/payment/_parts/Newebpay.vue`；複核＝過。）

## 刪除

（無）

## 依據

1. `jgb/E/payment-gateway-fees`：9.16 收案抽驗 P2——原標題「中國信託／藍新免費」只有「申請」免費的來源。`help:paymentapply_zh-Hant.html` 表格「國泰世華 僅法人 自行向銀行申請，首次設定費 5,000 元」「中國信託 法人與個人 於 JGB 系統線上申請，免費」「藍新 NewebPay … 於 JGB 系統線上申請，免費」；「藍新的款項會先留在藍新帳戶中，需自行登入藍新後台辦理提款，前 5 次免費，之後每次收取 10 元。」；全文無交易手續費／費率資料（⇒ 寫「未列出，需洽客服確認」，同頁結尾「歡迎透過線上客服與我們聯繫」）。標題「費率」改為「申請費用」、「免費」改為「不收申請費」；不寫身分限制（避免與已審 `payment-gateway-options` 依程式所寫的個人房東限制衝突）。
   複核修正：`src/pages/users/payment/_parts/Newebpay.vue` 條款「費率以藍新科技股份有限公司本服務會員系統公告為依據。」

## 差異比對輸出（最終位元組）

```
[diff] D/E fines in base: 200; doubt set: 1 (not found in base: 0)
[diff] changed/deleted items: 4 in 1 fines; deleted fines: 0
[diff] (b) changed ids outside doubt set: 0
[diff] (c) items on protected (non-doubt) fines: 0
[diff] (f) structural differences: 0
[diff] (a) fix-log rows: 4; unlogged diffs: 0; log rows with no diff: 0
[diff] (d) deleted fines: diff 0 vs fix-log 刪除 0; equal: True
[diff] (e) rows not passed and not a deletion: 0
[diff] RESULT: PASS
```

正對照（scratch 副本改已審 `payment-gateway-options` 一句）：

```
[diff] (b) changed ids outside doubt set: 1
[diff] (c) items on protected (non-doubt) fines: 1
[diff]   protected changed: ('jgb/E/payment-gateway-options', 'sentences', '0', '改')
[diff] RESULT: FAIL
```
