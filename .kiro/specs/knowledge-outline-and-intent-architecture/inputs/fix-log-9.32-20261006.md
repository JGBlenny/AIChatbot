# Plan 9.32 修正紀錄（抽查不成立 4 句依 D1 修正；依業主終審核可的 4 條套用於 repo drafts）

> 列由 `drafts_diff.py --list` 機械產生（基準＝組基準快照 scratch `p932/W-base/runs`，句序為 drafts 句序、0 起算）；判定＝先審（含複核）最終結論。**範圍**寫在「依據」欄（格式同 Plan 9.21 §1「新 D1」）：`依據 #n`＝Plan 9.31 抽查單第 n 句判不成立所指；`整條 #m`＝同條整條檢查連帶修改（m＝標題或 drafts 句序）；`先審 #m`＝本計畫先審新抓到的不成立句（D1 修一次＋複核）；`業主裁定`＝業主 2026-10-06 裁定的措辭。起草＝主 session（ops 原檔 scratch `p932/draft/ops.json`，逐項依據見計畫 §6 步驟 2）。

## 修正表

| 細目 | 欄位 | 句序 | 動作 | 依據 | 判定 |
|---|---|---|---|---|---|
| `jgb/A/notification-settings-extra-emails` | sentences | 2 | 改 | 依據 #2 | 過 |
| `jgb/D/contract-invite-and-review-period` | sentences | 0 | 改 | 依據 #26 | 過 |
| `jgb/D/contract-invite-and-review-period` | sentences | 1 | 改 | 業主裁定＋整條 #1 | 過 |
| `jgb/D/contract-invite-and-review-period` | title |  | 改 | 業主裁定＋整條 #標題 | 過 |
| `jgb/D/contract-list-row-gear-actions` | sentences | 0 | 改 | 依據 #5 | 過 |
| `jgb/D/contract-list-row-gear-actions` | sentences | 5 | 改 | 先審 #5 | 過 |
| `jgb/D/contract-list-row-gear-actions` | title |  | 改 | 整條 #標題 | 過 |
| `jgb/E/recharge-account-history-content` | sentences | 0 | 改 | 依據 #14 | 過 |
| `jgb/E/recharge-account-history-content` | title |  | 改 | 整條 #標題 | 過 |

## 刪除

## 依據
- #2 `jgb/A/notification-settings-extra-emails` drafts 句 2：9.31 獨立代理判不成立、業主裁定「不成立 (Recommended)」——「每個分類卡片都可各自新增／移除」漏權限例外（`edit_notification`）。證據 `verification/20261006-p931-spotcheck-judgment.json` 第 2 筆。
- #5 `jgb/D/contract-list-row-gear-actions` drafts 句 0：同上第 5 筆——「依狀態、身分、權限決定」屬排他列舉。
- #14 `jgb/E/recharge-account-history-content` drafts 句 0：同上第 15 筆（抽查單第 14 句）——「列出每一筆」不成立，畫面最多顯示最近 50 筆。
- #26 `jgb/D/contract-invite-and-review-period` drafts 句 0：同上第 27 筆（抽查單第 26 句）——「審閱期才能簽約」讀成須等滿才能簽。

## 整條依據
- `jgb/D/contract-list-row-gear-actions` 標題：括號「其餘依合約狀態、身分與權限增減」與句 0 同一排他列舉問題 ⇒ 改「依合約狀態、身分、權限等條件增減」。
- `jgb/E/recharge-account-history-content` 標題：括號「每筆金額變動」與句 0 同一 50 筆問題 ⇒ 改「最近 50 筆金額變動」。
- `jgb/D/contract-invite-and-review-period` 句 1 與標題：「不同團隊可以各自覆蓋預設值」「天數為團隊可調整設定」屬 Plan 9.29 §6 W3 留下的待裁措辭，依業主 2026-10-06 裁定「改成「由 JGB 依團隊設定」 (Recommended)」改寫（計畫 §6）。

## 先審新抓到
- `jgb/D/contract-list-row-gear-actions` drafts 句 5（未改動的原句）：先審判不成立——列「執行中合約」各階段選項時漏「提前解約」（`verification/20261006-p932-prereview.json`）；主 session 對碼確認後依 D1 修一次（句尾補「提前解約」的條件），fresh 複核成立（`verification/20261006-p932-recheck.json`）。

## 整條待裁
- 無（#26「團隊可調整」措辭已由業主核可本計畫時裁定改寫，見計畫 §6；選項說明中的否定子句「業者端沒有設定畫面」未寫入，原因見終審單）。
