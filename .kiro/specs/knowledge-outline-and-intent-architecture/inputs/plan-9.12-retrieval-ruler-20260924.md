# Plan 9.12：新架構檢索量尺（三層正本的凍結題集＋基線）— 2026-09-24 第 2 稿（第 1 稿凍結前審查 REVISE 6 條，全 FIX，見 §9）

> 業主 2026-09-24：量尺「準備新架構的題目，而不是原本的兩類」→ 規模／出題者／時機「照建議」。
> 起因：Plan 9.11 撤 A 後改評估 C；C 前置量測只有 24 題自寫題（`../HANDOFF-20260923.md` §9），不能當命中率、也不能拿來挑策略。
> ⛔ 本 Plan 不動 runtime／selector／正本內容；產物是凍結題集、量測工具輸出與基線報告。

## 0. 受測物與命題

- **受測物**：候選選取 `CandidateSelector.select`（K=5）在新三層正本（`rag-orchestrator/canon/jgb`，sha `9b67e763…`；索引建在全審暫存副本上，因現行正本全未審、可見子集為空）。
- **命題**：「問到某細目時，該細目進不進前 5 名候選；進不了時，粗目／架有沒有選對」。
- **證得了**：全體與分層（洩題等級／問法型／受眾／架）的細目 hit@5；失敗落在哪一層（架／粗目／細目）；答案集合＝gold ∪ 判者標出的 also_ok（同架＋跨架，**未窮盡**）；逐粗目結果只作描述（每粗目 n ≤ 6，附 n）。
- **證不了**：① 真實提問的頻率分布（另案以 S3 逐字稿校正）；② 回答品質（Verifier／模型行為）；③ none 層＝「審題者判定不借詞子集上的條件 recall」，⛔ 不是母體估計、⛔ 不當上限或下限（審題標籤未經信度驗證，且與命中機制相關、與問法型／架分布糾纏——報告附組成表）；④ 逐粗目排序或以逐粗目數字做決策（n 不足）。
  ⑤ also_ok 是判者標籤、未窮盡（收尾審查抽到同架漏標 2 例；跨架判者方法更寬鬆）⇒ 細目 hit@5（含 none 層）與層級歸因都以「判者標出的答案集合」為條件，判為失敗的題可能取到了未標的等價細目 ⇒ 數字**偏低、⛔ 不當精確值**；⛔ 凍結後不得依檢索結果補 also_ok（沿用 §5）。

## 1. 選題（決定性，⛔ 看結果不改）

- 母體＝新正本 57 粗目；每粗目依 `md5("ruler-9.12:" + fine_id)` 升冪取前 **3** 個細目（不足 3 取全部）。
- 每細目 **2** 題，問法型依 `md5("ruler-9.12-type:" + fine_id)` 決定性指派兩種不同型，型集合＝{直接, 口語, 情境, 俗稱}。
- 上限 57×3×2＝342 題。

## 2. 題目來源（優先真實材料）

1. **真實材料**：業主問法正本 `koyu-v2-phrasings.json` 中，所屬文章出現在該細目 `sources` 的 `help:<slug>` 者，排除（a）已逐字進講法的 7 句（b）既有凍結題；依 md5 取至多 2 句，型不強制對齊。
2. **補寫**：真實材料不足的名額，由出題代理補寫。出題代理**只看**：細目內文句、來源頁面路徑、指派的問法型與受眾；⛔ **不看**細目標題、講法、其他細目。
3. **題形規則**：一題一問、使用者口吻、⛔ 不含系統內部 id／程式路徑。

## 3. 過濾（門檻先定）

- 與**任一細目**的講法或標題 NFKC 逐字相同 ⇒ 剔除（不變量 34 同一把尺）。
- 與**該題 gold 細目**的標題／講法任一句，字元 bigram Jaccard **≥ 0.6** ⇒ 剔除並重寫一次；再犯 ⇒ 該名額記「缺」，⛔ 不放寬門檻。
- ⛔ 不用 embedding 相似度過濾（受測物本身就是 embedding 排序，會循環）。

## 4. 標準答案

- 主 gold＝出題對象細目。
- **多重答案檢查**：判者看「題目＋同一架全部細目（標題＋內文）」，標出其他也答得了的細目 ⇒ 列 `also_ok`；⛔ 判者看不到系統檢索輸出。
- **跨架補判（第 2 稿，業主「照建議」選 a）**：同一判者掃全部 515 細目標題挑候選、再看內文確認，`also_ok`＝同架 ∪ 跨架；於任何量測之前完成。
- 受眾：細目同時給售前與業者 ⇒ 第 0 題用 prospect、第 1 題用 property_manager；只給一方 ⇒ 兩題同一身分。每個指派身分須看得到 gold（全審副本下驗證，看不到 ⇒ 大聲失敗）。
  - ⚠️ 1.1 修正（量測前、只看過受眾分布）：原規則「property_manager 優先」使 340 題只有 4 題 prospect；正本 112/515 細目給售前，改後 43/340，與正本比例相當。

