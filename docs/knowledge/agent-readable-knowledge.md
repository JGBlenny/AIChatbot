# Agent 可讀知識形態指南

> 給誰看：撰寫／編輯 `knowledge_base` 售前池內容的人（含審核 `outline_approved_by` 的人）。
> 目的：售前池會被 `OutlineAssembler` 程式化組裝成大綱塞進 system prompt，也會被
> `kb.get` 整數 id 按需取回；不論哪條路徑，`OutputVerifier` 都要求模型的每句斷言
> 逐字回指到某一筆知識的原文。這份指南把「怎麼寫，Verifier 才放行、大綱才組得對」
> 講給知識編輯者聽，⛔ 不是寫給工程師看的程式文件（程式文件是下面各條的「依據」）。
> 每條規則後面的「依據」都可重跑查證：檔案路徑＋可 grep 的符號，或 `.claude/DECISIONS.md`
> 的決策編號；⛔ 不寫行號（行號會隨 commit 漂移）。

---

## 一、主題頁 vs 講法列

售前池的知識列分兩種角色，⛔ 不是同一件事的兩種寫法：

- **主題頁列**：`outline_approved_by` 是 `reviewed:<who>` 的列。
  ⚠️ **2026-09-07（任務 3.2）起這個旗標不再決定大綱**：售前大綱改由 git 正本
  （`rag-orchestrator/canon/prospect.md`）逐細目組裝，DB 售前池是正本匯入後的
  衍生物，⛔ 大綱不以衍生物為來源。這個旗標現在決定的是**另一件事**：模型用
  `kb.get(<整數 id>)` 取單列時取不取得到（未審一律 `NO_MATCH`）。
  「一筆知識要不要進大綱」現在的答案是「去正本裡開一個細目」，⛔ 不是在 DB 標旗標。
  依據：`rag-orchestrator/services/agent/canon/canon_assembler.py:load_canon_or_die`／
  `build_outline`（大綱來源）；`rag-orchestrator/services/agent/canon/review_state.py:content_reviewed_predicate`
  ＋`rag-orchestrator/services/agent/tools/kb.py:fetch_visible_row`（旗標現在管什麼）；
  DSP-012（審核旗標定案）。

- **講法列**：同一件事只是換一種問法／措辭的知識列，**不進大綱**、只留在池裡
  供 `kb.search`／`kb.get` 按需檢索命中。「一種講法一筆」是既有知識工程慣例
  （錨點供召回），但這批講法列若也被標成 `outline_approved_by`，會在大綱裡
  製造重複章節——2026-09-05 的實例是 3584/5377、3610/5376 兩對逐字相同的答案，
  被取消大綱標記（只取消講法列，主題頁列保留），知識本身沒有被刪除、只是
  不再進大綱組裝。**判準是「答案內容是否逐字或近乎逐字重複」，不是「講法多
  一種就算重複」**——同一批盤查裡 5378/5379/5380 各有獨有內容（催繳／匯入／
  帳單格式），即使主題相近也全部保留為主題頁列。
  依據：DSP-026（大綱重複列取消，範圍收窄為 2 列的裁決過程）；
  `.kiro/specs/agentic-mcp-orchestration/eval/outline-review-20260905.md`。

**寫給編輯者的規則**：新增一筆售前知識時，先問「這是要進大綱的主題事實，
還是幫助檢索命中的另一種問法」。前者才申請 `outline_approved_by` 審核；
後者留白，⛔ 不要因為「反正審核也不會擋」就把每一種講法都標成進大綱。

---

## 二、每筆自成一段可逐字引用的事實

Verifier 的引用比對是「一句答案 + 一段引文（quote）」對「某個 `tool_call_id`
的 `Provenance.text`」做逐字子字串比對（NFKC 正規化後）。這意味着**知識列本身
的文字就是模型唯一能合法引用的原文**——寫法直接決定模型能不能答對。

