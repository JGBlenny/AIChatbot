<!-- plan-meta
endpoint_from: pm 533/533, prospect 120/120
endpoint_to: pm 537/537, prospect 121/121
consent_zero:
-->
# Plan 9.25：只補真缺內容——社區選擇畫面＋補回 3 項資訊（4 條新細目）

> **現況**（`endpoint_progress.py`，2026-10-04，HEAD `6e4db63d`）：`已審細目 pm 533／533、prospect 120／120；頁面 pm 140／183、prospect 53／183`；現有 539 條細目全審。
>
> **本計畫預期**：新增 4 條細目並全審 ⇒ **已審 pm 533／533→537／537、prospect 120／120→121／121**；**頁面 pm 140→141**（只有 `communities.pick` 是正本完全沒有內容的頁）。頁面指標其餘缺口是引用沒對到入口檔、不是內容缺口（§0、§2），本計畫不追。
>
> **驗收清單（凍結）**：`.kiro/specs/knowledge-outline-and-intent-architecture/acceptance-9.25-20261004.md`（觀察點＝commit 後 HEAD）。

## 0. 為什麼有這份

- 業主 2026-10-04「繼續這些?」＋選擇「頁面缺口＋4項資訊合一份」「這份只做 pm，prospect 另議」「先不排」（存量補核）「ASK」；就緒審查第 1 輪後再選：「**只補真缺內容 (Recommended)**」——對選項「新寫 communities.pick＋3 項資訊（約 4～6 條新細目），頁面 pm 約 140→141；其餘 10 頁記為量尺待辦」。
- **頁面缺口對碼結果（§5 第 1 輪紀錄）**：pm 未覆蓋 43 頁中，11 頁原列「真缺口」，其中 10 頁的內容已由已審細目回答（`sources` 指向子元件，量尺只比入口檔）；只有 `communities.pick` 在正本沒有內容，而它的「何時會出現」也已由 `jgb/C/community-batch-add-and-copy`（句 3）與 `jgb/C/estate-list-add-must-pick-community`（句 1）回答——**真正缺的只有「選好社區之後會發生什麼」**。
- **3 項資訊**（9.24 依 D1 整句刪、記於 9.24 §2；第 4 項「免費方案最多 5 個物件」已由已審 `jgb/I/pricing-free-trial-feature-scope` 標題涵蓋）——寫成新細目，⛔ 塞回原細目（原細目內容一改就丟已審）。

## 1. 切片：只有 S1（起草＋00c 先審＋業主終審＋寫入＋全數核對＋一次 commit）

### 擬稿（主 session 起草；終審以 00c verifier 修正後的版本為準）

| 新細目 id | 粗目（drafts 逐字） | 標題 | 句子 | target_user |
|---|---|---|---|---|
| `jgb/I/pricing-landlord-initial-plan` | 方案、價格與免費試用 | 建立房東身分時會拿到什麼方案？（企業團隊與社宅房東自動取得免費方案；個人房東一般也是，透過特定優惠或行銷活動連結註冊時則取得活動指定的方案） | ①企業團隊與社宅房東身分建立時，一律自動取得免費方案。②個人房東身分建立時，一般也會自動取得免費方案。③個人房東如果是透過「註冊免費方案」類型的優惠連結，或行銷活動的邀請連結完成註冊，取得的是該活動指定的方案，而不是免費方案。 | pm、prospect |
| `jgb/D/contract-thinkcloud-diy-pdf-sign-blocked` | 租約公證（公證分頁與公證服務） | 客製化契約書送簽時 PDF 底稿解析失敗會怎樣？（簽署不會開始） | ①用「電子合約 - 客製化契約書」建立的合約，送去簽署時如果 PDF 底稿解析不出來，簽署不會開始。 | pm |
| `jgb/A/account-change-password-rules` | 帳號資訊 | 在帳號資訊頁改密碼，新密碼有什麼規則？（至少 6 個字元、需與確認新密碼一致；英數混合在這裡只是提示） | ①在帳號資訊頁修改密碼時，新密碼長度需至少 6 個字元，且需與確認新密碼欄位一致。②帳號資訊頁的密碼表單會提示「密碼應有至少一位英文和數字」，但按「儲存」時不會檢查這一條。③註冊帳號時設定的密碼則必須同時包含英文與數字。 | pm |
| `jgb/C/community-pick-next-step` | 社區列表與建立 | 社區選擇畫面選好社區之後會發生什麼？（複製社區直接建立副本並進入編輯；新增物件進入新增畫面；複製物件接著挑選物件） | ①社區選擇畫面會依用途顯示不同標題：「請選擇要複製的社區」「請選擇要新增物件的社區」「請選擇要複製物件的社區」。②複製社區時，選好社區按「下一步」，系統會直接建立一份副本並進入新社區的編輯頁。③新增物件時，選好社區按「下一步」，會進入在該社區新增物件的畫面。④複製物件時，選好社區按「下一步」，會接著進入挑選要複製哪一個物件的畫面。 | pm |