## 5. 業主抽查與凍結

- **前提**：業主以**最終題文**核可抽查（`md5("ruler-9.12-sample:"+slot)` 前 30），§8 記核可日期。
- **凍結檔** `inputs/ruler-9.12-questions.json`＝`{_meta, items}`：
  - `_meta`：來源 canon sha（`canon_src_doc_sha256`＝`9b67e763…`）、選題 seed 字串、題數、各輪產物說明、量測依賴（全審副本由 `tools/canon/ruler_eval.py` 自建、embedding 後端與維度、`vendor_id`、K）。
  - `items[]`：`id`（＝slot）、`q`、`fine_id`（gold）、`also_ok`、`coarse_id`、`shelf`、`type`、`audience`、`origin`、`leak`、`selected_fine`。
  - 凍結內容＝題目＋gold＋also_ok＋leak＋型＋受眾，全在同一檔、登記 sha256；⛔ 此檔永不修改。
- **登記**（跨 spec 寫入，本線擁有、回滾見 §7）：`.kiro/specs/agentic-mcp-orchestration/eval/samples-manifest.json` 加 set **`ruler-9.12`**（`available, path, sha256, how_to_verify, shape: "items[].q", count: 337, note`）；`scripts/audit/checks/canon_phrasing_frozen_disjoint.py::_extract_questions` 加 `ruler-9.12` 分支＋ self-test ⑥ 正對照（撞講法 ⇒ FAIL、不撞 ⇒ PASS）。
- **重映**：正本重生成改到細目 id ⇒ 另寫只能追加的 `inputs/ruler-9.12-remap-<to_sha8>.json`（`{from_canon_sha, to_canon_sha, map}`），量測時 `ruler_eval.py --remap` 套用；⛔ 不改凍結檔，已登記 sha 永遠不變。

## 6. 量測（不呼叫生成式 LLM；⚠️ 題目文字經 `embedding-api` 送 OpenAI `text-embedding-3-small`——第 1 稿寫「本機」是錯的，2026-09-24 資安審查指出後更正；本題集為合成題、不含個資）

- 工具：`rag-orchestrator/tools/canon/ruler_eval.py`（業主「照建議」升格為耐久工具、進版控；單元測試 `tests/unit/agent/test_ruler_eval_req.py`；`--self-test` 以合成題試跑）。
- 指標：答案集合＝gold ∪ 可見 also_ok；細目 hit@5、名次、hit@10（參考）；粗目命中＝前 5 名粗目 ∩ 答案集合粗目 ≠ ∅；架命中同理；層級斷言 hit ⇒ 粗目 ⇒ 架（違反即非 0 退出）；並斷言量測排序前 5＝`select()`。
- 報告：全體、依 leak／type／audience／shelf／origin，逐粗目（附 n、只作描述），leak×type 與 leak×shelf 組成表。
- 產物：`inputs/ruler-9.12-baseline-<日期>.json`（meta＋report＋逐題 rows，含 questions sha、全審副本 doc sha、embedding 維度、vbt）。
- 第一次＝基線，⛔ 不設門檻。

## 7. 執行分工與停止條件

- 主 session：選題／過濾／合併腳本（scratchpad，一次性工具 ⛔ 不 commit；凍結檔 `_meta` 記其 sha）；量測工具 `ruler_eval.py` 進版控。
- 回滾：撤 manifest 的 `ruler-9.12` 項＋撤 `_extract_questions` 分支與 self-test ⑥＋刪凍結檔；三者同進同退（`ruler_eval.py` 與其測試可獨立留下）。
- 出題代理、多重答案判者：各 1 個，brief 帶 Hard rules；判者與出題者不同代理。
- 停止：選題母體與 57 粗目數不符 ⇒ 停；缺題 >10% ⇒ 停、交業主；gold 可見性驗證失敗 ⇒ 停；業主抽查不核可 ⇒ 依指出者重寫／重判／重評後再抽查；量測工具非 0 退出 ⇒ 停、不出基線、查因。

## 8. 執行紀錄（量測前）

