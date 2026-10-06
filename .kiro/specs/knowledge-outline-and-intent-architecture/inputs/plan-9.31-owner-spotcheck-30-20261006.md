<!-- plan-meta
endpoint_from: pm 537/537, prospect 121/121
endpoint_to: pm 537/537, prospect 121/121
consent_zero: 「核可，同意本計畫 +0 (Recommended)」
-->
# Plan 9.31：業主抽查 30 句（目標驗收規格 §2.2）（2026-10-06）

> **現況**（2026-10-06，HEAD `3d0cba8a`）：`已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183`；正本 543 條全審、內容句（`content_units`）1,538 句；`canon_sha256 = 8a5844bc…`。
>
> **本計畫的進度單位**：規格 §2.2「業主抽查 30 句」——**已抽查 0／30 → 30／30**，並記下成立數。
>
> **已審細目數 +0**：本計畫只抽查、不改正本。抽查不成立的句子交下一份計畫依 D1 處置。`consent_zero` 已填入業主 2026-10-06 核可原文（見 §6）。

## 0. 依據

- 業主 2026-10-06：「照建議」——對主 session 建議「下一份先做業主抽查 30 句，把『整句刪掉的正確資訊重新起草』排在它後面」。
- 目標驗收規格 `goal-acceptance-spec-20261004.md`：
  - §2.2：「**業主抽查 30 句**（種子固定，從全部已審細目抽）：業主或其指定人對源，須 30／30 成立。」
  - §5 第 5 點：「抽查（20 件、30 句）由**業主本人**做；主 session 準備抽查單，每件／句附來源位置。」
- 種子凍結檔 `inputs/goal-eval-freeze-20261004.json`：`seeds.owner_spotcheck_sentences_30 = 20261006`，`rng = "Python random.Random(seed)"`。
- 規格與凍結檔沒有寫「母體怎麼排序」「怎麼從細目取句」；本計畫在抽樣前補上下面的定義並凍結（§1 步驟 1），⛔ 看到抽樣結果後再改。

## 1. 流程（一個切片，一次 commit）

**1. 步驟 0 基準**
- 記錄 HEAD；跑 `make audit`；確認 `rag-orchestrator/canon` 對 HEAD 無改動；記錄他線未提交檔指紋（含正對照 `runtime.py`）。

**2. 凍結抽樣定義並抽樣**（scratch 腳本，結果寫進抽查單）
- **母體**：HEAD 的 `rag-orchestrator/canon/jgb.json` 中 `reviewed_by` 非空的細目，依 `coarses[]`→`fines[]` 的檔內順序，每條細目的每個 `content_units[i]` 為一個元素，元素＝`(細目 id, i)`。現況 543 條、1,538 句。
- **抽樣**：`random.Random(20261006).sample(母體, 30)`，保持抽出順序編號 1～30。
- 抽查單記下：抽樣時的 HEAD 全碼、`canon_sha256`、母體大小、腳本原文。
- **重現檢查**：同一腳本跑兩次，30 筆逐筆相同。正對照：腳本印出的母體大小＝已審細目全部 `content_units` 數（現況 1,538）、`canon_sha256` 與 HEAD `jgb.json` 相同（證明讀的是指定正本）；負對照：種子改成 `20261007` 時抽出的清單不同（證明種子真的有作用）。腳本讀不到 `jgb.json`、已審細目數為 0 ⇒ 非 0 退出並印原因。

**3. 準備抽查單** `inputs/spotcheck-30-9.31-20261006.md`
- 每句一節：編號、細目 id、所屬粗目、細目標題、`target_user`、**句子原文**（正本 `content_units[i]` 逐字），以及**來源位置**：
  - 該細目的 `sources`；
  - **該細目全部 evidence**（每筆 `source`＋逐字 `quote_or_symbol`＋drafts 記的 `sentence_index`），一律全部列出。
    - 理由：drafts 的 evidence 句序已知有 23 條細目與句子錯位（HANDOFF §12-3「evidence 句序」、Plan 9.19 §2「既有的不對齊，共 23 條」），至今沒有清單也沒有修正紀錄；只列「對應本句」的 evidence 可能把支持別句的引文當成本句來源。
    - 標記「drafts 自報對應本句」：`content_units` 是正本斷句後的句子，drafts evidence 以 drafts 句序記；把正本句去標點後找它是哪一個 drafts 句的子字串，該 drafts 句序底下的 evidence 標「drafts 自報對應本句（句序未經驗證，請以內容判斷是否支持本句）」，其餘標「同細目其他句的 evidence」。
    - **大聲標記「來源位置需人工指認」**（三種情形，任一即標）：(a) 正本句對不到任何 drafts 句；(b) 對到多個 drafts 句；(c) 對到的 drafts 句底下沒有任何 evidence。⛔ 猜、⛔ 靜默留空。
    - 抽查單開頭寫明上述限制，請業主以 evidence 內容（而非句序標記）判斷來源是否支持句子。
  - 來源檔在哪裡看：`code:` ⇒ jgb2 commit `b2ee2ac382ce` 的檔案路徑；`help:` ⇒ 幫助中心檔名；`docs:` ⇒ repo 內事實帳本的錨點。