- `question_summary`：用短主題關鍵字（既有知識工程慣例，非本任務新規）——
  它是**檢索命中**用的鍵（`kb.search`／舊鏈向量檢索），寫成完整問句會稀釋主題詞。
  ⚠️ 它**不再**是大綱的分段依據（3.2 退役了關鍵字分類表）：大綱的分段由正本的
  粗目／細目決定，命中則靠細目標題與 `phrasings`（講法）。
  依據：`rag-orchestrator/services/agent/canon/canon_assembler.py:build_outline`
  （一細目一節，`id=fine.id`、`title=fine.title`）；正本格式見
  `rag-orchestrator/services/agent/canon/canon_parser.py:FINE_HEADING_RE`。

- `answer`：先述情境再帶條件，不模板化（既有知識工程慣例）；在 agent 場景下
  多一層理由——Verifier 的覆蓋檢查（下節）要求「答案句」與「引文」有足夠的
  非停用詞字元交集，情境化的完整句子比乾巴巴的條列更容易讓模型引用的句子
  與原文重疊夠多。
  依據：`rag-orchestrator/services/agent/verifier.py:_meaningful_chars`／
  `min_coverage_chars`（`config/agent_verifier_rules.json`）。

- **⛔ 「見上一筆」、⛔ 跨列指涉**：Verifier 逐字比對的範圍是**同一個
  `tool_call_id`** 內的 `Provenance` 集合（一筆 `kb.get` 或一個大綱 section），
  不會跨到別的 `tool_call_id` 找補；一筆答案裡寫「詳見上一題」，模型若照抄
  這句話，Verifier 會因為「上一題」三個字在任何工具回傳裡都逐字找不到而判
  `QUOTE_NOT_VERBATIM`——這不是機制沒補齊，是設計上就不追加載入鏈。每筆知識
  必須自身包含完整可引用的事實。
  依據：`rag-orchestrator/services/agent/verifier.py:_verify_citation`
  （`tool_result = tool_results.get(citation.tool_call_id)`，只在該工具結果的
  `provenances` 內找 `matched`）。

---

## 三、邊界句必明寫

「不支援 X」「無法 Y」這類邊界／限制句，用詞必須落在 Verifier 的
`negation_terms` 表內，否則極性檢查（下節）對不上——句子裡有沒有否定詞，是
拿這張**固定詞表**去比對命中，不是理解語意。

**當前實際詞表**（⛔ 不得憑印象替換為近義詞）：
「不支援」「不可以」「不能」「無法」「不會」「沒有」「未支援」「不提供」
「不支持」「不行」。

例如「合約 ⛔ 不支援批次匯入」用「不支援」是對的；若寫成「合約沒辦法批次
匯入」，「沒辦法」不在表內——若模型的答案句用了「不支援」而引用的知識原文
用「沒辦法」，兩邊的否定詞命中會不一致（一邊有命中、一邊沒有），Verifier
判定極性不一致而拒答。

⚠️ **2026-09-07（3.2）起大綱不再另抽一段「邊界句」**：舊版 `OutlineAssembler`
用一組獨立的窄詞表（「不支援」「無法」「不提供」）把句子抽進 `outline:boundary`
章節，那個機制與那張詞表都已退役。邊界事實現在寫在正本的細目裡（粗目 G
「限制與邊界」承接這個角色），⛔ 不再由程式從答案裡撈句子。
⇒ 現在只剩**一張**表要對齊：Verifier 的 `negation_terms`。

依據：`rag-orchestrator/config/agent_verifier_rules.json`
（`"negation_terms"` 陣列，10 詞）；
`rag-orchestrator/services/agent/verifier.py:_verify_citation`
（`sent_hits`/`quote_hits` 用 `self.rules.negation_terms` 命中判斷，
`bool(sent_hits) != bool(quote_hits)` ⇒ `POLARITY_MISMATCH`）。
（DSP-021 補的「不支持」「不行」屬 Verifier 否定詞表；舊的
`outline.py:_BOUNDARY_TERMS` 已於 3.2 退役，⛔ 不要再去對照它。）

---

## 四、內容矛盾要裁，⛔ 不自行選邊

兩份權威文件對同一件事寫法不同時（例：內政部合約範本是「五種」還是
「通用範本共 12 種＋三種特殊用途」），知識編輯者 ⛔ 不得憑感覺挑一個寫進
`answer`，也不能兩邊都寫進同一筆造成自相矛盾。DSP-010 的實際處理方式：