- 證據（釘住匯出 `b2ee2ac382ce`，起草時逐字 grep）：`app/User.php` Step4（`case Role::RULE_KEY_LANDLORD_INDIVIDUAL:`、`$promotion['type']=='registration_plan'`、`case Role::RULE_KEY_LANDLORD_CORPORATE:`、`case Role::RULE_KEY_LANDLORD_SOCIAL_HOUSING:`、`$role->plan_name = '免費方案';`）；`Admin/PromotionController.php` `'registration_plan' => '註冊免費方案',`；`MarketingInviteController.php` `'type'              => 'registration_plan',`；`ContractController.php` `// 僅攔 DiyPdfUnparseableException，其他例外類型保留既有錯誤路徑。`、`readToSignBlock`；`UserController.php` `'password' => 'min:6|required_with:password_confirmation|same:password_confirmation',`；`PasswordForm.vue` `tip_pwd_format: '密碼應有至少一位英文和數字',`；`account.blade.php` 儲存按鈕行（無 `password_allow_submit` 綁定，對照 `safety.blade.php` 有）；`AuthController.php`（`authEmail`）`'password' => 'required|string|min:6|regex:/^(?=.*[a-zA-Z])(?=.*[0-9]).*$/',`；`communities/pick/Index.vue` 三個 `t('請選擇要…的社區')`、`communityCopyFetcher` 後 `name: 'communities.edit'`、`/api2/estate/create?communityId=`、`name: 'estates.pick'`；`BottomNav.vue` `default: '下一步',`。
- **既有細目對照（起草與 verifier 必讀，⛔ 同題、⛔ 矛盾）**：`jgb/I/pricing-free-trial-eligibility`、`pricing-free-vs-experience-plan`、`pricing-free-trial-feature-scope`；`jgb/D/contract-thinkcloud-signing-variants`；`jgb/A/register-password-rule`（註冊端強制英數，與新細目句 ③ 一致）、`account-change-password`；`jgb/C/community-batch-add-and-copy`、`estate-list-add-must-pick-community`、`community-estates-add-batch-copy`。

### 步驟

