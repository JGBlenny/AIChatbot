# DSP-068 標點例外：適用行凍結清單（2026-09-23）

**規則（與 Plan §3 S3 映射列逐字同一條，⛔ 逐終止符判、無整句前提）**：細目**內容行**中，落在成對 `「」`／`『』`／`（）` 深度內、且**下一個字元為右括號**的終止符（`。！!？?`），寫入正本時刪去。⛔ 只動內容行；⛔ 標題／`phrasings`／屬性行一字不動；⛔ 引號外標點不動。**「適用行數」＝有 ≥1 個刪除位移的內容行數。**

重跑法：對每個 `sentences[i]` 取 `rstrip()` 後字串，以成對括號計深度，逐字元掃；深度 >0 且該字元為終止符、且下一字元為右括號者，記下位移。有位移者即適用行。

## 步驟 0 前（現況 drafts）：21 行／25 個字元

| 細目 id | 句索引 | 被刪字元位移 |
|---|---|---|
| `jgb/A/login-forget-password-link` | 0 | 13 |
| `jgb/A/login-forget-account-link` | 0 | 13 |
| `jgb/A/notification-settings-save` | 1 | 47,77 |
| `jgb/B/biglandlord-seat-limit` | 1 | 60 |
| `jgb/C/forcebinding-completion-states` | 1 | 27 |
| `jgb/C/estate-list-batch-actions` | 1 | 36,114 |
| `jgb/C/estate-house-preview-unpublished` | 0 | 61 |
| `jgb/C/estate-house-invite-countdown` | 0 | 64 |
| `jgb/E/bill-monthly-report-upload` | 3 | 79 |
| `jgb/E/social-housing-sheet-archive` | 0 | 60 |
| `jgb/E/recharge-account-immutable` | 3 | 73 |
| `jgb/F/repair-apply-detail-fields` | 2 | 82 |
| `jgb/F/repair-edit-switch-status` | 0 | 53 |
| `jgb/F/repair-edit-application-detail-readonly` | 0 | 80 |
| `jgb/F/repair-edit-tenant-memo` | 1 | 94 |
| `jgb/F/repair-edit-share-to-vendor` | 0 | 65 |
| `jgb/I/pricing-quota-full-block` | 2 | 18,91,170 |
| `jgb/I/demo-form-submit-result` | 0 | 28 |
| `jgb/I/control-panel-entry-scope` | 1 | 40 |
| `jgb/I/tcloud-link-invalid-cases` | 0 | 61 |
| `jgb/I/tcloud-link-invalid-cases` | 1 | 59 |

## 步驟 0（手改 drafts，生成前；⛔ 不由腳本代改）

這 2 行的終止符在標籤中間，⛔ 不適用刪除，須先把該引號拆成兩段各自逐字的引號。**拆後字面寫死如下**：

| 細目 id | 句索引 | 改為（逐字） |
|---|---|---|
| `jgb/A/login-no-account-register-link` | 0 | 尚未註冊的使用者也可從登入頁「還沒有帳號嗎？」旁的「立即註冊」連結前往註冊頁。 |
| `jgb/C/forcebinding-completion-states` | 0 | 當所有物件都綁定完成時，畫面會顯示「恭喜！」加上「你已經成功綁定所有物件」，並提供前往社區總表的按鈕。 |

## 步驟 0 後（生成時的預期實算）：**23 行／27 個字元**

拆後那兩段引號各自以終止符結尾、下一字為右括號 ⇒ 由 DSP-068 規則刪去（「還沒有帳號嗎？」→「還沒有帳號嗎」、「恭喜！」→「恭喜」），各新增 1 行 1 字元。

| 細目 id | 句索引 | 被刪字元位移 |
|---|---|---|
| `jgb/A/login-no-account-register-link` | 0 | 21 |
| `jgb/C/forcebinding-completion-states` | 0 | 20 |

⇒ **腳本的刪除清單應為 23 行／27 個字元**；與此不符即停。
