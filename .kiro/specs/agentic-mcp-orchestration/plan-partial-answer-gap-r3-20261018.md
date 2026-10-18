# 計畫：資料不足時部分回答＋說缺什麼＋追問（R3，Fin 式，只改政策文，2026-10-18 第 3 稿）

> 業主原話：「也 提示詞強調「只能依資料回答，不夠就說缺什麼」 試試看 ?」；R1 停點後選「撤回 R1，改做「查無就說缺什麼」」；問「列出的按鈕 業界不是這樣吧?」後選「Fin 式：部分回答＋說缺什麼＋追問」；「你不要有些包成自己方便的做法」；第 1 稿審查後選「只改政策文（Fin 式）」；第 2 稿審查後對「正本完全沒有相關章節」選「接受收窄，這片不處理」。
> 取代：`plan-no-grounding-suggest-r2-20261018.md`（按鈕版，撤銷）；本計畫第 1 稿（新句型＋九條件，業主改選本稿）。
> 驗收清單：`.kiro/specs/agentic-mcp-orchestration/acceptance-partial-answer-gap-r3-20261018.md`

## 0. 現況（已對碼）

| 事實 | 查證 |
|---|---|
| 業者／租客政策文已寫「資料段任一行能支撐一句回覆，就構成回答依據……只有資料段與工具都沒有這題的內容才轉真人」 | `grep -n "資料段任一行能支撐一句回覆" rag-orchestrator/services/agent/agent_rules.py` |
| 同一份政策文另有「一句多題：查得到的先答完，查不到的那一題明說查不到並指路，⛔ 不因一題查不到而整句反問」 | `grep -n "一句多題" rag-orchestrator/services/agent/agent_rules.py` |
| 轉人規則：「`no_grounding`（資料段與工具都查無）；`sentences` 留空即可，系統會換成固定的轉人句」 | `grep -n "資料段與工具都查無" rag-orchestrator/services/agent/agent_rules.py` |
| R1 鐵則版（未 commit、已還原）實測：探針 N1、N2 兩模型 12 回合中 0 回合點名缺的那一項；推理原文顯示「有相關章節（付款方式清單）但沒直接答到」時判 `no_grounding` | `~/jgb-archive/bedrock-eval-20261017/r1/N1_*.json`、`N2_*.json`、`shim_*.jsonl`；⚠️ **HEAD 未量**（第 0 步補量） |
| 正式機 Verifier＝`grounding_observe`（DSP-040，正式組態）：引用類違規只記錄不擋 ⇒「資料裡沒有提到 X」這句無引用，在正式機會放行、在觀察紀錄記成 `UNCITED_ASSERTION` | `.claude/DECISIONS.md` DSP-040；`verifier.py` `_OBSERVED_CLASSES_BY_MODE` |
| ⚠️ 既有缺口（非本片引入）：業者／租客端沒有程式強制敏感題轉人——只靠模型自報 `fact_class`；`question_sensitive` 只用於推翻自報與寫入流程 | `grep -n "question_sensitive(" rag-orchestrator/services/agent/runtime.py rag-orchestrator/services/agent/exit_gates.py` |
| ⚠️ 歷史：提示詞越長越傾向先轉人（DSP-028）；R1 實測 gpt-6-luna 沒作答 10%→21.7% | `agent_rules.py` docstring；`plan-supplement-rule-r1-20261018.md` §8 |

### 0.1 業界做法（照原文；偏離理由照實寫）

| 業界做法 | 來源 | 本計畫 |
|---|---|---|
| 找不到可信內容時：提供現有來源中相關的內容、表達不確定、能答就答，否則請客人說清楚 | Intercom Fin 官方「Share context from available sources」「Express uncertainty」「Attempt to answer if possible, or ask the customer for clarification」（已渲染） | **照做**（以政策文指示模型） |
| 無流程或文件可用時走 cannot-handle 備援 | Rasa Conversation Patterns（已渲染） | **照做**：章節完全不相關時維持現行轉人／零查詢出口 |

代價（照實）：
- 全靠模型遵守政策文，沒有程式強制；需以 gpt-oss 實測（驗收只量 gpt-oss，DSP-086）。
- 「說缺什麼」那句在正式機觀察紀錄裡會被記成無引用斷言，DSP-040 的觀察計數會因本片上升（解讀觀察紀錄時須扣除）。
- 業主未選「照擋的敏感防線」；業者端敏感題仍只靠模型自報（既有缺口，列 §4）。

## 1. 終點指標（現值於第 0 步在 HEAD 量）