- 選題：57 粗目、170 細目、340 題（koyu 真實句 10、補寫 330；prospect 43／pm 297）。
- 過濾：逐字 1、bigram 0.60 1 ⇒ 各重寫一次後全過（340/340）。
- 判者：`gold_ok=false` 11 題（3.2%）、`also_ok` 非空 27 題。**補定規則（量測前、未看檢索輸出）**：`gold_ok=false` ⇒ 出題者依判者理由重寫一次（仍看不到標題／講法）、同一判者重判；再 false ⇒ 該名額記「缺」。
- **真實句另定規則（量測前、未看檢索輸出）**：10 句 koyu 真實句中 7 句 `gold_ok=false`——`help:` 文章→細目的對映只到文章層，不保證該細目答得了。真實句 ⛔ 不改寫（改了就不是真實句），改為：
  - 判者找到答得了的細目 ⇒ gold 改為那些細目（`also_ok`∪原 gold 若 ok）；
  - 同一真實句出現在兩個名額 ⇒ 留第一個、其餘名額改補寫；
  - 無任何細目答得了（「我登入不進去」）⇒ 移出量尺、記入知識缺口候選，名額改補寫。
  - 結果：真實句留 5 句（gold 改 3 句）、補寫新增 5 名額；改 gold 後的真實句同樣過 §3 過濾（對新 gold）。
- 重寫 3＋新補 5 ⇒ 重判全 `gold_ok=true`。合併＋對最終 gold 重跑 §3：**339 題**（補寫 335、真實 4；57 粗目全覆蓋）；缺 1＝真實句「忘記密碼在哪裡點」改 gold 為 `jgb/A/login-forget-password-link` 後 bigram 0.71（該細目講法已幾乎逐字覆蓋此問法）⇒ 依規則移出。
- 知識缺口候選：真實句「我登入不進去」同架無任何細目答得了（判者）；`jgb/E/bill-sheet-download-button` 只寫「有下載按鈕」、他細目揭露按鈕無效 ⇒ 照它答會錯（併 81 題類待裁）。
- 業主抽查 30 題：`md5("ruler-9.12-sample:"+slot)` 前 30，清單 scratchpad `ruler/owner_sample_slots.json`。
- **獨立審題（業主「派代理看你產的題目」）**：keep 314／revise 24／drop 1；洩題 strong 10／mild 173／none 156；prospect 題問題率 25.6%（多為操作者情境）；審題判整體**偏高**（出題者看得到內文 ⇒ 用詞貼近）。另抓到 §3 過濾漏洞：標題為「問句（答案）」，與**整個標題**比 bigram 會被括號稀釋（「點交邀請送出後可以取消嗎？」與標題問句逐字相同卻放行）。
- **業主 2026-09-24「照建議」三項（量測前定死）**：
  1. §3 過濾加比「標題問句部分」（`（`／`(` 之前）：逐字相同或 bigram ≥ 0.6 ⇒ 剔除重寫；多抓 6 題（5 題即審題 strong）。
  2. revise／drop 與新過濾抓到者 ⇒ 出題者依審題理由重寫一次（看得到自己的舊題與理由、仍看不到標題／講法）⇒ 判者重判 ⇒ 審題者重評洩題等級；真實句不改寫、過濾不過即移出（「房東對外首頁是什麼」）。共重寫 25 題。
  3. §6 基線**依審題洩題等級分層報告**：none／mild／strong 各自 r@5；**none 層為主數字**，全體只當「用詞友善情境下的上限」；真實分布另以 S3 校正。
- 重寫 25 ⇒ 判者 24 題 ok（`bill-sheet-download-button#0` 仍答不了 ⇒ 缺，同知識缺口）；審題者 keep 24／revise 1（同一題），洩題 none 21／mild 4／strong 0。
- **凍結候選：337 題**（補寫 334、真實 3；57 粗目全覆蓋；prospect 42／pm 295；洩題 none 172／mild 165／strong 0）；缺 3（真實句 2 題過濾不過、1 題答不了）＝0.9%。

## 9. 第 1 稿凍結前審查（plan-verifier REVISE，6 條 P2）處置——全 FIX