1. **主 session 起草**：依 00c 寫成 4 條完整細目（13 鍵、講法 2～5 條、否定句附 `not_supported_greps` 實跑結果），存 `scratchpad/p925/new-fines.json`。機械檢查全過：evidence 逐字命中匯出（miss 0）、`not_supported_greps` 重跑相符、用語掃描（識別字／路徑）0、註解掃描 0、客戶名 0、講法與全庫 NFKC 不重複、`communities.pick` 細目 `sources` 含 `src/pages/communities/pick/Index.vue` 且有 evidence。
2. **00c 先審 verifier**（fresh，DSP-066）：4 條逐句判 成立／矛盾／無源／非事實（⛔ 抽樣）；另查同題（與上列既有細目或全庫）、跨粗目矛盾、排他／過度概括、`target_user` 合理、漏掉的可問事項。不成立 ⇒ D1 修一次＋複核；仍不過 ⇒ 整句刪；整條不成立 ⇒ 不寫。
3. **內容要點逐項重算＋不足即停**（寫進 drafts 之前；對照驗收清單 A1、A2）——下表每一項都要在修正／刪句後的版本裡有**對應且經 00c verifier 判成立**的句子（或標題要點由成立句支撐）；**任一項沒有 ⇒ 停、交業主**（縮小範圍須業主裁），⛔ 往步驟 4、5 走：

   | 項 | 對應驗收 | 必須有成立句說出 |
   |---|---|---|
   | P1 | A1 | 社區選擇畫面選好社區之後的去向：複製社區會建立副本並進入編輯、新增物件會進入新增畫面、複製物件會接著挑選物件（三種去向各有成立句），且細目 `sources` 含 `src/pages/communities/pick/Index.vue`、有 evidence |
   | P2 | A2(1) | 企業團隊與社宅房東自動取得免費方案；個人房東一般也自動取得免費方案；優惠連結（「註冊免費方案」類型）與行銷活動邀請連結兩條例外入口取得活動指定方案——三點皆有成立句，且無排他寫法 |
   | P3 | A2(2) | 客製化契約書送簽時 PDF 底稿解析不出來，簽署不會開始 |
   | P4 | A2(3) | 帳號資訊頁改密碼：新密碼至少 6 個字元、需與確認新密碼一致、英數提示在此不強制——三點皆有成立句；與 `jgb/A/register-password-rule`（註冊端強制英數）不矛盾 |
4. **業主終審**：審核單 `inputs/review-sheet-9.25-<日期>.md`（4 條標題＋句子＋verifier 判定）；業主原文逐字記 §6。終審後（若業主退回或要求刪句）再以步驟 3 的 P1～P4 逐項重算；任一項不足 ⇒ 停、交業主。
5. **寫入**（同 9.24 §1 步驟 0～9）：make audit 基準＋指紋 ⇒ 備份（runs、canon、HANDOFF）⇒ `add_fine.py` 附加到 `drafts-{A,C,D,I}.json` ⇒ 重生成（`--expect-reviewed-kept 539`）⇒ 既有 539 條逐欄不變 ⇒ 寫入 4 條 reviewed ⇒ 終點指標 ⇒ 全套 unit 差集 ∅ ⇒ §6／HANDOFF ⇒ `make audit` 只剩 W ⇒ fresh outcome verifier（`kind: write`，判準含同題／跨粗目矛盾／排他／過度概括）⇒ extract ⇒ `make audit` PASS ⇒ 指紋 ⇒ commit。
- **commit 範圍**：`drafts-{A,C,D,I}.json`、runs 生成 3 檔、`canon/jgb/{A,C,D,I}.md`、`CATALOG.md`、`jgb.json`、審核單、本計畫、驗收清單、HANDOFF、證據檔（實數於步驟 5 記 §6 並以 `git diff --cached --name-only` 核對）。
- **還原**：寫入 repo 後到 commit 前任何停下 ⇒ 由 `scratchpad/p925-backup/` 還原 runs（刪新增 3 檔）、canon、HANDOFF ⇒ 記 §6 ⇒ 停下交業主。commit 後驗收 FAIL ⇒ ⛔ 改寫歷史、回報業主。

## 2. 不做（另案）

- **量尺待辦（業主「只補真缺內容」）**：10 頁內容已有、引用未對到入口檔——`users.forget`、`users.verify`、`estates.dashboard.bills`、社宅 `landlordBasic`／`photos`／`subsidyTerms`／`facilities`、`entrustedContracts.list`、`balanceInvoices.edit.belongingEstates`、`indexs`（官網首頁內容在 `listings/Home.vue`，量尺比 blade `ListingController`）；另約 29 頁外殼頁、`notifications.index`（`#方法` 引用）、`/help` 外殼。`bills.sheet` 依 G3 排除。
- prospect 可見頁範圍（業主「另議」）；已審存量補核（業主「先不排」）。
- 9.23／9.24 verifier 附記的 P4。

## 3. 業主裁決與待裁

