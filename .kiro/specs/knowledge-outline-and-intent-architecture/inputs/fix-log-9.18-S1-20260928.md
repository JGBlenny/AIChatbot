# Plan 9.18 S1 修正紀錄（客戶名改寫＋`bill-scheduled-send-rule` IoT 例外）

> 允許集合 `scratchpad/p918-s1-allowed.json`（8 條）。基準＝`scratchpad/p918-s1-backup/drafts/`（改前 drafts）。句序一律為**備份側**句序。verifier 判定：過／不過／待核。改寫工具 `scratchpad/p918_edit.py`。

## 修正表

| 細目 id | 欄位 | 句序 | 動作 | 依據 | verifier |
|---|---|---|---|---|---|
| `jgb/A/notification-settings-report-buttons` | sentences | 1 | 改 | 依據 #1 | 過 |
| `jgb/B/advance-discount-items` | sentences | 0 | 改 | 依據 #2 | 過 |
| `jgb/B/advance-discount-items` | sentences | 1 | 改 | 依據 #2 | 過 |
| `jgb/B/advance-discount-items` | title |  | 改 | 依據 #2 | 過 |
| `jgb/B/advance-late-fee` | sentences | 0 | 改 | 依據 #3 | 過 |
| `jgb/B/advance-late-fee` | title |  | 改 | 依據 #3 | 過 |
| `jgb/B/advance-payment-cycle-discount` | sentences | 0 | 改 | 依據 #4 | 過 |
| `jgb/B/advance-payment-cycle-discount` | title |  | 改 | 依據 #4 | 過 |
| `jgb/B/advance-short-lease-approval` | sentences | 0 | 改 | 依據 #5 | 過 |
| `jgb/B/advance-short-lease-approval` | title |  | 改 | 依據 #5 | 過 |
| `jgb/B/lessee-bulk-notify` | sentences | 0 | 改 | 依據 #6 | 過 |
| `jgb/B/lessee-bulk-notify` | title |  | 改 | 依據 #6 | 過 |
| `jgb/D/contract-rentbasic-latefee` | sentences | 0 | 改 | 依據 #7 | 過 |
| `jgb/D/contract-rentbasic-latefee` | title |  | 改 | 依據 #7 | 過 |
| `jgb/E/bill-scheduled-send-rule` | sentences | 1 | 改 | 依據 #8 | 過 |
| `jgb/E/bill-scheduled-send-rule` | sentences | 2 | 新增句 | 依據 #8 | 過 |
| `jgb/E/bill-scheduled-send-rule` | sources |  | 改 | 依據 #8 | 過 |
| `jgb/E/bill-scheduled-send-rule` | title |  | 改 | 依據 #8 | 過 |

## 刪除

（無）

## 依據

1～7. **客戶名改寫（業主 D1）**：客戶名一律改為「特定合作團隊」；同一條需區分不同團隊時，寫「部分特定合作團隊」＋差異本身。只換名稱，句意、條件、數字不變；該條其他疑點留 9.19。
   1. `notification-settings-report-buttons`：句 1 的「特定樓宇團隊」→「特定合作團隊」。
   2. `advance-discount-items`：「統上或新北住都的合作團隊」→「部分特定合作團隊」；「新北住都合作團隊上限是 30 組」→「其中一個特定合作團隊的上限是 30 組」。
   3. `advance-late-fee`：「統上」→「特定合作團隊」。
   4. `advance-payment-cycle-discount`：「統上」→「特定合作團隊」；「一般團隊（含新北住都）」→「其他團隊……都沒有」。
   5. `advance-short-lease-approval`：「統上合作團隊」→「特定合作團隊」。
   6. `lessee-bulk-notify`：「統上」→「特定合作團隊」。
   7. `contract-rentbasic-latefee`：「新北住都角色群組」→「特定合作團隊」。
8. **IoT 例外（9.17 S3b 業主裁決「B 不完整，下個計畫補例外」）**：依 `inputs/evidence-9.17-S3b-scheduled-send-meter-20260927.md` 的 E3～E5。
   - 句 1 保留原規則。
   - 新增一句 IoT 例外（唯一未填的是電費＋綁定電錶＋讀得到讀數 ⇒ 可排入，排入與發送時自動補度數；補不到或 0 度 ⇒ 跳過不送）。
   - 標題改成含例外。
   - **第一次核**：新句 [2] 與標題判「不過」（P2）。新句寫「唯一的例外」，但 `app/Bill.php` `checkIotBill` 在 IoT 判斷之前有 `if ($this->type === self::BILL_TYPE_MOVEOUT) return true;`（`BILL_TYPE_MOVEOUT = 2` 即點退帳單），點退帳單也能排入。主 session 對碼確認後依 D1 修一次：拿掉「唯一」，改寫成「例外有兩種：點退帳單……；另外……電費……」，標題同步。其餘 16 項第一次核即判「過」。
   - **複核**（fresh verifier）＝兩項皆「過」（CONFIRMED）。附記建議未採用，避免改動已核項：「0 度」可寫成用電量 0、負用量也會跳過、BillBatchSend 在 12～15 點各跑一次。這些留 9.19 參考。
   - 來源補 `code:app/Bill.php`（`checkIotBill`、`canSchedule`）、`code:app/Http/Controllers/BillController.php`（`case 'scheduled':`、`prepareIotMeterForSend`）、`code:app/Console/Commands/BillBatchSend.php`（`$iotGuard`）。

## 差異比對輸出（最終位元組）

```
[diff] fines in base (shelves ABDE): 342; doubt set: 8 (not found in base: 0)
[diff] changed/deleted items: 18 in 8 fines; deleted fines: 0
[diff] (b) changed ids outside doubt set: 0
[diff] (c) items on protected (non-doubt) fines: 0
[diff] (f) structural differences: 0
[diff] (a) fix-log rows: 18; unlogged diffs: 0; log rows with no diff: 0
[diff] (d) deleted fines: diff 0 vs fix-log 刪除 0; equal: True
[diff] (e) rows not passed and not a deletion: 0
[diff] RESULT: PASS
```

正對照（scratch 副本各改 B `advance-fee-items`、E `bill-list-export` 一句）：

```
[diff] (b) changed ids outside doubt set: 2
[diff] (c) items on protected (non-doubt) fines: 2
[diff]   protected changed: ('jgb/B/advance-fee-items', 'sentences', '0', '改')
[diff]   protected changed: ('jgb/E/bill-list-export', 'sentences', '0', '改')
[diff] RESULT: FAIL
```