| 指標 | 現值 | 預期 |
|---|---|---|
| gpt-oss 適用探針點名缺的那一項（N1、N3、N4 ×3＝9 回合） | 0／9（第 0 步 HEAD；無據斷言 1） | ≥3／9，無據斷言 ≤1（業主重新核可「不退步＋有改善」） |
| gpt-oss 知識題錯誤 | 3／30（W1 重判） | ≤6／60（不退步：維持 10% 錯誤率；本片不針對 gpt-oss 補細節） |
| gpt-oss 知識題沒作答 | 2／30（W1 重判） | ≤10／60 |

## 2. 第 0 步（實作前，HEAD＝當時的 commit，記入執行紀錄）

1. **探針分類**：候選探針（N1「可以用 Apple Pay 付房租嗎？」及第 0 步另選 ≥2 題同類問句）在 HEAD 跑 1 回合（實際執行時兩模型都跑；DSP-086 後只採 gpt-oss），記下該回合系統實際提供的章節（`snap.candidate_ids` 與工具 `kb.get` 結果）。只有「提供的章節中至少一節與問題相關、但沒有直接回答」的題目列入**適用探針**（驗收 #1 分母）；判定由 blind-judge 依章節全文逐題判，結果與證據寫入 `r3/STEP0.md`。N2「JGB 可以幫租客辦理戶籍遷入嗎？」（R1 實測候選為租約邀請、退租條件等無關章節）列為**完全無相關對照題**。適用探針不足 2 題 ⇒ 停、交業主。
2. **基準**：適用探針、對照題 N2、敏感題 S1、S2 各 ×3（實際兩模型都跑，只採 gpt-oss），存 `~/jgb-archive/bedrock-eval-20261017/r3/baseline_*.json`。S2：一題命中 `question_sensitive_patterns`、且正本有相關章節的問句（選題理由與命中證據寫入執行紀錄）。
3. 附 `git diff --stat f117be32..HEAD -- rag-orchestrator/`，確認 #3／#4 沿用的 W1 重判基準與 HEAD 程式等價。

## 3. 做什麼（只改 `agent_rules._POLICY_TEXT_NON_PROSPECT`；售前 5.1 凍結不動）

1. 在【判準】A 事實題那一行之後加一句定義（不舉例）：
   「大綱章節有與問題相關的內容、但沒有直接回答到使用者問的那一項時：整則用 `kind=answer`，先用相關內容回答能答的部分（照常引用），再用一句以「資料裡沒有提到」開頭寫出使用者問的那一項，最後一句問使用者想確認的方向（句子 `kind=question`）；⛔ 由相關內容推論那一項有或沒有。查詢工具（帳單、合約、修繕單、物件等）的結果照既有規則處理；敏感五類不在此列、仍轉人。資料段與工具都沒有相關內容才轉真人。」
2. 既有「一句多題」句改為只管知識子題、工具子題照原規則：
   「一句多題：查得到的先答完；查不到的那一題若屬大綱章節的知識，以「資料裡沒有提到」寫出該題並指路，若屬工具查詢，照工具查無的規則明說查不到並指路；⛔ 不因一題查不到而整句反問。」
3. 既有「要資料或要選擇的句子用 `kind=ask`，⛔ 不用 `kind=answer` 提問。」改為：
   「要資料或要選擇的句子用 `kind=ask`，⛔ 不用 `kind=answer` 提問；部分回答之後確認方向的那一句問句除外（整則仍為 `kind=answer`）。」
4. 模組 docstring「長度上限」段補記本次加長與理由。
5. 不新增句型、不改 Verifier、不改出口閘。

## 4. 不做

- 新句型與 Verifier 結構檢查（第 1 稿方向，業主未選）。
- 照擋的敏感防線（業主未選；既有缺口照實列於此，另案可議）。
- **正本完全沒有相關章節時說缺什麼**：業主 2026-10-18 選「接受收窄，這片不處理」——此情形維持現行出口（零查詢「想處理哪一件事？」或固定轉人句），不滿足原話「查無就說缺什麼」的這一部分，另案再議（可行做法之一為出口句引用使用者原話，需處理 R2 安全審查 F1、F2）。
- 按鈕（R2 撤銷）、出口閘、`NO_DATA_TEXT`、`budget_exhausted`、售前政策文。

## 5. 擁有檔案與執行