- **已裁**：§0。執行模式 ASK。
- **待裁（核可時一併回覆）**：
  - (a) 本計畫範圍（4 條新細目）與流程（單片、主 session 起草、00c verifier 先審後交業主終審）。
  - (b) **CANON 盤查範圍**：`/canon-audit outline-drafting` 宣告來源含整個 `runs/outline-20260920/`（45 檔、2.0 MB）。建議只讀規約 00c、定義、骨架、DSP-065～068、HANDOFF 全文，drafts 只讀 A／C／D／I 涉及粗目段落，§6 記未全讀清單；或 (b2) 照規則全讀。

## 4. 停止條件

- 已審細目數任何時候下降 ⇒ 停。
- 內容要點 P1～P4 任一項不足（步驟 3、4）⇒ 停、交業主（寫進 drafts 之前）。
- 任一機械檢查或驗收項不符 ⇒ 依 §1 處置；不設預算停點（業主「別管上限 聚焦驗收成果」）。
- 一次只跑一個代理；代理 brief 帶 HANDOFF §12-2 必禁清單。

## 5. 就緒審查紀錄

- **第 1 輪（fresh plan-verifier）＝REVISE**（2026-10-04，針對原「11 頁＋3 項」版）：P2×3——(1) 缺口頁多半已有已審細目回答，計畫只准新增且起草者不讀正本 ⇒ 必然同題；密碼規則與 `register-password-rule` 跨粗目可能矛盾；(2) `indexs` 的 `target_user` 與 A1 只算 pm 衝突；(3) 刪條後無覆蓋重算與 commit 前停點。
- **主 session 對碼**：(1) 屬實且更廣——11 頁中 10 頁內容已由已審細目回答（`users.forget`：`forget-account-flow`、`forget-password-flow` 引 `parts/forget/*.vue`；`users.verify`：`register-verify-code-shape`、`register-email-verify-resend`；`estates.dashboard.bills`：`estate-dashboard-bills-tabs` 引 `src/routes/estates.js`；社宅 `photos`／`subsidyTerms` 細目 `code:` 來源 0、`facilities` 引 `SocialHousing.vue`、`landlordBasic` 引 `useEditStore.js`；`entrustedContracts.list`：`entrusted-contract-create-entry` 引 `_parts/PageTop.jsx`；`belongingEstates`：`balance-invoice-pick-and-individual-rent`；`indexs`：I-marketing-home 7 條引 `listings/Home.vue`）。只有 `communities.pick` 無內容。註冊端強制英數（`AuthController.php` `authEmail` 的 regex 規則、`AccountSetting.vue` `allowSubmit`），`register-password-rule` 成立。
- **處置**：交業主裁 ⇒ 業主「只補真缺內容」⇒ 本版改寫：範圍縮為 4 條新細目（(1) 同題風險以「既有細目對照」與 verifier 同題判準處理；(2) `indexs` 移出範圍；(3) 步驟 3、4 加覆蓋重算＋不足即停）。送第 2 輪。
- **第 2 輪（fresh plan-verifier）＝REVISE**（2026-10-04）：P2×1——步驟 3、4 的覆蓋重算只看「各剩一條」，比驗收 A1／A2 的內容要點鬆；verifier 刪句後（例：pricing 句 ③、密碼句 ②、community-pick 句 ②～④）仍會放行並 commit，commit 後才 FAIL。擬稿各句經該輪對匯出抽查皆有出處。⇒ **第二次自動 REVISE，停止重送、逐條處置**：**FIX**——步驟 3 改為 P1～P4 內容要點逐項對照表（對應 A1、A2(1)～(3)），任一項無成立句即停；步驟 4 終審後同表重算；§4 同步。依規則開一次收尾審查；再判 REVISE 就暫停交業主。
- **收尾審查（fresh plan-verifier）＝READY**（2026-10-04）⇒ 交業主核可（`next_gate: user_approval`）。

## 6. 執行紀錄

### 立案前預跑（2026-10-04，HEAD `6e4db63d`；repo 未動）