- 每節留業主判定欄：「成立／不成立／無法判斷＋理由」。
- 機械檢查：30 節＝抽樣結果；每節句子與正本逐字相同；每節列出的 evidence 筆數＝該細目 drafts evidence 筆數；每筆 evidence quote 逐字命中來源檔（正對照：任取一筆既有 evidence 命中）；三種「需人工指認」情形都有被標出——以合成樣本當正對照：(a) 把一句改成任何 drafts 句都不含的文字、(b) 造一個同時是兩個 drafts 句子字串的短句、(c) 刪掉某 drafts 句底下全部 evidence，三者跑出來都必須被標「來源位置需人工指認」；客戶名掃描（分與不分大小寫）0 或逐筆說明。

**4. 業主抽查**（業主本人，固定停點）〔⚠️ 2026-10-06 業主改定：改由指定獨立代理判、業主只裁疑義句，見 §6；以下兩點原文保留供追溯〕
- 業主逐句對源，回覆每句判定。主 session 把業主原文逐字記入 §6，並把判定填進抽查單。
- ⛔ 主 session 替業主判、⛔ 先派代理判了再給業主看（規格要的是業主本人對源）。業主要求協助查某句時，只提供來源檔內容與位置，判定仍由業主做。

**5. 結果與 commit**
- 30／30 成立 ⇒ §6 記「規格 §2.2 業主抽查達成」。
- 有不成立或無法判斷 ⇒ §6 列出各句與業主理由，轉下一份計畫依 D1 處置（修一次或整句刪→先審→業主終審→寫入→寫入核對）；本計畫 ⛔ 改正本。
- commit 前：一位 fresh verifier（`kind: change`）核對——抽樣可重現且與抽查單相同、抽查單句子與正本逐字相同、每節 evidence 全數列出且逐字命中、「drafts 自報對應本句」標記與三種「需人工指認」情形依規則標出（逐節重算）、業主判定與 §6 原文一致、正本未被改動。之後 `--extract` ⇒ `make audit` ⇒ commit（`Verified-by` 指向該證據）。
- **commit 範圍**：本計畫、驗收清單、抽查單、核對證據。⛔ `git add -A`、⛔ `--amend`；push 由業主自跑。

## 2. 不做（後續計畫）

- 抽查不成立句的修正（下一份計畫）。
- 9.24 以來整句刪掉的正確資訊重新起草（業主 2026-10-06 同意排在本計畫之後）。
- 9.30 終審單 §3 附帶觀察（疑似 jgb2 缺陷 3 項等）。
- 規格 §2.1 覆蓋、§2.4 效果的量測。

## 3. 業主裁決與待裁

- **已裁**：先做業主抽查 30 句（「照建議」）。
- **待裁（核可時回覆）**：本計畫，並明示同意 +0。
- **待裁（步驟 4）**：30 句逐句判定。

## 4. 停止條件與額度

- 正本在本計畫期間有任何改動 ⇒ 停。
- 抽樣重現檢查不一致 ⇒ 停、查腳本。
- 抽查單任一句與正本不逐字相同、或 evidence 未命中且未標「需人工指認」 ⇒ 不交業主、先修抽查單。
- **額度**：就緒審查約 0.1M、commit 前核對約 0.15M，共約 0.25M；累計超過 0.5M ⇒ 停下回報。
- **執行模式**：沿用本線 ASK；業主抽查是固定停點。

## 5. 就緒審查紀錄

- **第 1 輪**（fresh plan-verifier，2026-10-06）：REVISE，P2×1（substantive）——步驟 3 依 drafts 句序取 evidence，但 drafts evidence 句序已知 23 條錯位且無清單、無修正紀錄（HANDOFF §12-3、Plan 9.19 §2、Plan 9.20），錯位時會靜默附上支持別句的引文，機械檢查（只驗引文命中）抓不到；對到的 drafts 句沒有 evidence 時也沒規定怎麼標。**FIX**：每節一律列出該細目全部 evidence，句序對應者只標「drafts 自報對應本句（句序未經驗證）」；三種情形（對不到、對到多個、對到的句沒有 evidence）一律大聲標「來源位置需人工指認」，並以三種合成樣本當正對照；步驟 5 核對與驗收清單 B2 同步加入。主持人查證：spec 目錄內找不到 23 條錯位的具體清單（只有 Plan 9.19 記「共 23 條」），故採「全列＋標記」而非「依清單排除」。送收尾審查。
- **收尾審查**（fresh plan-verifier，2026-10-06）：**READY** ⇒ 交業主核可（`next_gate: user_approval`）。