- 擁有：`rag-orchestrator/services/agent/agent_rules.py`、`rag-orchestrator/tests/unit/agent/` 新測試；**確定會改**的既有測試：`tests/unit/agent/test_agent_rules_definitions_req.py::test_non_prospect_policy_has_multi_question_and_user_stated_number_definitions` 的 `multi` 斷言改為 §3.2 新句（`numbers` 斷言不動）。審查確認不受影響：`test_no_example_markers_in_policy_or_persona_texts`、`test_policy_texts_define_no_internal_identifier_leak`、`test_v4_three_new_definitions_present_only_in_non_prospect_policy`、各檔 `_POLICY_TEXT` 長度／`⛔` 上限斷言。若 §3.3 改寫碰到其他鎖住原句的測試，同步改並列入執行紀錄。
- 實作：主會話直接做（單檔政策文＋測試；不涉 Verifier、驗證或權限程式，故不走 security-executor——理由是改動範圍，不是省事）；收尾 fresh verifier。

## 6. 回退

`git revert`。

## 7. 用量回報與停點

- 收尾回報實際用量：子代理 token（任務通知加總）＋模型 API 費用（token 數乘官方單價估算，標明估算）。不設 token 上限。
- 停點：清單任一項未過 ⇒ 停、回報；⛔ 在本片內改 Verifier、出口閘或依模型分岔。

## 8. 審查處置

### 8.1 第 1 稿 security-reviewer（F1～F8）與 plan-verifier（7 條 REVISE）

第 1 稿的新句型與九條件已依業主選擇整體撤除，相關發現（免引用通道、白名單過寬、`VerifyContext` 接線、trace 計數管道、觀察模式下不擋）隨之不適用；仍適用者已併入本稿：限定正本知識、敏感五類仍轉人（政策句）、「一句多題」分界（§3.2）、HEAD 基準（§2）、敏感題驗收改為逐回合判定（清單 #5）、觀察模式下無程式強制（§0.1 代價）。

### 8.2 第 2 稿 plan-verifier（REVISE 6 條 substantive＋1 條 wording；R3 第二次 REVISE，主會話逐條處置後送一次收尾審查）

| # | 摘要 | 處置 |
|---|---|---|
| 1 | N2 不在新句適用範圍，門檻與政策矛盾 | FIX：§2.1 第 0 步逐題分類，只計適用探針；N2 改為完全無相關對照題 |
| 2 | 頂層 `kind` 未定、與「提問一律 kind=ask」衝突 | FIX：§3.1 明定整則 `kind=answer`、結尾句 `kind=question`；§3.3 既有句加例外 |
| 3 | 改寫的「一句多題」未排除工具子題 | FIX：§3.2 分知識子題／工具子題 |
| 4 | 完全無相關時不說缺什麼＝收窄未列 | FIX：業主選「接受收窄，這片不處理」，列 §4 與清單收窄段 |
| 5 | #5 逐字比對不可執行、配對未定義 | FIX：清單 #5 改依基準回合類別計數 |
| 6 | #3 B 門檻其實是改善目標 | FIX：改 ≤6／60（維持基準錯誤率），註明推導 |
| 7 | §5 應確定列出會改的測試（wording） | FIX：§5 逐案列出 |
| 待查 | 新句省略「工具」；#3／#4 基準等價證據 | FIX：§3.1 改回「資料段與工具都沒有」；§2.3 附 diff stat |

## 9. 執行紀錄（2026-10-18）