- 43 頁未覆蓋清單：容器內以 `endpoint_progress.page_hit` 對 HEAD 已審 pm 細目重算 ⇒ `units 183 covered 140 missing 43`。
- `add_fine.py`（`scratchpad/p925/`）：合成細目附加到 scratch `drafts-A.json` ⇒ `added 1 fines to shelves A`；重複加入 ⇒ `❌ … already exists`、exit 1；其餘八架與 repo `cmp` 相同；scratch 重生成 ⇒ `已審保留：539 條／丟棄：0 條`、`57 粗目／540 細目`；終點指標 `已審細目 pm 533／534、prospect 120／120；頁面 pm 140／183`。
- `bills.sheet` 排除依據：`inputs/plan-9.15-reviewed-canon-progress-20260926.md`「G3 裁『財務報表頁不列入大綱』」。第 4 項已涵蓋：`I.md` `{#jgb/I/pricing-free-trial-feature-scope}` 標題含「最多 5 個物件」（已審）。

### S1（2026-10-04）

- **業主裁決原文**（2026-10-04，對「請您核可，並決定 CANON 盤查範圍」）：「核可，盤查照 (b)」——核可本計畫（4 條新細目、單片流程）；盤查依 §3 (b) 範圍。
- **盤查方式**：依 (b) 讀規約 00c、定義、骨架、DSP-065～068、HANDOFF 全文，drafts 只讀 A／C／D／I 涉及粗目段落；**未以 `/canon-audit` 工具起盤查**（該工具強制讀完宣告的全部來源＝(b2)，且未結束前會擋所有視窗與子代理收尾）。
- **盤查（(b) 範圍）已讀**：`steps/00c-topic-first-drafting.md`、`inputs/definitions-outline-baseline-20260919.md`、`inputs/outline-skeleton-20260920.md`、`.claude/DECISIONS.md` DSP-065／065a／066／067／068／071、HANDOFF（本 session 全讀）、drafts-A「帳號資訊」、drafts-C「社區列表與建立」、drafts-D「租約公證（公證分頁與公證服務）」、drafts-I「方案、價格與免費試用」粗目段落。**未全讀**：`runs/outline-20260920/` 其餘 41 檔（drafts 其他粗目、open-questions、dsp-068、reviewed-dropped 各期產物）、`inputs/outline-summary-20260920.md`、`steps/00-feature-surface.md`。
- **步驟 1 起草**（主 session）：4 條存 `scratchpad/p925/new-fines.json`（擬稿依定義 D2「3～10 句」把 PDF 送簽細目補一句「送簽時會再解析底稿以放置簽名位置」，證據 `readToSignBlock`）。機械檢查：evidence 25 筆逐字命中匯出、miss 0；用語掃描（識別字／路徑）0；講法與正本全庫（NFKC）0 重複、新細目間 0 重複；客戶名詞表自檢 18 詞正負對照全過、命中 0；`not_supported_greps` 實跑：`account.blade.php` `password_allow_submit` 1、正對照 `safety.blade.php` 2；`ContractController.php` 送簽 catch 第 18466 行早於 `thinkcloud_api('create'` 第 18640／18649 行；`User.php` Step4 個人房東 `registration_plan` 分支設定 `plan_name = $promotion['plan_name']` 後 `break`。
- **步驟 2 00c 先審**（fresh verifier）＝**FAIL**：3 條全句成立（`pricing-landlord-initial-plan`、`contract-thinkcloud-diy-pdf-sign-blocked`、`account-change-password-rules`）；`community-pick-next-step` 句 3 與標題對應要點「新增物件進入新增畫面」矛盾——`EstateController.php` `create` 直接 `Estate::createEstate(...)` 後 `redirect()->route('estates.edit', …)`，使用者進的是「編輯物件」頁、物件已建立。P1 不足、P2～P4 足。附 P3：pricing 句 3「「註冊免費方案」類型」為後台用語（延後，保留：與 P2 要點一致）；P4×3（密碼提示 evidence 改引 `UserController` 實際傳入值、thinkcloud grep 說明 18640 為註解、pricing grep 須 `-F`／`/usr/bin/grep`）。
- **D1 修一次**（主 session）：句 3 改為「新增物件時，選好社區按「下一步」，系統會直接在該社區建立一筆新物件，並進入這筆物件的「編輯物件」頁。」；標題對應改「新增物件直接建立物件並進入編輯」；evidence 加 `EstateController.php`、`estates/edit/Index.vue` `label: t('編輯物件'),`；P4×3 一併修。evidence 29 筆 miss 0。修正前存 `new-fines-v1.json`。送 fresh 複核。
- **00c 複核**（fresh verifier）＝**PASS**：新句 3 與標題成立（`pick/Index.vue` `window.location.href = …/api2/estate/create?communityId=…` → `EstateController.php` `Estate::createEstate` → `redirect()->route('estates.edit', …)` → `estates/edit/Index.vue` 麵包屑 `label: t('編輯物件'),`）；修正範圍與 v1 逐欄比對只動計畫所述處；P1 三種去向各有成立句。附 P4×2（成功路徑以外的失敗分支未寫、`web.php` 兩條同名 `estates.edit` 路由），延後。
- **步驟 3 內容要點重算**：P1 足（句 2 複製社區、句 3 新增物件、句 4 複製物件，`sources` 含 `src/pages/communities/pick/Index.vue` 且有 evidence）；P2 足；P3 足；P4 足 ⇒ 過閘。
- **步驟 4**：審核單 `inputs/review-sheet-9.25-20261004.md` 已產生，交業主終審。
- **業主終審原文**（2026-10-04，對審核單 `review-sheet-9.25-20261004.md`）：「4 條終審過」——4 條全部標已審，條件是寫入後全數逐句核對成立。終審未退回、未刪句 ⇒ P1～P4 維持足。
- **步驟 5 寫入**：
  - 基準：`make audit` `OVERALL: PASS（2026-10-04）`；其他工作線未 commit 檔 41 個 sha256 指紋 `scratchpad/p925/foreign-fp.txt`（正對照含 `rag-orchestrator/services/agent/runtime.py`）；HEAD `6e4db63d1bb11ce5a22ebb8c9cefcf46fd6bee03`；備份 `scratchpad/p925-backup/`（runs、canon、`HANDOFF.bak`）與 repo 相同。
  - `add_fine.py` ⇒ `added 4 fines to shelves ACDI`；drafts-B／E／F／G／H 與備份相同。重生成 ⇒ `已審保留：539 條／丟棄：0 條`、`57 粗目／543 細目`、open_questions 54；runs 新增 `*-20261004-s1-925*` 3 檔（自 scratch 複製回 repo、`cmp` 相同）；`jgb.json` 對備份：新增恰為 4 個 id、既有 539 條 0 變動、粗目欄位不變；終點指標 `已審細目 pm 533／537、prospect 120／121`。
  - 寫入 reviewed ⇒ `added 4`；容器重匯出與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 539 -> current 543; added lines 4; approved 4`、`reviewed fines pm 537, prospect 121`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`。
  - **終點指標 `已審細目 pm 537／537、prospect 121／121；頁面 pm 142／183、prospect 53／183`**。頁面 +2：`page:communities.pick` 與 `page:estates.edit`（`community-pick-next-step` 句 3 的 evidence 引 `src/pages/estates/edit/Index.vue` 的麵包屑「編輯物件」，該檔即 `estates.edit` 入口檔）；失去 0 頁。
  - 單元：`scripts/run-tests.sh unit` ⇒ `passed=3931 failed=9`，與基準雙向差集＝∅（`scratchpad/p925/unit-after.log`）。
  - HANDOFF：開頭終點指標、一句話現況、開工第 2／5 步、§12-1（加 9.25 列並把 9.23／9.24 列依序排）、§12-4（未審段、新增頁面量尺待辦段）。
  - `make audit`（派 verifier 前）：與基準相比差異＝不變量 43 `W 工作樹有 4 條細目新增已審或已審內容變動，卻沒有 base＝HEAD 的全數逐句核對證據`（預期），以及不變量 34 講法數 1742→1753（＋11＝4 條新細目講法 3＋2＋3＋3，仍 PASS）（`scratchpad/p925/audit-prev.log`）。以下由證據檔與 commit 訊息記錄。