| # | 審查 | 處置 |
|---|---|---|
| 1 | 新 set 名稱會讓 `_extract_questions` raise ⇒ 不變量 34 登記即紅；三處寫入的擁有權／回滾未寫；30 題抽查不是最終題文 | §5 定 set 名 `ruler-9.12`、檔形 `{_meta, items}`、manifest 欄位；`_extract_questions` 已加分支＋ self-test ⑥（11/11 ✅）；§7 回滾；§5 前提＝業主以最終題文核可 |
| 2 | 重映 gold 與凍結 sha 衝突 | 凍結檔永不改；重映走只能追加的 `ruler-9.12-remap-<sha8>.json`，量測時套用 |
| 3 | 量測腳本缺 leak／粗目報告；粗目／架命中只看主 gold | `tools/canon/ruler_eval.py`：答案集合三層一致、層級斷言、leak／粗目／組成表；單元測試 7/7、`--self-test` 合成題 ✅ |
| 4 | also_ok 只判同架 | 業主選 a：跨架補判（§4），量測前完成 |
| 5 | none 層主張過度 | §0「證不了」③④；報告附組成表、逐粗目附 n 只作描述 |
| 6 | 基線不可重跑 | 量測工具進版控、自建全審副本；凍結檔 `_meta` 與基線產物記所有依賴與 sha |
- **跨架補判結果（量測前）**：新增跨架 also_ok 7 題（A 2、B 4、I 1；含審查舉的 `jgb/I/payment-bill-e-invoice-setup#1` ⇒ `jgb/D/contract-tax-invoice`）；also_ok 非空 19→24 題；無移除。⚠️ **方法偏離**：判者未逐題讀 515 標題，改用內文 4-gram 相似度掃全部細目挑候選（≥5 分全數人工核內文，3–4 分只抽查可疑主題群）⇒ **字面不同、語意等價的跨架細目可能漏判**；收尾審查另抽到同架漏標 2 例（`jgb/I/pricing-free-trial-feature-scope#0`、`jgb/E/balance-invoice-community-switch#0`）⇒ 限制範圍＝**全體 also_ok／細目命中與層級歸因**（見 §0 證不了 ⑤）。
- 知識矛盾（判者發現、未入 also_ok）：`jgb/E/payment-gateway-options`「個人房東目前可以選擇的是中國信託跟藍新」vs `jgb/I/payment-vendor-eligibility-by-role-and-plan`「個人房東不能開通藍新」⇒ 待業主裁（併 81 題類）。
- 凍結候選檔：scratchpad `ruler/ruler-9.12-questions.candidate.json`（337 題；`_meta` 含 seeds、腳本 sha、缺題紀錄）。

## 10. 收尾審查（plan-verifier，第 2 稿）REVISE 1 條 P2 ⇒ 依審查迴圈上限不再開審查，交業主

- P2（措辭／主張一致）：§0 答案集合被寫成完整、但 also_ok 未窮盡 ⇒ **FIX（縮小主張）**：§0 證得了改措辭、證不了加 ⑤、§8 限制範圍擴為全體；凍結檔 `_meta.also_ok_note` 與基線報告 meta 同句。
- P3 已順手修（工具）：一致性比對改引用 `candidate_selector.K`、`--k` 與 5 解耦；also_ok 的 id 在正本不存在 ⇒ 大聲失敗（看不到仍照舊排除）；受測正本 sha ⇒ 須等於凍結 `_meta.canon_src_doc_sha256`（或重映 `from_canon_sha`→`to_canon_sha`）否則大聲失敗；`_meta` sha 改完整 64 碼。
- P3 寫入：§7 停止條件加「業主抽查不核可 ⇒ 依業主指出者重寫、重判、重評後再抽查」「量測工具非 0 退出 ⇒ 停、不出基線、查因」；回滾清單註明 `ruler_eval.py`／測試可獨立留下。
- **彙整驗收**：① 現樹 `python3 scripts/audit/checks/canon_phrasing_frozen_disjoint.py` ✅ 且 counts 含 `ruler-9.12`: 337；② manifest sha256＝凍結檔 sha256；③ 基線 rows＝337、meta.questions_sha256＝凍結檔、meta.canon_src_doc_sha256＝凍結 `_meta`。

## 11. 凍結與基線（2026-09-24，業主「核可」）

- 凍結：`inputs/ruler-9.12-questions.json`（sha256 `95e75a11…`，337 題）；`samples-manifest.json` 加 `ruler-9.12`；不變量 34 讀到 337 題，交集仍只有既有的「合約範本有哪幾種」（無新增）；self-test 11/11；相關單元 98 passed。
- 工具修正（量測前、非依結果）：查詢 embedding 偶發 3 秒逾時 ⇒ `ruler_eval._retry` 重試 4 次（向量決定性，不影響結果）。
- **基線** `inputs/ruler-9.12-baseline-20260924.json`：hit@5 **0.979**（330/337）、hit@10 0.991、粗目 0.988、架 0.994；none 層 0.977（n=172）、mild 0.982（n=165）；俗稱 0.959、口語 0.967、情境 1.000、直接 0.989；prospect 0.976、pm 0.980。
- **診斷（不改量尺，只解讀）**：
  1. **講法目前完全不進索引**：`fine_index.INDEXED_PHRASING_STATUS = "approved"`，新正本 1,670 條講法全為 `status: proposed` ⇒ 索引＝標題＋內文句。gold 的獲勝鍵：title 168、content 169、phrasing 0。
  2. **量尺有天花板效應、偏高的主因不是標題而是內文**：出題者看不到標題但看得到內文，而內文句本身就是索引鍵；審題者的洩題等級只比標題 ⇒ none 層 172 題中 105 題由 content 鍵命中，**none 層並未排除這條洩漏**。對照 S6 我自寫的 24 題（非由內文改寫）hit@5 僅 19/24。
  3. 讀法：ruler-9.12 適合當**回歸守門**（改動把命中打壞時會掉），**不適合分辨 C 的改善策略**（330/337 已中，剩 7 題）。