## 6. 執行紀錄

- **業主核可**（2026-10-06，AskUserQuestion 逐字）：「核可，同意本計畫 +0 (Recommended)」（已填入 consent_zero）。
- **步驟 0**（HEAD `3d0cba8a`）：`make audit` OVERALL PASS；`rag-orchestrator/canon` 與 runs 對 HEAD 無改動；他線 41 檔指紋不變（含正對照 `runtime.py`）。
- **步驟 2 抽樣**（scratch `p931/draw.py`，原文如下）：母體 1,538 句（543 條已審細目全部 `content_units`）、`canon_sha256 = 8a5844bcc85dfe43d2f52f135d285e3beae8fbbf8858adac9b4f1ff09d4ec62f`；抽出 30 句、分屬 29 條細目（架別 E 7、A 6、C 5、D 4、I 3、B 3、F 2）。重現：同腳本跑兩次輸出逐位元相同；正對照：印出的母體大小與 `canon_sha256` 等於 HEAD 正本；負對照：種子 20261007 輸出不同；正本路徑不存在 ⇒ exit 2 並印原因。
  ```python
  pop = [(f["id"], i) for c in j["coarses"] for f in c["fines"] if str(f.get("reviewed_by") or "").strip() for i in range(len(f["content_units"]))]
  s = random.Random(seed).sample(pop, 30)
  ```
- **步驟 3 抽查單** `inputs/spotcheck-30-9.31-20261006.md`（scratch `p931/gen_sheet.py` 產生）：30 節與抽樣結果逐筆對應、每節句子與正本 `content_units[i]` 逐字相同（腳本複核 mismatch 0）；每節列出該細目全部 evidence，共 235 筆、逐字命中來源檔 235／235（初版有 2 筆未命中，查明是產生器把 `docs:.kiro/…` 審核單路徑錯解到 `docs/` 底下，修正後重產；引文本身在審核單命中 16 次）；30 節都有「drafts 自報對應本句」標記、「需人工指認」0 節；三種需人工指認情形以合成樣本自測（`--selftest`）皆標出、正常句不標。
  - **B6 客戶名掃描**：抽查單分大小寫命中 4、不分大小寫同 4，全部位於引文逐字字串（程式裡的特定合作團隊群組代號、範本代碼、團隊 id、旗標名）；四個字串在 HEAD 已 commit 的 drafts 中都已存在（`git grep -c`：9、44、1、5 處），抽查單未新增可對外理解的客戶資訊；計畫與驗收清單 0。
- **停點**：交業主本人逐句對源（步驟 4）。
- **業主加派的輔助分析**（2026-10-06，業主原文：「幫我派代理看這些符合細目標題嗎? 我不太清楚 ? 對應的問題是否檢索的到嗎?」；不取代規格 §2.2 的業主本人對源，也不判內容對錯）：
  - 盲判代理（只看細目標題、該細目全部內容句與抽中句，不看講法）判「抽中句是否符合細目標題」並替每句寫 2 個客人問法（口語 1、具體 1）。檔案實數：符合 24、部分 6、不符 0（代理自報 25／5，與它寫的檔不符，以檔為準）。部分 6 句皆為旁枝細節：#4 合約份數上限與預簽、#15 驗證成功畫面的客服提示、#19 無角色時的空狀態、#24 預設停在哪個分頁、#25 公證分頁的例外、#28 租客免註冊路徑。
  - 檢索：60 個問法以 `rag-orchestrator/tools/canon/ruler_eval.py`（線上同一套 `CandidateSelector.select`，K=5，身分 property_manager，正本 `8a5844bc…`）量：**hit@5 59／60**（名次 1：50、2：7、3：2、6：1），hit@10 60／60，粗目命中 60／60。唯一未進前 5 的是 #14 口語問法「虛擬帳號的歷程裡會列什麼資料？」排第 6（前 5 名皆同粗目「固定虛擬帳號管理」的其他細目，第 1 名是列表欄位那條）；同句的具體問法排第 1。
  - ⚠️ 限制：問法由看過句子與標題的代理寫，用詞容易與內文重疊（Plan 9.12「天花板效應」同一病灶），命中率偏樂觀，只作描述、⛔ 當檢索效果的驗收數字（效果驗收在規格 §2.4 用留出的真實客服題）。輸入與結果在 scratch `p931/side/`（問法為代理合成，非客服原話）。
