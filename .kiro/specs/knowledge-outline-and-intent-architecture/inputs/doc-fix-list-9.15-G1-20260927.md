# 文件／文案待修清單（Plan 9.15 S2 G1 裁決產出，2026-09-27）

> 業主裁決（`review-sheet-9.15-S2-DE-20260927.md` G1）：**以程式為準寫進細目，不一致處另列本清單交產品**。細目已依程式寫；本清單列出幫助中心或畫面文案與程式行為不一致之處，供產品決定改文件、改文案，或改程式。
> 來源：jgb2 釘住 commit `b2ee2ac382ce`；各條原始說明見 `.claude/skills/outline-curation/runs/outline-20260920/open-questions-20260923.md` 同編號。

| # | 細目 | 哪裡不一致 | 程式實況（細目已照此寫） | 待修的是 |
|---|---|---|---|---|
| 21 | `jgb/D/contract-create-estate-completeness-requirement` | 幫助中心 landlordonboarding04lease：未刊登物件不能新增合約 | 2024/11 起建約條件已改（`ContractController`） | 幫助中心 |
| 24 | `jgb/D/contract-rentbasic-template-and-dates` | 幫助中心 landlordonboarding04lease：「內政部所規範的五種合約範本」 | 範本清單由 `resources/structures/contract/edit/options.php` 定義，與五種名目不同 | 幫助中心 |
| 26 | `jgb/D/contract-additional-convention` | 補充條款兩種上限說法：「至多 1 頁 A4」與「最多 50 行、每行 50 字」 | 兩個限制同時存在（排版提示 vs 輸入限制） | 畫面文案（宜統一說法） |
| 28 | `jgb/D/social-housing-notary` | 幫助中心 Landlordonboarding09Socialhousing：「公證是必要的程序」 | 社宅合約有「不辦理公證理由」欄 | 幫助中心 |
| 33 | `jgb/D/move-out-timing-window` | 幫助中心只寫「30 天內到期或已解約可點退」，未寫到期後上限 | `Contract::canMoveOut()` 到期後無上限 | 幫助中心（補述） |
| 37 | `jgb/E/bill-list-keyword-search` | 程式註解說「合約帳單」不加入下拉 | 實際放在 `keyword_for.values`，下拉會出現 | 程式註解（或程式） |
| 38 | `jgb/E/bill-fee-item-rules` | 錯誤文案「當期度數必須大於上期度數」 | 判斷式是「小於」才報錯，等於不報錯 | 畫面文案或判斷式 |
| 45 | `jgb/E/newebpay-precondition` | 錯誤文案「請先完成手機號碼驗證」 | 只檢查手機欄位是否為空，未檢查驗證狀態 | 畫面文案或判斷式 |
| 46 | `jgb/E/newebpay-payment-methods` | 「開通帳號」與「取得金流廠商設定」兩處付款方式清單差「超商條碼」 | 開通 6 種、編輯畫面 7 種 | 程式（兩處清單不一致） |

另：D 架驗證中發現的 jgb2 程式缺陷（非文件問題，一併交產品）：
- 合約狀態「提前解約中」時，合約總表齒輪選單把「點退押金」誤寫成再推一次「點交物件」，畫面出現兩個停用的「點交物件」（`ContractController@webList` 的 `case Contract::CONTRACT_EARLY_TERMINATION`）。