1. 先查兩份文件各自的更新時間／版本，較新的文件優先採用（3600 主題頁採用
   `qa06_zh-Hant.html`，因其編輯日期較新）。
2. 在該筆知識或批次匯入的 `_meta.disputes` 裡明寫兩份文件的逐字差異與採用
   理由，讓爭議留痕、可回溯，⛔ 不得悄悄改掉就當沒發生過。
3. 標記為「⚠️爭議（未裁）」交業主定案，⛔ 未裁前不得回頭改成另一份文件的
   說法。

依據：DSP-010（`.claude/DECISIONS.md`）；
`scripts/knowledge-batches/presales-topic-contract-3600-20260904.json`
（`_meta.disputes` 欄位）。

---

## 五、`categories` 是檢索用的主題分類（⛔ 不再決定大綱分段）

⚠️ **2026-09-07（任務 3.2）改判**：舊版大綱把 `售前模組` 底下的列再依
`question_summary`＋`categories` 的關鍵字比對細分成六大模組（房源／租約／帳務／
團隊／IoT／修繕），另四個 `categories` 值（`售前顧問`／`售前方案`／`售前價格`／
`售前競品`）各自成一節，命不中則落兜底桶。**那張分類表、那個兜底桶、以及
「`categories` 沒填會影響大綱」這件事，全部退役。**

現在的分段來源是**正本自己的層級**：粗目（`## 標題 {#A}`）與細目
（`### 標題 {#prospect/A/slug}`），一細目一節、節 id 就是細目 id。要調整大綱
怎麼分段，改的是正本的粗目／細目，⛔ 不是改 DB 的 `categories`。

`categories` 仍然有用，但只在**檢索**那一側（`kb.search`／舊鏈的主題分類），
以及匯入時對回正本細目。寫知識時照既有慣例填即可：
`categories` 是主題分類，`business_types`／`target_user` 是業態與角色，
⛔ 三者不可互相取代。

依據：`rag-orchestrator/services/agent/canon/canon_assembler.py:build_outline`
（一細目一節）；`rag-orchestrator/services/agent/canon/canon_parser.py:COARSE_HEADING_RE`／
`FINE_HEADING_RE`（粗目／細目的層級定義）；正本本體
`rag-orchestrator/canon/prospect.md`。

## 六、Verifier 逐字引用對句子完整度的要求

寫給知識編輯者的白話版——模型能不能「答對又能被 Verifier 放行」，取決於
你寫的知識原文能不能撐住下面四個檢查：

1. **句尾符號才切句**：系統把答案切成句子的依據是句尾符號
   `。！!？?` 加換行，不是逗號或語意斷點。這代表你的知識 `answer` 裡如果
   該斷句的地方沒有用句號斷開（例如一路用頓號、逗號串到底不加句號），
   模型引用時抓出來的「一句」會過長或過短，容易讓引文與句子對不齊。
   依據：`rag-orchestrator/services/agent/verifier.py:_split_sentences`
   （逐字掃描，命中 `_SENTENCE_ENDS` 才切）。

2. **引文至少 6 個字**：模型引用的那段原文（`quote`）NFKC 正規化後長度要
   ≥ 6 字，太短（例如只引「租金」兩字）會被直接判 `QUOTE_TOO_SHORT`。這代表
   知識原文裡承載關鍵事實的片語不能寫得太碎，至少要能湊出一段 6 字以上、
   語意完整的子句供引用。
   依據：`rag-orchestrator/config/agent_verifier_rules.json`
   （`"min_quote_len": 6`）；
   `rag-orchestrator/services/agent/verifier.py:_verify_citation`
   （`len(quote_nfkc) < self.rules.min_quote_len`）。

3. **引文必須是原文逐字子字串（NFKC 正規化後）**：模型不能改寫、摘要、
   合併你的原文再引用——引文字面要能在知識原文裡逐字找到（全形/半形、
   大小寫等 NFKC 差異會被抵銷，但用詞本身不能換）。這代表**你怎麼寫，模型
   就只能怎麼引**——用詞含糊或有錯字，模型答錯或引錯字的機率都會提高。
   依據：`rag-orchestrator/services/agent/verifier.py:_verify_citation`
   （`quote_nfkc in _nfkc(prov.text)`）。