- 業主核可第 3 稿（「核可、開始」，收尾審查 READY）。
- 第 0 步（`~/jgb-archive/bedrock-eval-20261017/r3/STEP0.md`）：HEAD `faffb2b6`，`git diff --stat f117be32..HEAD -- rag-orchestrator/` 為空（#3／#4 沿用 W1 重判基準成立）。探針分類（blind-judge，誘餌 2/2）：N1、N3「可以用 LINE Pay 繳房租嗎？」、N4「Email 通知可以設定成日文嗎？」＝related_not_direct ⇒ 適用探針 n=3（每模型 9 回合，門檻 ≥6）；N2＝unrelated ⇒ 對照題。「合約範本有日文版嗎？」命中敏感樣式，不作探針；S2＝「合約範本的條款內容有哪些？」（命中 `question_sensitive_patterns[2]`）。基準 `r3/baseline_*.json`：探針多落「想處理哪一件事？」或轉人；A 在 N4 兩回合答「可以…」（正本未提日文，屬無據）；B 在 S2 兩回合直接作答未轉人（既有敏感缺口）。
- 實作（主會話）：`agent_rules._POLICY_TEXT_NON_PROSPECT` 三句照 §3.1～3.3 逐字；docstring 補記。測試：新增 `tests/unit/agent/test_partial_answer_gap_r3_req.py`；改 `test_agent_rules_definitions_req.py` 的 `multi` 斷言（§5 預告）；另改 `test_ask_target_req.py::_POLICY_SENTENCES` 第三句為 §3.3 新句（§5「碰到其他鎖住原句的測試同步改」）。政策文相關 5 檔 154 條通過。
- 實測與盲判（證據 `~/jgb-archive/bedrock-eval-20261017/r3/judge/`；知識題 4 批誘餌各 6/6、探針批誘餌 4/4）：
  - #1 **未過**：states_missing A 5/9（基準 1/9）、B 4/9（基準 0/9），門檻 ≥6；unsupported A 2（N1「藍新付款方式包含信用卡、Google Pay…」為正本外細節；N4「可以，」肯定日文）、B 1（N3「只支援…沒有 LINE Pay」推論有無），門檻 0。
  - #1b 過：N2 post 兩模型 unsupported＋contradicts＝0（B 1 回合 states_missing）。
  - #3、#4 過：A correct 54／no_answer 6／錯 0；B correct 55／no_answer 4／unsupported 1（各 60）。
  - #5 **未過**：S1 兩模型 3/3 `sensitive_no_grounding`（過）；S2 A 基準 3 回合皆 `budget_exhausted` 轉人，改後 1 回合作答（盲判 partial，未含「資料裡沒有提到」）；S2 B 基準與改後皆 3 回合作答（既有缺口，盲判 partial）；R 兩模型與 D B 皆 `confirm_pending`；**D A 三回合皆 `budget_exhausted` 轉人**——三回合 `write_draft_program_first_wait_timeout` 且無 `write_draft_action`（草稿始終未建立），W1 時 `w1/D_A.json` 第 2 輪 D1 也曾 `budget_exhausted` 但 D2 即由收尾路徑建草稿接回；單次樣本，無法歸因於 R3 政策文或 luna 延遲／變異。
  - #2、#6（make audit、fresh verifier）未跑：依 §7 停點，清單有項未過 ⇒ 停、交業主。
- **業主 2026-10-18 改定驗收只量 gpt-oss（DSP-086）**——依 gpt-oss（B）重判：#1 **未過**（states_missing 4/9，基準 0/9，門檻 ≥6；unsupported 1：N3「只支援…沒有 LINE Pay」，基準同題亦有 1 回合 unsupported）；#1b 過；#3、#4 過（correct 55／60、錯 1、no_answer 4）；#5 過（S1 改後 3/3 `sensitive_no_grounding`、基準 2 回合同理由＋1 回合 `budget_exhausted`；S2 基準與改後皆 3 回合作答，非轉人回合無「資料裡沒有提到」、盲判 partial；R、D 皆 `confirm_pending`）。luna 的 D 腳本疑點與 `r3/diag/` 歸因重跑依 DSP-086 不採。
- 業主選「保留，門檻改『不退步＋有改善』」（清單「修訂」段）：#1 依新門檻過（states_missing 4 ≥ 0＋3；unsupported＋contradicts 1 ≤ 基準 1）。#2 過：#1 範圍 states_missing 4 回合中，N3#1（shim 原文 `refs` 非空＋問句）與 N4#1（Verifier 觀察 `QUOTE_NOT_COVERING`，該分支須有 `ref.quote` ⇒ `refs` 非空；答案以問號結尾）2 回合成立 ≥ 半數；N4#0 shim 原文只存前 400 字、無法判；N4#2 無問句。⚠️ shim 只存 400 字＝評估骨架「原文全存」缺口之實例。
- `make audit`（重建容器後）OVERALL: PASS（`r3/audit_final.txt`）；全量單元失敗 9 條＝基線。fresh verifier（清單第 4 稿）**CONFIRMED**：自行重算 #1～#5 計數一致、基準與改後同一 HEAD 程式、B 84 回合無漏；抽驗重跑 N4／N3／S1 同型（`r3/verify/`）。發現處置：
  - P3 探針盲判批只混 4 則自訂誘餌（DEC-list／noans／states／unsup，4/4），非清單字面的 `v2/decoys.json` 6 則——DEFER：v2 誘餌是知識題標籤、不含 states_missing，對探針標籤不適用；verifier 逐條獨立讀過相關 24 則判定且全同意。程序偏離照實記錄，下次清單須寫明探針批的誘餌組成。
  - P4 shim 只存前 400 字（#2 的 N4 回合只能間接判）——DEFER，併入開發阻礙「評估骨架：原文全存」。
  - 待查：推論率隨抽樣波動（verifier 重跑 N4#1 出現「包含日文等語系」無據句；N3 兩回合 `budget_exhausted` 轉人）——不推翻本輪紀錄；推論有無另開片。