- **業主改定抽查執行者**（2026-10-06）：業主問「我要怎麼做? 不是你該抽驗嗎」；主 session 說明規格 §5 第 5 點原定業主本人、§2.2 允許「業主或其指定人」、改動需業主明示。業主回覆（AskUserQuestion 逐字）：「指定獨立代理判，我只裁疑義句 (Recommended)」。⇒ 步驟 4 改為：一位 fresh 獨立代理（非主 session——主 session 做了抽樣、抽查單與小抄，不獨立）對 30 句逐句對源判「成立／不成立／無法判斷」，混 1 條誘餌（誘餌漏抓 ⇒ 作廢換人一次）；代理判不成立或無法判斷的句子，主 session 先找反證，再交業主裁定；業主裁定原文逐字記本節。規格 §5 第 5 點已加註改定。驗收清單 B3 依此改寫（業主核可的改動，原文同上）。
- **步驟 4 獨立判定**（fresh verifier，約 0.23M；brief 由 scratch `p931/judge/` 機械產生，31 句＝30 句＋誘餌 1，誘餌＝9.28 誘餌表第 12 項、位置種子 20261031 ⇒ 第 10 句）：結果存 `verification/20261006-p931-spotcheck-judgment.json`（自代理 transcript 機械取出最後一份 `kind: spotcheck`，31 筆順序與 manifest 相同）。**誘餌判「不成立」並引來源（`SelectContractMethod.jsx` 的 `description: '自製合約模板'`）⇒ 判定有效**。真 30 句：**成立 26、不成立 4、無法判斷 0**。
  - 不成立 4 句（抽查單編號）與主 session 反證檢查：
    - #2 `jgb/A/notification-settings-extra-emails` 句 4：「每個分類卡片都可各自新增／移除」漏權限例外。對碼確認：`src/pages/users/notification/Index.vue` 的 `hasPermissionToEdit: computed(()=>store.state.userData?.permission?.edit_notification || false)`，新增／移除前 `if (!state.hasPermissionToEdit){ return }`、新增鈕 `&& state.hasPermissionToEdit`。未找到反證。
    - #5 `jgb/D/contract-list-row-gear-actions` 句 2：「依狀態、身分、權限決定」屬排他列舉，程式另依社會住宅合約、租客是否註冊、可否續約、特定合作團隊簽核狀態增減或停用選項。反證檢查：句子未用「只」字，但列出三項當決定因素；社宅合約與特定合作團隊條件不屬三者之一。屬措辭層級的判斷，交業主裁。
    - #14 `jgb/E/recharge-account-history-content` 句 1：「列出每一筆金額變動紀錄」不成立。對碼確認：前端 `openHistoryLightbox` 呼叫 `/api/recharge-accounts/${record.id}/history` 不帶參數、無分頁；`RechargeAccountListController::history` 預設 `per_page` 50、`orderBy('id', 'desc')->paginate(...)` ⇒ 只顯示最近 50 筆。未找到反證。
    - #26 `jgb/D/contract-invite-and-review-period` 句 1：「給租客一段審閱期才能簽約」讀起來像必須等滿才能簽；程式裡這段期間是邀請失效期限（`contract_inviting_expire_at`），期限內可隨時簽，幫助中心也寫「需要在72小時內進行簽約，否則該連結就會失效」。反證檢查：在 `ContractController.php` 與 `resources/views/contract/sign.blade.php` 搜 `contract_inviting_at` 的出現處，只見顯示用的時間格式化與是否為空的判斷，未見「未滿審閱期不得簽」的時間比較（同檔正對照：`contract_inviting_expire_at` 寫入 2 處）；屬讀碼、未實機。後半句（天數讀團隊設定、未設定 3 天）成立。
  - 代理另記 findings 9 則（幫助中心過時、標題前提未寫、可讀成二選一等），不影響判定，保留在證據檔。
- **停點**：4 句交業主裁定。
- **業主裁定**（2026-10-06，AskUserQuestion 逐字，四題各一）：#2「不成立 (Recommended)」、#5「不成立 (Recommended)」、#14「不成立 (Recommended)」、#26「不成立 (Recommended)」。
- **結果（B4）**：**成立 26／30、不成立 4／30**（#2、#5、#14、#26）⇒ 規格 §2.2「須 30／30 成立」**未達成**；4 句轉下一份計畫依 D1 處置（修一次或整句刪 → 先審 → 業主終審 → 寫入 → 寫入核對），本計畫不改正本。抽查單判定欄已依代理判定與業主裁定填寫。