4. **覆蓋字元 ≥ 規則值（目前 4 字）**：答案句子與引文之間，扣掉常見虛詞
   （的、了、是、在……等停用字）後的字元交集要 ≥ 4 個。這代表**引文不能只
   是句子裡無關痛癢的一小段**——引文必須真正承載這句話的實質內容，不能
   斷章取義引一段跟句子主旨不相干的原文來湊數。
   依據：`rag-orchestrator/config/agent_verifier_rules.json`
   （`"min_coverage_chars": 4`）；
   `rag-orchestrator/services/agent/verifier.py:_meaningful_chars`
   （停用字元集合）／`_verify_citation`（`overlap = _meaningful_chars(...) &
   _meaningful_chars(...)`）。

5. **否定詞一致（極性）**：見第三節，答案句子與引文「有沒有踩到
   `negation_terms` 表裡的詞」必須一致——都有否定詞，或都沒有，不能一邊
   肯定一邊否定。
   依據：`rag-orchestrator/services/agent/verifier.py:_verify_citation`
   （`POLARITY_MISMATCH` 分支）。

**好例子**：知識原文寫「合約目前不支援批次匯入，需要逐筆建立」——模型答
「合約不支援批次匯入」，引用「不支援批次匯入」（8 字，逐字存在於原文，
覆蓋字元「不支援批次匯入」與答案句幾乎全部重疊，兩邊都有「不支援」故極性
一致）⇒ 放行。

**壞例子**：知識原文寫「舊系統已繳完的歷史帳單也沒有搬移功能」，模型答
「歷史帳單不支援搬移」卻引用「舊系統」兩字（少於 6 字且與句子主旨「不支援
搬移」無關）⇒ `QUOTE_TOO_SHORT`／`QUOTE_NOT_COVERING`。若模型改引「沒有
搬移功能」（6 字、逐字存在、覆蓋高、兩邊都有否定詞「沒有」對「不支援」——
注意這裡兩邊字面不同但都在 `negation_terms` 表內，極性判斷看的是「有沒有
命中表內任一詞」不是「是不是同一個詞」）⇒ 放行。

---

## 七、寫完一筆知識的自檢清單

- [ ] 這筆要不要讓模型用 `kb.get(<id>)` 取得到？要的話 `outline_approved_by`
      得是 `reviewed:<who>`。⚠️ 這個旗標**不再**決定進不進大綱——進大綱是
      「正本裡有沒有這個細目」的事。
- [ ] `question_summary` 是短主題關鍵字，不是完整問句（它是檢索命中的鍵，
      ⛔ 已不再決定大綱分段）。
- [ ] `answer` 先述情境再帶條件，不是模板化條列；沒有「詳見上一筆」
      「同上」這類跨列指涉。
- [ ] 邊界／限制句用了 `negation_terms` 表內的詞（見第三節詞表），不是
      「沒辦法」這類表外近義詞。
- [ ] 承載關鍵事實的子句長度 ≥ 6 字且語意完整，不是被拆得過碎的短語。
- [ ] 與其他既有知識內容矛盾時，已依第四節流程留痕＋標爭議，⛔ 沒有自行
      選邊改寫。
- [ ] `categories` 已填值（不留 NULL）——它現在服務檢索與匯入對帳，
      ⛔ 不再決定這筆會落到大綱的哪一節（那由正本的粗目／細目決定）。
- [ ] 若這件事要進大綱，去 `rag-orchestrator/canon/prospect.md` 開／改細目，
      並照 `rag-orchestrator/canon/README.md` 重導出同源的 `.json`
      （⚠️ 只改 `.md` 沒重導出 ⇒ 啟動時 `load_canon_or_die` 直接紅）。

---

## 依據總覽（供 grep 核對本文件未編造）

本文件所有規則的依據皆已在各節內文標注「依據：」，可逐條用檔案路徑＋符號
或 `.claude/DECISIONS.md` 決策編號重跑查證。查無依據的項目本文件一律標注
「查無」，不補值——目前無此類項目。
