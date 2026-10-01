# Plan 9.20 S0 修正紀錄（hold 2 條整條刪除＋客戶名改寫 1 條）

> 允許集合 `scratchpad/p920-s0/allowed.json`，共 3 條：hold 2 條，加上客戶名命中 1 條。hold 清單 `scratchpad/p920-s0/hold.json`。
> 基準＝`scratchpad/p920-s0/backup/drafts/`。句序一律為**備份側**句序，從 0 起算。改寫工具 `scratchpad/p920-s0/edit_fine.py`。
> verifier 欄：「過／不過」由 fresh verifier 判；刪細目列填「—」（業主裁定，不送核對）。

## 修正表

| 細目 id | 欄位 | 句序 | 動作 | 依據 | verifier |
|---|---|---|---|---|---|
| `jgb/A/login-sso-redirect-no-duplicate-buttons` | fine |  | 刪細目 | 依據 #1 | — |
| `jgb/B/biglandlord-escrow-owner` | fine |  | 刪細目 | 依據 #1 | — |
| `jgb/D/contract-payment-method` | sentences | 1 | 改 | 依據 #2 | 過 |

## 刪除

- `jgb/A/login-sso-redirect-no-duplicate-buttons`
- `jgb/B/biglandlord-escrow-owner`

## 依據

1. **hold 2 條整條刪除**：業主 2026-09-28 裁定（Plan 9.19 §6 S1「兩條必須整條刪除的細目『列下個計畫刪除 (Recommended)』」）。理由見 `inputs/fix-log-9.19-S1-20260928.md`：
   - `login-sso-redirect-no-duplicate-buttons`：情境在現行程式走不到；
   - `biglandlord-escrow-owner`：內容只存在於舊 blade。
2. **客戶名改寫**：9.16 S3 審核單 `inputs/review-sheet-9.16-S3-DE-20260927.md` 的 doubt 寫道：「句中出現客戶名「Meta Capital 系列」，應改成「特定合作團隊的專用範本」」。
   - 9.20 S0 以程式抽出的詞表（`scratchpad/p920-s0/customer-terms.json`，18 詞，每詞附正負對照）逐細目掃全正本，只命中這 1 條，而且它未審。
   - 改前：「「線上金流」只有在使用者國別是台灣、且合約範本不是 Meta Capital 系列時才會顯示這個選項。」
   - 改後：「「線上金流」只有在使用者國別是台灣、且合約範本不是特定合作團隊的專用範本時才會顯示這個選項。」
   - evidence 不變（`src/pages/contracts/edit/payment/General.vue` 的 `meta_capital_condos`／`meta_capital_office` 判斷，只在 evidence 中出現，不進正本）。

## 核對過程

- fresh verifier（2026-10-01，brief 依 `templates/brief-fix-verify.txt`，只核這 1 項）＝**CONFIRMED**：`jgb/D/contract-payment-method｜sentences｜1｜改｜過`。
- 附建議（P4，不阻擋，延後）：已審的 `jgb/D/contract-rentbasic-early-termination` 第 4 句也用「特定合作團隊的專用範本」，指的卻是另一份範本（社宅專用範本，不受線上金流這條限制）。因此本條若要更精確，可寫成「某特定合作團隊的兩份專用範本」。延後的理由：本條會在 S4（D／E 修正）重審時一併處理；S0 依 D1 只修 doubt 所指的客戶名。

## 差異比對輸出（最終位元組）

`P919_DIFF_SHELVES=ABCDEFGHI python3 scratchpad/p920-s0/drafts_diff.py --base scratchpad/p920-s0/backup/drafts --cur runs/outline-20260920 --doubt scratchpad/p920-s0/allowed.json --fix-log <本檔>`

```
[diff] (g) evidence remaps on allowed fines: 0; new out-of-range: 0
[diff] fines in base (shelves ABCDEFGHI): 541; doubt set: 3 (not found in base: 0)
[diff] changed/deleted items: 3 in 3 fines; deleted fines: 2
[diff] (b) changed ids outside doubt set: 0
[diff] (c) items on protected (non-doubt) fines: 0
[diff] (f) structural differences: 0
[diff] (a) fix-log rows: 3; unlogged diffs: 0; log rows with no diff: 0
[diff] (d) deleted fines: diff 2 vs fix-log 刪除 2; equal: True
[diff] (e) rows not passed and not a deletion: 0
[diff] RESULT: PASS
```

drafts-C／E／F／G／H／I 與備份 `cmp` 相同。
